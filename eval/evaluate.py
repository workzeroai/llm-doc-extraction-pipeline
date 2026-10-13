"""평가: 파이프라인 결과(results.jsonl)를 정답 JSON과 비교해 리포트를 만든다.

    python -m eval.evaluate --results .docpipe/out/results.jsonl --gold data/samples/gold --out eval/report.md

지표
- 필드별 정확도: 추출까지 간 문서에서, 정답과 같은 값을 낸 비율(문자열은 공백만 정리해 비교, 품목은 행 전체 일치)
- 문서별 완전 일치율: 모든 필드가 정답과 같은 문서 비율
- 사람 확인 비율: 확인 대기열로 간 문서 비율
- 반드시 확인 문서 검출률: 문서 자체에 결함(필수값 누락·합계 불일치·텍스트 없음)이 있는 문서를 대기열로 보냈는가
- 조용한 오류: 저장소로 갔지만 틀린 필드가 있는 문서(가장 위험한 실패)
- 평균 처리 시간: 문서 1건의 텍스트 추출~분기 시간
"""
from __future__ import annotations

import argparse
import html
import json
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pipeline.normalize import collapse_ws
from pipeline.route import REASONS
from schemas import DOC_TYPES, TYPE_LABEL, field_labels, field_names

TAG_ORDER = ["일반", "날짜 표기 혼용", "표 안 금액·한글 금액", "필드 누락", "합계 불일치", "저품질 스캔"]


def same_value(pred: Any, gold: Any) -> bool:
    if gold is None or pred is None:
        return pred is None and gold is None
    if isinstance(gold, str):
        return isinstance(pred, str) and collapse_ws(pred) == collapse_ws(gold)
    if isinstance(gold, list):
        if not isinstance(pred, list) or len(pred) != len(gold):
            return False
        return all(isinstance(p, dict) and all(same_value(p.get(k), g[k]) for k in g) for p, g in
                   zip(pred, gold, strict=True))
    return pred == gold and type(pred) is type(gold)


@dataclass
class DocEval:
    doc_id: str
    doc_type: str
    tags: list[str]
    must_review: bool
    expected_reasons: list[str]
    status: str
    reason_code: str | None
    detail: str
    extracted: bool
    type_ok: bool
    wrong_fields: list[str]
    n_fields: int
    total_ms: float

    @property
    def exact(self) -> bool:
        return self.extracted and self.type_ok and not self.wrong_fields


@dataclass
class EvalReport:
    meta: dict[str, Any]
    docs: list[DocEval]
    field_stats: dict[str, dict[str, list[int]]]          # type → field → [correct, total]
    stage_ms: dict[str, float]
    md_path: Path | None = None
    html_path: Path | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    # -------- 집계
    @property
    def n(self) -> int:
        return len(self.docs)

    @property
    def extracted(self) -> list[DocEval]:
        return [d for d in self.docs if d.extracted and d.type_ok]

    @property
    def field_total(self) -> tuple[int, int]:
        c = sum(v[0] for t in self.field_stats.values() for v in t.values())
        n = sum(v[1] for t in self.field_stats.values() for v in t.values())
        return c, n

    @property
    def reviewed(self) -> list[DocEval]:
        return [d for d in self.docs if d.status == "review"]

    @property
    def must(self) -> list[DocEval]:
        return [d for d in self.docs if d.must_review]

    @property
    def caught(self) -> list[DocEval]:
        return [d for d in self.must if d.status == "review"]

    @property
    def missed(self) -> list[DocEval]:
        return [d for d in self.must if d.status != "review"]

    @property
    def reason_matched(self) -> list[DocEval]:
        return [d for d in self.caught if d.reason_code in d.expected_reasons]

    @property
    def silent_errors(self) -> list[DocEval]:
        return [d for d in self.docs if d.status == "saved" and (d.wrong_fields or not d.type_ok)]

    @property
    def optional_review(self) -> list[DocEval]:
        return [d for d in self.reviewed if not d.must_review]

    @property
    def mean_ms(self) -> float:
        return round(statistics.fmean(d.total_ms for d in self.docs), 1) if self.docs else 0.0

    @property
    def p95_ms(self) -> float:
        xs = sorted(d.total_ms for d in self.docs)
        return round(xs[min(len(xs) - 1, int(0.95 * len(xs)))], 1) if xs else 0.0

    def by_tag(self) -> list[tuple[str, int, int, int, int]]:
        rows = []
        for tag in TAG_ORDER:
            ds = [d for d in self.docs if (d.tags[0] if d.tags else "일반") == tag]
            if ds:
                rows.append((tag, len(ds), sum(d.exact for d in ds), sum(d.status == "review" for d in ds),
                             sum(d.must_review for d in ds)))
        return rows

    def reason_counts(self) -> Counter:
        return Counter(d.reason_code for d in self.reviewed)


def _pct(a: int, b: int) -> str:
    return f"{a / b * 100:.1f}%" if b else "-"


def load_results(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    meta: dict[str, Any] = {}
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if "_meta" in obj:
            meta = obj["_meta"]
        else:
            rows.append(obj)
    return meta, rows


def load_gold(gold_dir: Path) -> dict[str, dict[str, Any]]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(gold_dir.glob("*.json"))}


def evaluate(meta: dict[str, Any], results: list[dict[str, Any]], gold: dict[str, dict[str, Any]]) -> EvalReport:
    stats: dict[str, dict[str, list[int]]] = {t: {f: [0, 0] for f in field_names(t)} for t in DOC_TYPES}
    docs: list[DocEval] = []
    stage: dict[str, list[float]] = defaultdict(list)
    for r in results:
        g = gold[r["doc_id"]]
        gt = g["doc_type"]
        extracted = r.get("data") is not None
        type_ok = r.get("doc_type") == gt
        wrong: list[str] = []
        if extracted and type_ok:
            for f in field_names(gt):
                ok = same_value(r["data"].get(f), g["fields"].get(f))
                stats[gt][f][0] += ok
                stats[gt][f][1] += 1
                if not ok:
                    wrong.append(f)
        for k, v in r.get("timings_ms", {}).items():
            stage[k].append(v)
        docs.append(DocEval(r["doc_id"], gt, g["difficulty"], g["must_review"], g["expected_reasons"], r["status"],
                            r.get("reason_code"), r.get("detail", ""), extracted, type_ok, wrong,
                            len(field_names(gt)), r.get("total_ms", 0.0)))
    stage_ms = {k: round(statistics.fmean(v), 2) for k, v in stage.items()}
    return EvalReport(meta, docs, stats, stage_ms)


# ---------------------------------------------------------------- Markdown


def _basis(meta: dict[str, Any]) -> str:
    return "모의 추출기 기준" if not meta.get("is_llm") else f"{meta.get('provider_label', '')} 기준"


def to_markdown(rep: EvalReport) -> str:
    m = rep.meta
    c, n = rep.field_total
    ex = rep.extracted
    lines: list[str] = []
    a = lines.append
    a(f"# 평가 리포트 — {_basis(m)}")
    a("")
    if not m.get("is_llm"):
        a("> **이 수치는 LLM 정확도가 아닙니다.** 키 없이 돌리는 기본 모드의 **모의 추출기(규칙·정규식 기반 대체 구현, LLM 아님)**를 "
          "가상 문서 30건에 돌린 결과입니다. 모의 추출기는 이 저장소의 가상 양식에 맞춰 만들었으므로 필드 정확도는 높게 나오는 것이 정상이며, "
          "이 리포트에서 볼 것은 **실패가 사람 확인 대기열로 정확히 가는지**(검증·분기 설계)입니다. "
          "실제 LLM 평가는 API 키를 넣고 `python -m pipeline.run --provider gemini`(또는 `anthropic`, `openai`)로 실행하면 같은 형식의 리포트가 생성됩니다.")
    else:
        a(f"> 공급자: **{m.get('provider_label')}** · 가상 문서 30건 기준")
    a("")
    a(f"- 공급자: {m.get('provider_label', m.get('provider'))}")
    a(f"- 문서: {rep.n}건(계약서·견적서·청구서 각 10건, 어려운 케이스 {sum(1 for d in rep.docs if d.tags)}건) · 모두 생성 스크립트로 만든 가상 문서")
    if rep.extra.get("simulated"):
        a(f"- 공급자 오류 시뮬레이션: {rep.extra['simulated']} (데모 설정, 재시도 대기 시간은 생략)")
    a("")
    a("## 요약")
    a("")
    a("| 지표 | 값 | 기준 |")
    a("|---|---|---|")
    a(f"| 필드별 정확도(전체) | **{_pct(c, n)}** ({c}/{n}) | 추출까지 간 {len(ex)}건의 필드 |")
    a(f"| 문서별 완전 일치율 | **{_pct(sum(d.exact for d in rep.docs), len(ex))}** ({sum(d.exact for d in rep.docs)}/{len(ex)}) | 추출까지 간 문서 |")
    a(f"| 문서별 완전 일치율(전체 30건) | {_pct(sum(d.exact for d in rep.docs), rep.n)} ({sum(d.exact for d in rep.docs)}/{rep.n}) | 텍스트 추출 실패·공급자 오류 포함 |")
    a(f"| 사람 확인 비율 | **{_pct(len(rep.reviewed), rep.n)}** ({len(rep.reviewed)}/{rep.n}) | 확인 대기열로 간 문서 |")
    a(f"| 반드시 확인 문서 검출률 | **{_pct(len(rep.caught), len(rep.must))}** ({len(rep.caught)}/{len(rep.must)}) | 결함 있는 문서 중 대기열로 간 비율 |")
    a(f"| 원인 코드 일치 | {len(rep.reason_matched)}/{len(rep.caught)} | 기대한 원인 코드로 분류됨 |")
    a(f"| 조용한 오류(저장됐지만 틀림) | **{len(rep.silent_errors)}건** | 자동 저장 {sum(d.status == 'saved' for d in rep.docs)}건 중 |")
    a(f"| 평균 처리 시간 | {rep.mean_ms:,.0f} ms/건 (p95 {rep.p95_ms:,.0f} ms) | 텍스트 추출~분기, {_basis(m)} |")
    a("")
    a("## 실패 방어 — 결함 문서를 놓치지 않는가")
    a("")
    a("| 문서 | 결함 | 기대 원인 | 실제 결과 | 내용 |")
    a("|---|---|---|---|---|")
    for d in rep.must:
        res = f"확인 대기열 · {d.reason_code}" if d.status == "review" else "**저장됨(놓침)**"
        a(f"| {d.doc_id} | {', '.join(d.tags)} | {', '.join(d.expected_reasons)} | {res} | {_md(d.detail)} |")
    a("")
    if rep.missed:
        a(f"**놓친 문서 {len(rep.missed)}건:** {', '.join(d.doc_id for d in rep.missed)}")
    else:
        a("결함 문서는 모두 확인 대기열로 갔고, 저장소에는 들어가지 않았습니다.")
    a("")
    a("### 결함은 없지만 확인으로 간 문서")
    a("")
    if rep.optional_review:
        a("| 문서 | 난이도 | 원인 | 내용 |")
        a("|---|---|---|---|")
        for d in rep.optional_review:
            a(f"| {d.doc_id} | {', '.join(d.tags) or '일반'} | {d.reason_code} | {_md(d.detail)} |")
    else:
        a("없음")
    a("")
    a("### 조용한 오류 — 검증을 통과해 저장됐지만 정답과 다른 값")
    a("")
    if rep.silent_errors:
        a("| 문서 | 난이도 | 틀린 필드 |")
        a("|---|---|---|")
        for d in rep.silent_errors:
            a(f"| {d.doc_id} | {', '.join(d.tags) or '일반'} | {', '.join(d.wrong_fields) or '유형 분류'} |")
        a("")
        a("규칙(합계·날짜·사업자번호 검증번호)으로 잡을 수 없는 글자 오류는 저장소까지 갈 수 있습니다. "
          "이름·번호 같은 문자열 필드는 원본 대조나 거래처 마스터 조회가 다음 방어선입니다.")
    else:
        a("없음")
    a("")
    a("## 난이도별")
    a("")
    a("| 난이도 | 문서 | 완전 일치 | 확인 대기열 | 반드시 확인 |")
    a("|---|---|---|---|---|")
    for tag, k, exact, rev, must in rep.by_tag():
        a(f"| {tag} | {k} | {exact} | {rev} | {must} |")
    a("")
    a("## 확인 대기열 원인 코드")
    a("")
    a("| 원인 코드 | 뜻 | 건수 |")
    a("|---|---|---|")
    counts = rep.reason_counts()
    for code, label in REASONS.items():
        a(f"| `{code}` | {label} | {counts.get(code, 0)} |")
    a("")
    a("## 필드별 정확도")
    a("")
    for t in DOC_TYPES:
        labels = field_labels(t)
        st = rep.field_stats[t]
        tc, tn = sum(v[0] for v in st.values()), sum(v[1] for v in st.values())
        a(f"**{TYPE_LABEL[t]}** — {_pct(tc, tn)} ({tc}/{tn})")
        a("")
        a("| 필드 | 이름 | 정확도 |")
        a("|---|---|---|")
        for f, (ok, tot) in st.items():
            a(f"| `{f}` | {labels[f]} | {_pct(ok, tot)} ({ok}/{tot}) |")
        a("")
    a("## 문서별 결과")
    a("")
    a("| 문서 | 유형 | 난이도 | 결과 | 원인 | 틀린 필드 | 처리 ms |")
    a("|---|---|---|---|---|---|---|")
    for d in rep.docs:
        status = "저장" if d.status == "saved" else "확인 대기열"
        wrong = "추출 전 중단" if not d.extracted else (", ".join(d.wrong_fields) or "-")
        a(f"| {d.doc_id} | {TYPE_LABEL[d.doc_type]} | {', '.join(d.tags) or '일반'} | {status} | "
          f"{d.reason_code or '-'} | {wrong} | {d.total_ms:,.0f} |")
    a("")
    a("## 단계별 평균 처리 시간")
    a("")
    a("| 단계 | 평균 ms |")
    a("|---|---|")
    names = {"text": "텍스트 추출", "classify": "유형 분류", "extract": "구조화 추출", "validate": "검증", "route": "분기·저장"}
    for k, v in rep.stage_ms.items():
        a(f"| {names.get(k, k)} | {v:,.1f} |")
    a("")
    a("## 다시 만들기")
    a("")
    a("```bash")
    a("python -m pipeline.run --offline --simulate-provider-errors --report eval/report.md   # 모의 추출기")
    a("python -m pipeline.run --provider gemini --report eval/report.gemini.md               # 실제 LLM(키 필요)")
    a("```")
    a("")
    a("처리 시간은 실행 환경에 따라 달라집니다. 나머지 수치는 같은 seed·같은 공급자면 같습니다.")
    return "\n".join(lines) + "\n"


def _md(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


# ---------------------------------------------------------------- HTML (스크린샷용)


def to_html(rep: EvalReport) -> str:
    m = rep.meta
    c, n = rep.field_total
    ex = rep.extracted
    exact = sum(d.exact for d in rep.docs)
    e = html.escape

    def card(label: str, value: str, sub: str, tone: str = "") -> str:
        return f'<div class="card {tone}"><div class="lab">{e(label)}</div><div class="val">{e(value)}</div><div class="sub">{e(sub)}</div></div>'

    cards = "".join([
        card("반드시 확인 문서 검출", f"{len(rep.caught)}/{len(rep.must)}", "결함 문서 → 확인 대기열", "ok" if not rep.missed else "bad"),
        card("조용한 오류", f"{len(rep.silent_errors)}건", f"자동 저장 {sum(d.status == 'saved' for d in rep.docs)}건 중", "warn" if rep.silent_errors else "ok"),
        card("사람 확인 비율", _pct(len(rep.reviewed), rep.n), f"{len(rep.reviewed)}/{rep.n}건"),
        card("필드별 정확도", _pct(c, n), f"{c}/{n} 필드 · 추출 {len(ex)}건"),
        card("문서 완전 일치", _pct(exact, len(ex)), f"{exact}/{len(ex)}건"),
        card("평균 처리 시간", f"{rep.mean_ms:,.0f} ms", f"p95 {rep.p95_ms:,.0f} ms"),
    ])
    def result_cell(d: DocEval) -> str:
        if d.status == "review":
            return f"<span class='pill ok'>확인 대기열</span> <span class='mono'>{e(d.reason_code or '')}</span>"
        return "<span class='pill bad'>놓침</span>"

    must_rows = "".join(
        f"<tr><td class='mono'>{e(d.doc_id)}</td><td>{e(', '.join(d.tags))}</td><td class='mono'>{e(', '.join(d.expected_reasons))}</td>"
        f"<td>{result_cell(d)}</td><td class='detail'>{e(d.detail)}</td></tr>" for d in rep.must)
    opt_rows = "".join(
        f"<tr><td class='mono'>{e(d.doc_id)}</td><td>{e(', '.join(d.tags) or '일반')}</td><td class='mono'>{e(d.reason_code or '')}</td>"
        f"<td class='detail'>{e(d.detail)}</td></tr>" for d in rep.optional_review) or "<tr><td colspan=4>없음</td></tr>"
    silent_rows = "".join(
        f"<tr><td class='mono'>{e(d.doc_id)}</td><td>{e(', '.join(d.tags) or '일반')}</td><td class='mono'>{e(', '.join(d.wrong_fields))}</td></tr>"
        for d in rep.silent_errors) or "<tr><td colspan=3>없음</td></tr>"
    tag_rows = "".join(f"<tr><td>{e(t)}</td><td>{k}</td><td>{x}</td><td>{r}</td><td>{mu}</td></tr>"
                       for t, k, x, r, mu in rep.by_tag())
    field_blocks = []
    for t in DOC_TYPES:
        labels = field_labels(t)
        st = rep.field_stats[t]
        tc, tn = sum(v[0] for v in st.values()), sum(v[1] for v in st.values())
        bars = "".join(
            f"<div class='frow'><span class='fname'>{e(labels[f])}</span><span class='bar'><i style='width:{(ok / tot * 100) if tot else 0:.1f}%'></i></span>"
            f"<span class='fval'>{ok}/{tot}</span></div>" for f, (ok, tot) in st.items())
        field_blocks.append(f"<div class='fcol'><h3>{e(TYPE_LABEL[t])} <small>{_pct(tc, tn)}</small></h3>{bars}</div>")
    basis = _basis(m)
    warn = ("<div class='banner'><b>LLM 정확도가 아닙니다.</b> 키 없이 도는 <b>모의 추출기(규칙·정규식 기반, LLM 아님)</b>를 가상 문서 30건에 돌린 결과입니다. "
            "볼 것은 <b>실패가 사람 확인 대기열로 정확히 가는지</b>입니다. 실제 LLM은 <code>--provider gemini</code> 등으로 같은 리포트를 만듭니다.</div>"
            if not m.get("is_llm") else "")
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>평가 리포트 — {e(basis)}</title>
<style>
:root {{ --ink:#0f172a; --body:#1e293b; --muted:#64748b; --line:#e2e8f0; --zone:#f8fafc; --accent:#6d28d9; --accent-bg:#ede9fe;
  --ok:#15803d; --ok-bg:#dcfce7; --warn:#b45309; --warn-bg:#fef3c7; --bad:#b91c1c; --bad-bg:#fee2e2; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:#fff; color:var(--body); font:15px/1.6 Pretendard, 'Malgun Gothic', sans-serif; }}
main {{ max-width:1180px; margin:0 auto; padding:12px 8px 40px; }}
section {{ padding:24px 32px 28px; background:#fff; }}
h1 {{ margin:0 0 4px; font-size:28px; color:var(--ink); }}
h2 {{ font-size:19px; color:var(--ink); margin:30px 0 12px; }}
h3 {{ font-size:15px; margin:0 0 10px; color:var(--ink); }} h3 small {{ color:var(--accent); font-weight:700; margin-left:6px; }}
.meta {{ color:var(--muted); margin-bottom:16px; }}
.banner {{ background:var(--accent-bg); border-left:4px solid var(--accent); padding:12px 16px; border-radius:8px; color:#3b0764; }}
.cards {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-top:18px; }}
.card {{ border:1px solid var(--line); border-radius:12px; padding:14px 16px; background:var(--zone); }}
.card.ok {{ background:var(--ok-bg); border-color:#86efac; }} .card.warn {{ background:var(--warn-bg); border-color:#fcd34d; }}
.card.bad {{ background:var(--bad-bg); border-color:#fca5a5; }}
.lab {{ color:var(--muted); font-size:13px; }} .val {{ font-size:28px; font-weight:800; color:var(--ink); line-height:1.3; }}
.sub {{ font-size:13px; color:var(--muted); }}
table {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
th {{ text-align:left; background:var(--accent-bg); color:#3b0764; padding:8px 10px; font-weight:700; }}
td {{ border-bottom:1px solid var(--line); padding:7px 10px; vertical-align:top; }}
.mono {{ font-family:Consolas, 'Cascadia Code', monospace; font-size:12.5px; white-space:nowrap; }}
td:nth-child(-n+2), th {{ white-space:nowrap; }}
.detail {{ color:#334155; font-size:12.5px; }}
.pill {{ display:inline-block; padding:1px 8px; border-radius:999px; font-size:12px; font-weight:700; }}
.pill.ok {{ background:var(--ok-bg); color:var(--ok); }} .pill.bad {{ background:var(--bad-bg); color:var(--bad); }}
.fields {{ display:grid; grid-template-columns:repeat(3,1fr); gap:22px; }}
.frow {{ display:grid; grid-template-columns:168px 1fr 44px; align-items:center; gap:8px; font-size:13px; margin:3px 0; }}
.bar {{ height:9px; background:var(--line); border-radius:9px; overflow:hidden; }} .bar i {{ display:block; height:100%; background:#8b5cf6; }}
.fval {{ color:var(--muted); text-align:right; font-family:Consolas, monospace; font-size:12px; }}
.two {{ display:grid; grid-template-columns:1fr 1fr; gap:22px; }}
footer {{ margin:8px 32px 0; color:var(--muted); font-size:12.5px; }}
</style></head><body><main>
<section id="summary">
<h1>평가 리포트 — {e(basis)}</h1>
<div class="meta">공급자: {e(str(m.get('provider_label', '')))} · 가상 문서 {rep.n}건(계약서·견적서·청구서 각 10건, 어려운 케이스 {sum(1 for d in rep.docs if d.tags)}건)</div>
{warn}
<div class="cards">{cards}</div>
</section>
<section id="safety">
<h2>실패 방어 — 결함 문서는 모두 확인 대기열로</h2>
<table><tr><th>문서</th><th>결함</th><th>기대 원인</th><th>결과</th><th>내용</th></tr>{must_rows}</table>
<div class="two" style="margin-top:20px">
<div><h3>결함은 없지만 확인으로 간 문서</h3><table><tr><th>문서</th><th>난이도</th><th>원인</th><th>내용</th></tr>{opt_rows}</table></div>
<div><h3>조용한 오류 (저장됐지만 틀린 값)</h3><table><tr><th>문서</th><th>난이도</th><th>틀린 필드</th></tr>{silent_rows}</table>
<h3 style="margin-top:18px">난이도별</h3><table><tr><th>난이도</th><th>문서</th><th>완전 일치</th><th>확인</th><th>반드시 확인</th></tr>{tag_rows}</table></div>
</div>
</section>
<section id="fields">
<h2>필드별 정확도</h2>
<div class="fields">{''.join(field_blocks)}</div>
</section>
<footer>모든 문서·회사·인명은 생성 스크립트로 만든 가상 데이터입니다. 처리 시간은 실행 환경에 따라 달라집니다.</footer>
</main></body></html>"""


def evaluate_dir(results_path: Path, gold_dir: Path, md_path: Path | None = None,
                 html_path: Path | None = None) -> EvalReport:
    meta, rows = load_results(results_path)
    rep = evaluate(meta, rows, load_gold(gold_dir))
    sim = [r["doc_id"] for r in rows if any("시뮬레이션" in e for e in r.get("provider_errors", []))]
    if sim:
        rep.extra["simulated"] = ", ".join(sim) + " 문서에 일시 오류 503을 주입"
    if md_path:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(to_markdown(rep), encoding="utf-8", newline="\n")
        rep.md_path = md_path
    if html_path:
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(to_html(rep), encoding="utf-8", newline="\n")
        rep.html_path = html_path
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="파이프라인 결과 평가 리포트")
    ap.add_argument("--results", type=Path, default=Path(".docpipe/out/results.jsonl"))
    ap.add_argument("--gold", type=Path, default=Path("data/samples/gold"))
    ap.add_argument("--out", type=Path, default=Path("eval/report.md"))
    ap.add_argument("--html", type=Path, default=None)
    args = ap.parse_args(argv)
    rep = evaluate_dir(args.results, args.gold, args.out, args.html)
    c, n = rep.field_total
    print(f"필드 정확도 {_pct(c, n)} · 확인 {len(rep.reviewed)}/{rep.n} · 결함 검출 {len(rep.caught)}/{len(rep.must)} → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
