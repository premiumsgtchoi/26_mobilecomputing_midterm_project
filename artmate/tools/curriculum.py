"""교육과정 검색 도구 search_curriculum (design.md §5.4, §6)."""
import re
from functools import lru_cache
from typing import Annotated, Literal

from langchain_chroma import Chroma
from langchain_core.tools import InjectedToolArg, tool

from artmate import config
from artmate.llm import get_embeddings

CODE_RE = re.compile(r"\[\d미\d{2}-\d{2}\] ?")


@lru_cache
def get_db() -> Chroma:
    return Chroma(
        collection_name=config.CHROMA_COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=str(config.CHROMA_DIR),
    )


def index_exists() -> bool:
    return (config.CHROMA_DIR / "chroma.sqlite3").exists()


@tool(response_format="content_and_artifact")
def search_curriculum(
    query: str,
    school_level: Annotated[str, InjectedToolArg],
    area: Literal["미적 체험", "표현", "감상"] | None = None,
) -> tuple[str, list[str]]:
    """2022 개정 미술과 교육과정에서 학생의 학교급에 맞는 학습 내용과 수준을 검색한다.
    미술 개념·학습 내용(명암, 구도, 감상 방법 등)에 관한 질문에 답하기 전에 사용한다.
    작가·작품·시대 배경 같은 사실 정보는 이 도구가 아니라 web_search를 쓴다.

    query: 학생 표현을 그대로 쓰지 말고 교육과정 용어로 바꿔 쓴다.
      예) 명암 → 조형 요소, 비평 → 감상, 색 섞기 → 표현 재료와 방법,
          그림 설명하기 → 작품의 내용과 형식 분석, 아이디어 떠올리기 → 발상
    area: 질문이 분명히 한 영역에 속할 때만 지정한다. '미적 체험' | '표현' | '감상'

    결과는 답의 수준과 방향을 정하는 내부 근거이다. 학생에게 인용하거나 출처로 밝히지 않는다."""
    if not index_exists():
        return "교육과정 근거 없음 (검색 인덱스가 없음)", []

    # 공통 청크는 제외하고 선택 학교급만 검색 (design.md §5.4)
    conditions = [{"school_level": school_level}]
    if area:
        conditions.append({"area": area})
    flt = conditions[0] if len(conditions) == 1 else {"$and": conditions}
    docs = get_db().similarity_search(query, k=config.RAG_TOP_K, filter=flt)
    if not docs:
        return "교육과정 근거 없음", []

    # 모델에는 성취기준 코드를 지운 본문만 넘기고(P2), 코드·절은 동작 보기용으로 따로 돌려준다
    content = "\n\n".join(CODE_RE.sub("", d.page_content) for d in docs)
    labels = [d.metadata["code"] or f"{d.metadata['section']}·{d.metadata['area']}" for d in docs]
    return content, labels
