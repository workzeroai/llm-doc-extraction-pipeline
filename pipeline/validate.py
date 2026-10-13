"""검증 = JSON Schema(형식) + 업무 규칙(내용) + 확신도.

추출기(LLM이든 모의 추출기든)가 낸 값을 믿지 않고 코드가 다시 확인한다.

| 코드 | 분기 원인        | 내용 |
|------|------------------|------|
| S01  | SCHEMA_MISMATCH  | 스키마 위반(키 누락·타입·사업자번호 형식·정의 밖 키) |
| R01  | RULE_VIOLATION   | 업무상 필수값이 null(문서에 없거나 못 읽음) |
| R02  | RULE_VIOLATION   | 날짜가 YYYY-MM-DD가 아니거나 없는 날짜 |
| R03  | RULE_VIOLATION   | 날짜 순서(시작 ≤ 종료, 발행 ≤ 기한) |
| R04  | RULE_VIOLATION   | 품목 금액 ≠ 수량 × 단가 |
| R05  | RULE_VIOLATION   | 공급가액(소계) ≠ 품목 금액 합 |
| R06  | RULE_VIOLATION   | 부가세 ≠ 공급가액의 10%(±1원) |
| R07  | RULE_VIOLATION   | 합계 ≠ 공급가액 + 부가세 |
| R08  | RULE_VIOLATION   | 사업자등록번호 검증번호 불일치(오인식·오기) |
| C01  | LOW_CONFIDENCE   | 필수값을 추출기가 '확신 없음'으로 표시 |
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from jsonschema import Draft202012Validator

from schemas import field_labels, load_schema, required_values

RULE_LABELS = {
    "S01": "스키마 위반", "R01": "필수값 누락", "R02": "날짜 형식", "R03": "날짜 순서", "R04": "품목 금액 계산",
    "R05": "소계 = 품목 합", "R06": "부가세 10%", "R07": "합계 = 공급가액+세액", "R08": "사업자번호 검증",
    "C01": "확신 낮음",
}
CODE_REASON = {"S01": "SCHEMA_MISMATCH", "C01": "LOW_CONFIDENCE"}
DATE_FIELDS = ("contract_date", "start_date", "end_date", "issue_date", "valid_until", "due_date")
DATE_ORDER = {"contract": [("start_date", "end_date")], "quote": [("issue_date", "valid_until")],
              "invoice": [("issue_date", "due_date")]}
MONEY = {"contract": ("supply_amount", "vat", "total_amount"), "quote": ("subtotal", "vat", "total"),
         "invoice": ("subtotal", "vat", "total")}
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class Issue:
    code: str
    field: str | None
    message: str

    @property
    def reason(self) -> str:
        return CODE_REASON.get(self.code, "RULE_VIOLATION")

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "field": self.field, "message": self.message, "reason": self.reason}


def biz_no_valid(value: str) -> bool:
    digits = [int(c) for c in value if c.isdigit()]
    if len(digits) != 10:
        return False
    weights = [1, 3, 7, 1, 3, 7, 1, 3, 5]
    total = sum(d * w for d, w in zip(digits[:9], weights, strict=True)) + (digits[8] * 5) // 10
    return (10 - total % 10) % 10 == digits[9]


def won(n: int) -> str:
    return f"{n:,}원"


def schema_issues(doc_type: str, data: dict[str, Any]) -> list[Issue]:
    validator = Draft202012Validator(load_schema(doc_type))
    out = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(p) for p in err.absolute_path) or None
        out.append(Issue("S01", path, f"{path or '(문서)'}: {err.message}"))
    return out


def rule_issues(doc_type: str, data: dict[str, Any]) -> list[Issue]:
    labels = field_labels(doc_type)
    out: list[Issue] = []
    # R01 필수값
    for f in required_values(doc_type):
        v = data.get(f)
        if v is None or (isinstance(v, list) and not v):
            out.append(Issue("R01", f, f"{labels[f]}({f}) 값이 없음"))
    # R02 날짜 형식
    parsed: dict[str, date] = {}
    for f in DATE_FIELDS:
        v = data.get(f)
        if v is None or f not in labels:
            continue
        try:
            if not _ISO.match(v):
                raise ValueError
            parsed[f] = date.fromisoformat(v)
        except ValueError:
            out.append(Issue("R02", f, f"{labels[f]} '{v}'가 YYYY-MM-DD 형식의 날짜가 아님"))
    # R03 날짜 순서
    for a, b in DATE_ORDER[doc_type]:
        if a in parsed and b in parsed and parsed[a] > parsed[b]:
            out.append(Issue("R03", b, f"{labels[a]} {parsed[a]} > {labels[b]} {parsed[b]}"))
    # R04·R05 품목
    supply_f, vat_f, total_f = MONEY[doc_type]
    items = data.get("items")
    if isinstance(items, list) and items:
        for i, it in enumerate(items, 1):
            if it["qty"] * it["unit_price"] != it["amount"]:
                out.append(Issue("R04", f"items.{i - 1}.amount",
                                 f"품목 {i} '{it['name']}': {it['qty']:,} × {won(it['unit_price'])} = "
                                 f"{won(it['qty'] * it['unit_price'])} ≠ 인쇄 {won(it['amount'])}"))
        s = sum(it["amount"] for it in items)
        if data.get(supply_f) is not None and s != data[supply_f]:
            out.append(Issue("R05", supply_f, f"{labels[supply_f]} {won(data[supply_f])} ≠ 품목 합 {won(s)}"))
    # R06·R07 부가세·합계
    supply, vat, total = data.get(supply_f), data.get(vat_f), data.get(total_f)
    if supply is not None and vat is not None and abs(vat - supply * 0.1) > 1:
        out.append(Issue("R06", vat_f, f"{labels[vat_f]} {won(vat)} ≠ {labels[supply_f]}의 10% {won(supply // 10)}"))
    if supply is not None and vat is not None and total is not None and supply + vat != total:
        out.append(Issue("R07", total_f,
                         f"{labels[total_f]} {won(total)} ≠ {won(supply)} + {won(vat)} = {won(supply + vat)}"))
    # R08 사업자번호
    for f in ("vendor_biz_no", "supplier_biz_no", "buyer_biz_no"):
        v = data.get(f)
        if v and f in labels and not biz_no_valid(v):
            out.append(Issue("R08", f, f"{labels[f]} {v} 검증번호 불일치(오인식 또는 오기 가능)"))
    return out


def confidence_issues(doc_type: str, uncertain: list[str]) -> list[Issue]:
    labels = field_labels(doc_type)
    req = set(required_values(doc_type))
    return [Issue("C01", f, f"{labels.get(f, f)}({f}) — 추출기가 확신 없음으로 표시") for f in uncertain if f in req]


def validate(doc_type: str, data: dict[str, Any], uncertain: list[str] | None = None) -> list[Issue]:
    """스키마가 깨졌으면 업무 규칙은 건너뛴다(타입이 틀린 값으로 계산하지 않음)."""
    issues = schema_issues(doc_type, data)
    if issues:
        return issues
    return rule_issues(doc_type, data) + confidence_issues(doc_type, uncertain or [])
