# 아트메이트 기술 맵 (M1, 발표 자료용)

교재 기술이 아트메이트 코드의 어디에 어떻게 구현되었는지 정리한 문서이다.
기준 커밋 `554c90a` (2026-10-27). 코드 발췌는 실제 코드 그대로이며, 생략한 줄은 `# …`로 표시했다.

| 교재 장 | 기술 | 구현 파일 | 핵심 함수·객체 |
|---|---|---|---|
| 3장 | 멀티턴, 프롬프트 | `app.py`, `artmate/prompts/` | `build_system_prompt`, `lc_history` |
| 4·9장 | PDF 전처리, RAG, 질의 확장 | `scripts/build_index.py`, `artmate/tools/curriculum.py` | `build_chunks`, `search_curriculum` |
| 6장 | 이미지(비전) | `artmate/images.py`, `app.py` | `load_image`, `to_data_url` |
| 7·8장 | 도구 호출, 스트림, 파이단틱 | `artmate/agent.py`, `artmate/quiz.py` | `stream_answer`, `@tool`, `with_structured_output` |
| 10장 | 웹 검색 | `artmate/tools/web.py` | `web_search`, `format_sources` |

---

## 1. 3장 멀티턴·프롬프트

- **구현 파일**: `app.py`, `artmate/prompts/__init__.py`, `base.py`, `school_level.py`, `areas.py`
- **핵심 함수**: `build_system_prompt(school_level)`, 세션 상태 `lc_history`

```python
# artmate/prompts/__init__.py
def build_system_prompt(school_level: str) -> str:
    """base + 학교급 + (M1) 3개 영역 요약."""
    return "\n\n".join([BASE_PROMPT, SCHOOL_LEVEL_PROMPTS[school_level], AREAS_SUMMARY_PROMPT])

# artmate/agent.py
    messages = [SystemMessage(build_system_prompt(school_level)), *history]
```

**동작 원리**
- 시스템 프롬프트를 공통 원칙(base) + 학교급(초등/중등) + 영역 전략 3개 블록으로 조합한다.
- 대화 이력 `lc_history`를 매 턴 통째로 보내 모델이 앞선 대화를 기억하게 한다. 이력에는 학생 질문과 최종 답만 남긴다.
- 학교급을 바꾸면 수준이 섞이지 않도록 대화를 자동 초기화한다.

**데이터 흐름**
학생 입력 → `HumanMessage`로 `lc_history`에 추가 → `[SystemMessage(조합 프롬프트)] + lc_history` → Gemini → 답을 `AIMessage`로 `lc_history`에 추가

---

## 2. 4·9장 PDF 전처리·RAG·질의 확장

### 2-1. PDF 전처리와 청킹 (4장)

- **구현 파일**: `scripts/build_index.py` (1회 실행: `python -m scripts.build_index`)
- **핵심 함수**: `build_chunks`, `parse_code`, `join_lines`, `content_system_chunks`

```python
CODE_RE = re.compile(r"\[(\d)미(0[1-3])-(\d{2})\]")
LEVELS = {"6": "초등", "9": "중등"}  # 4미(3~4학년)는 대상 학교급이 아니므로 제외
AREAS = {"01": "미적 체험", "02": "표현", "03": "감상"}

def build_chunks(pdf_path) -> list[dict]:
    doc = pymupdf.open(pdf_path)
    paras = join_lines([line for page in doc for line in page_lines(page)])
```

**동작 원리**
- pymupdf로 쪽 머리말을 지운 텍스트를 뽑고, 줄바꿈으로 끊긴 낱말을 이어 문단을 복원한다.
- 성취기준 코드(`[6미01-02]`)에서 학교급·영역 메타데이터를 자동으로 뽑고, 해설에 다시 나오는 같은 코드는 한 청크로 합친다.
- 내용 체계 표는 셀 위치로 다시 읽어 3~4학년 열을 버린다. 결과는 청크 55개(성취기준 26, 고려 사항 6, 내용 체계 6, 공통 17)이다.

**데이터 흐름**
교육과정 PDF(23쪽) → 텍스트 추출·문단 복원 → 청크 55개 + 메타데이터(`school_level`, `area`, `code`, `chunk_type`, `section`) → `data/processed/chunks.json` + Gemini 임베딩(배치 2회 요청) → Chroma(`data/chroma/`, 코사인 거리)

### 2-2. RAG 검색 (9장)

- **구현 파일**: `artmate/tools/curriculum.py`
- **핵심 함수**: `search_curriculum(query, school_level, area)`

```python
    conditions = [{"school_level": school_level}]
    if area:
        conditions.append({"area": area})
    flt = conditions[0] if len(conditions) == 1 else {"$and": conditions}
    docs = get_db().similarity_search(query, k=config.RAG_TOP_K, filter=flt)
    # …
    content = "\n\n".join(CODE_RE.sub("", d.page_content) for d in docs)
```

**동작 원리**
- 검색어를 임베딩해 Chroma에서 가장 가까운 청크 4개를 찾는다. 이때 선택한 학교급으로만 거르며, 공통 청크는 뺀다.
- 중등 모드에서는 초등 성취기준이 구조적으로 검색되지 않는다(S8).
- 모델에는 성취기준 코드를 지운 본문만 넘기고(P2), 코드는 동작 보기 패널에만 보낸다.

**데이터 흐름**
모델이 만든 검색어 + 세션의 학교급 → 질의 임베딩(1회 요청) → Chroma 메타데이터 필터 + 유사도 검색 top-4 → (코드 제거 본문 → 모델) / (코드 목록 → 동작 보기)

### 2-3. 질의 확장 (9장)

- **구현 파일**: `artmate/tools/curriculum.py` (도구 설명 docstring)

```python
    query: 학생 표현을 그대로 쓰지 말고 교육과정 용어로 바꿔 쓴다.
      예) 명암 → 조형 요소, 비평 → 감상, 색 섞기 → 표현 재료와 방법,
          그림 설명하기 → 작품의 내용과 형식 분석, 아이디어 떠올리기 → 발상
```

**동작 원리**
- 교육과정 PDF에는 '명암'이라는 낱말이 한 번도 나오지 않아, 학생 표현 그대로 검색하면 근거를 찾지 못한다.
- 도구 설명에 변환 규칙을 적어 두어, 모델이 도구 인자를 만들 때 교육과정 용어로 바꿔 검색하게 한다.
- 별도 LLM 호출이 없어 API 호출 수가 늘지 않는다.

**데이터 흐름**
"명암이 뭐예요?" → 모델이 도구 인자를 생성(`query='명암 조형 요소 표현'`, 실제 호출 기록) → `search_curriculum` → 결과 `9미02-03`, `내용 체계·표현` 등

---

## 3. 6장 이미지(비전)

- **구현 파일**: `artmate/images.py`, `app.py`
- **핵심 함수**: `load_image(file)`, `to_data_url(img)`, `on_image_upload()`

```python
# artmate/images.py — 검증 뒤 회전 보정·축소, 전송 직전 JPEG base64 데이터 URL로 변환
    img = ImageOps.exif_transpose(img)  # 휴대폰 사진 회전 보정
    img.thumbnail((config.IMAGE_MAX_SIDE, config.IMAGE_MAX_SIDE))
    # …
    img.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
```

`app.py`에서는 업로드한 이미지를 바로 다음 메시지 1회에만 첨부한다.

```python
    image = st.session_state.pending_image
    st.session_state.pending_image = None
    # …
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": images.to_data_url(image)},
        ]
    st.session_state.lc_history.append(HumanMessage(content))
```

**동작 원리**
- 업로드 단계에서 형식·크기를 검증하고 긴 변 1024px로 줄여 토큰과 전송 시간을 아낀다.
- 이미지는 파일로 저장하지 않고 세션 메모리(PIL 객체)에만 둔다. 다음 질문 1회에 텍스트와 함께 멀티모달 메시지로 묶는다.
- 랭체인이 데이터 URL을 Gemini 요청의 이미지 파트로 바꿔 전송하고, Gemini가 이미지와 질문을 함께 읽어 답한다.

**업로드부터 Gemini 전달까지 단계별 흐름**

| 단계 | 위치 | 하는 일 | 결과 |
|---|---|---|---|
| 1. 선택 | `app.py` `st.file_uploader` | `type=["jpg","jpeg","png"]`로 선택 창을 거르고, `max_upload_size=5`로 5MB를 넘는 파일은 브라우저 단계에서 거부한다(NFR-09). | 업로드 파일(`UploadedFile`, 메모리 내 바이트) |
| 2. 이벤트 | `app.py` `on_image_upload` | 업로더 값이 바뀔 때만 실행된다. 파일을 지우면 첨부 대기 이미지도 지운다. | 검증 함수 호출 |
| 3. 크기 검증 | `images.load_image` | 바이트 수가 5MB를 넘으면 학생용 안내 문구로 `ValueError`를 낸다(서버 쪽 이중 확인). | 통과 또는 오류 문구 |
| 4. 형식 검증 | `images.load_image` | `Image.open`으로 실제 파일 형식을 읽어 JPEG/PNG만 통과시킨다. 확장자만 바꾼 파일도 거른다. | PIL 이미지 |
| 5. 회전 보정 | `ImageOps.exif_transpose` | 휴대폰 사진의 EXIF 회전 정보를 적용해 똑바로 세운다. | 바로 선 이미지 |
| 6. 축소 | `img.thumbnail` | 비율을 유지하며 긴 변을 1024px 이하로 줄인다. | 최대 1024px 이미지 |
| 7. 배경 처리 | `convert("RGBA")` → 흰 RGB에 `paste` | 투명 PNG의 투명 부분을 흰색으로 채워 JPEG로 보낼 수 있게 한다. | RGB 이미지 |
| 8. 세션 보관 | `current_image`, `pending_image` | 파일·DB에 저장하지 않고 세션 메모리에만 둔다(NFR-02). 사이드바에 "다음 질문에 이 이미지가 함께 전달돼요."를 표시한다. | 첨부 대기 상태 |
| 9. 첨부 | `app.py` 채팅 입력 처리 | 학생이 질문을 보내면 `pending_image`를 꺼내고 비운다. 1회만 첨부된다. | 이번 질문의 이미지 |
| 10. 인코딩 | `images.to_data_url` | JPEG(품질 85)로 다시 저장해 base64로 인코딩한다. 다시 저장하므로 위치 정보 등 EXIF가 빠진다. | `data:image/jpeg;base64,…` |
| 11. 메시지 구성 | `HumanMessage(content)` | 텍스트 파트와 `image_url` 파트를 가진 멀티모달 메시지를 `lc_history`에 넣는다. 화면에는 240px 썸네일을 표시한다. | 멀티모달 `HumanMessage` |
| 12. 전송 | `agent.stream_answer` → `ChatGoogleGenerativeAI.stream` | `[SystemMessage] + lc_history`를 보낸다. `langchain-google-genai`가 데이터 URL을 Gemini 요청의 이미지 데이터 파트로 바꾼다. | Gemini가 이미지+질문을 함께 읽음 |
| 13. 이후 턴 | `lc_history` | 이미지가 든 메시지가 이력에 남아 다음 턴에도 함께 전송된다. 그래서 이미지 맥락이 유지되지만 매 턴 토큰을 쓴다. | 이미지 맥락 유지 |

실패 처리: 답 생성이 실패하면 질문을 이력에서 빼고 `pending_image`를 되돌려 다시 보낼 수 있게 한다. 퀴즈 출제에는 이미지 대신 "(이미지를 함께 올림)" 표시만 넘긴다.

---

## 4. 7·8장 도구 호출·스트림·파이단틱

### 4-1. 도구 정의 (`@tool`, 8장)

- **구현 파일**: `artmate/tools/curriculum.py`, `artmate/tools/web.py`
- **핵심**: `@tool(response_format="content_and_artifact")`, `InjectedToolArg`

```python
@tool(response_format="content_and_artifact")
def search_curriculum(
    query: str,
    school_level: Annotated[str, InjectedToolArg],
    area: Literal["미적 체험", "표현", "감상"] | None = None,
) -> tuple[str, list[str]]:
```

**동작 원리**
- docstring이 모델이 읽는 도구 사용 설명서가 되고, 타입 힌트가 인자 스키마가 된다(`area`는 3개 값만 허용).
- `school_level`은 `InjectedToolArg`라서 모델 스키마에 나타나지 않는다. 에이전트가 세션 상태에서 주입하므로 학생 대화로 학교급을 바꿀 수 없다.
- 반환값은 (모델용 본문, artifact)로 나뉜다. artifact(코드·URL)는 모델에 가지 않고 동작 보기와 출처 첨부에만 쓴다.

### 4-2. 도구 호출 루프와 스트림 (7·8장)

- **구현 파일**: `artmate/agent.py`, `app.py`
- **핵심 함수**: `stream_answer(history, school_level, calls)`, `llm.bind_tools`, `st.write_stream`

```python
        for chunk in model.stream(messages):
            response = chunk if response is None else response + chunk
            if chunk.text:
                yield chunk.text
        if not response.tool_calls:
            # …
            return
        messages.append(response)
```

**동작 원리**
- `bind_tools`로 도구 2개를 알려 주고, 매 라운드 응답을 스트림으로 받아 청크를 합친다. 도구 호출이 있으면 실행 결과(`ToolMessage`)를 붙여 다시 호출한다.
- 도구 호출이 없으면 이미 흘러나온 글자가 곧 최종 답이다. 최종 답만 받으려고 따로 호출하지 않는다.
- 도구 라운드는 최대 3회이고, 상한에 도달하면 `tool_choice="none"`으로 답을 마무리한다. `app.py`는 `st.write_stream`으로 글자를 바로 화면에 흘린다.

**데이터 흐름**
`[System] + 이력` → Gemini(도구 목록 포함) → 도구 호출 요청 → 도구 실행(학교급 주입) → `ToolMessage` 추가 → Gemini → 최종 답 글자 스트림 → (웹 검색을 했으면 출처 줄 추가) → 화면 + `lc_history`, 호출 내역 → 동작 보기 패널

### 4-3. 파이단틱 구조화 출력 (8장)

- **구현 파일**: `artmate/quiz.py`
- **핵심 함수**: `make_quiz(messages, school_level)`, `QuizItem`, `Quiz`

```python
class QuizItem(BaseModel):
    question: str = Field(description="문항")
    options: list[str] = Field(min_length=4, max_length=4, description="선택지 4개")
    answer_index: int = Field(ge=0, le=3, description="정답 선택지 번호(0~3)")
    explanation: str = Field(description="대화 내용을 근거로 한 1~2문장 해설")
# …
    quiz = get_chat_model().with_structured_output(Quiz).invoke([
```

**동작 원리**
- 파이단틱 모델의 제약(문항 2~3개, 선택지 4개, 정답 0~3)이 JSON 스키마로 Gemini에 전달되고, 응답을 파싱할 때 다시 검증된다.
- 화면 대화 기록만 넘겨 대화에서 다룬 관찰·감상 내용으로만 출제하게 하고, 학교급별 출제 지침을 붙인다.
- 학생 질문이 2개 미만이면 API를 호출하지 않고 안내만 띄운다.

**데이터 흐름**
"확인 퀴즈 만들기" 버튼 → 대화 기록을 "학생: … / 아트메이트: …" 텍스트로 정리 → Gemini 구조화 출력(1회) → `Quiz` 객체 → `st.radio` 풀이 → 선택 즉시 정답 여부·해설

---

## 5. 10장 웹 검색

- **구현 파일**: `artmate/tools/web.py`, `artmate/agent.py`
- **핵심 함수**: `web_search(query)`, `_search`, `site_name`, `format_sources`

```python
        results = [(r, "신뢰 도메인") for r in _search(query, list(TRUSTED_DOMAINS))]
        # 신뢰 도메인 결과가 부족하면 도메인 제한 없이 1회 재검색해 남은 자리를 채운다
        if len(results) < config.WEB_MIN_TRUSTED:
            seen = {r["url"] for r, _ in results}
            extra = [r for r in _search(query, None) if r["url"] not in seen]
            results += [(r, "일반 재검색") for r in extra[: config.WEB_MAX_RESULTS - len(results)]]
```

**동작 원리**
- 타빌리 `include_domains`로 신뢰 도메인 6곳(국립현대미술관, 국립중앙박물관, 한국민족문화대백과 등)을 먼저 검색한다. 결과가 2개 미만이면 제한 없이 1회 다시 검색해 최대 3개를 채운다.
- 작가·작품·시대 배경은 모델이 알고 있어도 이 도구로 확인한 뒤 답하도록 프롬프트와 도구 설명에 적었다.
- 출처는 모델이 쓰지 않고, 에이전트가 답 끝에 `출처: [사이트명](링크)`를 붙인다. 같은 사이트는 첫 링크 하나만 쓴다.

**데이터 흐름**
"이 그림은 누가 그렸어요?" → 모델이 `web_search(query)` 호출 → 타빌리 신뢰 도메인 검색(필요시 일반 재검색) → (제목·사이트명·요약 → 모델) / (`[신뢰 도메인]`·`[일반 재검색]` 구분 + URL → 동작 보기·출처 줄) → 답 + "출처: [한국민족문화대백과](…)"

---

## 6. 프로젝트 폴더 트리

```
26_mobilecomputing_midterm_project/
├─ app.py                     # 스트림릿 진입점 (UI, 이미지 첨부, 퀴즈 풀이, 동작 보기)
├─ README.md                  # 실행 방법
├─ CLAUDE.md                  # 개발 원칙
├─ spec.md / design.md / tasks.md
├─ requirements.txt           # 사용 패키지 버전 고정
├─ .env.example               # 키 이름만 (실제 키는 .env, git 제외)
├─ .streamlit/config.toml     # Deploy 버튼 숨김
├─ artmate/
│  ├─ config.py               # 모델명, 경로, 상수
│  ├─ llm.py                  # Gemini 채팅·임베딩 객체
│  ├─ agent.py                # 도구 호출 루프 + 스트림 (7·8장)
│  ├─ images.py               # 이미지 검증·축소·인코딩 (6장)
│  ├─ quiz.py                 # 파이단틱 구조화 출력 퀴즈 (8장)
│  ├─ prompts/
│  │  ├─ base.py              # 공통 원칙 (3장)
│  │  ├─ school_level.py      # 초등/중등 지침
│  │  ├─ areas.py             # 미적 체험·표현·감상 전략
│  │  └─ quiz.py              # 퀴즈 출제 지침
│  └─ tools/
│     ├─ curriculum.py        # search_curriculum (9장)
│     └─ web.py               # web_search (10장)
├─ scripts/
│  └─ build_index.py          # PDF → 청크 → Chroma (4·9장)
├─ tests/
│  └─ test_chunking.py        # 코드 추출·학교급·영역 판정, 청크 수 검증
└─ data/
   ├─ raw/교육과정.pdf         # git 제외
   ├─ processed/chunks.json   # 청크 55개 (검토용)
   └─ chroma/                 # 벡터 DB (git 제외)
```

---

## 7. 시연 흐름(S5 → S6 → 퀴즈)의 API 호출 수

- **채팅**은 Gemini 응답 생성 요청이다. 도구를 쓰지 않는 턴은 1회, 도구 라운드가 1번 있는 턴은 2회이며, 한 턴의 최대는 4회(도구 라운드 3 + 마무리 1)이다.
- **임베딩**은 `search_curriculum`을 부를 때마다 질의 임베딩 1회가 든다.
- **타빌리**는 `web_search` 1회당 1회이고, 신뢰 도메인 결과가 2개 미만이면 2회이다.
- 실제 횟수는 모델이 도구를 부르는지에 따라 달라지므로 아래는 예상값이다. 앱 시작과 퀴즈 풀이(답 고르기)는 API를 쓰지 않는다. 인덱스 구축(임베딩 2회)은 시연 전에 1회만 한다.

| 단계 | 학생 행동 (예) | 채팅 | 임베딩 | 타빌리 |
|---|---|---|---|---|
| S5-1 | 작품 이미지 업로드 + "이 그림 같이 감상해 볼래?" | 1~2 | 0~1 | 0 |
| S5-2 | "아이들이 둥글게 앉아 있어요." (기술) | 1 | 0 | 0 |
| S5-3 | "가운데 아이가 울고 있어서 재미있어요." (분석·해석) | 1 | 0 | 0 |
| S6 | "이 그림은 누가 그렸어요? 어느 시대예요?" | 2 | 0~1 | 1~2 |
| 퀴즈 | "확인 퀴즈 만들기" 버튼 | 1 | 0 | 0 |
| **합계** | | **6~7** | **0~2** | **1~2** |

- 개발 중 확인한 무료 한도는 `gemini-3.5-flash`가 하루 약 20회, 개발 기본값인 `gemini-3.5-flash-lite`가 하루 약 500회였다. 리허설은 flash-lite로 하고, 본 시연을 flash로 한다면 한 번 흐름에 하루 한도의 3분의 1 정도를 쓰는 셈이다.
- S5에서 학생 답이 짧거나 모델이 턴마다 교육과정 검색을 하면 채팅이 턴당 2회로 늘 수 있다. 시연 전 리허설에서 "에이전트 동작 보기"로 실제 횟수를 확인하는 것이 좋다.
