"""n8n/workflow.json 만들기 — Code 노드 JS(n8n/code/*.js)에 schemas/*.json 정보를 넣어 워크플로 하나로 조립한다.

    python scripts/build_n8n.py          # n8n/workflow.json 갱신
    python scripts/build_n8n.py --check  # 갱신이 필요하면 종료 코드 1 (CI·테스트용)

자격증명(Gemini, Google Sheets)은 비워 둔다. n8n에서 가져온 뒤 각 노드에서 직접 연결한다.
노드 id는 이름에서 만든 UUIDv5라 다시 만들어도 같은 파일이 나온다.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.prompts import SYSTEM_PROMPT  # noqa: E402
from schemas import DOC_TYPES, TYPE_LABEL, field_labels, load_schema, required_values  # noqa: E402

OUT = ROOT / "n8n" / "workflow.json"
NS = uuid.UUID("6f1c2b0e-7d1a-4f3e-9a51-2c4b8e0d9f10")
WEBHOOK_PLACEHOLDER = "https://hooks.example.com/REPLACE_WITH_YOUR_WEBHOOK"  # Slack·Discord 수신 웹훅으로 바꾼다
SHEET_PLACEHOLDER = "REPLACE_WITH_GOOGLE_SHEET_ID"


def nid(name: str) -> str:
    return str(uuid.uuid5(NS, name))


def schemas_js() -> str:
    out = {}
    for t in DOC_TYPES:
        props = load_schema(t)["properties"]
        types = {k: (v["type"] if isinstance(v["type"], list) else [v["type"]]) for k, v in props.items()}
        out[t] = {
            "label": TYPE_LABEL[t],
            "labels": field_labels(t),
            "types": types,
            "required_values": required_values(t),
            "biz_fields": [k for k in props if k.endswith("biz_no")],
        }
    return json.dumps(out, ensure_ascii=False)


def code(name: str) -> str:
    src = (ROOT / "n8n" / "code" / f"{name}.js").read_text(encoding="utf-8")
    return src.replace("/*__SCHEMAS__*/ {}", schemas_js())


def sheet_columns(cols: list[str]) -> dict:
    return {
        "mappingMode": "defineBelow",
        "value": {c: f"={{{{ $json.{c} }}}}" for c in cols},
        "matchingColumns": [],
        "schema": [{"id": c, "displayName": c, "required": False, "defaultMatch": False, "display": True,
                    "type": "string", "canBeUsedToMatch": True} for c in cols],
    }


def node(name: str, type_: str, version: float, pos: tuple[int, int], params: dict, **extra) -> dict:
    n = {"parameters": params, "id": nid(name), "name": name, "type": type_, "typeVersion": version,
         "position": list(pos)}
    n.update(extra)
    return n


def sticky(name: str, pos: tuple[int, int], content: str, w: int, h: int, color: int) -> dict:
    return node(name, "n8n-nodes-base.stickyNote", 1, pos, {"content": content, "height": h, "width": w, "color": color})


def build() -> dict:
    nodes = [
        sticky("안내", (-60, -420), "## 문서 추출 파이프라인 (n8n 판)\nPDF → 텍스트 → 유형 분류 → **LLM 구조화 추출** → "
               "**스키마·업무 규칙 검증** → 저장 / **사람 확인 대기열** + 알림\n\n가져온 뒤 할 일: ① Gemini 모델 노드에 자격증명 연결 "
               "② Google Sheets 두 노드에 자격증명·시트 ID ③ 알림 노드의 웹훅 URL\n\nPython 기준 구현과 같은 규칙: "
               "github.com/workzeroai/llm-doc-extraction-pipeline", 760, 220, 5),
        sticky("실패 방어", (1040, -420), "### 실패 방어\n- LLM 노드: 실패 시 3회 재시도 후에도 오류면 **멈추지 않고** 다음 노드로 넘김 "
               "→ 검증 노드가 `PROVIDER_ERROR`로 분류\n- 검증 노드: 응답 형식·스키마·합계·날짜·필수값·사업자번호 검증번호\n"
               "- 실패·애매한 건은 저장하지 않고 확인 대기열 시트 + 알림", 620, 220, 3),
        node("PDF 업로드 (Webhook)", "n8n-nodes-base.webhook", 2, (0, 0),
             {"httpMethod": "POST", "path": "doc-extract", "responseMode": "onReceived", "options": {}},
             webhookId=nid("webhook-doc-extract")),
        node("폴더 감시 (inbox)", "n8n-nodes-base.localFileTrigger", 1, (0, 220),
             {"triggerOn": "folder", "path": "/data/inbox", "events": ["add"], "options": {}}),
        node("PDF 읽기", "n8n-nodes-base.readWriteFile", 1, (220, 220),
             {"fileSelector": "={{ $json.path }}", "options": {}}),
        node("PDF 텍스트 추출", "n8n-nodes-base.extractFromFile", 1, (440, 100),
             {"operation": "pdf", "binaryPropertyName": "data", "options": {}}),
        node("텍스트 확인·유형 분류", "n8n-nodes-base.code", 2, (660, 100),
             {"mode": "runOnceForAllItems", "jsCode": code("classify")}),
        node("추출 가능?", "n8n-nodes-base.if", 2, (880, 100), {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                "conditions": [{"id": nid("cond-route"), "leftValue": "={{ $json.route }}", "rightValue": "extract",
                                "operator": {"type": "string", "operation": "equals"}}],
                "combinator": "and",
            },
            "options": {},
        }),
        node("LLM 구조화 추출", "@n8n/n8n-nodes-langchain.chainLlm", 1.5, (1100, 0), {
            "promptType": "define",
            "text": "={{ $json.prompt }}",
            "hasOutputParser": False,
            "messages": {"messageValues": [{"message": SYSTEM_PROMPT}]},
        }, retryOnFail=True, maxTries=3, waitBetweenTries=2000, onError="continueRegularOutput"),
        node("Gemini 모델", "@n8n/n8n-nodes-langchain.lmChatGoogleGemini", 1, (1100, 220),
             {"modelName": "models/gemini-2.5-flash", "options": {"temperature": 0}}),
        node("스키마·업무 규칙 검증", "n8n-nodes-base.code", 2, (1360, 0),
             {"mode": "runOnceForAllItems", "jsCode": code("validate")}),
        node("검증 통과?", "n8n-nodes-base.if", 2, (1580, 0), {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                "conditions": [{"id": nid("cond-status"), "leftValue": "={{ $json.status }}", "rightValue": "saved",
                                "operator": {"type": "string", "operation": "equals"}}],
                "combinator": "and",
            },
            "options": {},
        }),
        node("저장 (Google Sheets: extracted)", "n8n-nodes-base.googleSheets", 4.5, (1820, -100), {
            "operation": "append",
            "documentId": {"__rl": True, "mode": "id", "value": SHEET_PLACEHOLDER},
            "sheetName": {"__rl": True, "mode": "name", "value": "extracted"},
            "columns": sheet_columns(["doc_id", "doc_type", "data_json"]),
            "options": {},
        }),
        node("확인 대기열 (Google Sheets: review_queue)", "n8n-nodes-base.googleSheets", 4.5, (1820, 160), {
            "operation": "append",
            "documentId": {"__rl": True, "mode": "id", "value": SHEET_PLACEHOLDER},
            "sheetName": {"__rl": True, "mode": "name", "value": "review_queue"},
            "columns": sheet_columns(["doc_id", "doc_type", "reason_code", "detail"]),
            "options": {},
        }),
        node("알림 (웹훅)", "n8n-nodes-base.httpRequest", 4.2, (2060, 160), {
            "method": "POST",
            "url": WEBHOOK_PLACEHOLDER,
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ text: `[확인 필요] ${$json.doc_id} · ${$json.reason_code} · ${$json.detail}`, "
                        "content: `[확인 필요] ${$json.doc_id} · ${$json.reason_code} · ${$json.detail}` }) }}",
            "options": {},
        }, onError="continueRegularOutput"),
    ]

    def link(dst: str, idx: int = 0, typ: str = "main") -> dict:
        return {"node": dst, "type": typ, "index": idx}

    connections = {
        "PDF 업로드 (Webhook)": {"main": [[link("PDF 텍스트 추출")]]},
        "폴더 감시 (inbox)": {"main": [[link("PDF 읽기")]]},
        "PDF 읽기": {"main": [[link("PDF 텍스트 추출")]]},
        "PDF 텍스트 추출": {"main": [[link("텍스트 확인·유형 분류")]]},
        "텍스트 확인·유형 분류": {"main": [[link("추출 가능?")]]},
        "추출 가능?": {"main": [[link("LLM 구조화 추출")], [link("확인 대기열 (Google Sheets: review_queue)")]]},
        "Gemini 모델": {"ai_languageModel": [[link("LLM 구조화 추출", 0, "ai_languageModel")]]},
        "LLM 구조화 추출": {"main": [[link("스키마·업무 규칙 검증")]]},
        "스키마·업무 규칙 검증": {"main": [[link("검증 통과?")]]},
        "검증 통과?": {"main": [[link("저장 (Google Sheets: extracted)")],
                                 [link("확인 대기열 (Google Sheets: review_queue)")]]},
        "확인 대기열 (Google Sheets: review_queue)": {"main": [[link("알림 (웹훅)")]]},
    }
    return {
        "name": "문서 추출 파이프라인 — 추출 · 검증 · 사람 확인 대기열",
        "nodes": nodes,
        "pinData": {},
        "connections": connections,
        "active": False,
        "settings": {"executionOrder": "v1"},
        "tags": [],
    }


def render() -> str:
    return json.dumps(build(), ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    text = render()
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print("n8n/workflow.json이 최신이 아닙니다: python scripts/build_n8n.py")
            return 1
        print("n8n/workflow.json 최신")
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"생성: {OUT.relative_to(ROOT)} (노드 {len(build()['nodes'])}개)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
