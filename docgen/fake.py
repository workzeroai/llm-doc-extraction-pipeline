"""가상 회사·인명·품목·금액·날짜 생성기.

모든 이름은 음절 목록을 조합해 지어낸 것이다(실제 회사·인물과 무관). 같은 seed면 같은 값이 나온다.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

# 회사 이름 = 앞말 + 업종 말. 일부러 흔하지 않은 조합을 쓴다.
_CO_HEAD = ["한빛누리", "다온새솔", "푸른모래", "솔마루", "가람윤슬", "새벽별", "나래온", "바로미", "온새미로", "늘해랑",
            "도담결", "라온숲", "미리내빛", "아라채움", "여울다린", "하람누리", "보람채", "그린나래", "별하솔", "도래울"]
_CO_TAIL = ["테크", "디자인랩", "솔루션즈", "데이터웍스", "커머스", "미디어", "시스템", "컨설팅", "에듀", "랩스"]
_CO_FORM = ["주식회사 {}", "(주){}", "{} 주식회사", "{}"]

_SURNAME = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임", "한", "오", "서", "신", "권"]
_GIVEN = ["서준", "하은", "도윤", "지우", "민서", "예준", "수아", "시우", "지안", "건우", "서연", "유진", "태민", "다인", "현우",
          "소율", "준호", "채원", "은재", "가온"]

# (품목, 기준 단가, 단위)
CATALOG: list[tuple[str, int, str]] = [
    ("웹사이트 유지보수", 450_000, "개월"),
    ("클라우드 서버 운영 대행", 380_000, "개월"),
    ("랜딩 페이지 디자인", 1_200_000, "식"),
    ("상세 페이지 촬영·편집", 650_000, "건"),
    ("데이터 라벨링(이미지)", 120, "건"),
    ("업무 자동화 컨설팅", 900_000, "일"),
    ("사내 교육 워크숍", 1_500_000, "회"),
    ("검색광고 운영 대행", 700_000, "개월"),
    ("CRM 메시지 템플릿 제작", 80_000, "건"),
    ("보안 점검 리포트", 2_200_000, "식"),
    ("영상 자막 작업", 35_000, "분"),
    ("모바일 앱 QA 테스트", 300_000, "일"),
]
LONG_ITEMS = [
    "고객 문의 자동 분류 시스템 구축 및 운영 담당자 교육(2회 포함)",
    "브랜드 리뉴얼에 따른 온라인 판매처 상세 페이지 전면 개편 디자인",
    "월간 성과 리포트 자동화 대시보드 구축과 데이터 연결 설정 작업",
]
SERVICE_TITLES = ["홈페이지 리뉴얼 용역", "업무 자동화 구축 용역", "온라인 광고 운영 대행", "고객 데이터 정비 용역",
                  "사내 교육 프로그램 운영", "쇼핑몰 운영 대행", "콘텐츠 제작 용역", "데이터 분석 리포트 용역"]
PAYMENT_TERMS = ["계약 체결 후 선금 30%, 완료 후 잔금 70% 지급", "매월 말일 기준 월 단위 정산 후 익월 10일 지급",
                 "검수 완료 후 30일 이내 일시 지급", "착수금 50%, 중도금 없이 잔금 50% 완료 후 지급"]

KOR_DIGITS = "영일이삼사오육칠팔구"


def company(rng: random.Random, exclude: set[str] | None = None) -> str:
    exclude = exclude or set()
    for _ in range(100):
        name = rng.choice(_CO_FORM).format(rng.choice(_CO_HEAD) + rng.choice(_CO_TAIL))
        if name not in exclude:
            return name
    raise RuntimeError("회사 이름 후보가 부족합니다")


def person(rng: random.Random) -> str:
    return rng.choice(_SURNAME) + rng.choice(_GIVEN)


def biz_no_checksum(first9: str) -> int:
    """사업자등록번호 마지막 자리(검증번호) 계산."""
    weights = [1, 3, 7, 1, 3, 7, 1, 3, 5]
    digits = [int(c) for c in first9]
    total = sum(d * w for d, w in zip(digits, weights, strict=True)) + (digits[8] * 5) // 10
    return (10 - total % 10) % 10


def biz_no(rng: random.Random) -> str:
    """검증번호가 맞는 가상 사업자등록번호(000-00-00000)."""
    first9 = f"{rng.randint(101, 899)}{rng.randint(81, 88)}{rng.randint(1000, 9999)}"
    full = first9 + str(biz_no_checksum(first9))
    return f"{full[:3]}-{full[3:5]}-{full[5:]}"


def rand_date(rng: random.Random, start: date = date(2026, 1, 5), end: date = date(2026, 9, 25)) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    day = min(d.day, [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)


# ---------------------------------------------------------------- 표기

DATE_STYLES = ("iso", "dot", "dot_space", "korean", "short", "slash")


def fmt_date(d: date, style: str) -> str:
    if style == "iso":
        return d.isoformat()
    if style == "dot":
        return f"{d.year}.{d.month:02d}.{d.day:02d}"
    if style == "dot_space":
        return f"{d.year}. {d.month}. {d.day}."
    if style == "korean":
        return f"{d.year}년 {d.month}월 {d.day}일"
    if style == "short":
        return f"{d.year % 100:02d}.{d.month:02d}.{d.day:02d}"
    if style == "slash":
        return f"{d.year}/{d.month}/{d.day}"
    raise ValueError(style)


def won(n: int, style: str = "won") -> str:
    if style == "won":
        return f"{n:,}원"
    if style == "krw":
        return f"₩{n:,}"
    if style == "plain":
        return f"{n:,}"
    raise ValueError(style)


def korean_amount(n: int) -> str:
    """12,300,000 → '금 일천이백삼십만원정' (계약서에 흔한 한글 금액 표기)."""
    if n <= 0:
        return "금 영원정"
    units = [(10**8, "억"), (10**4, "만"), (1, "")]
    small = [(1000, "천"), (100, "백"), (10, "십"), (1, "")]
    out = []
    rest = n
    for big, big_name in units:
        chunk, rest = divmod(rest, big)
        if not chunk:
            continue
        part = ""
        for s, s_name in small:
            d, chunk = divmod(chunk, s)
            if d:
                part += KOR_DIGITS[d] + s_name
        out.append(part + big_name)
    return "금 " + "".join(out) + "원정"
