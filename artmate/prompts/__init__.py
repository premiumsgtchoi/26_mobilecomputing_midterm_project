"""조합식 시스템 프롬프트 (design.md §7)."""
from artmate.prompts.areas import AREAS_SUMMARY_PROMPT
from artmate.prompts.base import BASE_PROMPT
from artmate.prompts.school_level import SCHOOL_LEVEL_PROMPTS


def build_system_prompt(school_level: str) -> str:
    """base + 학교급 + (M1) 3개 영역 요약."""
    return "\n\n".join([BASE_PROMPT, SCHOOL_LEVEL_PROMPTS[school_level], AREAS_SUMMARY_PROMPT])
