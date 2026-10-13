"""문서 유형 분류(규칙 기반) → 유형별 스키마 선택.

제목·핵심 낱말 점수로 고른다. LLM을 부르기 전에 싸고 빠르게 거르는 단계이며,
점수가 낮거나 1·2위 차이가 작으면 '유형 판별 불가'로 사람 확인에 넘긴다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

KEYWORDS: dict[str, list[tuple[str, int]]] = {
    "contract": [("계약서", 5), ("이하갑", 3), ("계약기간", 2), ("계약금액", 2), ("착수일", 1), ("용역", 1), ("갑과을", 2)],
    "quote": [("견적서", 5), ("quotation", 3), ("견적번호", 2), ("유효기한", 2), ("견적합니다", 2), ("견적금액", 1)],
    "invoice": [("청구서", 5), ("invoice", 3), ("청구번호", 2), ("납부기한", 2), ("공급받는자", 2), ("청구금액", 1)],
}
MIN_SCORE = 5
MIN_MARGIN = 3


@dataclass
class Classification:
    doc_type: str | None
    scores: dict[str, int]
    confidence: float
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.doc_type is not None


def classify(text: str) -> Classification:
    flat = re.sub(r"[\s\"'“”]+", "", text).lower()
    scores = {t: sum(w for kw, w in kws if kw in flat) for t, kws in KEYWORDS.items()}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    (top, s1), (_, s2) = ranked[0], ranked[1]
    conf = round(s1 / (s1 + s2), 2) if s1 + s2 else 0.0
    if s1 < MIN_SCORE:
        return Classification(None, scores, conf, f"유형 낱말 점수가 낮음({s1}점)")
    if s1 - s2 < MIN_MARGIN:
        return Classification(None, scores, conf, f"유형 후보가 둘 이상({ranked[0][0]} {s1} · {ranked[1][0]} {s2})")
    return Classification(top, scores, conf)
