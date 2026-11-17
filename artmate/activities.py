"""활동 정의 (design.md §8.5). 영역은 학생에게 보이지 않는 내부 속성이다."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Activity:
    key: str
    area: str  # 표현 | 감상 (교육과정 검색 주입·M2 분기용)
    label: str  # 사이드바 이름
    description: str  # 메인 제목 아래 한 줄 설명
    result: str  # 마무리 결과물


ACTIVITIES = {
    a.key: a
    for a in [
        Activity("idea", "표현", "아이디어 초안 만들기",
                 "주제에서 출발해 장면, 재료, 색까지 작품 아이디어를 함께 구체화해요.", "아이디어 초안 카드"),
        Activity("feedback", "표현", "내 작품 피드백",
                 "내 작품의 잘된 점을 찾고, 더 발전시킬 점과 다음에 할 일을 정해요.", "작품 성찰 카드"),
        Activity("appreciate", "감상", "작품 감상하기",
                 "보고, 살피고, 해석하고, 내 생각을 말하는 순서로 작품을 감상해요.", "감상 정리 카드"),
        Activity("background", "감상", "작가·배경 알아보기",
                 "작가와 작품이 만들어진 시대 배경을 확인된 자료로 알아봐요.", "확인 퀴즈"),
    ]
}
