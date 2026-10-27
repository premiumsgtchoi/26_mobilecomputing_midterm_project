"""웹 검색 도구 web_search (design.md §6)."""
from functools import lru_cache
from urllib.parse import urlparse

from langchain_core.tools import ToolException, tool
from langchain_tavily import TavilySearch

from artmate import config

# 신뢰 도메인과 출처 표기용 기관명 (OI-04)
TRUSTED_DOMAINS = {
    "mmca.go.kr": "국립현대미술관",
    "museum.go.kr": "국립중앙박물관",
    "emuseum.go.kr": "e뮤지엄",
    "encykorea.aks.ac.kr": "한국민족문화대백과",
    "ko.wikipedia.org": "위키백과",
    "artsandculture.google.com": "구글 아트 앤 컬처",
}


@lru_cache
def get_tavily() -> TavilySearch:
    return TavilySearch(
        max_results=config.WEB_MAX_RESULTS,
        search_depth="basic",
        tavily_api_key=config.TAVILY_API_KEY,
    )


def _search(query: str, domains: list[str] | None) -> list[dict]:
    try:
        res = get_tavily().invoke({"query": query, "include_domains": domains})
    except ToolException:  # 결과 0건이면 TavilySearch가 예외를 낸다
        return []
    if "error" in res:
        raise RuntimeError(res["error"])
    return res["results"]


def site_name(url: str) -> str:
    host = urlparse(url).netloc.removeprefix("www.")
    return next((name for d, name in TRUSTED_DOMAINS.items() if host.endswith(d)), host)


@tool(response_format="content_and_artifact")
def web_search(query: str) -> tuple[str, list[dict]]:
    """작가, 작품, 미술사·시대 배경 같은 사실 정보를 신뢰할 수 있는 사이트에서 검색한다.
    미술 개념·학습 내용(명암, 구도, 감상 방법 등)은 이 도구가 아니라 search_curriculum을 쓴다.

    출처는 시스템이 답 끝에 자동으로 붙이므로 답에 쓰지 않는다."""
    if not config.TAVILY_API_KEY:
        return "웹 검색 실패: 확인된 정보만으로 답할 것", [{"scope": "검색 실패: TAVILY_API_KEY 없음", "url": ""}]
    try:
        results = [(r, "신뢰 도메인") for r in _search(query, list(TRUSTED_DOMAINS))]
        # 신뢰 도메인 결과가 부족하면 도메인 제한 없이 1회 재검색해 남은 자리를 채운다
        if len(results) < config.WEB_MIN_TRUSTED:
            seen = {r["url"] for r, _ in results}
            extra = [r for r in _search(query, None) if r["url"] not in seen]
            results += [(r, "일반 재검색") for r in extra[: config.WEB_MAX_RESULTS - len(results)]]
    except Exception as e:
        return "웹 검색 실패: 확인된 정보만으로 답할 것", [{"scope": f"검색 실패: {type(e).__name__}", "url": ""}]
    if not results:
        return "웹 검색 결과 없음: 확인된 정보만으로 답할 것", []

    # 링크는 모델에 넘기지 않는다(출처는 에이전트가 artifact의 URL로 붙임)
    content = "\n\n".join(
        f"[{i}] {r['title']} (사이트: {site_name(r['url'])})\n{r['content']}"
        for i, (r, _) in enumerate(results, 1)
    )
    return content, [{"scope": scope, "url": r["url"]} for r, scope in results]


def format_sources(urls: list[str]) -> str:
    """답 끝에 붙일 출처 줄. 같은 URL은 한 번만 쓴다."""
    return "출처: " + ", ".join(f"[{site_name(u)}]({u})" for u in dict.fromkeys(urls))
