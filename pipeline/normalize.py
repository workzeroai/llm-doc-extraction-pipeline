"""문서 표기 → 정규 값(날짜 ISO, 원 단위 정수) 변환과 OCR 숫자 오인식 보정.

모의 추출기가 쓰고, 실제 LLM 공급자는 프롬프트로 같은 규칙을 요구한다.
반환값의 두 번째 항목(fixed)은 "원문을 고쳐서 읽었다"는 뜻으로, 추출기가 해당 필드를 불확실로 표시하는 근거가 된다.
"""
from __future__ import annotations

import re
from datetime import date

_LOOKALIKE = {"O": "0", "o": "0", "l": "1", "I": "1", "|": "1"}
_SEP = ".,/-:"


def fix_ocr_digits(s: str) -> tuple[str, bool]:
    """숫자 사이·옆의 O/l/I를 0/1로 고친다(예: '1,2OO,OOO' → '1,200,000', 'l68' → '168').

    영문 단어(INV, QUOTATION 등)는 건드리지 않도록 이웃 글자가 숫자일 때만 바꾼다.
    """
    out: list[str] = []
    changed = False
    n = len(s)
    for i, ch in enumerate(s):
        if ch in _LOOKALIKE:
            nxt = s[i + 1] if i + 1 < n else ""
            nxt2 = s[i + 2] if i + 2 < n else ""
            j, skipped = len(out) - 1, 0
            while j >= 0 and out[j] in " " + _SEP and skipped < 2:  # '9. l.'처럼 구분자·공백 건너 숫자
                j, skipped = j - 1, skipped + 1
            prev_num = j >= 0 and out[j].isdigit()
            next_num = nxt.isdigit() or (nxt in _LOOKALIKE and nxt2.isdigit()) or (nxt in ",." and nxt2.isdigit())
            if prev_num or next_num:
                out.append(_LOOKALIKE[ch])
                changed = True
                continue
        out.append(ch)
    return "".join(out), changed


# ---------------------------------------------------------------- 날짜

_DATE_PATTERNS = [
    re.compile(r"(?P<y>\d{4})\s*년\s*(?P<m>\d{1,2})\s*월\s*(?P<d>\d{1,2})\s*일"),
    re.compile(r"(?P<y>\d{4})\s*[-./]\s*(?P<m>\d{1,2})\s*[-./]\s*(?P<d>\d{1,2})\.?"),
    re.compile(r"(?<!\d)(?P<y>\d{2})\s*[./]\s*(?P<m>\d{1,2})\s*[./]\s*(?P<d>\d{1,2})(?!\d)"),
]


def parse_date(s: str | None) -> tuple[str | None, bool]:
    """'2026년 3월 5일' · '2026. 3. 5.' · '26.03.05' · '2026/3/5' · '2026-03-05' → '2026-03-05'."""
    if not s:
        return None, False
    text, fixed = fix_ocr_digits(s)
    for pat in _DATE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        y = int(m["y"])
        if y < 100:
            y += 2000
        try:
            return date(y, int(m["m"]), int(m["d"])).isoformat(), fixed
        except ValueError:
            return None, True
    return None, fixed


def find_dates(s: str) -> list[str]:
    """한 줄 안의 날짜를 순서대로 모두 찾는다('2026-04-05 ~ 2026-09-04' 같은 기간 표기용)."""
    text, _ = fix_ocr_digits(s)
    found: list[tuple[int, str]] = []
    taken: list[tuple[int, int]] = []
    for pat in _DATE_PATTERNS:
        for m in pat.finditer(text):
            if any(a <= m.start() < b for a, b in taken):
                continue
            iso, _ = parse_date(m.group(0))
            if iso:
                found.append((m.start(), iso))
                taken.append((m.start(), m.end()))
    return [iso for _, iso in sorted(found)]


# ---------------------------------------------------------------- 금액

_KOR_NUM = {"영": 0, "일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6, "칠": 7, "팔": 8, "구": 9}
_KOR_SMALL = {"십": 10, "백": 100, "천": 1000}
_KOR_BIG = {"만": 10**4, "억": 10**8, "조": 10**12}
_KOR_AMOUNT = re.compile(r"금\s*([영일이삼사오육칠팔구십백천만억조\s]+?)\s*원정?")
_NUM_TOKEN = re.compile(r"\d[\d,.]*\d|\d")


def parse_korean_number(s: str) -> int | None:
    """'일천이백삼십만' → 12,300,000. 형식이 아니면 None."""
    s = re.sub(r"\s+", "", s)
    if not s or any(ch not in _KOR_NUM and ch not in _KOR_SMALL and ch not in _KOR_BIG for ch in s):
        return None
    total = section = digit = 0
    for ch in s:
        if ch in _KOR_NUM:
            digit = _KOR_NUM[ch]
        elif ch in _KOR_SMALL:
            section += (digit or 1) * _KOR_SMALL[ch]
            digit = 0
        else:
            section += digit
            total += (section or 1) * _KOR_BIG[ch]
            section = digit = 0
    return total + section + digit


def parse_amount(s: str | None) -> tuple[int | None, bool]:
    """'12,000,000원' · '₩12,000,000' · '금 일천이백만원정' · OCR '1,2OO.OOO' → 12000000."""
    if not s:
        return None, False
    m = _KOR_AMOUNT.search(s)
    if m:
        n = parse_korean_number(m.group(1))
        if n is not None:
            return n, False
    text, fixed = fix_ocr_digits(s)
    tok = _NUM_TOKEN.search(text)
    if not tok:
        return None, fixed
    raw = tok.group(0)
    if "." in raw:
        # 원화 금액에 소수점은 없으므로 '.'은 천 단위 구분자를 잘못 읽은 것으로 본다
        if re.fullmatch(r"\d{1,3}([.,]\d{3})+", raw):
            fixed = True
        else:
            raw = raw.split(".")[0]
            fixed = True
    return int(re.sub(r"[,.]", "", raw)), fixed


def parse_int(s: str | None) -> tuple[int | None, bool]:
    """수량: '12개월' · '1,200' → 정수."""
    if not s:
        return None, False
    text, fixed = fix_ocr_digits(s)
    tok = re.search(r"\d[\d,]*", text)
    if not tok:
        return None, fixed
    return int(tok.group(0).replace(",", "")), fixed


BIZ_NO = re.compile(r"(?<!\d)(\d{3})\s*-\s*(\d{2})\s*-\s*(\d{5})(?!\d)")


def find_biz_no(s: str) -> tuple[str | None, bool]:
    text, fixed = fix_ocr_digits(s)
    m = BIZ_NO.search(text)
    if not m:
        return None, fixed
    return f"{m[1]}-{m[2]}-{m[3]}", fixed


def collapse_ws(s: str | None) -> str | None:
    if s is None:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s or None
