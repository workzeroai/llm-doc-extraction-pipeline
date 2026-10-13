"""README용 데모 이미지 만들기(개발용, 포트폴리오 디자인 키트 필요).

    pip install -e ".[assets]"
    python scripts/make_demo_assets.py --kit ../_design

1. 가상 문서 PDF 3장(계약서·표가 있는 견적서·저품질 스캔)을 PNG로 → docs/shots/sample-docs.png
2. 임시 폴더에서 `docpipe demo`를 돌려 단계별 터미널 출력(ANSI)을 저장 → 키트 터미널 창 PNG → docs/shots/NN-*.png
3. PNG를 묶어 docs/demo.gif
4. 평가 리포트 HTML을 구역별로 캡처 → docs/shots/report-*.png
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

from rich.console import Console

ROOT = Path(__file__).resolve().parents[1]
GIF_STEPS = ["01-generate", "02-classify", "03-extract", "04-validate", "05-route", "06-evaluate"]
REPORT_SECTIONS = {"report-summary": "#summary", "report-safety": "#safety", "report-fields": "#fields"}
SAMPLE_PAGES = [("CT-02", "계약서 · 양식 B"), ("QT-07", "견적서 · 표 안 긴 품목명"), ("QT-10", "저품질 스캔 + OCR 층")]


def render_pages(docs_dir: Path, out: Path) -> None:
    """PDF 첫 페이지 3장을 나란히 놓은 한 장짜리 이미지."""
    import pypdfium2 as pdfium
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    pages = []
    for doc_id, _ in SAMPLE_PAGES:
        pdf = pdfium.PdfDocument(str(docs_dir / f"{doc_id}.pdf"))
        img = pdf[0].render(scale=1.6).to_pil().convert("RGB")
        pdf.close()
        pages.append(img)
    w, h = pages[0].size
    pad, gap, cap_h = 48, 40, 56
    canvas = Image.new("RGB", (pad * 2 + w * 3 + gap * 2, pad * 2 + h + cap_h), "#f8fafc")
    font_path = None
    for cand in (Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts/Pretendard-Bold.ttf",
                 Path("C:/Windows/Fonts/malgunbd.ttf")):
        if cand.exists():
            font_path = cand
            break
    font = ImageFont.truetype(str(font_path), 30) if font_path else ImageFont.load_default()
    draw = ImageDraw.Draw(canvas)
    for i, (img, (doc_id, cap)) in enumerate(zip(pages, SAMPLE_PAGES, strict=True)):
        x = pad + i * (w + gap)
        shadow = Image.new("RGBA", (w + 24, h + 24), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rectangle([12, 14, w + 12, h + 14], fill=(15, 23, 42, 60))
        canvas.paste(shadow.filter(ImageFilter.GaussianBlur(8)), (x - 12, pad - 12), shadow.filter(ImageFilter.GaussianBlur(8)))
        canvas.paste(img, (x, pad))
        draw.rectangle([x, pad, x + w - 1, pad + h - 1], outline="#cbd5e1", width=2)
        draw.text((x, pad + h + 14), f"{doc_id}  {cap}", font=font, fill="#334155")
    canvas.thumbnail((2400, 2400))
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, optimize=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit", type=Path, default=ROOT.parent / "_design", help="포트폴리오 디자인 키트 폴더")
    ap.add_argument("--out", type=Path, default=ROOT / "docs")
    args = ap.parse_args()
    sys.path.insert(0, str(args.kit.resolve()))
    import shots  # type: ignore[import-not-found]

    from pipeline.demo import run_demo
    from pipeline.providers import MockExtractor

    shot_dir = args.out / "shots"
    shot_dir.mkdir(parents=True, exist_ok=True)
    render_pages(ROOT / "data" / "samples" / "docs", shot_dir / "sample-docs.png")
    print("생성:", shot_dir / "sample-docs.png")

    tmp = Path(tempfile.mkdtemp(prefix="docpipe-assets-"))
    prev = Path.cwd()
    try:
        cap = tmp / "capture"
        console = Console(record=True, width=100, force_terminal=True, color_system="standard", highlight=False,
                          file=open(tmp / "stdout.txt", "w", encoding="utf-8"))  # noqa: SIM115
        # 화면에 로컬 임시 경로가 찍히지 않도록 임시 폴더로 이동해 상대 경로(.docpipe)로 실행한다
        os.chdir(tmp)
        try:
            result = run_demo(Path(".docpipe"), console, MockExtractor(), capture_dir=cap)
            report_html = result.report.html_path.resolve() if result.report.html_path else None
        finally:
            os.chdir(prev)
        for ansi in sorted(cap.glob("*.ansi")):
            text = ansi.read_text(encoding="utf-8").strip("\n")
            command = "docpipe demo" if ansi.stem.startswith("01") else None
            out = shot_dir / f"{ansi.stem}.png"
            shots.render_terminal(text, out, f"docpipe demo · {ansi.stem[3:]}", command, width=900, scale=2)
            print("생성:", out)
        frames = [shot_dir / f"{s}.png" for s in GIF_STEPS]
        gif = shots.make_gif(frames, args.out / "demo.gif", duration=2200, width=900)
        print("생성:", gif, f"{gif.stat().st_size / 1e6:.1f}MB")
        if report_html:
            # 캡처용 사본에 키트의 Pretendard @font-face를 넣는다(저장소 리포트 HTML은 글꼴을 싣지 않음)
            from kit_common import font_face_css  # type: ignore[import-not-found]

            styled = tmp / "report-capture.html"
            html = report_html.read_text(encoding="utf-8").replace("<style>", "<style>" + font_face_css(), 1)
            styled.write_text(html, encoding="utf-8")
            for name, selector in REPORT_SECTIONS.items():
                out = shot_dir / f"{name}.png"
                shots.capture_html(str(styled), out, width=1280, height=900, scale=2, selector=selector)
                print("생성:", out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
