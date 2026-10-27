"""확인 퀴즈: 대화 내용으로 객관식 문항을 구조화 출력으로 만든다 (design.md §8.4)."""
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from artmate import config
from artmate.llm import get_chat_model
from artmate.prompts.quiz import QUIZ_LEVEL_GUIDES, QUIZ_PROMPT


class QuizItem(BaseModel):
    question: str = Field(description="문항")
    options: list[str] = Field(min_length=4, max_length=4, description="선택지 4개")
    answer_index: int = Field(ge=0, le=3, description="정답 선택지 번호(0~3)")
    explanation: str = Field(description="대화 내용을 근거로 한 1~2문장 해설")


class Quiz(BaseModel):
    items: list[QuizItem] = Field(min_length=2, max_length=3)


def enough_conversation(messages: list[dict]) -> bool:
    return sum(m["role"] == "user" for m in messages) >= config.QUIZ_MIN_QUESTIONS


def make_quiz(messages: list[dict], school_level: str) -> Quiz:
    """화면 대화 기록(role, content)만으로 퀴즈를 만든다."""
    transcript = "\n".join(
        f"{'학생' if m['role'] == 'user' else '아트메이트'}: {m['content']}"
        + (" (이미지를 함께 올림)" if m.get("image") is not None else "")
        for m in messages
    )
    quiz = get_chat_model().with_structured_output(Quiz).invoke([
        SystemMessage(QUIZ_PROMPT.format(level_guide=QUIZ_LEVEL_GUIDES[school_level])),
        HumanMessage(f"[대화]\n{transcript}"),
    ])
    if quiz is None:
        raise ValueError("퀴즈 응답을 해석하지 못함")
    return quiz
