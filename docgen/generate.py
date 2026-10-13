"""가상 문서 PDF 30건 + 정답 JSON 생성.

    python -m docgen.generate --out data/samples --seed 42

산출물: <out>/docs/*.pdf, <out>/gold/*.json, <out>/manifest.json
seed가 같으면 정답 JSON은 항상 같고, 같은 글꼴이면 PDF 바이트도 같다.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
from dataclasses import dataclass
from pathlib import Path

from docgen.documents import DOC_TYPES, TYPE_LABEL, DocSpec, build_all
from docgen.fonts import FontNotFoundError, FontPair, find_korean_font

DEFAULT_SEED = 42
BUNDLED = Path(__file__).resolve().parents[1] / "data" / "samples"


@dataclass
class GenerateResult:
    out_dir: Path
    specs: list[DocSpec]
    font: str            # 사용한 글꼴 이름 또는 "bundled"

    @property
    def docs_dir(self) -> Path:
        return self.out_dir / "docs"

    @property
    def gold_dir(self) -> Path:
        return self.out_dir / "gold"


def write_gold(specs: list[DocSpec], gold_dir: Path) -> None:
    gold_dir.mkdir(parents=True, exist_ok=True)
    for s in specs:
        (gold_dir / f"{s.doc_id}.json").write_text(
            json.dumps(s.gold(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def manifest(specs: list[DocSpec], seed: int) -> dict:
    hard = [s for s in specs if s.tags]
    return {
        "seed": seed,
        "total": len(specs),
        "by_type": {t: sum(1 for s in specs if s.doc_type == t) for t in DOC_TYPES},
        "hard_cases": len(hard),
        "hard_ratio": round(len(hard) / len(specs), 3),
        "must_review": [s.doc_id for s in specs if s.must_review],
        "docs": [{"doc_id": s.doc_id, "type": s.doc_type, "label": TYPE_LABEL[s.doc_type], "variant": s.variant,
                  "difficulty": s.tags, "render": s.render} for s in specs],
    }


def generate(out_dir: Path, seed: int = DEFAULT_SEED, font: FontPair | None = None) -> GenerateResult:
    from docgen.pdf import render_pdf
    from docgen.scan import render_scan

    font = font or find_korean_font()
    specs = build_all(seed)
    docs = out_dir / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    for s in specs:
        path = docs / s.file_name
        if s.render == "pdf":
            render_pdf(s.layout, path, font, title=f"{TYPE_LABEL[s.doc_type]} {s.doc_id}")
        else:
            rng = random.Random(seed * 7919 + hash_id(s.doc_id))
            render_scan(s.layout, path, font, rng, with_ocr_layer=s.render == "scan_ocr")
    write_gold(specs, out_dir / "gold")
    (out_dir / "manifest.json").write_text(json.dumps(manifest(specs, seed), ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8", newline="\n")
    return GenerateResult(out_dir, specs, font.name)


def hash_id(doc_id: str) -> int:
    """파이썬 hash()는 실행마다 달라서 쓰지 않는다."""
    return sum((i + 1) * ord(c) for i, c in enumerate(doc_id))


def generate_or_bundled(out_dir: Path, seed: int = DEFAULT_SEED) -> GenerateResult:
    """한글 글꼴이 있으면 새로 생성, 없으면 저장소에 들어 있는 생성본(data/samples)을 복사한다."""
    try:
        return generate(out_dir, seed)
    except FontNotFoundError:
        if seed != DEFAULT_SEED or not BUNDLED.exists():
            raise
        if out_dir.resolve() != BUNDLED.resolve():
            shutil.copytree(BUNDLED, out_dir, dirs_exist_ok=True)
        return GenerateResult(out_dir, build_all(seed), "bundled")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="가상 문서 PDF + 정답 JSON 생성")
    ap.add_argument("--out", type=Path, default=BUNDLED)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args(argv)
    res = generate(args.out, args.seed)
    print(f"생성: {len(res.specs)}건 → {res.out_dir} (글꼴 {res.font})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
