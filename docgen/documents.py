"""문서 30건의 값·양식·정답(gold)을 만든다.

한 문서 = 정답 값(fields) + 화면 배치(Layout). PDF 렌더러(pdf.py)와 스캔 렌더러(scan.py)가
같은 Layout을 그리므로 정답과 문서 내용이 어긋나지 않는다.

유형별 10건 = 일반 5건 + 어려운 케이스 5건(전체 50%):
  idx 5  날짜 표기 혼용      (같은 문서 안에 2026년 3월 5일 / 26.03.05 / 2026/3/5 …)
  idx 6  표 안 금액·한글 금액 (금액이 표 안에만 있거나 '금 일천이백만원정' 표기, 긴 품목명 줄바꿈)
  idx 7  필드 누락           (계약서·청구서: 필수값 누락 → 확인 필요 / 견적서: 선택값 누락 → null로 저장)
  idx 8  합계 불일치         (문서 자체의 계산 오류 → 확인 필요)
  idx 9  저품질 스캔         (계약서: 텍스트 층 없는 이미지 / 견적서·청구서: 잡음 섞인 OCR 텍스트 층)
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from docgen import fake

DOC_TYPES = ("contract", "quote", "invoice")
TYPE_PREFIX = {"contract": "CT", "quote": "QT", "invoice": "IV"}
TYPE_LABEL = {"contract": "계약서", "quote": "견적서", "invoice": "청구서"}
PER_TYPE = 10

HARD_TAGS = {5: "날짜 표기 혼용", 6: "표 안 금액·한글 금액", 7: "필드 누락", 8: "합계 불일치", 9: "저품질 스캔"}


# ---------------------------------------------------------------- 배치 모델


@dataclass
class Title:
    text: str
    sub: str = ""


@dataclass
class Para:
    text: str


@dataclass
class Meta:
    """라벨-값 2열 표."""
    pairs: list[tuple[str, str]]


@dataclass
class Table:
    headers: list[str]
    rows: list[list[str]]
    widths: list[float]               # 상대 폭
    align: list[str]                  # "L" | "R" | "C"
    footer: list[list[str]] = field(default_factory=list)  # 표 아래 합계 행(라벨, 값)


@dataclass
class Sign:
    lines: list[str]


@dataclass
class Note:
    text: str


Block = Title | Para | Meta | Table | Sign | Note


@dataclass
class Layout:
    blocks: list[Block]
    footer: str = "본 문서는 데모용 가상 문서입니다. 실제 회사·인물·거래와 무관합니다."

    def text_lines(self) -> list[str]:
        """사람이 읽는 순서의 텍스트 줄(스캔 문서의 OCR 텍스트 층에 쓴다)."""
        out: list[str] = []
        for b in self.blocks:
            if isinstance(b, Title):
                out.append(b.text)
                if b.sub:
                    out.append(b.sub)
            elif isinstance(b, Para | Note):
                out.append(b.text)
            elif isinstance(b, Meta):
                out.extend(f"{k} {v}" for k, v in b.pairs)
            elif isinstance(b, Table):
                out.append(" ".join(b.headers))
                out.extend(" ".join(r) for r in b.rows)
                out.extend(" ".join(r) for r in b.footer)
            elif isinstance(b, Sign):
                out.extend(b.lines)
        out.append(self.footer)
        return out


@dataclass
class DocSpec:
    doc_id: str
    doc_type: str
    index: int
    variant: str                       # "A" | "B" 양식 변형
    tags: list[str]
    render: str                        # "pdf" | "scan_image" | "scan_ocr"
    fields: dict[str, Any]             # 정답 값(문서에 인쇄된 값 그대로, 없으면 None)
    layout: Layout
    must_review: bool                  # 문서 자체에 결함이 있어 반드시 사람 확인으로 가야 하는가
    expected_reasons: list[str]

    @property
    def file_name(self) -> str:
        return f"{self.doc_id}.pdf"

    def gold(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "file": self.file_name,
            "doc_type": self.doc_type,
            "variant": self.variant,
            "difficulty": self.tags,
            "render": self.render,
            "must_review": self.must_review,
            "expected_reasons": self.expected_reasons,
            "fields": self.fields,
        }


# ---------------------------------------------------------------- 공통 도우미


def _date_styles(rng: random.Random, idx: int, variant: str) -> list[str]:
    """문서 안 날짜 표기. 일반 문서는 한 가지로 통일, 날짜 혼용 문서는 섞는다."""
    if idx == 5:
        styles = ["korean", "short", "slash", "dot_space"]
        rng.shuffle(styles)
        return styles
    base = {"A": ["iso", "korean"], "B": ["dot", "dot_space"]}[variant][idx % 2]
    return [base] * 4


def _items(rng: random.Random, n: int, long_names: bool = False) -> list[dict[str, Any]]:
    picks = rng.sample(fake.CATALOG, n)
    items = []
    for i, (name, base, _unit) in enumerate(picks):
        qty = rng.randint(1, 12) if base >= 10_000 else rng.choice([500, 1200, 3000])
        unit_price = max(10, round(base * rng.choice([0.8, 0.9, 1.0, 1.1, 1.25]), -3 if base >= 10_000 else 0))
        if long_names and i < len(fake.LONG_ITEMS):
            name = fake.LONG_ITEMS[i]
        items.append({"name": name, "qty": qty, "unit_price": int(unit_price), "amount": int(qty * unit_price)})
    return items


def _render_mode(doc_type: str, idx: int) -> str:
    if idx != 9:
        return "pdf"
    return "scan_image" if doc_type == "contract" else "scan_ocr"


# ---------------------------------------------------------------- 계약서


def build_contract(idx: int, rng: random.Random, variant: str) -> DocSpec:
    client = fake.company(rng)
    vendor = fake.company(rng, {client})
    signer_a, signer_b = fake.person(rng), fake.person(rng)
    c_date = fake.rand_date(rng)
    start = c_date + timedelta(days=rng.randint(0, 14))
    end = fake.add_months(start, rng.randint(2, 11)) - timedelta(days=1)
    supply = rng.randint(30, 480) * 100_000
    vat = supply // 10
    total = supply + vat
    if idx == 8:                       # 합계 불일치: 인쇄된 총액이 공급가액 + 부가세와 다르다
        total = supply + vat + rng.choice([100_000, 1_000_000])
    styles = _date_styles(rng, idx, variant)
    f = {
        "contract_no": f"CT-2026-{rng.randint(100, 999)}{idx}",
        "title": rng.choice(fake.SERVICE_TITLES),
        "client_name": client,
        "vendor_name": vendor,
        "vendor_biz_no": fake.biz_no(rng),
        "contract_date": c_date.isoformat(),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "supply_amount": supply,
        "vat": vat,
        "total_amount": total,
        "payment_terms": rng.choice(fake.PAYMENT_TERMS),
        "client_signer": signer_a,
        "vendor_signer": signer_b,
    }
    if idx == 7:                       # 필드 누락: 완료일(필수)이 문서에 없다
        f["end_date"] = None
    d = lambda iso, k: fake.fmt_date(date.fromisoformat(iso), styles[k])  # noqa: E731
    blocks: list[Block] = [
        Title("용역 계약서" if variant == "A" else "용 역 계 약 서", f["title"]),
        Para(f"{client}(이하 \"갑\"이라 한다)와 {vendor}(이하 \"을\"이라 한다)는 "
             f"아래와 같이 용역 계약을 체결한다."),
    ]
    period = (f"{d(f['start_date'], 1)} ~ {d(f['end_date'], 2)}" if f["end_date"]
              else f"{d(f['start_date'], 1)}부터 (완료일은 별도 협의)")
    if idx == 6:                       # 금액이 표 안에만, 총액은 한글 금액 표기
        pairs = [("계약번호", f["contract_no"]), ("계약명", f["title"]), ("계약일", d(f["contract_date"], 0)),
                 ("계약기간", period), ("대금 지급 조건", f["payment_terms"])]
        blocks.append(Meta(pairs))
        blocks.append(Para("계약 금액은 아래 표와 같다."))
        blocks.append(Table(["구분", "금액", "비고"],
                            [["공급가액", fake.won(supply, "plain"), "부가가치세 별도"],
                             ["부가가치세", fake.won(vat, "plain"), "공급가액의 10%"],
                             ["합계", fake.korean_amount(total), "부가가치세 포함"]],
                            [1.2, 2.2, 1.6], ["L", "R", "L"]))
    elif variant == "A":
        pairs = [("계약번호", f["contract_no"]), ("계약명", f["title"]), ("계약일", d(f["contract_date"], 0)),
                 ("계약기간", period), ("계약금액(공급가액)", fake.won(supply)), ("부가가치세", fake.won(vat)),
                 ("총 계약금액", fake.won(total)), ("대금 지급 조건", f["payment_terms"])]
        blocks.append(Meta(pairs))
    else:
        pairs = [("계약 번호", f["contract_no"]), ("용역명", f["title"]), ("체결일", d(f["contract_date"], 0)),
                 ("착수일", d(f["start_date"], 1))]
        if f["end_date"]:
            pairs.append(("완료일", d(f["end_date"], 2)))
        pairs += [("공급가액", fake.won(supply, "krw")), ("세액", fake.won(vat, "krw")),
                  ("합계금액", fake.won(total, "krw")), ("지급 방법", f["payment_terms"])]
        blocks.append(Meta(pairs))
    blocks.append(Para("갑과 을은 신의에 따라 이 계약을 성실히 이행하며, 계약서 2부를 작성하여 각 1부씩 보관한다."))
    blocks.append(Sign([f"갑  {client}  대표 {signer_a} (인)",
                        f"을  {vendor}  사업자등록번호 {f['vendor_biz_no']}  대표 {signer_b} (인)"]))
    must, reasons = _expect(idx, "contract")
    return DocSpec(_id("contract", idx), "contract", idx, variant, _tags(idx), _render_mode("contract", idx), f,
                   Layout(blocks), must, reasons)


# ---------------------------------------------------------------- 견적서


def build_quote(idx: int, rng: random.Random, variant: str) -> DocSpec:
    supplier = fake.company(rng)
    client = fake.company(rng, {supplier})
    issue = fake.rand_date(rng)
    valid = issue + timedelta(days=rng.choice([14, 30, 30, 60]))
    items = _items(rng, rng.randint(2, 4), long_names=idx == 6)
    subtotal = sum(i["amount"] for i in items)
    if idx == 8:                       # 합계 불일치: 소계가 품목 합과 다르다
        subtotal += rng.choice([50_000, 200_000])
    vat = subtotal // 10
    total = subtotal + vat
    styles = _date_styles(rng, idx, variant)
    f = {
        "quote_no": f"Q{issue.strftime('%y%m%d')}-{rng.randint(10, 99)}",
        "issue_date": issue.isoformat(),
        "valid_until": valid.isoformat(),
        "supplier_name": supplier,
        "supplier_biz_no": fake.biz_no(rng),
        "client_name": client,
        "manager": fake.person(rng),
        "items": items,
        "subtotal": subtotal,
        "vat": vat,
        "total": total,
    }
    if idx == 7:                       # 선택값 누락: 유효기한·담당자 없음 → null로 저장돼야 한다(지어내면 오류)
        f["valid_until"] = None
        f["manager"] = None
    d = lambda iso, k: fake.fmt_date(date.fromisoformat(iso), styles[k])  # noqa: E731
    money = "krw" if idx == 6 else ("won" if variant == "A" else "plain")
    pairs = [("견적번호", f["quote_no"]), ("견적일자", d(f["issue_date"], 0))]
    if f["valid_until"]:
        pairs.append(("유효기한", d(f["valid_until"], 1)))
    pairs += [("수신", f"{client} 귀하"), ("공급자 상호", supplier), ("사업자등록번호", f["supplier_biz_no"])]
    if f["manager"]:
        pairs.append(("담당자", f["manager"]))
    headers = (["No", "품목", "수량", "단가", "금액"] if variant == "A"
               else ["번호", "내역", "수량", "단가(원)", "공급가액(원)"])
    rows = [[str(n), it["name"], f"{it['qty']:,}", fake.won(it["unit_price"], money), fake.won(it["amount"], money)]
            for n, it in enumerate(items, 1)]
    footer = [["공급가액 합계" if variant == "A" else "소계", fake.won(subtotal, money)],
              ["부가세(10%)" if variant == "A" else "세액", fake.won(vat, money)],
              ["총 견적금액" if variant == "A" else "견적 금액 합계", fake.won(total, money)]]
    blocks: list[Block] = [
        Title("견 적 서" if variant == "A" else "견적서", "QUOTATION"),
        Meta(pairs),
        Para("아래와 같이 견적합니다." + (" (부가가치세 별도 표기)" if variant == "B" else "")),
        Table(headers, rows, [0.5, 3.4, 0.8, 1.4, 1.6], ["C", "L", "R", "R", "R"], footer),
        Note("본 견적은 유효기한 내 발주 시 적용되며, 세부 범위는 협의에 따라 조정될 수 있습니다."),
    ]
    must, reasons = _expect(idx, "quote")
    return DocSpec(_id("quote", idx), "quote", idx, variant, _tags(idx), _render_mode("quote", idx), f,
                   Layout(blocks), must, reasons)


# ---------------------------------------------------------------- 청구서


def build_invoice(idx: int, rng: random.Random, variant: str) -> DocSpec:
    supplier = fake.company(rng)
    buyer = fake.company(rng, {supplier})
    issue = fake.rand_date(rng)
    due = issue + timedelta(days=rng.choice([14, 20, 30]))
    items = _items(rng, rng.randint(2, 4))
    printed = [dict(i) for i in items]
    if idx == 8:                       # 합계 불일치: 품목 1건의 금액이 수량×단가와 다르다(소계는 인쇄된 금액의 합)
        printed[0]["amount"] = printed[0]["amount"] + rng.choice([100_000, 1_000_000])
    subtotal = sum(i["amount"] for i in printed)
    vat = subtotal // 10
    total = subtotal + vat
    styles = _date_styles(rng, idx, variant)
    f = {
        "invoice_no": f"INV-{issue.strftime('%Y%m')}-{rng.randint(1000, 9999)}",
        "issue_date": issue.isoformat(),
        "due_date": due.isoformat(),
        "supplier_name": supplier,
        "supplier_biz_no": fake.biz_no(rng),
        "buyer_name": buyer,
        "buyer_biz_no": fake.biz_no(rng),
        "items": printed,
        "subtotal": subtotal,
        "vat": vat,
        "total": total,
        "memo": rng.choice(["입금 계좌는 별도 안내드립니다.", "세금계산서는 발행일 기준으로 발행됩니다.",
                            "문의는 담당 부서로 연락 바랍니다."]),
    }
    if idx == 7:                       # 필드 누락: 납부기한(필수)이 없다
        f["due_date"] = None
    d = lambda iso, k: fake.fmt_date(date.fromisoformat(iso), styles[k])  # noqa: E731
    pairs = [("청구번호", f["invoice_no"]), ("발행일", d(f["issue_date"], 0))]
    if f["due_date"]:
        pairs.append(("납부기한", d(f["due_date"], 1)))
    pairs += [("공급자", f"{supplier} ({f['supplier_biz_no']})"), ("공급받는자", f"{buyer} ({f['buyer_biz_no']})")]
    unit_suffix = idx == 6
    headers = ["품목", "수량", "단가", "공급가액"] if variant == "A" else ["내역", "수량", "단가", "금액"]
    rows = []
    for it in printed:
        unit = next((u for n, _b, u in fake.CATALOG if n == it["name"]), "")
        qty = f"{it['qty']:,}{unit}" if unit_suffix else f"{it['qty']:,}"
        rows.append([it["name"], qty, fake.won(it["unit_price"], "won" if unit_suffix else "plain"),
                     fake.won(it["amount"], "won" if unit_suffix else "plain")])
    vat_label = "VAT" if idx == 6 else "세액"
    footer = [["공급가액", fake.won(subtotal)], [vat_label, fake.won(vat)], ["청구금액 합계", fake.won(total)]]
    blocks: list[Block] = [
        Title("청구서" if variant == "A" else "거래명세서 겸 청구서", "INVOICE"),
        Meta(pairs),
        Table(headers, rows, [3.4, 1.0, 1.5, 1.7], ["L", "R", "R", "R"], footer),
        Note(f"비고: {f['memo']}"),
    ]
    must, reasons = _expect(idx, "invoice")
    return DocSpec(_id("invoice", idx), "invoice", idx, variant, _tags(idx), _render_mode("invoice", idx), f,
                   Layout(blocks), must, reasons)


# ---------------------------------------------------------------- 조립


def _id(doc_type: str, idx: int) -> str:
    return f"{TYPE_PREFIX[doc_type]}-{idx + 1:02d}"


def _tags(idx: int) -> list[str]:
    return [HARD_TAGS[idx]] if idx in HARD_TAGS else []


def _expect(idx: int, doc_type: str) -> tuple[bool, list[str]]:
    """문서 결함 → 반드시 사람 확인으로 가야 하는 경우와 기대 원인 코드."""
    if idx == 7 and doc_type in ("contract", "invoice"):
        return True, ["RULE_VIOLATION"]
    if idx == 8:
        return True, ["RULE_VIOLATION"]
    if idx == 9 and doc_type == "contract":
        return True, ["TEXT_EXTRACTION_FAILED"]
    return False, []


BUILDERS = {"contract": build_contract, "quote": build_quote, "invoice": build_invoice}


def build_all(seed: int = 42) -> list[DocSpec]:
    specs = []
    for t_i, doc_type in enumerate(DOC_TYPES):
        for idx in range(PER_TYPE):
            rng = random.Random(seed * 1000 + t_i * 100 + idx)
            variant = "A" if idx % 2 == 0 else "B"
            specs.append(BUILDERS[doc_type](idx, rng, variant))
    return specs
