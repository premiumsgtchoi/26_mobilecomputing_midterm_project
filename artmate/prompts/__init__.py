"""조합식 시스템 프롬프트 (design.md §7)."""
from artmate.prompts.activities import ACTIVITY_PROMPTS, OUT_OF_ACTIVITY_PROMPT
from artmate.prompts.base import BASE_PROMPT
from artmate.prompts.school_level import SCHOOL_LEVEL_PROMPTS


def build_system_prompt(school_level: str, activity: str) -> str:
    """base + 학교급 + 선택 활동 지침 + 활동 밖 요청 규칙."""
    return "\n\n".join(
        [BASE_PROMPT, SCHOOL_LEVEL_PROMPTS[school_level], ACTIVITY_PROMPTS[activity], OUT_OF_ACTIVITY_PROMPT]
    )
