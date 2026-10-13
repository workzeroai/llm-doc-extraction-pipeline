import json
import random

import pytest

from docgen import fake
from docgen.documents import build_all
from docgen.fonts import FontNotFoundError, find_korean_font
from docgen.generate import generate, generate_or_bundled, manifest
from pipeline.validate import biz_no_valid


def test_build_all_shape_and_hard_ratio():
    specs = build_all(42)
    assert len(specs) == 30
    assert {s.doc_type for s in specs} == {"contract", "quote", "invoice"}
    hard = [s for s in specs if s.tags]
    assert len(hard) / len(specs) >= 0.3
    assert sorted(s.doc_id for s in specs if s.must_review) == ["CT-08", "CT-09", "CT-10", "IV-08", "IV-09", "QT-09"]
    m = manifest(specs, 42)
    assert m["hard_ratio"] == 0.5 and m["total"] == 30


def test_gold_is_reproducible_and_matches_committed(samples):
    """seed가 같으면 정답 JSON이 저장소 생성본과 글자까지 같다(글꼴과 무관)."""
    for s in build_all(42):
        committed = json.loads((samples / "gold" / f"{s.doc_id}.json").read_text(encoding="utf-8"))
        assert committed == json.loads(json.dumps(s.gold(), ensure_ascii=False))


def test_generated_values_are_internally_consistent():
    for s in build_all(42):
        f = s.fields
        for k in ("vendor_biz_no", "supplier_biz_no", "buyer_biz_no"):
            if f.get(k):
                assert biz_no_valid(f[k]), (s.doc_id, k)
        if s.index == 8:     # 합계 불일치는 의도된 결함
            continue
        if s.doc_type == "contract":
            assert f["supply_amount"] + f["vat"] == f["total_amount"]
        else:
            assert sum(i["amount"] for i in f["items"]) == f["subtotal"]
            assert f["subtotal"] + f["vat"] == f["total"]


def test_fake_helpers():
    rng = random.Random(1)
    assert fake.company(rng) != ""
    assert len(fake.person(rng)) >= 2
    assert fake.fmt_date(__import__("datetime").date(2026, 3, 5), "short") == "26.03.05"
    with pytest.raises(ValueError):
        fake.fmt_date(__import__("datetime").date(2026, 3, 5), "nope")
    with pytest.raises(ValueError):
        fake.won(1, "nope")
    assert fake.korean_amount(0) == "금 영원정"
    assert fake.add_months(__import__("datetime").date(2026, 1, 31), 1).isoformat() == "2026-02-28"


def _has_font() -> bool:
    try:
        find_korean_font()
        return True
    except FontNotFoundError:
        return False


@pytest.mark.skipif(not _has_font(), reason="한글 TrueType 글꼴 없음")
def test_generate_pdfs_have_expected_text(tmp_path):
    from pipeline.pdftext import extract_text

    res = generate(tmp_path, 42)
    assert len(list(res.docs_dir.glob("*.pdf"))) == 30
    assert extract_text(res.docs_dir / "CT-10.pdf").ok is False          # 텍스트 층 없는 스캔
    qt = extract_text(res.docs_dir / "QT-01.pdf")
    assert qt.ok and "견적번호" in qt.text


def test_font_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("DOCGEN_FONT", str(tmp_path / "missing.ttf"))
    with pytest.raises(FontNotFoundError):
        find_korean_font()


def test_generate_or_bundled_falls_back_without_font(monkeypatch, tmp_path):
    import docgen.generate as g

    def no_font():
        raise FontNotFoundError("없음")

    monkeypatch.setattr(g, "find_korean_font", no_font)
    res = generate_or_bundled(tmp_path / "w")
    assert res.font == "bundled"
    assert len(list(res.docs_dir.glob("*.pdf"))) == 30
