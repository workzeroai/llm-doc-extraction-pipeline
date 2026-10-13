// n8n Code 노드: 텍스트 확인 · 유형 분류 · 프롬프트 만들기 (모드: Run Once for All Items)
// Python 기준 구현 pipeline/pdftext.py · pipeline/classify.py · pipeline/prompts.py 와 같은 규칙이다.
// SCHEMAS는 scripts/build_n8n.py가 schemas/*.json에서 넣는다(손으로 고치지 않는다).
const SCHEMAS = /*__SCHEMAS__*/ {};
const MIN_CHARS = 30;
const MIN_SCORE = 5;
const MIN_MARGIN = 3;
const KEYWORDS = {
  contract: [["계약서", 5], ["이하갑", 3], ["계약기간", 2], ["계약금액", 2], ["착수일", 1], ["용역", 1], ["갑과을", 2]],
  quote: [["견적서", 5], ["quotation", 3], ["견적번호", 2], ["유효기한", 2], ["견적합니다", 2], ["견적금액", 1]],
  invoice: [["청구서", 5], ["invoice", 3], ["청구번호", 2], ["납부기한", 2], ["공급받는자", 2], ["청구금액", 1]],
};

function classify(text) {
  const flat = text.replace(/[\s"'“”]+/g, "").toLowerCase();
  const scores = {};
  for (const [type, kws] of Object.entries(KEYWORDS)) {
    scores[type] = kws.reduce((s, [kw, w]) => s + (flat.includes(kw) ? w : 0), 0);
  }
  const ranked = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  const [[top, s1], [second, s2]] = ranked;
  if (s1 < MIN_SCORE) return { type: null, reason: `유형 낱말 점수가 낮음(${s1}점)` };
  if (s1 - s2 < MIN_MARGIN) return { type: null, reason: `유형 후보가 둘 이상(${top} ${s1} · ${second} ${s2})` };
  return { type: top, reason: "" };
}

function userPrompt(text, type) {
  const s = SCHEMAS[type];
  const fields = Object.entries(s.labels).map(([k, v]) => `- ${k}: ${v}`).join("\n");
  return `문서 유형: ${s.label} (${type})\n뽑을 필드:\n${fields}\n- uncertain_fields: 확신할 수 없는 필드 이름 목록\n\n` +
    `JSON 객체 하나로만 답하세요. 키는 위 필드 이름 그대로, 품목(items)은 {name, qty, unit_price, amount} 배열입니다.\n\n` +
    `<document>\n${text}\n</document>`;
}

const out = [];
for (const [i, item] of $input.all().entries()) {
  const text = String(item.json.text || "");
  // 문서 ID: 앞 단계가 준 doc_id → PDF 메타데이터 제목(예: "견적서 QT-07") → 순번
  const title = item.json.info && item.json.info.Title ? String(item.json.info.Title) : "";
  const idInTitle = title.match(/[A-Z]{2}-\d{2}/);
  const docId = String(item.json.doc_id || (idInTitle ? idInTitle[0] : title) || `upload-${i + 1}`);
  const base = { doc_id: docId, text_chars: text.trim().length };
  if (text.trim().length < MIN_CHARS) {
    out.push({ json: { ...base, route: "review", doc_type: null, reason_code: "TEXT_EXTRACTION_FAILED",
      detail: `텍스트 ${text.trim().length}자 — 텍스트 층이 없는 스캔 이미지로 보임(OCR 필요)` } });
    continue;
  }
  const c = classify(text);
  if (!c.type) {
    out.push({ json: { ...base, route: "review", doc_type: null, reason_code: "CLASSIFICATION_UNCERTAIN", detail: c.reason } });
    continue;
  }
  out.push({ json: { ...base, route: "extract", doc_type: c.type, prompt: userPrompt(text, c.type) } });
}
return out;
