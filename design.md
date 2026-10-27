# design.md — 아트메이트(ArtMate) 설계서

| 항목 | 내용 |
|---|---|
| 대응 명세 | `spec.md` v0.2 |
| 문서 버전 | v0.3 (초안) |
| 작성일 | 2026-10-26 |
| 상태 | 검토 중 |

> 이 문서는 `spec.md`의 요구사항을 **어떻게 구현하는가(How)**를 정의한다. 구현 순서와 단위 작업은 `tasks.md`에서 정의한다.

---

## 0. 문서 운영 원칙 (Living Document)

1. `spec.md`, `design.md`, `tasks.md`는 **개발 중 변경될 수 있는 살아 있는 문서**이다.
2. 변경은 항상 **spec → design → tasks → 코드** 순서로 반영한다. 코드만 바꾸고 문서를 두지 않는다.
3. 변경이 생기면 각 문서 하단의 **변경 이력**에 날짜, 내용, 사유를 한 줄로 기록한다.
4. 구현 중 설계와 다른 판단이 필요하면, 구현을 멈추고 이 문서의 해당 절을 먼저 수정한다.

---

## 1. 개발 원칙: Streamlit 점진적 누적 구현

| 원칙 | 내용 |
|---|---|
| 항상 실행 가능 | 모든 단계가 끝날 때마다 `streamlit run app.py`로 실행되고 화면에서 결과를 확인할 수 있어야 한다. |
| 기능 단위 누적 | 한 단계에서 한 가지 기능만 추가한다. 이전 단계 기능은 깨지지 않아야 한다. |
| 눈에 보이는 확인 | 각 단계는 화면에서 확인 가능한 **확인 포인트**를 가진다(`tasks.md`에 명시). |
| 동작 과정 표시 | 사이드바의 **"에이전트 동작 보기"** 패널에 라우팅 결과, 도구 호출, 마스킹 여부를 표시한다. 개발 중 확인과 발표 시연에 모두 활용한다. |
| 교체 가능한 구조 | M1의 프롬프트·도구 모듈은 M2에서 수정 없이 재사용되도록 UI와 분리한다. |

---

## 2. 기술 스택

| 구분 | 선택 | 비고 |
|---|---|---|
| 언어 | Python 3.11 이상 | Windows, venv |
| UI | `streamlit` | 채팅 UI, 사이드바, 스트림 출력 |
| LLM 연동 | `langchain`, `langchain-google-genai` | `ChatGoogleGenerativeAI` |
| 그래프 | `langgraph` | M2 |
| 채팅 모델 | Gemini Flash-Lite 계열 stable 모델 (기본값 `gemini-3.5-flash-lite`) | `.env`의 `GEMINI_MODEL`로 교체 가능 (`gemini-3.5-flash` 등) |
| 임베딩 | `gemini-embedding-001` | `GoogleGenerativeAIEmbeddings` |
| 벡터 DB | `chromadb`, `langchain-chroma` | 로컬 저장 |
| PDF 처리 | `pymupdf` | 교육과정 PDF 텍스트 추출 |
| 웹 검색 | `langchain-tavily` | `TavilySearch` |
| 로컬 sLLM | 올라마 + `langchain-ollama` | M2 |
| 이미지 처리 | `pillow`, `scikit-learn` | 리사이즈, KMeans 색상 추출 |
| 설정 | `python-dotenv`, `pydantic` | 환경 변수, 구조화 출력 |
| 테스트 | `pytest` | 정규식, 청킹 등 결정적 로직만 |

**모델 선정 근거 (OI-01)**: 이 프로젝트는 응답 속도와 비용이 중요하고, 이미지 입력과 도구 호출을 모두 지원해야 하므로 Flash 계열을 사용한다. 개발 중에는 무료 사용량 한도(Flash 하루 약 20회)로 점검이 막혀 **Flash-Lite를 기본값**으로 쓰고, 응답 품질 비교나 시연 때는 `.env`에서 `gemini-3.5-flash`로 바꿀 수 있다. 모델명은 설정값으로 분리해 둔다.

---

## 3. 디렉터리 구조

```
artmate/
├─ app.py                      # Streamlit 진입점 (UI만 담당)
├─ CLAUDE.md
├─ spec.md / design.md / tasks.md
├─ .env.example                # 키 이름만 기재, 실제 키는 .env
├─ requirements.txt
├─ data/
│  ├─ raw/                     # 교육과정 PDF (사용자가 배치)
│  ├─ processed/               # 추출 텍스트, 청크 JSON
│  └─ chroma/                  # 벡터 DB (git 제외)
├─ scripts/
│  └─ build_index.py           # PDF → 청크 → 벡터 DB 구축 (1회 실행)
├─ artmate/
│  ├─ config.py                # 모델명, 경로, 상수
│  ├─ llm.py                   # Gemini 채팅·임베딩 객체 생성
│  ├─ prompts/
│  │  ├─ base.py               # 공통 원칙 P1~P6
│  │  ├─ school_level.py       # 초등/중등 어휘·수준 지침
│  │  └─ areas.py              # 미적 체험·표현·감상 지침 (M2에서 분리 사용)
│  ├─ tools/
│  │  ├─ curriculum.py         # search_curriculum
│  │  ├─ web.py                # web_search
│  │  └─ palette.py            # extract_color_palette (M2)
│  ├─ agent.py                 # M1: 단일 에이전트 (도구 호출 루프)
│  ├─ quiz.py                  # 퀴즈 구조화 출력
│  ├─ images.py                # 이미지 검증·리사이즈·인코딩
│  ├─ guard.py                 # M2: 정규식 + sLLM 마스킹
│  └─ graph.py                 # M2: 랭그래프 오케스트레이션
└─ tests/
   ├─ test_chunking.py
   └─ test_guard_regex.py
```

`.gitignore`에는 `.env`, `data/chroma/`, `data/raw/`, `venv/`를 포함한다.

---

## 4. 설정 (`config.py`, `.env`)

```
# .env.example
GOOGLE_API_KEY=
TAVILY_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite
EMBEDDING_MODEL=gemini-embedding-001
OLLAMA_MODEL=          # M2에서 확정
```

| 상수 | 값 | 근거 |
|---|---|---|
| `MAX_IMAGE_MB` | 5 | 업로드 제한 (OI-06) |
| `IMAGE_MAX_SIDE` | 1024 px | 전송 전 리사이즈로 토큰·속도 절감 |
| `RAG_TOP_K` | 4 | 근거 검색 결과 수 |
| `MAX_TOOL_ROUNDS` | 3 | M1 도구 호출 루프 상한 |
| `MAX_SUPERVISOR_CALLS` | 2 | M2 재호출 상한 (NFR-06) |
| `PALETTE_COLORS` | 5 | 색상 팔레트 개수 |

---

## 5. RAG 설계 (`search_curriculum`)

### 5.1 원자료
국가교육과정정보센터(NCIC)에서 내려받은 **2022 개정 미술과 교육과정 PDF**를 `data/raw/`에 둔다.

### 5.2 청킹 전략 (OI-03)
교육과정 문서는 성취기준 코드가 규칙적이므로, **성취기준 단위 청킹**을 기본으로 한다.

| 청크 유형 | 분할 기준 | 내용 |
|---|---|---|
| 성취기준 청크 | `[6미01-01]`, `[9미02-03]` 형태의 코드 | 성취기준 문장 + 바로 뒤의 해설·고려 사항 |
| 일반 청크 | 장·절 제목 | 성격, 목표, 내용 체계 등 (약 800자 단위, 100자 중첩) |

### 5.3 메타데이터
성취기준 코드에서 자동으로 추출한다.

| 필드 | 추출 규칙 | 예 |
|---|---|---|
| `school_level` | 코드 앞자리 `6` → 초등, `9` → 중등 | `[6미03-02]` → 초등 |
| `area` | 영역 번호 `01` → 미적 체험, `02` → 표현, `03` → 감상 | `[9미02-01]` → 표현 |
| `code` | 성취기준 코드 원문 | `6미03-02` |
| `chunk_type` | `standard` / `general` | |

일반 청크는 해당 절의 학교급을 따르며, 판단할 수 없으면 `school_level="공통"`, `area="공통"`으로 둔다. 영역 번호와 영역명의 대응은 PDF에서 확인한 뒤 확정한다(OI-05와 함께 검증).

### 5.4 검색
- 검색 시 `school_level ∈ {선택 학교급, 공통}` 필터를 적용한다(S8).
- `area`가 주어지면 `area ∈ {해당 영역, 공통}` 필터를 추가한다.
- 결과는 학생에게 직접 노출하지 않고, 에이전트의 응답 근거로만 사용한다(P2).

### 5.5 구축 절차
`scripts/build_index.py`를 1회 실행해 `data/processed/chunks.json`과 `data/chroma/`를 만든다. 청크 JSON을 남겨 두면 청킹 결과를 눈으로 검토할 수 있다.

---

## 6. 도구 설계

모든 도구는 랭체인 `@tool` 데코레이터로 정의하고, 독스트링을 **에이전트가 읽는 사용 설명서**로 작성한다.

```python
@tool
def search_curriculum(query: str, area: str | None = None) -> str:
    """2022 개정 미술과 교육과정에서 관련 내용을 검색한다.
    학생 질문에 답하기 전, 학교급에 맞는 학습 내용과 수준을 확인할 때 사용한다.
    area: '미적 체험' | '표현' | '감상' (선택)"""

@tool
def web_search(query: str) -> str:
    """작가, 작품, 미술사적 배경, 표현 기법 등 교육과정 문서에 없는
    사실 정보를 신뢰할 수 있는 사이트에서 검색한다. 결과에는 출처가 포함된다."""

@tool
def extract_color_palette(n_colors: int = 5) -> str:   # M2
    """학생이 올린 이미지의 주요 색상과 비율을 추출한다.
    색에 관한 대화를 할 때 사용한다."""
```

| 도구 | 구현 요점 |
|---|---|
| `search_curriculum` | 학교급은 인자가 아니라 **세션 상태에서 주입**한다(학생 대화로 학교급이 바뀌지 않도록). |
| `web_search` | 타빌리 `include_domains`로 신뢰 도메인 우선 검색(아래 목록). 결과가 부족하면 도메인 제한 없이 1회 재검색한다. 결과 요약에 제목과 URL을 포함한다. |
| `extract_color_palette` | 세션에 저장된 현재 이미지를 Pillow로 축소한 뒤 KMeans로 군집화한다. 결과는 HEX 코드와 비율 문자열로 반환하고, UI는 이를 색상 칩으로 렌더링한다. |

**신뢰 도메인 목록 (OI-04)**: `mmca.go.kr`(국립현대미술관), `museum.go.kr`(국립중앙박물관), `emuseum.go.kr`(e뮤지엄), `encykorea.aks.ac.kr`(한국민족문화대백과), `ko.wikipedia.org`, `artsandculture.google.com`. 구현 중 검색 품질을 보고 조정한다.

---

## 7. 프롬프트 설계

시스템 프롬프트는 **조합식**으로 만든다.

```
시스템 프롬프트 = base (P1~P6 공통 원칙)
              + school_level[초등 | 중등]
              + (M1) 3개 영역 지침 요약  /  (M2) 해당 영역 에이전트 지침 전체
```

| 블록 | 핵심 내용 |
|---|---|
| base | 아트메이트의 정체성, 발문 중심, 강점 우선 피드백, 성취기준 비노출, 출처 제시, 개인정보 요청 금지, 서식 규칙(굵게 표시 안에 따옴표 금지) |
| 초등 | 짧은 문장, 쉬운 낱말, 한 번에 질문 1개, 친근한 존댓말 |
| 중등 | 미술 용어 사용, 개념 간 연결, 한 번에 질문 1~2개 |
| 미적 체험 | 관찰 → 발견 → 느낌 표현 순서의 발문 |
| 표현 | 주제 탐색 → 발상 → 계획 → 제작 → 성찰 단계 인식 |
| 감상 | 펠드만 4단계, 현재 단계를 기억하고 순서대로 진행 |

프롬프트는 코드와 분리된 파이썬 상수로 관리해, 문구 수정 시 로직을 건드리지 않도록 한다.

---

## 8. M1 아키텍처: 랭체인 단일 에이전트

### 8.1 처리 흐름
```
app.py (입력 수신)
  → images.py (이미지 검증·리사이즈·base64)
  → agent.py
      1) 메시지 구성: [SystemMessage] + 대화 이력 + [HumanMessage(text, image)]
      2) llm.bind_tools([search_curriculum, web_search])
      3) 도구 호출 루프 (최대 MAX_TOOL_ROUNDS)
      4) 최종 응답 스트림 출력
  → app.py (화면 출력, 동작 로그 기록)
```

### 8.2 구현 방식 선택
교재 8장의 방식과 같이 `bind_tools`와 **직접 작성한 도구 호출 루프**를 사용한다. 이 방식은 동작이 투명해 디버깅과 발표 설명이 쉽고, M2에서 같은 도구를 랭그래프 노드로 옮기기 쉽다.

### 8.3 이미지 메시지
```python
HumanMessage(content=[
    {"type": "text", "text": user_text},
    {"type": "image_url", "image_url": f"data:image/jpeg;base64,{b64}"},
])
```
- 이미지는 업로드 직후 **다음 메시지 1회에만** 첨부하고, 이후에는 대화 이력에 포함된 형태로 맥락을 유지한다.
- 현재 이미지는 `st.session_state.current_image`에 보관해 M2의 색상 추출 도구가 참조한다.

### 8.4 확인 퀴즈 (FR-08)
도구가 아닌 **버튼 기반 구조화 출력**으로 단순화한다.
```python
class QuizItem(BaseModel):
    question: str
    options: list[str]      # 4개
    answer_index: int
    explanation: str

class Quiz(BaseModel):
    items: list[QuizItem]   # 2~3문항
```
사이드바의 "확인 퀴즈 만들기" 버튼을 누르면 최근 대화를 바탕으로 `llm.with_structured_output(Quiz)`를 호출하고, `st.radio`로 풀이 화면을 렌더링한다.

---

## 9. M2 아키텍처: 랭그래프 오케스트레이션

### 9.1 상태
```python
class ArtState(TypedDict):
    messages: Annotated[list, add_messages]
    school_level: Literal["초등", "중등"]
    masked: bool                     # 이번 입력에서 마스킹 발생 여부
    next_agent: str                  # supervisor 판단 결과
    supervisor_calls: int            # 재호출 횟수
    trace: list[str]                 # "에이전트 동작 보기" 표시용 로그
```

### 9.2 그래프
```
START → guard → supervisor ─┬→ aesthetic   (미적 체험)
                            ├→ expression  (표현)
                            ├→ appreciation(감상)
                            └→ END         ('FINISH' 또는 상한 도달)
         aesthetic / expression / appreciation → supervisor
```

| 노드 | 동작 |
|---|---|
| guard | 정규식 마스킹 → sLLM 탐지·마스킹 → `masked` 기록 |
| supervisor | `with_structured_output(Route)`로 다음 에이전트 결정. 일반 질문은 가장 가까운 영역 에이전트로 보낸다. |
| 영역 에이전트 3개 | 각 영역 지침 + 해당 도구로 응답. M1의 도구 호출 루프를 그대로 재사용 |

```python
class Route(BaseModel):
    next: Literal["aesthetic", "expression", "appreciation", "FINISH"]
    reason: str
```
- supervisor는 첫 호출에서 반드시 에이전트 하나를 고른다.
- 에이전트 응답 후 재호출 시, 요청이 충족되었으면 `FINISH`를 고른다.
- `supervisor_calls >= MAX_SUPERVISOR_CALLS`이면 무조건 종료한다.

### 9.3 영역별 도구 배정

| 에이전트 | 도구 |
|---|---|
| 미적 체험 | search_curriculum, extract_color_palette |
| 표현 | search_curriculum, web_search |
| 감상 | search_curriculum, web_search |

### 9.4 메모리
랭그래프 `MemorySaver`(인메모리)와 세션별 `thread_id`를 사용한다. 앱을 종료하면 대화가 사라지며, 이는 NFR-02의 의도와 일치한다.

---

## 10. 개인정보 보호 설계 (M2, `guard.py`)

### 10.1 1단: 정규식 마스킹

| 대상 | 치환 |
|---|---|
| 휴대전화·전화번호 | `[전화번호]` |
| 이메일 | `[이메일]` |
| 주소(시·구·동·로·길 + 번지 패턴) | `[주소]` |
| 학교명(`○○초`, `○○초등학교`, `○○중`, `○○중학교`) | `[학교]` |

### 10.2 2단: sLLM 탐지
- 정규식을 통과한 텍스트를 올라마 모델에 전달하고, **사람 이름 등 개인 식별 표현 목록을 JSON으로 반환**하게 한다.
- 반환된 표현을 원문에서 `[이름]` 등으로 치환한다.
- 작가 이름(예: 김홍도, 고흐)은 개인정보가 아니므로 마스킹하지 않도록 프롬프트에 예시를 둔다.

### 10.3 sLLM 후보와 선정 방법 (OI-02)
RTX 2080(VRAM 8GB)에서 실행 가능한 **3B~8B급 4비트 양자화 모델** 중 한국어 처리가 가능한 모델을 후보로 둔다.

| 후보 계열 | 비고 |
|---|---|
| EXAONE 계열 (LG AI연구원) | 한국어 특화 |
| Qwen 계열 | 다국어, 지시 이행 성능 |
| Gemma 계열 | Gemini와 같은 계열의 오픈 모델 |

**선정 방법**: S7 유형의 테스트 문장 10개(이름·학교·작가명 혼합)로 탐지 정확도와 응답 시간을 비교해 1개를 선택한다. 정확한 태그명은 올라마 라이브러리에서 확인한다.

### 10.4 장애 대비
올라마가 실행되지 않으면 1단 정규식만 적용하고, "에이전트 동작 보기"에 경고를 표시한다. 앱은 중단되지 않는다.

---

## 11. 화면 설계 (`app.py`)

```
┌ 사이드바 ─────────────────┐  ┌ 메인 ──────────────────────────────┐
│ 🎨 아트메이트               │  │ 안내 문구 (첫 화면)                  │
│ 학교급: (●) 초등 ( ) 중등   │  │ [대화 메시지들]                      │
│ 이미지 업로드               │  │   - 업로드 이미지 썸네일              │
│  ※ 얼굴·이름표 사진 금지    │  │   - 색상 칩 (M2)                    │
│ [확인 퀴즈 만들기]          │  │   - 출처 링크                        │
│ [대화 초기화]              │  │ [퀴즈 풀이 영역]                     │
│ ▸ 에이전트 동작 보기        │  │ [채팅 입력창]                        │
│   - 라우팅, 도구 호출, 마스킹│  │                                     │
└────────────────────────┘  └─────────────────────────────────────┘
```

| 세션 상태 키 | 용도 |
|---|---|
| `messages` | 화면 표시용 대화 기록 |
| `lc_history` | 모델 전달용 랭체인 메시지 |
| `school_level` | 학교급 |
| `current_image` | 현재 이미지(PIL 객체) |
| `pending_image` | 다음 메시지에 첨부할 이미지 |
| `trace` | 동작 로그 |
| `quiz` | 생성된 퀴즈 |

- 학교급을 바꾸면 대화를 초기화할지 묻지 않고 **자동 초기화**한다(수준이 섞이는 것을 방지).
- 이미지는 JPG/PNG, 5MB 이하만 허용한다.

---

## 12. 오류 처리

| 상황 | 처리 |
|---|---|
| API 키 없음 | 시작 시 안내 메시지 표시 후 입력 비활성화 |
| Gemini 호출 실패·사용량 초과 | 친절한 재시도 안내 메시지, 동작 로그에 오류 기록 |
| 벡터 DB 없음 | `build_index.py` 실행 안내 표시, 도구는 "근거 없음"을 반환하고 대화는 계속 |
| 타빌리 실패 | 도구가 "검색 실패"를 반환, 에이전트는 확인된 정보만으로 답하도록 지시 |
| 올라마 미실행 | 10.4 참조 |

---

## 13. 검증 방법

| 대상 | 방법 |
|---|---|
| 정규식, 청킹, 메타데이터 추출 | `pytest` 자동 테스트 |
| 시나리오 S1~S8 | `spec.md`의 인수 기준 체크리스트로 화면에서 수동 확인 |
| 도구 호출 여부 | "에이전트 동작 보기" 패널로 확인 |

LLM 응답 품질은 자동 테스트하지 않는다. 각 단계 종료 시 관련 시나리오를 화면에서 1회 이상 실행해 확인한다.

---

## 14. 미결 사항 처리 현황

| ID | 내용 | 결정 |
|---|---|---|
| OI-01 | Gemini 모델 | Flash 계열 stable, 개발 기본 `gemini-3.5-flash-lite`, 설정으로 교체 가능 (§2) |
| OI-02 | 로컬 sLLM | 3개 계열 후보, S7 테스트로 M2 첫 단계에서 선정 (§10.3) |
| OI-03 | 청킹 | 성취기준 단위 + 일반 절 단위 (§5.2) |
| OI-04 | 신뢰 도메인 | §6 목록으로 시작, 구현 중 조정 |
| OI-05 | 시나리오별 성취기준 매핑 | **미결**: 인덱스 구축 후 `chunks.json`에서 추출해 spec에 반영 |
| OI-06 | 이미지 크기 제한 | 5MB, 전송 전 긴 변 1024px로 리사이즈 (§4) |

---

## 변경 이력

| 날짜 | 버전 | 내용 |
|---|---|---|
| 2026-10-26 | v0.1 | 초안 작성 |
| 2026-10-26 | v0.2 | §7 base에 서식 규칙 추가: `**'명암'**이`처럼 따옴표가 든 굵게 표시 뒤에 조사가 붙으면 마크다운 굵게가 깨진다 |
| 2026-10-26 | v0.3 | §2·§4·§14 개발 기본 모델을 `gemini-3.5-flash` → `gemini-3.5-flash-lite`로 변경: Flash 무료 한도(하루 약 20회)가 T2 점검 중 소진되어 개발·점검이 막혔다 |
