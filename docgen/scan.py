"""저품질 스캔 문서 흉내: Layout을 이미지로 그린 뒤 기울기·잡음·흐림·JPEG 손실을 넣어 PDF에 붙인다.

- scan_image: 이미지 한 장뿐(텍스트 층 없음) → 파이프라인은 '텍스트 추출 실패'로 사람 확인에 넘겨야 한다.
- scan_ocr  : 이미지 + 보이지 않는 OCR 텍스트 층. OCR 오류(0→O, 1→l, 쉼표→점, 띄어쓰기 끼어듦,
              드물게 숫자·글자 오인식)를 일부러 섞는다. 복합기 스캔 PDF가 흔히 이런 모양이다.
"""
from __future__ import annotations

import io
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas

from docgen.documents import Layout, Meta, Note, Para, Sign, Table, Title
from docgen.fonts import FontPair
from docgen.pdf import register

W, H = 1240, 1754          # A4 @150dpi
MARGIN = 120


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=font) > width and cur:
            lines.append(cur)
            cur = ch.lstrip()
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines or [""]


def draw_layout(layout: Layout, font: FontPair) -> Image.Image:
    img = Image.new("L", (W, H), 255)
    dr = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(str(font.bold), 46)
    f_body = ImageFont.truetype(str(font.regular), 22)
    f_bold = ImageFont.truetype(str(font.bold), 21)
    f_cell = ImageFont.truetype(str(font.regular), 20)
    f_note = ImageFont.truetype(str(font.regular), 17)
    inner = W - 2 * MARGIN
    y = 130
    for b in layout.blocks:
        if isinstance(b, Title):
            tw = dr.textlength(b.text, font=f_title)
            dr.text(((W - tw) / 2, y), b.text, font=f_title, fill=20)
            y += 64
            if b.sub:
                sw = dr.textlength(b.sub, font=f_note)
                dr.text(((W - sw) / 2, y), b.sub, font=f_note, fill=90)
                y += 30
            y += 40
        elif isinstance(b, Para | Note):
            fnt = f_body if isinstance(b, Para) else f_note
            for line in _wrap(dr, b.text, fnt, inner):
                dr.text((MARGIN, y), line, font=fnt, fill=30 if isinstance(b, Para) else 90)
                y += 34 if isinstance(b, Para) else 28
            y += 18
        elif isinstance(b, Meta):
            lw = int(inner * 0.28)
            for k, v in b.pairs:
                vlines = _wrap(dr, v, f_cell, inner - lw - 24)
                h = 18 + 30 * len(vlines)
                dr.rectangle([MARGIN, y, MARGIN + inner, y + h], outline=60, width=2)
                dr.line([MARGIN + lw, y, MARGIN + lw, y + h], fill=60, width=2)
                dr.text((MARGIN + 12, y + 9), k, font=f_bold, fill=20)
                for i, vl in enumerate(vlines):
                    dr.text((MARGIN + lw + 12, y + 9 + 30 * i), vl, font=f_cell, fill=20)
                y += h
            y += 30
        elif isinstance(b, Table):
            total = sum(b.widths)
            xs = [MARGIN]
            for w in b.widths:
                xs.append(xs[-1] + int(inner * w / total))
            rows = [b.headers, *b.rows]
            for r_i, row in enumerate(rows):
                cells = [_wrap(dr, c, f_cell, xs[i + 1] - xs[i] - 16) for i, c in enumerate(row)]
                h = 16 + 28 * max(len(c) for c in cells)
                dr.rectangle([xs[0], y, xs[-1], y + h], outline=60, width=2)
                for x in xs[1:-1]:
                    dr.line([x, y, x, y + h], fill=60, width=2)
                for i, lines in enumerate(cells):
                    for j, line in enumerate(lines):
                        fnt = f_bold if r_i == 0 else f_cell
                        tw = dr.textlength(line, font=fnt)
                        a = "C" if r_i == 0 else b.align[i]
                        x = xs[i] + 8 if a == "L" else (xs[i + 1] - 8 - tw if a == "R" else (xs[i] + xs[i + 1] - tw) / 2)
                        dr.text((x, y + 8 + 28 * j), line, font=fnt, fill=20)
                y += h
            for label, value in b.footer:
                h = 44
                dr.rectangle([xs[0], y, xs[-1], y + h], outline=60, width=2)
                dr.line([xs[-2], y, xs[-2], y + h], fill=60, width=2)
                dr.text((xs[0] + 10, y + 10), label, font=f_bold, fill=20)
                tw = dr.textlength(value, font=f_cell)
                dr.text((xs[-1] - 8 - tw, y + 10), value, font=f_cell, fill=20)
                y += h
            y += 26
        elif isinstance(b, Sign):
            y += 20
            for line in b.lines:
                dr.text((MARGIN, y), line, font=f_body, fill=20)
                y += 44
    fw = dr.textlength(layout.footer, font=f_note)
    dr.text(((W - fw) / 2, H - 90), layout.footer, font=f_note, fill=110)
    return img


def degrade(img: Image.Image, rng: random.Random, strength: float = 1.0) -> Image.Image:
    """기울기·흐림·대비 저하·잡음·JPEG 손실."""
    angle = rng.uniform(0.6, 1.4) * strength * rng.choice([-1, 1])
    out = img.rotate(angle, resample=Image.BICUBIC, fillcolor=245)
    out = out.filter(ImageFilter.GaussianBlur(0.7 * strength))
    out = out.point(lambda p: int(40 + p * 0.78))  # 대비 저하(누런 종이 느낌)
    noise = Image.frombytes("L", out.size, rng.randbytes(out.size[0] * out.size[1]))
    out = Image.blend(out, noise, 0.10 * strength)
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=int(45 - 10 * strength))
    return Image.open(io.BytesIO(buf.getvalue()))


_DIGIT_LOOKALIKE = {"0": "O", "1": "l"}
_HARD_DIGIT = {"8": "3", "6": "5", "3": "8"}
_HANGUL_CONFUSE = {"사": "시", "주": "추", "원": "윈", "회": "희", "명": "멍"}


def ocr_noise(lines: list[str], rng: random.Random, level: float = 1.0) -> list[str]:
    """OCR 텍스트 층 흉내. 대부분은 사람이(또는 LLM이) 문맥으로 고칠 수 있는 오류이고, 일부는 못 고친다."""
    out = []
    for line in lines:
        s = []
        for i, ch in enumerate(line):
            nxt = line[i + 1] if i + 1 < len(line) else ""
            prv = line[i - 1] if i else ""
            r = rng.random()
            if ch in _DIGIT_LOOKALIKE and r < 0.22 * level:
                s.append(_DIGIT_LOOKALIKE[ch])
            elif ch in _HARD_DIGIT and r < 0.03 * level:
                s.append(_HARD_DIGIT[ch])
            elif ch == "," and prv.isdigit() and r < 0.15 * level:
                s.append(".")
            elif ch in _HANGUL_CONFUSE and r < 0.04 * level:
                s.append(_HANGUL_CONFUSE[ch])
            elif "가" <= ch <= "힣" and "가" <= nxt <= "힣" and r < 0.05 * level:
                s.append(ch + " ")
            else:
                s.append(ch)
        out.append("".join(s))
    return out


def render_scan(layout: Layout, out: Path, font: FontPair, rng: random.Random, with_ocr_layer: bool) -> Path:
    img = degrade(draw_layout(layout, font), rng)
    out.parent.mkdir(parents=True, exist_ok=True)
    c = rl_canvas.Canvas(str(out), pagesize=A4, invariant=1)
    c.setAuthor("docgen (가상 데이터)")
    buf = io.BytesIO()
    img.convert("L").save(buf, "JPEG", quality=60)
    c.drawImage(ImageReader(io.BytesIO(buf.getvalue())), 0, 0, width=A4[0], height=A4[1])
    if with_ocr_layer:
        reg, _ = register(font)
        t = c.beginText()
        t.setTextRenderMode(3)          # 보이지 않는 텍스트(스캔 PDF의 OCR 층과 같은 방식)
        t.setFont(reg, 9)
        t.setTextOrigin(40, A4[1] - 60)
        t.setLeading(14)
        for line in ocr_noise(layout.text_lines(), rng):
            t.textLine(line)
        c.drawText(t)
    c.showPage()
    c.save()
    return out
