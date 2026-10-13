import pytest
from jsonschema import Draft202012Validator

from pipeline.prompts import llm_schema, user_prompt
from schemas import DOC_TYPES, field_labels, field_names, load_schema, required_values


@pytest.mark.parametrize("doc_type", DOC_TYPES)
def test_schema_is_valid_and_strict(doc_type):
    s = load_schema(doc_type)
    Draft202012Validator.check_schema(s)
    assert s["additionalProperties"] is False
    assert set(s["required"]) == set(s["properties"])           # 키는 항상 있어야 함(값은 null 허용)
    assert set(required_values(doc_type)) <= set(s["properties"])
    assert 10 <= len(field_names(doc_type)) <= 15
    assert all(field_labels(doc_type).values())


def test_unknown_type():
    with pytest.raises(KeyError):
        load_schema("receipt")


def test_gold_validates_against_schema(gold):
    for doc_id, g in gold.items():
        errors = list(Draft202012Validator(load_schema(g["doc_type"])).iter_errors(g["fields"]))
        assert not errors, (doc_id, errors[:1])


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


@pytest.mark.parametrize("doc_type", DOC_TYPES)
def test_llm_schema_is_structured_output_friendly(doc_type):
    s = llm_schema(doc_type)
    Draft202012Validator.check_schema(s)
    assert s["required"][-1] == "uncertain_fields"
    for n in _walk(s):
        assert "pattern" not in n and "format" not in n and "x-required-values" not in n
        assert not isinstance(n.get("type"), list)                 # null 허용은 anyOf로
        if n.get("type") == "object":
            assert n["additionalProperties"] is False
            assert set(n["required"]) == set(n["properties"])
    # 'title' 필드(계약명)가 메타 키로 오인돼 빠지지 않아야 한다
    if doc_type == "contract":
        assert "title" in s["properties"]


def test_user_prompt_lists_fields():
    p = user_prompt("본문", "quote")
    assert "견적서" in p and "items: 품목" in p and "<document>\n본문\n</document>" in p
