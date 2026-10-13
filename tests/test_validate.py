import copy

import pytest

from pipeline.validate import biz_no_valid, validate


@pytest.fixture
def quote(gold):
    return copy.deepcopy(gold["QT-01"]["fields"])


@pytest.fixture
def contract(gold):
    return copy.deepcopy(gold["CT-01"]["fields"])


def codes(issues):
    return [i.code for i in issues]


def test_clean_documents_pass(gold):
    for doc_id, g in gold.items():
        if g["must_review"]:
            continue
        assert validate(g["doc_type"], g["fields"]) == [], doc_id


def test_defective_documents_fail(gold):
    expected = {"CT-08": "R01", "CT-09": "R07", "IV-08": "R01", "IV-09": "R04", "QT-09": "R05"}
    for doc_id, code in expected.items():
        g = gold[doc_id]
        issues = validate(g["doc_type"], g["fields"])
        assert code in codes(issues), (doc_id, codes(issues))
        assert all(i.reason == "RULE_VIOLATION" for i in issues)


def test_schema_mismatch_skips_rules(quote):
    quote["total"] = "삼백만원"
    quote["extra"] = 1
    del quote["vat"]
    issues = validate("quote", quote)
    assert set(codes(issues)) == {"S01"}
    assert all(i.reason == "SCHEMA_MISMATCH" for i in issues)
    assert len(issues) == 3


def test_biz_no_pattern_is_schema(quote):
    quote["supplier_biz_no"] = "123-45-678"
    assert codes(validate("quote", quote)) == ["S01"]


def test_r02_r03_dates(contract):
    contract["contract_date"] = "2026/03/05"
    contract["start_date"], contract["end_date"] = "2026-09-01", "2026-03-01"
    c = codes(validate("contract", contract))
    assert "R02" in c and "R03" in c


def test_r04_r05_r06_r07(quote):
    quote["items"][0]["amount"] += 10
    quote["vat"] += 5000
    c = codes(validate("quote", quote))
    assert {"R04", "R05", "R06", "R07"} <= set(c)


def test_r08_biz_checksum(contract):
    good = contract["vendor_biz_no"]
    assert biz_no_valid(good)
    last = int(good[-1])
    contract["vendor_biz_no"] = good[:-1] + str((last + 1) % 10)
    assert codes(validate("contract", contract)) == ["R08"]
    assert not biz_no_valid("123")


def test_r01_empty_items_and_c01_confidence(quote):
    quote["items"] = []
    c = codes(validate("quote", quote, uncertain=["total", "manager"]))
    assert "R01" in c
    assert c.count("C01") == 1          # manager는 선택값이라 확신 낮음 대상 아님


def test_issue_dict(quote):
    quote["total"] += 1
    d = validate("quote", quote)[0].as_dict()
    assert d["code"] == "R07" and d["reason"] == "RULE_VIOLATION" and d["field"] == "total"
