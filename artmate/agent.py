"""M1 단일 에이전트: bind_tools + 도구 호출 루프 + 최종 응답 스트림 (design.md §8)."""
from collections.abc import Iterator

from langchain_core.messages import BaseMessage, SystemMessage

from artmate import config
from artmate.llm import get_chat_model
from artmate.prompts import build_system_prompt
from artmate.tools.curriculum import search_curriculum
from artmate.tools.web import format_sources, web_search

TOOLS = {t.name: t for t in [search_curriculum, web_search]}


def stream_answer(history: list[BaseMessage], school_level: str, calls: list[dict]) -> Iterator[str]:
    """최종 응답 글자를 흘려보낸다. 도구 호출 내역은 calls에 덧붙인다."""
    llm = get_chat_model()
    with_tools = llm.bind_tools(list(TOOLS.values()))
    # 상한에 도달한 마지막 라운드는 도구를 더 부르지 못하게 하고 답을 마무리시킨다
    no_more_tools = llm.bind_tools(list(TOOLS.values()), tool_choice="none")
    messages = [SystemMessage(build_system_prompt(school_level)), *history]

    for round_ in range(config.MAX_TOOL_ROUNDS + 1):
        model = with_tools if round_ < config.MAX_TOOL_ROUNDS else no_more_tools
        # 라운드마다 스트림으로 받아 합친다. 도구 호출이 없으면 흘러나온 글자가 곧 최종 응답이다
        response = None
        for chunk in model.stream(messages):
            response = chunk if response is None else response + chunk
            if chunk.text:
                yield chunk.text
        if not response.tool_calls:
            # 웹 검색 출처는 모델 대신 코드가 답 끝에 붙인다 (design.md §6)
            urls = [r["url"] for c in calls if c["tool"] == web_search.name for r in c["results"] if r["url"]]
            if urls:
                yield "\n\n" + format_sources(urls)
            return

        messages.append(response)
        for call in response.tool_calls:
            args = call["args"]
            if call["name"] == search_curriculum.name:
                # 학교급은 모델이 아니라 세션 상태에서 주입 (design.md §6)
                args = {**args, "school_level": school_level}
            result = TOOLS[call["name"]].invoke({**call, "args": args})
            messages.append(result)
            calls.append({"tool": call["name"], "args": args, "results": result.artifact})
