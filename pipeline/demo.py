"""`docpipe demo`: 가상 문서 생성 → 텍스트 추출·분류 → 구조화 추출 → 검증 → 분기·알림 → 평가 리포트를 한 번에.

기본은 모의 추출기(규칙·정규식 기반, LLM 아님)라 API 키가 필요 없다. 공급자 오류 시뮬레이션
(QT-04 한 번 실패 후 재시도 성공, IV-05 재시도 소진)을 켜서 공급자 장애 분기도 보여 준다.
"""
from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console, Group
from rich.json import JSON
from rich.panel import Panel
from rich.text import Text

from docgen.documents import DOC_TYPES, HARD_TAGS, TYPE_LABEL, TYPE_PREFIX
from docgen.generate import GenerateResult, generate_or_bundled
from eval.evaluate import EvalReport, evaluate_dir
from pipeline import ui
from pipeline.extract import DEMO_FAILURE_PLAN, SimulatedFailures
from pipeline.providers import Provider
from pipeline.route import REASONS, Notifier
from pipeline.run import RunSummary, run_pipeline

TOTAL = 6
SAMPLE_DOC = "QT-07"   # 표 안 긴 품목명이 줄바꿈된 견적서 — 추출 예시로 보여 준다


@dataclass
class DemoResult:
    gen: GenerateResult
    summary: RunSummary
    report: EvalReport


class _Capture:
    """단계별 출력을 파일로 남긴다(README 스크린샷·GIF용)."""

    def __init__(self, console: Console, out_dir: Path | None):
        self.console, self.out_dir = console, out_dir
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)

    def cut(self, name: str) -> None:
        if self.out_dir:
            text = self.console.export_text(styles=True, clear=True)
            (self.out_dir / f"{name}.ansi").write_text(text, encoding="utf-8")


def run_demo(workdir: Path, console: Console, provider: Provider, *, simulate: bool = True,
             capture_dir: Path | None = None, report_md: Path | None = None) -> DemoResult:
    cap = _Capture(console, capture_dir)
    if simulate:
        provider = SimulatedFailures(provider, DEMO_FAILURE_PLAN)
    label = getattr(provider, "label", provider.name)

    # 1. 가상 문서 ----------------------------------------------------------
    ui.step(console, 1, TOTAL, "가상 문서 생성", "계약서·견적서·청구서 PDF 30건 + 정답 JSON (seed 42)")
    gen = generate_or_bundled(workdir / "samples")
    t = ui.table(expand=False)
    t.add_column("유형", style="bold")
    t.add_column("문서", justify="right")
    t.add_column("일반", justify="right")
    t.add_column("어려운 케이스", justify="right")
    t.add_column("반드시 사람 확인", justify="right")
    for dt in DOC_TYPES:
        specs = [s for s in gen.specs if s.doc_type == dt]
        t.add_row(f"{TYPE_LABEL[dt]} {TYPE_PREFIX[dt]}-01~10", str(len(specs)), str(sum(not s.tags for s in specs)),
                  str(sum(bool(s.tags) for s in specs)), str(sum(s.must_review for s in specs)))
    hard = sum(bool(s.tags) for s in gen.specs)
    console.print(t)
    console.print(Text.assemble(("어려운 케이스 ", "bright_black"), (f"{hard}/{len(gen.specs)}건 ", "bold"),
                                (f"({hard / len(gen.specs):.0%}) — 유형마다 5종씩", "bright_black")))
    console.print(Text(" · ".join(HARD_TAGS.values()), style="cyan"))
    src = "저장소 생성본 복사(한글 글꼴 없음)" if gen.font == "bundled" else f"글꼴 {gen.font} 임베드"
    console.print(Text(f"{gen.docs_dir.as_posix()} · {src} · 회사·인명은 모두 지어낸 가상 데이터", style="bright_black"))
    cap.cut("01-generate")

    # 실행(2~5단계는 이 결과를 단계별로 보여 준다) ---------------------------
    alerts: list[str] = []
    out_dir = workdir / "out"
    summary = run_pipeline(gen.docs_dir, out_dir, provider, notifier=Notifier(console=alerts.append),
                           sleep=_no_wait if simulate else time.sleep)
    by_id = {r.doc_id: r for r in summary.results}
    gold = {s.doc_id: s for s in gen.specs}

    # 2. 텍스트 추출·분류 --------------------------------------------------
    ui.step(console, 2, TOTAL, "텍스트 추출 · 유형 분류", "pdfplumber → 규칙 기반 분류 → 유형별 스키마 선택")
    grid = ui.table(expand=False)
    for dt in DOC_TYPES:
        grid.add_column(TYPE_LABEL[dt], min_width=24)
    for i in range(10):
        row = []
        for dt in DOC_TYPES:
            r = by_id[f"{TYPE_PREFIX[dt]}-{i + 1:02d}"]
            cell = Text(f"{r.doc_id} ", style="bold")
            if r.text_chars < 30:
                cell.append(f"{r.text_chars}자 텍스트 없음", style="bold red")
            else:
                ok = r.doc_type == gold[r.doc_id].doc_type
                cell.append(f"{r.text_chars:>4}자 ", style="bright_black")
                cell.append("→ " + TYPE_LABEL.get(r.doc_type or "", "?"), style="green" if ok else "red")
            if gold[r.doc_id].render != "pdf":
                cell.append(" 스캔", style="yellow")
            row.append(cell)
        grid.add_row(*row)
    console.print(grid)
    texted = [r for r in summary.results if r.text_chars >= 30]
    cls_ok = sum(r.doc_type == gold[r.doc_id].doc_type for r in texted)
    console.print(Text.assemble(("텍스트 추출 ", "bright_black"), (f"{len(texted)}/{len(summary.results)}건", "bold"),
                                (" · 유형 분류 ", "bright_black"), (f"{cls_ok}/{len(texted)} 정답 일치", "bold green"),
                                (" · 텍스트 층 없는 스캔은 추출 단계로 보내지 않음", "bright_black")))
    cap.cut("02-classify")

    # 3. 구조화 추출 --------------------------------------------------------
    ui.step(console, 3, TOTAL, "구조화 추출", label)
    sample = by_id.get(SAMPLE_DOC)
    if sample and sample.data:
        shown = {k: sample.data[k] for k in ("quote_no", "issue_date", "client_name", "items", "subtotal", "total")}
        body = Group(Text(f"{SAMPLE_DOC} 견적서 · 표 안에서 줄이 바뀐 긴 품목명 → 한 줄로", style="bright_black"),
                     JSON(json.dumps(shown, ensure_ascii=False), indent=2))
        console.print(Panel(body, title="출력 (스키마 quote.json 형식)", title_align="left", border_style="magenta",
                            width=96))
    if not summary.is_llm:
        console.print(Text("모의 추출기 = 규칙·정규식 기반 대체 구현(LLM 아님). 키를 넣고 --provider gemini|anthropic|openai 로 "
                           "바꾸면 같은 스키마·같은 검증을 거친다.", style="bright_black"))
    for r in summary.results:
        if r.provider_errors:
            line = Text(f"{r.doc_id} ", style="bold")
            if r.status == "review" and r.reason_code == "PROVIDER_ERROR":
                line.append(f"일시 오류 503 × {r.attempts} → 재시도 소진 → 공급자 오류로 확인 대기열", style="red")
            else:
                line.append(f"일시 오류 503 → 재시도 {r.attempts - 1}회 → 성공", style="yellow")
            line.append(" (시뮬레이션)", style="bright_black")
            console.print(line)
    extracted = [r for r in summary.results if r.data is not None]
    unsure = sum(len(r.uncertain_fields) for r in extracted)
    console.print(Text.assemble(("추출 ", "bright_black"), (f"{len(extracted)}건", "bold"),
                                (" · '확신 없음' 표시 필드 ", "bright_black"), (f"{unsure}개", "bold")))
    cap.cut("03-extract")

    # 4. 검증 ---------------------------------------------------------------
    ui.step(console, 4, TOTAL, "검증", "JSON Schema + 업무 규칙(합계·날짜·필수값·사업자번호)")
    vt = ui.table(expand=True)
    vt.add_column("문서", style="bold", width=6)
    vt.add_column("규칙", width=26, no_wrap=True)
    vt.add_column("내용", ratio=1, overflow="fold")
    for r in extracted:
        for iss in r.issues[:2]:
            vt.add_row(r.doc_id, Text(f"{iss['code']} {_rule_label(iss['code'])}", style="yellow"), iss["message"])
    console.print(vt)
    passed = sum(1 for r in extracted if not r.issues)
    console.print(Text.assemble(("검증 통과 ", "bright_black"), (f"{passed}건", "bold green"),
                                (" · 위반 ", "bright_black"), (f"{len(extracted) - passed}건", "bold yellow"),
                                (" · 추출기가 낸 값을 믿지 않고 코드가 다시 계산한다", "bright_black")))
    cap.cut("04-validate")

    # 5. 분기·알림 ----------------------------------------------------------
    ui.step(console, 5, TOTAL, "분기 · 알림", "통과 → SQLite·CSV / 실패·애매 → review_queue.csv + 알림")
    counts = Counter(r.reason_code for r in summary.review)
    rt = ui.table(expand=False)
    rt.add_column("원인 코드")
    rt.add_column("뜻")
    rt.add_column("건수", justify="right")
    rt.add_column("문서")
    for code in REASONS:
        docs = [r.doc_id for r in summary.review if r.reason_code == code]
        rt.add_row(Text(code, style=ui.REASON_STYLE[code] if docs else "bright_black"), REASONS[code],
                   str(counts.get(code, 0)), ", ".join(docs))
    console.print(Text.assemble(("저장 ", "bright_black"), (f"{len(summary.saved)}건", "bold green"),
                                (f" → {(out_dir / 'docpipe.sqlite3').as_posix()} · extracted/*.csv", "bright_black")))
    console.print(Text.assemble(("확인 대기열 ", "bright_black"), (f"{len(summary.review)}건", "bold yellow"),
                                (f" → {(out_dir / 'review_queue.csv').as_posix()}", "bright_black")))
    console.print(rt)
    for a in alerts[:9]:
        console.print(Text(a, style="yellow"), overflow="fold")
    hook = "웹훅 전송" if Notifier().webhook_url else "웹훅 미설정(DOCPIPE_WEBHOOK_URL) → 콘솔 알림만"
    console.print(Text(hook, style="bright_black"))
    cap.cut("05-route")

    # 6. 평가 ---------------------------------------------------------------
    basis = "모의 추출기 기준" if not summary.is_llm else f"{label} 기준"
    ui.step(console, 6, TOTAL, "평가 리포트", f"정답 JSON 대비 · {basis}")
    report = evaluate_dir(out_dir / "results.jsonl", gen.gold_dir, md_path=report_md or workdir / "report.md",
                          html_path=workdir / "report.html")
    c, n = report.field_total
    exact = sum(d.exact for d in report.docs)
    mt = ui.table(expand=False)
    mt.add_column("지표")
    mt.add_column("값", justify="right")
    mt.add_column("기준", style="bright_black")
    mt.add_row(Text("반드시 확인 문서 → 확인 대기열", style="bold"),
               Text(f"{len(report.caught)}/{len(report.must)}", style="bold green" if not report.missed else "bold red"),
               "필수값 누락·합계 불일치·텍스트 없음")
    mt.add_row(Text("조용한 오류(저장됐지만 틀림)", style="bold"),
               Text(f"{len(report.silent_errors)}건", style="bold green" if not report.silent_errors else "bold yellow"),
               f"자동 저장 {len(summary.saved)}건 중")
    mt.add_row("사람 확인 비율", f"{ui.pct(len(report.reviewed), report.n)}", f"{len(report.reviewed)}/{report.n}건")
    mt.add_row("필드별 정확도", ui.pct(c, n), f"{c}/{n} 필드")
    mt.add_row("문서별 완전 일치율", ui.pct(exact, len(report.extracted)), f"{exact}/{len(report.extracted)}건(추출까지 간 문서)")
    mt.add_row("평균 처리 시간", f"{report.mean_ms:,.0f} ms", f"p95 {report.p95_ms:,.0f} ms")
    console.print(mt)
    if not summary.is_llm:
        console.print(Text("※ 모의 추출기 기준 수치이며 LLM 정확도가 아니다. 실제 LLM은 --provider 로 같은 리포트를 만든다.",
                           style="yellow"))
    console.print(Text(f"리포트: {report.md_path.as_posix() if report.md_path else ''} · "
                       f"{report.html_path.as_posix() if report.html_path else ''}", style="cyan"))
    cap.cut("06-evaluate")
    return DemoResult(gen, summary, report)


def _no_wait(_seconds: float) -> None:
    """시뮬레이션에서는 재시도 대기를 생략한다(처리 시간 지표가 대기 시간으로 부풀지 않게)."""


def _rule_label(code: str) -> str:
    from pipeline.validate import RULE_LABELS

    return RULE_LABELS.get(code, code)
