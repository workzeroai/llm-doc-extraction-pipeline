"""Layout → 텍스트 층이 있는 PDF (reportlab, 한글 글꼴 임베드, 같은 입력이면 같은 바이트)."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, TableStyle
from reportlab.platypus import Table as RLTable

from docgen.documents import Layout, Meta, Note, Para, Sign, Table, Title
from docgen.fonts import FontPair

INK = colors.HexColor("#1e293b")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#94a3b8")
HEAD_BG = colors.HexColor("#ede9fe")
META_BG = colors.HexColor("#f8fafc")

_registered: dict[str, tuple[str, str]] = {}


def register(font: FontPair) -> tuple[str, str]:
    key = str(font.regular)
    if key not in _registered:
        reg, bold = f"KR-{font.name}", f"KR-{font.name}-Bold"
        pdfmetrics.registerFont(TTFont(reg, str(font.regular)))
        pdfmetrics.registerFont(TTFont(bold, str(font.bold)))
        _registered[key] = (reg, bold)
    return _registered[key]


def _styles(reg: str, bold: str) -> dict[str, ParagraphStyle]:
    base = dict(fontName=reg, fontSize=10, leading=15, textColor=INK, wordWrap="CJK")
    return {
        "title": ParagraphStyle("title", **{**base, "fontName": bold, "fontSize": 22, "leading": 28,
                                            "alignment": TA_CENTER}),
        "sub": ParagraphStyle("sub", **{**base, "fontSize": 10, "textColor": MUTED, "alignment": TA_CENTER}),
        "body": ParagraphStyle("body", **base),
        "cell": ParagraphStyle("cell", **{**base, "fontSize": 9.5, "leading": 13}),
        "cell_r": ParagraphStyle("cell_r", **{**base, "fontSize": 9.5, "leading": 13, "alignment": TA_RIGHT}),
        "cell_c": ParagraphStyle("cell_c", **{**base, "fontSize": 9.5, "leading": 13, "alignment": TA_CENTER}),
        "label": ParagraphStyle("label", **{**base, "fontName": bold, "fontSize": 9.5, "leading": 13}),
        "head": ParagraphStyle("head", **{**base, "fontName": bold, "fontSize": 9.5, "leading": 13,
                                          "alignment": TA_CENTER}),
        "note": ParagraphStyle("note", **{**base, "fontSize": 8.5, "leading": 12, "textColor": MUTED}),
        "sign": ParagraphStyle("sign", **{**base, "fontSize": 10.5, "leading": 20, "alignment": TA_LEFT}),
    }


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_pdf(layout: Layout, out: Path, font: FontPair, title: str = "") -> Path:
    reg, bold = register(font)
    st = _styles(reg, bold)
    width = A4[0] - 40 * mm
    story: list = []
    for b in layout.blocks:
        if isinstance(b, Title):
            story += [Paragraph(_esc(b.text), st["title"])]
            if b.sub:
                story += [Paragraph(_esc(b.sub), st["sub"])]
            story.append(Spacer(1, 8 * mm))
        elif isinstance(b, Para):
            story += [Paragraph(_esc(b.text), st["body"]), Spacer(1, 4 * mm)]
        elif isinstance(b, Note):
            story += [Spacer(1, 2 * mm), Paragraph(_esc(b.text), st["note"]), Spacer(1, 3 * mm)]
        elif isinstance(b, Meta):
            data = [[Paragraph(_esc(k), st["label"]), Paragraph(_esc(v), st["cell"])] for k, v in b.pairs]
            t = RLTable(data, colWidths=[width * 0.28, width * 0.72])
            t.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.6, LINE),
                ("BACKGROUND", (0, 0), (0, -1), META_BG),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story += [t, Spacer(1, 5 * mm)]
        elif isinstance(b, Table):
            total_w = sum(b.widths)
            col_w = [width * w / total_w for w in b.widths]
            cell = {"L": st["cell"], "R": st["cell_r"], "C": st["cell_c"]}
            data = [[Paragraph(_esc(h), st["head"]) for h in b.headers]]
            data += [[Paragraph(_esc(v), cell[a]) for v, a in zip(r, b.align, strict=True)] for r in b.rows]
            n_cols = len(b.headers)
            for label, value in b.footer:
                data.append([Paragraph(_esc(label), st["label"])] + [""] * (n_cols - 2)
                            + [Paragraph(_esc(value), st["cell_r"])])
            t = RLTable(data, colWidths=col_w, repeatRows=1)
            style = [
                ("GRID", (0, 0), (-1, -1), 0.6, LINE),
                ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
            first_footer = 1 + len(b.rows)
            for r in range(first_footer, first_footer + len(b.footer)):
                style += [("SPAN", (0, r), (n_cols - 2, r)), ("BACKGROUND", (0, r), (-1, r), META_BG)]
            t.setStyle(TableStyle(style))
            story += [t, Spacer(1, 4 * mm)]
        elif isinstance(b, Sign):
            story.append(Spacer(1, 6 * mm))
            story += [Paragraph(_esc(line), st["sign"]) for line in b.lines]
    out.parent.mkdir(parents=True, exist_ok=True)

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont(reg, 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(A4[0] / 2, 12 * mm, layout.footer)
        canvas.restoreState()

    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=22 * mm,
                            bottomMargin=20 * mm, title=title, author="docgen (가상 데이터)", invariant=1)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out
