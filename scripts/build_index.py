"""교육과정 PDF → 청크 → 벡터 DB 구축 (design.md §5). 실행: python -m scripts.build_index"""
import json
import re

import pymupdf
from langchain_chroma import Chroma
from langchain_core.documents import Document

from artmate import config
from artmate.llm import get_embeddings

CODE_RE = re.compile(r"\[(\d)미(0[1-3])-(\d{2})\]")
LEVELS = {"6": "초등", "9": "중등"}  # 4미(3~4학년)는 대상 학교급이 아니므로 제외
LEVEL_NAMES = {"초등": "초등학교 5~6학년", "중등": "중학교"}
AREAS = {"01": "미적 체험", "02": "표현", "03": "감상"}
PAGE_HEADERS = ("공통 교육과정", "미술과 교육과정")
HEADING_RE = re.compile(r"^(\d\.|[가-하]\.|\(\d\)|\([가-하]\)|\[(초등학교|중학교)|교육과정 설계의 개요)")
ITEM_RE = re.compile(r"^(•|\[\d미|\([가-하\d]\) )")
AREA_HEADING_RE = re.compile(r"^\(\d\) (미적 체험|표현|감상)$")

# (절 이름, 시작 문단, 끝 문단) — 800자 단위로 나누는 공통 일반 청크
GENERAL_SECTIONS = [
    ("설계 개요", "교육과정 설계의 개요", "1. 성격 및 목표"),
    ("성격", "가. 성격", "나. 목표"),
    ("목표", "나. 목표", "2. 내용 체계"),
    ("교수·학습", "3. 교수", "나. 평가"),
    ("평가", "나. 평가", None),
]


def parse_code(text: str) -> dict | None:
    """문장 앞의 성취기준 코드로 학교급·영역을 판정한다. 6미·9미가 아니면 None."""
    m = CODE_RE.match(text)
    if not m or m[1] not in LEVELS:
        return None
    return {"code": f"{m[1]}미{m[2]}-{m[3]}", "school_level": LEVELS[m[1]], "area": AREAS[m[2]]}


def page_lines(page) -> list[str]:
    """쪽 머리말과 쪽 번호를 뺀 줄 목록."""
    lines = page.get_text().split("\n")
    if len(lines) > 1 and lines[0].strip() in PAGE_HEADERS and lines[1].strip().isdigit():
        lines = lines[2:]
    return lines


def join_lines(lines: list[str]) -> list[str]:
    """줄바꿈으로 끊긴 문장을 이어 문단 목록으로 만든다.
    PDF가 줄 끝 띄어쓰기를 보존하므로 줄을 그대로 이으면 낱말 중간 끊김이 복원된다."""
    paras, can_continue = [], False
    for line in lines:
        s = line.strip()
        if not s or s.startswith("[그림]"):
            continue
        if len(s) <= 20 and HEADING_RE.match(s):  # 짧은 제목 줄은 단독 문단
            paras.append(s)
            can_continue = False
        elif can_continue and not ITEM_RE.match(s):
            paras[-1] += line
        else:
            paras.append(line)
            can_continue = True
    return [re.sub(r"\s+", " ", p).strip() for p in paras]


def find(paras: list[str], prefix: str) -> int:
    return next(i for i, p in enumerate(paras) if p.startswith(prefix))


def split_text(paras: list[str], size: int = 800, overlap: int = 100) -> list[str]:
    """문장을 size자 안팎으로 모으고, 앞 청크 끝 overlap자를 다음 청크 앞에 붙인다.
    PDF에서 본문 문단 경계가 드러나지 않아 긴 문단이 생기므로 문장('다.') 단위로 나눈다."""
    chunks, cur = [], ""
    for p in [s for para in paras for s in re.split(r"(?<=다\.) ", para)]:
        if cur and len(cur) + 1 + len(p) > size:
            chunks.append(cur)
            tail = cur[-overlap:]
            cur = tail[tail.find(" ") + 1:] + "\n" + p  # 낱말 중간에서 시작하지 않게
        else:
            cur = f"{cur}\n{p}" if cur else p
    chunks.append(cur)
    return chunks


def make_chunk(cid, text, school_level, area, chunk_type, section, code="") -> dict:
    return {
        "id": cid,
        "text": text,
        "metadata": {
            "school_level": school_level,
            "area": area,
            "code": code,  # Chroma 메타데이터는 None을 받지 않으므로 빈 문자열
            "chunk_type": chunk_type,
            "section": section,
        },
    }


def school_chunks(block: list[str], level: str) -> list[dict]:
    """학교급 블록에서 성취기준 청크(해설 합침)와 영역별 고려 사항 청크를 만든다."""
    standards, considerations = {}, {}
    area = mode = last = None
    for p in block:
        if m := AREA_HEADING_RE.match(p):
            area, mode = m[1], "standard"
        elif p.startswith("(가) 성취기준 해설"):
            mode = "해설"
        elif p.startswith("(나) 성취기준 적용 시 고려 사항"):
            mode = "고려"
            considerations[area] = []
        elif mode == "standard":
            info = parse_code(p)
            if info is None:
                continue
            if (info["school_level"], info["area"]) != (level, area):
                raise ValueError(f"{info['code']}가 {level} {area} 절에 있음: 영역 대응 확인 필요")
            standards[info["code"]] = {"text": p, **info}
        elif mode == "해설":
            text = p.removeprefix("• ")
            info = parse_code(text)
            last = info["code"] if info else last  # 코드 없는 문단은 앞 해설의 이어짐
            standards[last]["text"] += "\n" + text
        elif mode == "고려":
            considerations[area].append(p)

    name = LEVEL_NAMES[level]
    chunks = [
        make_chunk(s["code"], f"{name} {s['area']} 성취기준\n{s['text']}",
                   level, s["area"], "standard", "성취기준", s["code"])
        for s in standards.values()
    ]
    chunks += [
        make_chunk(f"고려-{level}-{a}", f"{name} {a} - 성취기준 적용 시 고려 사항\n" + "\n".join(ps),
                   level, a, "general", "고려 사항")
        for a, ps in considerations.items()
    ]
    return chunks


def cell_items(page, bbox) -> list[str]:
    """표 셀을 위치로 다시 읽어 '⋅' 항목 목록으로 돌려준다."""
    text = page.get_text(clip=bbox).replace("\n", "")
    text = re.sub(r",(?=\S)", ", ", text)  # 셀 안 줄바꿈에서 빠진 쉼표 뒤 띄어쓰기
    return [re.sub(r"\s+", " ", s).strip() for s in text.split("⋅") if s.strip()]


def content_system_chunks(doc) -> list[dict]:
    """내용 체계 표에서 핵심 아이디어와 5~6학년·중학교 열만 뽑는다(3~4학년 열 제외)."""
    tables = [
        (page, t)
        for page in doc
        for t in page.find_tables().tables
        if t.extract()[0][0] == "핵심 아이디어"
    ]
    if len(tables) != len(AREAS):
        raise ValueError(f"내용 체계 표가 {len(tables)}개: 3개여야 함")

    chunks = []
    for (page, t), area in zip(tables, AREAS.values()):
        ideas = cell_items(page, t.rows[0].cells[1])
        for level, col in (("초등", 2), ("중등", 3)):
            lines = [f"{LEVEL_NAMES[level]} {area} - 내용 체계", "핵심 아이디어:"]
            lines += [f"- {s}" for s in ideas]
            for r in (4, 5, 6):  # 지식·이해, 과정·기능, 가치·태도
                category = t.extract()[r][0].strip("[]")
                lines.append(f"{category}: " + ", ".join(cell_items(page, t.rows[r].cells[col])))
            chunks.append(make_chunk(f"체계-{level}-{area}", "\n".join(lines),
                                     level, area, "general", "내용 체계"))
    return chunks


def build_chunks(pdf_path) -> list[dict]:
    doc = pymupdf.open(pdf_path)
    paras = join_lines([line for page in doc for line in page_lines(page)])

    chunks = []
    for name, start, end in GENERAL_SECTIONS:
        i, j = find(paras, start), (find(paras, end) if end else len(paras))
        for n, text in enumerate(split_text(paras[i + 1:j]), 1):
            chunks.append(make_chunk(f"{name}-{n}", f"미술과 교육과정 - {name}\n{text}",
                                     "공통", "공통", "general", name))

    chunks += content_system_chunks(doc)
    elem, mid, end = find(paras, "[초등학교"), find(paras, "[중학교]"), find(paras, "3. 교수")
    chunks += school_chunks(paras[elem + 1:mid], "초등")
    chunks += school_chunks(paras[mid + 1:end], "중등")
    return chunks


def main():
    chunks = build_chunks(config.CURRICULUM_PDF)
    config.CHUNKS_JSON.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    standards = [c["metadata"] for c in chunks if c["metadata"]["chunk_type"] == "standard"]
    print(f"청크 {len(chunks)}개 저장: {config.CHUNKS_JSON}")
    for level in LEVELS.values():
        n = sum(m["school_level"] == level for m in standards)
        print(f"  {level} 성취기준 {n}개")

    embeddings = get_embeddings()
    # 실제 API 요청 수를 세기 위해 클라이언트 호출을 감싼다
    calls = 0
    embed_content = embeddings.client.models.embed_content

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return embed_content(*args, **kwargs)

    embeddings.client.models.embed_content = counted

    # 다시 실행하면 기존 컬렉션을 지우고 새로 만든다
    Chroma(collection_name=config.CHROMA_COLLECTION,
           persist_directory=str(config.CHROMA_DIR)).delete_collection()
    Chroma.from_documents(
        [Document(c["text"], metadata=c["metadata"]) for c in chunks],
        embeddings,
        ids=[c["id"] for c in chunks],
        collection_name=config.CHROMA_COLLECTION,
        persist_directory=str(config.CHROMA_DIR),
        collection_metadata={"hnsw:space": "cosine"},
    )
    print(f"벡터 DB 저장: {config.CHROMA_DIR} (임베딩 API 요청 {calls}회)")


if __name__ == "__main__":
    main()
