"""한글 글꼴 찾기. PDF에 글꼴을 임베드해야 하므로 TrueType(.ttf) 파일이 필요하다.

우선순위: 환경 변수 DOCGEN_FONT(+DOCGEN_FONT_BOLD) → Pretendard → 나눔고딕 → 맑은 고딕.
CI(Ubuntu)는 `apt install fonts-nanum`으로 나눔고딕을 쓴다. 글꼴이 없으면 저장소에 들어 있는
생성본(data/samples)을 그대로 쓰면 된다(내용은 같다).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class FontNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class FontPair:
    name: str
    regular: Path
    bold: Path


def _dirs() -> list[Path]:
    out = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        out.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
    out.append(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts")
    home = Path.home()
    out += [home / ".fonts", home / ".local/share/fonts", Path("/usr/share/fonts/truetype/nanum"),
            Path("/usr/share/fonts/truetype"), Path("/usr/share/fonts"), Path("/Library/Fonts"), home / "Library/Fonts"]
    return out


_CANDIDATES = [
    ("Pretendard", "Pretendard-Regular.ttf", "Pretendard-Bold.ttf"),
    ("NanumGothic", "NanumGothic.ttf", "NanumGothicBold.ttf"),
    ("MalgunGothic", "malgun.ttf", "malgunbd.ttf"),
]


def find_korean_font() -> FontPair:
    env = os.environ.get("DOCGEN_FONT")
    if env:
        reg = Path(env)
        bold = Path(os.environ.get("DOCGEN_FONT_BOLD", env))
        if not reg.exists():
            raise FontNotFoundError(f"DOCGEN_FONT 경로가 없습니다: {reg}")
        return FontPair("Custom", reg, bold if bold.exists() else reg)
    for name, reg_file, bold_file in _CANDIDATES:
        for d in _dirs():
            reg = d / reg_file
            if reg.exists():
                bold = d / bold_file
                return FontPair(name, reg, bold if bold.exists() else reg)
    raise FontNotFoundError(
        "한글 TrueType 글꼴을 찾지 못했습니다. Pretendard·나눔고딕을 설치하거나 DOCGEN_FONT=글꼴.ttf 를 지정하세요. "
        "(글꼴 없이도 저장소의 data/samples 생성본으로 데모를 돌릴 수 있습니다)"
    )
