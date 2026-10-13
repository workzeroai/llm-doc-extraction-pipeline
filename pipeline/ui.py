"""터미널 화면(rich). 색은 16색 기본 이름만 쓴다(터미널·스크린샷 어디서나 같은 색)."""
from __future__ import annotations

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from pipeline.route import REASONS

REASON_STYLE = {
    "TEXT_EXTRACTION_FAILED": "bold red",
    "CLASSIFICATION_UNCERTAIN": "bold red",
    "PROVIDER_ERROR": "bold red",
    "SCHEMA_MISMATCH": "bold yellow",
    "RULE_VIOLATION": "bold yellow",
    "LOW_CONFIDENCE": "yellow",
}


def table(**kw) -> Table:
    return Table(box=box.ROUNDED, header_style="bold", title_justify="left", title_style="bold", **kw)


def step(console: Console, n: int, total: int, title: str, sub: str = "") -> None:
    head = Text()
    head.append(f" {n}/{total} ", style="bold white on magenta")
    head.append(f" {title}", style="bold")
    if sub:
        head.append(f"  {sub}", style="bright_black")
    console.print()
    console.print(head)


def reason_text(code: str | None) -> Text:
    if not code:
        return Text("-", style="bright_black")
    return Text(f"{REASONS[code]}", style=REASON_STYLE.get(code, "yellow"))


def status_text(status: str) -> Text:
    return Text("저장", style="bold green") if status == "saved" else Text("확인 대기열", style="bold yellow")


def pct(a: int, b: int) -> str:
    return f"{a / b * 100:.1f}%" if b else "-"
