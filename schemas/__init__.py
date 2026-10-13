"""추출 스키마 3종(JSON Schema draft 2020-12).

- 모든 필드가 `required`(키는 반드시 있어야 함)이고 값은 null 허용 → "문서에 없으면 null"을 형식으로 강제한다.
- `x-required-values`: null이면 안 되는 업무상 필수값(검증 단계의 R01 규칙이 읽는다).
"""
from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

SCHEMA_DIR = Path(__file__).resolve().parent
DOC_TYPES = ("contract", "quote", "invoice")
TYPE_LABEL = {"contract": "계약서", "quote": "견적서", "invoice": "청구서"}


@cache
def load_schema(doc_type: str) -> dict[str, Any]:
    if doc_type not in DOC_TYPES:
        raise KeyError(f"알 수 없는 문서 유형: {doc_type} (가능: {', '.join(DOC_TYPES)})")
    return json.loads((SCHEMA_DIR / f"{doc_type}.json").read_text(encoding="utf-8"))


def field_names(doc_type: str) -> list[str]:
    return list(load_schema(doc_type)["properties"])


def field_labels(doc_type: str) -> dict[str, str]:
    return {k: v.get("title", k) for k, v in load_schema(doc_type)["properties"].items()}


def required_values(doc_type: str) -> list[str]:
    return list(load_schema(doc_type).get("x-required-values", []))
