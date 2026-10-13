import pytest

from docgen import fake
from pipeline.normalize import (
    collapse_ws,
    find_biz_no,
    find_dates,
    fix_ocr_digits,
    parse_amount,
    parse_date,
    parse_int,
    parse_korean_number,
)


@pytest.mark.parametrize(("raw", "iso"), [
    ("2026-03-05", "2026-03-05"),
    ("2026.03.05", "2026-03-05"),
    ("2026. 3. 5.", "2026-03-05"),
    ("2026년 3월 5일", "2026-03-05"),
    ("26.03.05", "2026-03-05"),
    ("2026/3/5", "2026-03-05"),
])
def test_parse_date_formats(raw, iso):
    assert parse_date(raw) == (iso, False)


def test_parse_date_ocr_and_invalid():
    assert parse_date("2026. 9. l.") == ("2026-09-01", True)
    assert parse_date("2026-02-30") == (None, True)
    assert parse_date(None) == (None, False)
    assert parse_date("별도 협의") == (None, False)


def test_find_dates_period():
    assert find_dates("2026-04-05 ~ 2026년 9월 4일") == ["2026-04-05", "2026-09-04"]
    assert find_dates("2026-04-05부터 (완료일은 별도 협의)") == ["2026-04-05"]


@pytest.mark.parametrize(("raw", "value", "fixed"), [
    ("12,000,000원", 12_000_000, False),
    ("₩12,000,000", 12_000_000, False),
    ("금 일천이백만원정", 12_000_000, False),
    ("합계 금 사천일백사십칠만원정 부가가치세 포함", 41_470_000, False),
    ("1,2OO,OOO원", 1_200_000, True),
    ("33,550.000원", 33_550_000, True),
    ("l68.0O0", 168_000, True),
    ("없음", None, False),
])
def test_parse_amount(raw, value, fixed):
    assert parse_amount(raw) == (value, fixed)


def test_korean_number_roundtrip():
    for n in (10, 1_000, 12_300_000, 41_470_000, 105_000_000, 2_000_000_000):
        assert parse_korean_number(fake.korean_amount(n)[2:-2]) == n
    assert parse_korean_number("abc") is None


def test_fix_ocr_digits_keeps_words():
    assert fix_ocr_digits("INV-202603-8487 QUOTATION No") == ("INV-202603-8487 QUOTATION No", False)
    assert fix_ocr_digits("Q26O1O6-21") == ("Q260106-21", True)


def test_parse_int_and_biz_no_and_ws():
    assert parse_int("12개월") == (12, False)
    assert parse_int("1,2O0") == (1200, True)
    assert parse_int(None) == (None, False)
    assert find_biz_no("하람 (861-84-3l408)") == ("861-84-31408", True)
    assert find_biz_no("번호 없음") == (None, False)
    assert collapse_ws("  가  나 \n 다 ") == "가 나 다"
    assert collapse_ws("   ") is None
