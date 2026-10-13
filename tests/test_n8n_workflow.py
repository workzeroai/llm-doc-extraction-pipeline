"""n8n 워크플로: 가져오기 가능한 구조인지, Code 노드 JS가 Python 기준 구현과 같은 판정을 내는지."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from pipeline.classify import classify
from pipeline.validate import validate

ROOT = Path(__file__).resolve().parents[1]
WF = json.loads((ROOT / "n8n" / "workflow.json").read_text(encoding="utf-8"))
NODES = {n["name"]: n for n in WF["nodes"]}
NODE_BIN = shutil.which("node")


def test_workflow_is_up_to_date():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_n8n.py"), "--check"], capture_output=True)
    assert r.returncode == 0, r.stdout.decode("utf-8", "replace")


def test_workflow_structure():
    assert WF["active"] is False and WF["settings"]["executionOrder"] == "v1"
    ids = [n["id"] for n in WF["nodes"]]
    assert len(ids) == len(set(ids)) and len(NODES) == len(WF["nodes"])
    for n in WF["nodes"]:
        assert {"parameters", "id", "name", "type", "typeVersion", "position"} <= set(n)
        assert n["type"].startswith(("n8n-nodes-base.", "@n8n/n8n-nodes-langchain."))
        assert "credentials" not in n                      # 자격증명은 비워 둔다
    for src, outputs in WF["connections"].items():
        assert src in NODES
        for kind, branches in outputs.items():
            for branch in branches:
                for link in branch:
                    assert link["node"] in NODES and link["type"] == kind
    targets = {link["node"] for o in WF["connections"].values() for b in o.values() for br in b for link in br}
    triggers = {"PDF 업로드 (Webhook)", "폴더 감시 (inbox)"}
    for name, n in NODES.items():
        if n["type"] == "n8n-nodes-base.stickyNote" or name in triggers:
            continue
        if n["type"].startswith("@n8n/n8n-nodes-langchain.lm"):     # 모델 하위 노드는 바깥으로 연결된다
            assert name in WF["connections"], f"{name}: 연결 없음"
        else:
            assert name in targets, f"{name}: 들어오는 연결 없음"
    assert WF["connections"]["Gemini 모델"]["ai_languageModel"][0][0]["node"] == "LLM 구조화 추출"
    llm = NODES["LLM 구조화 추출"]
    assert llm["retryOnFail"] and llm["maxTries"] == 3 and llm["onError"] == "continueRegularOutput"
    branches = WF["connections"]["검증 통과?"]["main"]
    assert branches[0][0]["node"].startswith("저장") and branches[1][0]["node"].startswith("확인 대기열")


def _run_js(node_name: str, items: list[dict], source: list[dict] | None = None) -> list[dict]:
    payload = {"code": NODES[node_name]["parameters"]["jsCode"], "items": [{"json": i} for i in items],
               "source": [{"json": s} for s in (source or [])]}
    r = subprocess.run([NODE_BIN, str(ROOT / "tests" / "n8n_harness.js")], input=json.dumps(payload).encode("utf-8"),
                       capture_output=True, check=True)
    return [o["json"] for o in json.loads(r.stdout.decode("utf-8"))]


@pytest.mark.skipif(NODE_BIN is None, reason="node 없음")
def test_classify_node_matches_python(texts):
    items = [{"text": t, "doc_id": d} for d, t in texts.items()]
    out = _run_js("텍스트 확인·유형 분류", items)
    for d, o in zip(texts, out, strict=True):
        text = texts[d]
        if len(text.strip()) < 30:
            assert o["reason_code"] == "TEXT_EXTRACTION_FAILED"
        else:
            assert o["route"] == "extract" and o["doc_type"] == classify(text).doc_type
            assert "<document>" in o["prompt"]
    out = _run_js("텍스트 확인·유형 분류", [{"text": "견적서 청구서 견적번호 청구번호 그 밖의 아무 말이나 길게 적어 둔 문서"}])
    assert out[0]["reason_code"] == "CLASSIFICATION_UNCERTAIN" and out[0]["doc_id"] == "upload-1"


def _mutations(gold):
    """gold 정답에 결함을 넣은 사례들 → JS와 Python의 판정을 비교한다."""
    cases = []
    for g in gold.values():
        cases.append((g["doc_type"], g["fields"], []))
    q = json.loads(json.dumps(gold["QT-01"]["fields"]))
    q["vat"] += 7
    cases.append(("quote", q, ["total"]))
    c = json.loads(json.dumps(gold["CT-01"]["fields"]))
    c["start_date"], c["contract_date"] = "2026-12-31", "2026/01/01"
    c["vendor_biz_no"] = c["vendor_biz_no"][:-1] + str((int(c["vendor_biz_no"][-1]) + 1) % 10)
    cases.append(("contract", c, []))
    bad = json.loads(json.dumps(gold["IV-01"]["fields"]))
    bad["total"] = "많음"
    bad["extra"] = 1
    cases.append(("invoice", bad, []))
    return cases


@pytest.mark.skipif(NODE_BIN is None, reason="node 없음")
def test_validate_node_matches_python(gold):
    cases = _mutations(gold)
    items = [{"text": "```json\n" + json.dumps({**data, "uncertain_fields": unc}, ensure_ascii=False) + "\n```"}
             for _, data, unc in cases]
    source = [{"doc_id": f"D{i}", "doc_type": t} for i, (t, _, _) in enumerate(cases)]
    out = _run_js("스키마·업무 규칙 검증", items, source)
    for (t, data, unc), o in zip(cases, out, strict=True):
        py = validate(t, data, unc)
        js_codes = sorted(i["code"] for i in o.get("issues", []))
        assert js_codes == sorted(i.code for i in py), (t, js_codes, [i.code for i in py])
        assert (o["status"] == "saved") == (not py)


@pytest.mark.skipif(NODE_BIN is None, reason="node 없음")
def test_validate_node_error_paths():
    out = _run_js("스키마·업무 규칙 검증", [{"error": {"message": "503"}}, {"text": "죄송합니다"}],
                  [{"doc_id": "A", "doc_type": "quote"}, {"doc_id": "B", "doc_type": "quote"}])
    assert out[0]["reason_code"] == "PROVIDER_ERROR" and out[1]["reason_code"] == "SCHEMA_MISMATCH"
