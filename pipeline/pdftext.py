"""PDF → 텍스트 (pdfplumber). 텍스트 층이 없거나 너무 짧으면 '텍스트 추출 실패'."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MIN_CHARS = 30   # 이보다 짧으면 텍스트 층이 없는 스캔 이미지로 본다


@dataclass
class TextResult:
    text: str
    pages: int
    ok: bool
    error: str = ""

    @property
    def chars(self) -> int:
        return len(self.text.strip())


def extract_text(path: Path, min_chars: int = MIN_CHARS) -> TextResult:
    import pdfplumber

    try:
        with pdfplumber.open(str(path)) as pdf:
            pages = len(pdf.pages)
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception as e:  # 손상된 PDF 등
        return TextResult("", 0, False, f"PDF를 열 수 없음: {type(e).__name__}")
    if len(text.strip()) < min_chars:
        return TextResult(text, pages, False,
                          f"텍스트 {len(text.strip())}자 — 텍스트 층이 없는 스캔 이미지로 보임(OCR 필요)")
    return TextResult(text, pages, True)
