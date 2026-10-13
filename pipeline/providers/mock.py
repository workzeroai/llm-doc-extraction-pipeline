"""모의 추출기(mock extractor) — LLM이 아니다.

API 키 없이 파이프라인 전체(분류 → 추출 → 검증 → 분기 → 평가)를 돌리기 위한 **규칙·정규식 기반 대체 구현**이다.
LLM 공급자와 같은 출력 모양(스키마 필드 + uncertain_fields)을 낸다.

- 라벨 동의어 사전(예: 계약일·체결일)과 정규식으로 값을 찾는다. 이 저장소의 가상 양식에 맞춰 만들었으므로
  여기서 나온 정확도를 LLM 정확도로 읽으면 안 된다.
- 원문을 고쳐 읽은 경우(OCR 0↔O 보정, 라벨 없이 추정 등)는 해당 필드를 uncertain_fields에 넣는다.
- 문서의 오류를 고치지 않는다(합계가 틀려도 인쇄된 값을 그대로 낸다). 검증은 다음 단계의 일이다.
"""
from __future__ import annotations

import re
from typing import Any

from pipeline.normalize import (
    collapse_ws,
    find_biz_no,
    find_dates,
    fix_ocr_digits,
    parse_amount,
    parse_date,
    parse_int,
)
from pipeline.providers.base import ProviderOutput


def _ns(s: str) -> str:
    return re.sub(r"\s+", "", s)


class _Doc:
    """텍스트 줄 + 라벨 찾기 도우미. 사용한 줄에 OCR 보정이 있었는지 함께 돌려준다."""

    def __init__(self, text: str):
        self.lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        self.uncertain: set[str] = set()

    def label(self, labels: list[str]) -> str | None:
        """라벨로 시작하는 첫 줄의 나머지(값). OCR이 라벨 사이에 넣은 공백은 무시한다."""
        for lab in labels:
            target = _ns(lab)
            for line in self.lines:
                if not _ns(line).startswith(target):
                    continue
                # 원문에서 라벨 글자 수만큼(공백 제외) 소비
                i = consumed = 0
                while i < len(line) and consumed < len(target):
                    if not line[i].isspace():
                        consumed += 1
                    i += 1
                return line[i:].strip(" :：")
        return None

    def mark(self, name: str, flag: bool) -> None:
        if flag:
            self.uncertain.add(name)

    def text_field(self, name: str, labels: list[str], strip: str = "") -> str | None:
        v = self.label(labels)
        if v is None:
            return None
        if strip:
            v = v.replace(strip, "")
        return collapse_ws(v)

    def date_field(self, name: str, labels: list[str]) -> str | None:
        v = self.label(labels)
        iso, fixed = parse_date(v)
        self.mark(name, fixed or (v is not None and iso is None))
        return iso

    def amount_field(self, name: str, labels: list[str]) -> int | None:
        v = self.label(labels)
        n, fixed = parse_amount(v)
        self.mark(name, fixed or (v is not None and n is None))
        return n

    def token_field(self, name: str, labels: list[str], pattern: str) -> str | None:
        v = self.label(labels)
        if v is None:
            return None
        fixed_v, fixed = fix_ocr_digits(v)
        m = re.search(pattern, fixed_v)
        self.mark(name, fixed or m is None)
        return m.group(0) if m else collapse_ws(v)


# ---------------------------------------------------------------- 품목 표

_ROW = re.compile(
    r"^(?:(?P<no>\d{1,2})\s+)?(?P<name>.*?)\s*"
    r"(?P<qty>\d[\d,]*)\s*(?:[가-힣]{1,2})?\s+"
    r"₩?\s*(?P<unit>\d[\d,.]*)\s*원?\s+"
    r"₩?\s*(?P<amount>\d[\d,.]*)\s*원?$"
)
_HEADER_KEYS = ("수량", "단가")
_FOOTER_KEYS = ("공급가액합계", "소계", "공급가액", "부가세", "세액", "VAT", "총견적금액", "견적금액합계", "청구금액합계", "합계")


def _join_name(parts: list[str]) -> str:
    out = ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        out = p if not out else (out + p if p.startswith("(") else out + " " + p)
    return collapse_ws(out) or ""


def parse_items(doc: _Doc) -> list[dict[str, Any]] | None:
    lines = doc.lines
    start = next((i for i, ln in enumerate(lines) if all(k in _ns(ln) for k in _HEADER_KEYS)), None)
    if start is None:
        return None
    entries: list[tuple[str, Any]] = []        # ("row", dict) | ("frag", str)
    any_fixed = False
    for ln in lines[start + 1:]:
        if _ns(ln).startswith(_FOOTER_KEYS):
            break
        fixed_ln, fixed = fix_ocr_digits(ln)
        m = _ROW.match(fixed_ln)
        if m:
            any_fixed |= fixed
            qty, f1 = parse_int(m["qty"])
            unit, f2 = parse_amount(m["unit"])
            amount, f3 = parse_amount(m["amount"])
            any_fixed |= f1 or f2 or f3
            entries.append(("row", {"name": m["name"].strip(), "qty": qty, "unit_price": unit, "amount": amount}))
        else:
            entries.append(("frag", ln))
    rows = [e for e in entries if e[0] == "row"]
    if not rows:
        return None
    # 셀 안에서 줄이 바뀐 품목명: 숫자 줄이 셀 세로 가운데에 오므로 앞뒤 조각을 나눠 붙인다
    ambiguous = False
    idx_rows = [i for i, e in enumerate(entries) if e[0] == "row"]
    prefix: dict[int, list[str]] = {i: [] for i in idx_rows}
    suffix: dict[int, list[str]] = {i: [] for i in idx_rows}
    prev = None
    for k, i in enumerate(idx_rows):
        frags = [e[1] for e in entries[(prev + 1 if prev is not None else 0):i] if e[0] == "frag"]
        if prev is None:
            prefix[i] = frags
        else:
            half = len(frags) // 2
            if len(frags) % 2:
                ambiguous = True
                half += 1
            suffix[prev], prefix[i] = frags[:half], frags[half:]
        prev = i
        if k == len(idx_rows) - 1:
            suffix[i] = [e[1] for e in entries[i + 1:] if e[0] == "frag"]
    items = []
    for i in idx_rows:
        row = entries[i][1]
        if prefix[i] or suffix[i]:
            row["name"] = _join_name([*prefix[i], row["name"], *suffix[i]])
        row["name"] = collapse_ws(row["name"]) or ""
        items.append(row)
    doc.mark("items", any_fixed or ambiguous or any(not it["name"] for it in items))
    return items


# ---------------------------------------------------------------- 유형별


def _contract(doc: _Doc, text: str) -> dict[str, Any]:
    flat = re.sub(r"\s*\n\s*", "", text)
    f: dict[str, Any] = {}
    f["contract_no"] = doc.token_field("contract_no", ["계약번호"], r"[A-Z]{2}-\d{4}-\d+")
    f["title"] = doc.text_field("title", ["계약명", "용역명"])
    m_a = re.search(r"(?m)^(.+?)\(이하\s*\"?갑\"?", text)
    m_b = re.search(r"\(이하\s*\"?갑\"?이라\s*한다\)[와과]\s*(.+?)\(이하\s*\"?을\"?", flat)
    f["client_name"] = collapse_ws(m_a[1]) if m_a else None
    f["vendor_name"] = collapse_ws(m_b[1]) if m_b else None
    # 서명란은 문서 끝에 있다. 본문 줄바꿈으로 '을 체결한다.'처럼 시작하는 줄과 헷갈리지 않게 '대표'가 있는 마지막 줄
    sign_a = next((ln for ln in reversed(doc.lines) if re.match(r"^갑\s", ln) and "대표" in ln), "")
    sign_b = next((ln for ln in reversed(doc.lines) if re.match(r"^을\s", ln) and "대표" in ln), "")
    if f["client_name"] is None and sign_a:          # 전문(前文)이 없으면 서명란에서 추정
        m = re.match(r"^갑\s+(.+?)\s+대표", sign_a)
        f["client_name"] = collapse_ws(m[1]) if m else None
        doc.mark("client_name", True)
    if f["vendor_name"] is None and sign_b:
        m = re.match(r"^을\s+(.+?)\s+(?:사업자등록번호|대표)", sign_b)
        f["vendor_name"] = collapse_ws(m[1]) if m else None
        doc.mark("vendor_name", True)
    biz, fixed = find_biz_no(sign_b or text)
    f["vendor_biz_no"] = biz
    doc.mark("vendor_biz_no", fixed)
    f["contract_date"] = doc.date_field("contract_date", ["계약일", "체결일"])
    period = doc.label(["계약기간"])
    if period is not None:
        dates = find_dates(period)
        f["start_date"] = dates[0] if dates else None
        f["end_date"] = dates[1] if len(dates) > 1 else None
        _, fixed = fix_ocr_digits(period)
        doc.mark("start_date", fixed)
        doc.mark("end_date", fixed)
    else:
        f["start_date"] = doc.date_field("start_date", ["착수일", "시작일"])
        f["end_date"] = doc.date_field("end_date", ["완료일", "종료일"])
    f["supply_amount"] = doc.amount_field("supply_amount", ["계약금액(공급가액)", "공급가액"])
    f["vat"] = doc.amount_field("vat", ["부가가치세", "세액", "부가세"])
    f["total_amount"] = doc.amount_field("total_amount", ["총 계약금액", "합계금액", "합계"])
    f["payment_terms"] = doc.text_field("payment_terms", ["대금 지급 조건", "지급 방법", "지급 조건"])
    m = re.search(r"대표\s*(\S+)", sign_a)
    f["client_signer"] = m[1] if m else None
    m = re.search(r"대표\s*(\S+)", sign_b)
    f["vendor_signer"] = m[1] if m else None
    return f


def _quote(doc: _Doc, text: str) -> dict[str, Any]:
    f: dict[str, Any] = {}
    f["quote_no"] = doc.token_field("quote_no", ["견적번호"], r"Q\d{6}-\d+")
    f["issue_date"] = doc.date_field("issue_date", ["견적일자", "견적일"])
    f["valid_until"] = doc.date_field("valid_until", ["유효기한", "유효기간"])
    f["supplier_name"] = doc.text_field("supplier_name", ["공급자 상호", "상호", "공급자"])
    biz = doc.label(["사업자등록번호"])
    f["supplier_biz_no"], fixed = find_biz_no(biz or "")
    doc.mark("supplier_biz_no", fixed or (biz is not None and f["supplier_biz_no"] is None))
    f["client_name"] = doc.text_field("client_name", ["수신"], strip="귀하")
    f["manager"] = doc.text_field("manager", ["담당자"])
    f["items"] = parse_items(doc)
    f["subtotal"] = doc.amount_field("subtotal", ["공급가액 합계", "소계", "공급가액"])
    f["vat"] = doc.amount_field("vat", ["부가세(10%)", "부가세", "세액", "VAT"])
    f["total"] = doc.amount_field("total", ["총 견적금액", "견적 금액 합계", "합계"])
    return f


def _party(value: str | None) -> tuple[str | None, str | None, bool]:
    """'(주)가람테크 (123-45-67890)' → 이름, 사업자번호."""
    if value is None:
        return None, None, False
    biz, fixed = find_biz_no(value)
    name = re.sub(r"\(\s*[\dOolI|\s-]{10,}\)\s*$", "", value)
    return collapse_ws(name), biz, fixed


def _invoice(doc: _Doc, text: str) -> dict[str, Any]:
    f: dict[str, Any] = {}
    f["invoice_no"] = doc.token_field("invoice_no", ["청구번호"], r"INV-\d{6}-\d+")
    f["issue_date"] = doc.date_field("issue_date", ["발행일", "청구일"])
    f["due_date"] = doc.date_field("due_date", ["납부기한", "지급기한"])
    name, biz, fixed = _party(doc.label(["공급자"]))
    f["supplier_name"], f["supplier_biz_no"] = name, biz
    doc.mark("supplier_biz_no", fixed)
    name, biz, fixed = _party(doc.label(["공급받는자"]))
    f["buyer_name"], f["buyer_biz_no"] = name, biz
    doc.mark("buyer_biz_no", fixed)
    f["items"] = parse_items(doc)
    f["subtotal"] = doc.amount_field("subtotal", ["공급가액"])
    f["vat"] = doc.amount_field("vat", ["세액", "VAT", "부가세"])
    f["total"] = doc.amount_field("total", ["청구금액 합계", "합계"])
    memo = doc.text_field("memo", ["비고"])
    f["memo"] = memo
    return f


_EXTRACTORS = {"contract": _contract, "quote": _quote, "invoice": _invoice}


class MockExtractor:
    """규칙·정규식 기반 모의 추출기. LLM이 아니며, 키 없이 파이프라인을 재현하기 위한 기본 모드."""

    name = "mock"
    model = "rules-v1"
    is_llm = False
    label = "모의 추출기(규칙·정규식 기반, LLM 아님)"

    def extract(self, *, doc_id: str, text: str, doc_type: str, schema: dict[str, Any]) -> ProviderOutput:
        doc = _Doc(text)
        data = _EXTRACTORS[doc_type](doc, text)
        # 스키마 순서에 맞추고 빠진 키는 null
        ordered = {k: data.get(k) for k in schema["properties"]}
        return ProviderOutput(data=ordered, uncertain_fields=sorted(doc.uncertain), raw_text="")
