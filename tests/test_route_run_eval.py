import csv
import json
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar

from eval.evaluate import evaluate, evaluate_dir, load_results, same_value, to_html, to_markdown
from pipeline.route import Notifier, Router

# ---------------------------------------------------------------- 분기 결과(30건)

def test_every_defective_doc_goes_to_review(demo_run, gold):
    by_id = {r.doc_id: r for r in demo_run.results}
    for doc_id, g in gold.items():
        if g["must_review"]:
            r = by_id[doc_id]
            assert r.status == "review", doc_id
            assert r.reason_code in g["expected_reasons"], (doc_id, r.reason_code)


def test_review_and_saved_are_disjoint(demo_run):
    out = demo_run.out_dir
    db = sqlite3.connect(out / "docpipe.sqlite3")
    saved = {row[0] for row in db.execute("SELECT doc_id FROM documents")}
    db.close()
    with (out / "review_queue.csv").open(encoding="utf-8-sig") as fp:
        queued = {row["doc_id"] for row in csv.DictReader(fp)}
    assert saved == {r.doc_id for r in demo_run.saved}
    assert queued == {r.doc_id for r in demo_run.review}
    assert not saved & queued and len(saved | queued) == 30
    for t in ("contract", "quote", "invoice"):
        assert (out / "extracted" / f"{t}.csv").exists()


def test_provider_error_and_retry_paths(demo_run):
    by_id = {r.doc_id: r for r in demo_run.results}
    assert by_id["IV-05"].reason_code == "PROVIDER_ERROR" and by_id["IV-05"].attempts == 3
    assert by_id["QT-04"].status == "saved" and by_id["QT-04"].attempts == 2
    assert by_id["CT-10"].reason_code == "TEXT_EXTRACTION_FAILED"


def test_evaluation_metrics(demo_run, samples):
    rep = evaluate_dir(demo_run.out_dir / "results.jsonl", samples / "gold")
    assert rep.n == 30
    assert len(rep.must) == 6 and not rep.missed and len(rep.reason_matched) == 6
    assert rep.silent_errors == []
    c, n = rep.field_total
    assert n > 300 and c / n > 0.9
    assert rep.mean_ms > 0 and rep.p95_ms >= rep.mean_ms * 0.5
    assert {t for t, *_ in rep.by_tag()} >= {"일반", "합계 불일치", "저품질 스캔"}
    assert rep.extra["simulated"].startswith("IV-05")


def test_report_outputs(demo_run, samples, tmp_path):
    rep = evaluate_dir(demo_run.out_dir / "results.jsonl", samples / "gold", tmp_path / "r.md", tmp_path / "r.html")
    md = (tmp_path / "r.md").read_text(encoding="utf-8")
    assert md.startswith("# 평가 리포트 — 모의 추출기 기준")
    assert "LLM 정확도가 아닙니다" in md and "--provider gemini" in md
    assert "| 반드시 확인 문서 검출률 | **100.0%** (6/6)" in md
    html = (tmp_path / "r.html").read_text(encoding="utf-8")
    assert 'id="safety"' in html and "모의 추출기" in html
    assert rep.md_path and rep.html_path


def test_report_for_llm_provider_and_misses(demo_run, samples, gold):
    meta, rows = load_results(demo_run.out_dir / "results.jsonl")
    meta = {**meta, "is_llm": True, "provider_label": "Gemini (test)"}
    # 결함 문서 하나를 '저장'으로 바꿔 놓친 경우의 리포트 모양을 확인
    rows = [dict(r, status="saved", reason_code=None) if r["doc_id"] == "QT-09" else r for r in rows]
    rep = evaluate(meta, rows, gold)
    md = to_markdown(rep)
    assert md.startswith("# 평가 리포트 — Gemini (test) 기준")
    assert "놓친 문서 1건" in md and "**저장됨(놓침)**" in md
    assert [d.doc_id for d in rep.silent_errors] == []
    assert "놓침" in to_html(rep)


def test_same_value_rules():
    assert same_value(None, None) and not same_value("a", None)
    assert same_value(" 가  나 ", "가 나")
    assert not same_value(1, "1") and not same_value(True, 1)
    items = [{"name": "가", "qty": 1, "unit_price": 2, "amount": 2}]
    assert same_value([dict(items[0])], items) and not same_value([], items) and not same_value("x", items)


# ---------------------------------------------------------------- 알림

class _Hook(BaseHTTPRequestHandler):
    received: ClassVar[list] = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        _Hook.received.append(json.loads(body))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *a):
        pass


def test_webhook_notifier_posts_json(tmp_path):
    srv = HTTPServer(("127.0.0.1", 0), _Hook)
    th = threading.Thread(target=srv.handle_request, daemon=True)
    th.start()
    printed = []
    n = Notifier(console=printed.append, webhook_url=f"http://127.0.0.1:{srv.server_address[1]}/hook")
    router = Router(tmp_path, n)
    router.queue(doc_id="X-01", doc_type="quote", file="X-01.pdf", provider="mock", reason_code="RULE_VIOLATION",
                 detail="R05", data={"a": 1})
    th.join(5)
    srv.server_close()
    router.close()
    assert _Hook.received and _Hook.received[0]["doc_id"] == "X-01"
    assert "[확인 필요] X-01" in _Hook.received[0]["text"] == _Hook.received[0]["content"]
    assert printed and not n.webhook_errors


def test_webhook_failure_does_not_stop(tmp_path):
    n = Notifier(console=None, webhook_url="http://127.0.0.1:9/unreachable", timeout=0.5)
    n.alert("X-02", "PROVIDER_ERROR", "x")
    assert n.webhook_errors and n.sent


def test_router_reset_and_count(tmp_path):
    r = Router(tmp_path, Notifier(console=None, webhook_url=None))
    r.save(doc_id="A", doc_type="quote", file="A.pdf", provider="mock", data={"items": [{"name": "x"}], "total": 1})
    r.queue(doc_id="B", doc_type=None, file="B.pdf", provider="mock", reason_code="TEXT_EXTRACTION_FAILED",
            detail="0자", data=None)
    assert r.saved_count() == 1 and r.queue_path.exists()
    r.reset()
    assert r.saved_count() == 0 and not r.queue_path.exists()
    r.close()
