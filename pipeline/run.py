"""파이프라인 기준 구현: PDF → 텍스트 → 유형 분류 → 구조화 추출 → 검증 → 저장/확인 대기열.

    python -m pipeline.run --offline          # 키 없이: 가상 문서 생성 → 파이프라인 → 평가 리포트
    python -m pipeline.run --provider gemini  # GEMINI_API_KEY가 있으면 같은 흐름을 실제 LLM으로
"""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pipeline.classify import classify
from pipeline.extract import extract_with_retry
from pipeline.pdftext import extract_text
from pipeline.providers import OutputFormatError, Provider, ProviderError
from pipeline.route import REASONS, Notifier, Router
from pipeline.validate import RULE_LABELS, validate

DEFAULT_WORKDIR = Path(".docpipe")


@dataclass
class DocResult:
    doc_id: str
    file: str
    status: str                                   # "saved" | "review"
    doc_type: str | None = None
    reason_code: str | None = None                # 확인 대기열로 간 대표 원인
    detail: str = ""
    issues: list[dict[str, Any]] = field(default_factory=list)
    data: dict[str, Any] | None = None
    uncertain_fields: list[str] = field(default_factory=list)
    text_chars: int = 0
    classify_scores: dict[str, int] = field(default_factory=dict)
    attempts: int = 0
    provider_errors: list[str] = field(default_factory=list)
    timings_ms: dict[str, float] = field(default_factory=dict)

    @property
    def total_ms(self) -> float:
        return round(sum(self.timings_ms.values()), 2)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["total_ms"] = self.total_ms
        return d


@dataclass
class RunSummary:
    provider: str
    provider_label: str
    is_llm: bool
    results: list[DocResult]
    out_dir: Path
    alerts: list[str]

    @property
    def saved(self) -> list[DocResult]:
        return [r for r in self.results if r.status == "saved"]

    @property
    def review(self) -> list[DocResult]:
        return [r for r in self.results if r.status == "review"]


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 2)


def process_document(path: Path, provider: Provider, router: Router, *,
                     sleep: Callable[[float], None] = time.sleep) -> DocResult:
    r = DocResult(doc_id=path.stem, file=path.name, status="review")
    pname = provider.name

    def to_review(code: str, detail: str) -> DocResult:
        r.status, r.reason_code, r.detail = "review", code, detail
        router.queue(doc_id=r.doc_id, doc_type=r.doc_type, file=r.file, provider=pname, reason_code=code,
                     detail=detail, data=r.data)
        return r

    # 1. 텍스트 추출
    t0 = time.perf_counter()
    tr = extract_text(path)
    r.timings_ms["text"] = _ms(t0)
    r.text_chars = tr.chars
    if not tr.ok:
        return to_review("TEXT_EXTRACTION_FAILED", tr.error)

    # 2. 유형 분류
    t0 = time.perf_counter()
    c = classify(tr.text)
    r.timings_ms["classify"] = _ms(t0)
    r.classify_scores = c.scores
    if not c.ok:
        return to_review("CLASSIFICATION_UNCERTAIN", c.reason)
    r.doc_type = c.doc_type

    # 3. 구조화 추출
    t0 = time.perf_counter()
    try:
        att = extract_with_retry(provider, doc_id=r.doc_id, text=tr.text, doc_type=c.doc_type, sleep=sleep)
    except ProviderError as e:
        r.timings_ms["extract"] = _ms(t0)
        r.attempts, r.provider_errors = e.attempts, list(e.errors)
        return to_review("PROVIDER_ERROR", str(e))
    except OutputFormatError as e:
        r.timings_ms["extract"] = _ms(t0)
        return to_review("SCHEMA_MISMATCH", f"응답 형식 오류: {e}")
    r.timings_ms["extract"] = _ms(t0)
    r.attempts, r.provider_errors = att.attempts, att.errors
    r.data, r.uncertain_fields = att.output.data, att.output.uncertain_fields  # type: ignore[union-attr]

    # 4. 검증
    t0 = time.perf_counter()
    issues = validate(c.doc_type, r.data, r.uncertain_fields)
    r.timings_ms["validate"] = _ms(t0)
    r.issues = [i.as_dict() for i in issues]

    # 5. 분기
    t0 = time.perf_counter()
    if issues:
        order = list(REASONS)
        main = min(issues, key=lambda i: order.index(i.reason))
        same = [i for i in issues if i.reason == main.reason]
        detail = " / ".join(f"{i.code} {RULE_LABELS[i.code]}: {i.message}" for i in same[:3])
        if len(same) > 3:
            detail += f" 외 {len(same) - 3}건"
        to_review(main.reason, detail)
    else:
        router.save(doc_id=r.doc_id, doc_type=c.doc_type, file=r.file, provider=pname, data=r.data)
        r.status = "saved"
    r.timings_ms["route"] = _ms(t0)
    return r


def run_pipeline(docs_dir: Path, out_dir: Path, provider: Provider, *, notifier: Notifier | None = None,
                 on_doc: Callable[[DocResult], None] | None = None,
                 sleep: Callable[[float], None] = time.sleep) -> RunSummary:
    router = Router(out_dir, notifier)
    router.reset()
    results = []
    try:
        for path in sorted(docs_dir.glob("*.pdf")):
            res = process_document(path, provider, router, sleep=sleep)
            results.append(res)
            if on_doc:
                on_doc(res)
    finally:
        router.close()
    meta = {"provider": provider.name, "model": provider.model, "is_llm": provider.is_llm,
            "provider_label": getattr(provider, "label", provider.name)}
    with (out_dir / "results.jsonl").open("w", encoding="utf-8", newline="\n") as fp:
        fp.write(json.dumps({"_meta": meta}, ensure_ascii=False) + "\n")
        for res in results:
            fp.write(json.dumps(res.to_dict(), ensure_ascii=False) + "\n")
    return RunSummary(provider.name, meta["provider_label"], provider.is_llm, results, out_dir,
                      list(router.notifier.sent))


def main(argv: list[str] | None = None) -> int:
    from docgen.generate import generate_or_bundled
    from eval.evaluate import evaluate_dir
    from pipeline.extract import DEMO_FAILURE_PLAN, SimulatedFailures
    from pipeline.providers import MissingCredentialError, get_provider

    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    ap = argparse.ArgumentParser(description="문서 추출 파이프라인 기준 구현")
    ap.add_argument("--offline", action="store_true", help="키 없이 모의 추출기로 실행(기본)")
    ap.add_argument("--provider", default="mock", help="mock | gemini | anthropic | openai")
    ap.add_argument("--workdir", type=Path, default=DEFAULT_WORKDIR)
    ap.add_argument("--simulate-provider-errors", action="store_true", help="데모용 공급자 오류 시뮬레이션")
    ap.add_argument("--report", type=Path, default=None, help="평가 리포트 Markdown 경로(기본: <workdir>/report.md)")
    args = ap.parse_args(argv)
    name = "mock" if args.offline else args.provider
    try:
        provider: Provider = get_provider(name)
    except MissingCredentialError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 2
    if args.simulate_provider_errors:
        provider = SimulatedFailures(provider, DEMO_FAILURE_PLAN)
    gen = generate_or_bundled(args.workdir / "samples")
    summary = run_pipeline(gen.docs_dir, args.workdir / "out", provider, notifier=Notifier(console=None),
                           sleep=(lambda _s: None) if args.simulate_provider_errors else time.sleep)
    report = evaluate_dir(args.workdir / "out" / "results.jsonl", gen.gold_dir,
                          md_path=args.report or args.workdir / "report.md")
    print(f"공급자: {summary.provider_label}")
    print(f"저장 {len(summary.saved)}건 · 확인 대기열 {len(summary.review)}건 · 리포트 {report.md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
