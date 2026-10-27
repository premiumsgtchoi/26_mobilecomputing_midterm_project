"""성취기준 코드 추출, 학교급·영역 판정, 청킹 결과 테스트 (design.md §5)."""
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # artmate, scripts 임포트용

from artmate import config  # noqa: E402
from scripts.build_index import build_chunks, parse_code  # noqa: E402


@pytest.mark.parametrize(
    "text, expected",
    [
        ("[6미03-02] 미술 작품의 내용과 형식을", ("6미03-02", "초등", "감상")),
        ("[9미01-04] 삶과 미술의 관계를", ("9미01-04", "중등", "미적 체험")),
        ("[9미02-01] 주제를 탐구하고", ("9미02-01", "중등", "표현")),
    ],
)
def test_parse_code(text, expected):
    info = parse_code(text)
    assert (info["code"], info["school_level"], info["area"]) == expected


@pytest.mark.parametrize("text", ["[4미01-01] 3~4학년 성취기준", "[6미04-01] 없는 영역", "코드 없는 문장"])
def test_parse_code_rejects(text):
    assert parse_code(text) is None


# 아래는 실제 PDF가 있어야 실행된다(data/raw는 git에서 제외)
pdf_required = pytest.mark.skipif(not config.CURRICULUM_PDF.exists(), reason="교육과정 PDF 없음")


@pytest.fixture(scope="module")
def chunks():
    return build_chunks(config.CURRICULUM_PDF)


@pytest.fixture(scope="module")
def standards(chunks):
    return [c for c in chunks if c["metadata"]["chunk_type"] == "standard"]


@pdf_required
def test_standard_counts(standards):
    assert len(standards) == 26
    levels = Counter(c["metadata"]["school_level"] for c in standards)
    assert levels == {"초등": 13, "중등": 13}


@pdf_required
@pytest.mark.parametrize("level", ["초등", "중등"])
def test_area_counts(standards, level):
    areas = Counter(c["metadata"]["area"] for c in standards if c["metadata"]["school_level"] == level)
    assert areas == {"미적 체험": 4, "표현": 5, "감상": 4}


@pdf_required
def test_no_grade_3_4(chunks):
    assert not any("4미" in c["text"] or c["metadata"]["code"].startswith("4미") for c in chunks)


@pdf_required
def test_code_matches_metadata(standards):
    for c in standards:
        m = c["metadata"]
        assert c["id"] == m["code"]
        assert parse_code(f"[{m['code']}]") == {k: m[k] for k in ("code", "school_level", "area")}


@pdf_required
def test_commentary_merged(standards):
    by_code = {c["id"]: c["text"] for c in standards}
    # 해설에 다시 나온 코드는 별도 청크 없이 같은 성취기준 청크에 합쳐진다
    assert "성취기준은" in by_code["6미01-02"] and "성취기준은" in by_code["9미03-04"]
    assert "성취기준은" not in by_code["6미01-01"]
    # 여러 줄에 걸친 성취기준 문장도 한 문장으로 이어진다
    assert "공동체 문화에 기여할 수 있다." in by_code["9미03-04"]


@pdf_required
def test_consideration_chunks(chunks):
    cons = [c["metadata"] for c in chunks if c["metadata"]["section"] == "고려 사항"]
    assert {(m["school_level"], m["area"]) for m in cons} == {
        (lv, a) for lv in ("초등", "중등") for a in ("미적 체험", "표현", "감상")
    }
