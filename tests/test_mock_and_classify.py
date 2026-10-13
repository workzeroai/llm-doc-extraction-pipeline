from eval.evaluate import same_value
from pipeline.classify import classify
from pipeline.providers import MockExtractor
from schemas import field_names, load_schema


def test_classify_all_text_docs(texts, gold):
    for doc_id, text in texts.items():
        if not text.strip():
            continue
        c = classify(text)
        assert c.ok and c.doc_type == gold[doc_id]["doc_type"], doc_id
        assert 0.5 < c.confidence <= 1.0


def test_classify_uncertain():
    assert not classify("메모 한 줄").ok
    c = classify("견적서 청구서 견적번호 청구번호")
    assert not c.ok and "둘 이상" in c.reason


def test_mock_is_not_an_llm():
    m = MockExtractor()
    assert m.is_llm is False and "LLM 아님" in m.label


def test_mock_extracts_clean_docs_exactly(texts, gold):
    m = MockExtractor()
    for doc_id, g in gold.items():
        if g["render"] != "pdf":
            continue
        out = m.extract(doc_id=doc_id, text=texts[doc_id], doc_type=g["doc_type"], schema=load_schema(g["doc_type"]))
        wrong = [f for f in field_names(g["doc_type"]) if not same_value(out.data.get(f), g["fields"][f])]
        assert wrong == [], (doc_id, wrong)
        assert out.uncertain_fields == [], (doc_id, out.uncertain_fields)


def test_mock_keeps_document_errors(texts, gold):
    """합계가 틀린 문서도 고치지 않고 인쇄된 값을 낸다(검증이 잡게)."""
    g = gold["CT-09"]
    out = MockExtractor().extract(doc_id="CT-09", text=texts["CT-09"], doc_type="contract",
                                  schema=load_schema("contract"))
    assert out.data["total_amount"] == g["fields"]["total_amount"]
    assert out.data["total_amount"] != out.data["supply_amount"] + out.data["vat"]


def test_mock_flags_ocr_noise(texts):
    out = MockExtractor().extract(doc_id="QT-10", text=texts["QT-10"], doc_type="quote", schema=load_schema("quote"))
    assert "items" in out.uncertain_fields


def test_mock_missing_values_are_null(texts):
    out = MockExtractor().extract(doc_id="QT-08", text=texts["QT-08"], doc_type="quote", schema=load_schema("quote"))
    assert out.data["valid_until"] is None and out.data["manager"] is None


def test_mock_contract_fallbacks():
    text = "용역 계약서\n계약번호 CT-2026-1\n계약일 2026-01-02\n갑 가람테크 대표 김하은 (인)\n을 누리랩스 대표 이서준 (인)"
    out = MockExtractor().extract(doc_id="X", text=text, doc_type="contract", schema=load_schema("contract"))
    assert out.data["client_name"] == "가람테크" and out.data["vendor_name"] == "누리랩스"
    assert {"client_name", "vendor_name"} <= set(out.uncertain_fields)


def test_mock_quote_without_table():
    text = "견적서\n견적번호 Q260101-1\n견적일자 2026-01-01"
    out = MockExtractor().extract(doc_id="X", text=text, doc_type="quote", schema=load_schema("quote"))
    assert out.data["items"] is None
