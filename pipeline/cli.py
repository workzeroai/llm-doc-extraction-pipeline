"""docpipe 명령.

    docpipe demo                       # 키 없이 한 번에: 생성 → 분류 → 추출 → 검증 → 분기 → 평가
    docpipe demo --provider gemini     # 키가 있으면 같은 흐름을 실제 LLM으로
    docpipe generate --out data/samples
    docpipe run --docs data/samples/docs --provider mock
    docpipe evaluate --results .docpipe/out/results.jsonl
    docpipe queue                      # 사람 확인 대기열 보기
"""
from __future__ import annotations

import contextlib
import csv
import sys
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.text import Text

from pipeline import ui

app = typer.Typer(add_completion=False, no_args_is_help=True, help="LLM 문서 추출 파이프라인 (키 없으면 모의 추출기)")
DEFAULT_WORKDIR = Path(".docpipe")


def _console() -> Console:
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    return Console(highlight=False)


def _provider(name: str, console: Console):
    from pipeline.providers import MissingCredentialError, get_provider

    try:
        return get_provider(name)
    except MissingCredentialError as e:
        console.print(Text(f"오류: {e}", style="bold red"))
        raise typer.Exit(2) from e
    except ValueError as e:
        console.print(Text(f"오류: {e}", style="bold red"))
        raise typer.Exit(2) from e


@app.command()
def demo(
    workdir: Path = typer.Option(DEFAULT_WORKDIR, help="작업 폴더(문서·결과·리포트)"),
    provider: str = typer.Option("mock", help="mock | gemini | anthropic | openai"),
    simulate: bool = typer.Option(True, "--simulate/--no-simulate", help="공급자 오류 시뮬레이션(데모용)"),
    report: Path | None = typer.Option(None, help="평가 리포트 Markdown 경로(기본: <workdir>/report.md)"),
) -> None:
    """한 번에: 가상 문서 생성 → 텍스트 추출·분류 → 구조화 추출 → 검증 → 분기·알림 → 평가 리포트."""
    from pipeline.demo import run_demo

    console = _console()
    p = _provider(provider, console)
    console.print(Text.assemble(("docpipe demo", "bold"), ("  공급자: ", "bright_black"),
                                (getattr(p, "label", p.name), "bold magenta")))
    run_demo(workdir, console, p, simulate=simulate, report_md=report)


@app.command()
def generate(out: Path = typer.Option(Path("data/samples"), help="출력 폴더"),
             seed: int = typer.Option(42, help="난수 seed")) -> None:
    """가상 문서 PDF 30건 + 정답 JSON 생성."""
    from docgen.generate import generate as gen

    console = _console()
    res = gen(out, seed)
    console.print(f"생성: {len(res.specs)}건 → {res.out_dir.as_posix()} (글꼴 {res.font})")


@app.command()
def run(docs: Path = typer.Option(Path("data/samples/docs"), help="PDF 폴더"),
        out: Path = typer.Option(DEFAULT_WORKDIR / "out", help="결과 폴더"),
        provider: str = typer.Option("mock", help="mock | gemini | anthropic | openai"),
        simulate: bool = typer.Option(False, "--simulate/--no-simulate", help="공급자 오류 시뮬레이션")) -> None:
    """PDF 폴더를 파이프라인에 통과시킨다(평가 없이)."""
    from pipeline.extract import DEMO_FAILURE_PLAN, SimulatedFailures
    from pipeline.route import Notifier
    from pipeline.run import run_pipeline

    console = _console()
    p = _provider(provider, console)
    if simulate:
        p = SimulatedFailures(p, DEMO_FAILURE_PLAN)

    def show(r) -> None:
        line = Text(f"{r.doc_id:<6} ", style="bold")
        line.append_text(ui.status_text(r.status))
        if r.reason_code:
            line.append("  ")
            line.append_text(ui.reason_text(r.reason_code))
            line.append(f"  {r.detail}", style="bright_black")
        console.print(line, overflow="fold")

    summary = run_pipeline(docs, out, p, notifier=Notifier(console=None), on_doc=show,
                           sleep=(lambda _s: None) if simulate else time.sleep)
    console.print(f"저장 {len(summary.saved)}건 · 확인 대기열 {len(summary.review)}건 → {out.as_posix()}")


@app.command()
def evaluate(results: Path = typer.Option(DEFAULT_WORKDIR / "out" / "results.jsonl"),
             gold: Path = typer.Option(Path("data/samples/gold")),
             out: Path = typer.Option(Path("eval/report.md")),
             html: Path | None = typer.Option(None)) -> None:
    """결과를 정답 JSON과 비교해 평가 리포트를 만든다."""
    from eval.evaluate import evaluate_dir

    console = _console()
    rep = evaluate_dir(results, gold, out, html)
    c, n = rep.field_total
    console.print(f"필드 정확도 {ui.pct(c, n)} · 확인 {len(rep.reviewed)}/{rep.n} · "
                  f"결함 검출 {len(rep.caught)}/{len(rep.must)} → {out.as_posix()}")


@app.command()
def queue(workdir: Path = typer.Option(DEFAULT_WORKDIR)) -> None:
    """사람 확인 대기열(review_queue.csv) 보기."""
    console = _console()
    path = workdir / "out" / "review_queue.csv"
    if not path.exists():
        console.print("확인 대기열이 비어 있습니다(먼저 docpipe demo 또는 docpipe run).")
        return
    t = ui.table(expand=True)
    for col, kw in (("문서", {"width": 6}), ("유형", {"width": 6}), ("원인", {"width": 14}), ("내용", {"ratio": 1})):
        t.add_column(col, **kw)
    with path.open(encoding="utf-8-sig") as fp:
        for row in csv.DictReader(fp):
            t.add_row(row["doc_id"], row["doc_type"], ui.reason_text(row["reason_code"]), row["detail"])
    console.print(t)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
