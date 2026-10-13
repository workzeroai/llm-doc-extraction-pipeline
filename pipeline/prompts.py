"""LLM 공급자에 보내는 프롬프트와 구조화 출력용 스키마.

설계 원칙
- 모델에게 계산을 맡기지 않는다. 문서에 적힌 값만 옮기게 하고, 합계·날짜 순서·사업자번호 검증은
  코드(validate.py)가 한다. 그래야 모델이 '맞춰 놓은' 숫자가 문서의 오류를 가리지 않는다.
- 없는 값은 null. 지어내면 확인 대기열로 가지 않고 조용히 틀린 값이 저장되기 때문이다.
- 확신이 없는 필드는 uncertain_fields에 적게 하고, 필수 필드면 사람 확인으로 보낸다.
"""
from __future__ import annotations

import copy
from typing import Any

from schemas import TYPE_LABEL, field_labels, load_schema

SYSTEM_PROMPT = """당신은 한국어 업무 문서(계약서·견적서·청구서)에서 값을 뽑아 JSON 하나로만 답하는 추출기입니다.

규칙
1. 문서에 적힌 값만 옮깁니다. 문서에 없는 값은 null로 둡니다. 추측하거나 계산해서 채우지 않습니다.
   합계가 틀려 보여도 문서에 인쇄된 값을 그대로 씁니다(검증은 다음 단계가 합니다).
2. 날짜는 YYYY-MM-DD로 바꿉니다. '26.03.05'처럼 연도가 두 자리면 2000년대로 봅니다.
3. 금액은 원 단위 정수입니다. 쉼표·₩·'원'을 빼고, '금 일천이백만원정' 같은 한글 금액도 숫자로 바꿉니다.
4. 사업자등록번호는 000-00-00000 형식으로 씁니다.
5. 품목은 표의 행 순서대로 적고, 셀 안에서 줄이 바뀐 품목명은 한 줄로 이어 씁니다.
6. 스캔 잡음 때문에 확신할 수 없는 값은 가장 그럴듯한 값을 쓰고, 그 필드 이름을 uncertain_fields에 넣습니다.
7. JSON 밖의 설명은 쓰지 않습니다."""


def user_prompt(text: str, doc_type: str) -> str:
    labels = field_labels(doc_type)
    fields = "\n".join(f"- {k}: {v}" for k, v in labels.items())
    return (f"문서 유형: {TYPE_LABEL[doc_type]} ({doc_type})\n"
            f"뽑을 필드:\n{fields}\n- uncertain_fields: 확신할 수 없는 필드 이름 목록\n\n"
            f"<document>\n{text}\n</document>")


_DROP_KEYS = ("$schema", "$id", "x-required-values", "pattern", "format", "title", "description")


def _to_llm(node: Any) -> Any:
    """null 허용 타입 배열(["string","null"])을 anyOf로 바꾸고, 구조화 출력이 지원하지 않는 키를 뺀다."""
    if isinstance(node, list):
        return [_to_llm(n) for n in node]
    if not isinstance(node, dict):
        return node
    out = {k: _to_llm(v) for k, v in node.items() if k not in _DROP_KEYS}
    if "properties" in node:
        out["properties"] = {k: _to_llm(v) for k, v in node["properties"].items()}
    t = out.get("type")
    if isinstance(t, list) and "null" in t:
        base = {k: v for k, v in out.items() if k != "type"}
        non_null = [x for x in t if x != "null"]
        branch = {"type": non_null[0], **base}
        return {"anyOf": [branch, {"type": "null"}]}
    return out


def llm_schema(doc_type: str) -> dict[str, Any]:
    """구조화 출력에 넘길 스키마: 원래 필드 + uncertain_fields, 모든 객체 additionalProperties=false."""
    schema = copy.deepcopy(load_schema(doc_type))
    names = list(schema["properties"])
    out = _to_llm(schema)
    out["properties"]["uncertain_fields"] = {"type": "array", "items": {"type": "string", "enum": names}}
    out["required"] = [*names, "uncertain_fields"]
    out["additionalProperties"] = False
    return out
