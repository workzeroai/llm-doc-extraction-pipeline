// n8n Code 노드: LLM 응답 해석 → 스키마 검사 → 업무 규칙 검증 → 분기 표시 (모드: Run Once for All Items)
// Python 기준 구현 pipeline/validate.py 와 같은 규칙(S01, R01~R08, C01)이다.
// SCHEMAS는 scripts/build_n8n.py가 schemas/*.json에서 넣는다(손으로 고치지 않는다).
const SCHEMAS = /*__SCHEMAS__*/ {};
const SOURCE_NODE = "텍스트 확인·유형 분류";
const ORDER = ["TEXT_EXTRACTION_FAILED", "CLASSIFICATION_UNCERTAIN", "PROVIDER_ERROR", "SCHEMA_MISMATCH", "RULE_VIOLATION", "LOW_CONFIDENCE"];
const DATE_FIELDS = ["contract_date", "start_date", "end_date", "issue_date", "valid_until", "due_date"];
const DATE_ORDER = { contract: [["start_date", "end_date"]], quote: [["issue_date", "valid_until"]], invoice: [["issue_date", "due_date"]] };
const MONEY = { contract: ["supply_amount", "vat", "total_amount"], quote: ["subtotal", "vat", "total"], invoice: ["subtotal", "vat", "total"] };
const won = (n) => `${Number(n).toLocaleString("en-US")}원`;

function parseJson(raw) {
  let t = String(raw || "").trim();
  if (t.startsWith("```")) t = t.replace(/^```[a-zA-Z]*\n?/, "").replace(/```\s*$/, "");
  const obj = JSON.parse(t);
  if (obj === null || typeof obj !== "object" || Array.isArray(obj)) throw new Error("JSON 객체가 아님");
  return obj;
}

function typeOk(v, types) {
  return types.some((t) => (t === "null" && v === null) || (t === "string" && typeof v === "string") ||
    (t === "integer" && Number.isInteger(v)) || (t === "array" && Array.isArray(v)));
}

function schemaIssues(type, data) {
  const s = SCHEMAS[type];
  const issues = [];
  for (const k of Object.keys(s.types)) {
    if (!(k in data)) issues.push({ code: "S01", field: k, message: `${k}: 필수 키가 없음` });
    else if (!typeOk(data[k], s.types[k])) issues.push({ code: "S01", field: k, message: `${k}: 타입이 ${s.types[k].join("|")}가 아님` });
  }
  for (const k of Object.keys(data)) if (!(k in s.types)) issues.push({ code: "S01", field: k, message: `${k}: 스키마에 없는 키` });
  for (const k of s.biz_fields) {
    if (typeof data[k] === "string" && !/^\d{3}-\d{2}-\d{5}$/.test(data[k])) issues.push({ code: "S01", field: k, message: `${k}: 000-00-00000 형식이 아님` });
  }
  for (const [i, it] of (Array.isArray(data.items) ? data.items : []).entries()) {
    const ok = it && typeof it.name === "string" && Number.isInteger(it.qty) && Number.isInteger(it.unit_price) && Number.isInteger(it.amount);
    if (!ok) issues.push({ code: "S01", field: `items.${i}`, message: `items.${i}: name·qty·unit_price·amount 형식 오류` });
  }
  return issues;
}

function bizNoValid(v) {
  const d = v.replace(/\D/g, "").split("").map(Number);
  if (d.length !== 10) return false;
  const w = [1, 3, 7, 1, 3, 7, 1, 3, 5];
  const total = w.reduce((s, wi, i) => s + d[i] * wi, 0) + Math.floor((d[8] * 5) / 10);
  return (10 - (total % 10)) % 10 === d[9];
}

function ruleIssues(type, data) {
  const s = SCHEMAS[type];
  const L = s.labels;
  const issues = [];
  for (const f of s.required_values) {
    const v = data[f];
    if (v === null || v === undefined || (Array.isArray(v) && v.length === 0)) issues.push({ code: "R01", field: f, message: `${L[f]}(${f}) 값이 없음` });
  }
  const parsed = {};
  for (const f of DATE_FIELDS) {
    const v = data[f];
    if (v === null || v === undefined || !(f in L)) continue;
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v);
    const dt = m ? new Date(Date.UTC(+m[1], +m[2] - 1, +m[3])) : null;
    if (!m || dt.getUTCMonth() !== +m[2] - 1 || dt.getUTCDate() !== +m[3]) issues.push({ code: "R02", field: f, message: `${L[f]} '${v}'가 YYYY-MM-DD 형식의 날짜가 아님` });
    else parsed[f] = v;
  }
  for (const [a, b] of DATE_ORDER[type]) {
    if (parsed[a] && parsed[b] && parsed[a] > parsed[b]) issues.push({ code: "R03", field: b, message: `${L[a]} ${parsed[a]} > ${L[b]} ${parsed[b]}` });
  }
  const [sf, vf, tf] = MONEY[type];
  const items = data.items;
  if (Array.isArray(items) && items.length) {
    items.forEach((it, i) => {
      if (it.qty * it.unit_price !== it.amount) {
        issues.push({ code: "R04", field: `items.${i}.amount`, message: `품목 ${i + 1} '${it.name}': ${it.qty.toLocaleString("en-US")} × ${won(it.unit_price)} = ${won(it.qty * it.unit_price)} ≠ 인쇄 ${won(it.amount)}` });
      }
    });
    const sum = items.reduce((acc, it) => acc + it.amount, 0);
    if (data[sf] !== null && data[sf] !== undefined && sum !== data[sf]) issues.push({ code: "R05", field: sf, message: `${L[sf]} ${won(data[sf])} ≠ 품목 합 ${won(sum)}` });
  }
  const supply = data[sf], vat = data[vf], total = data[tf];
  const has = (x) => x !== null && x !== undefined;
  if (has(supply) && has(vat) && Math.abs(vat - supply * 0.1) > 1) issues.push({ code: "R06", field: vf, message: `${L[vf]} ${won(vat)} ≠ ${L[sf]}의 10% ${won(Math.floor(supply / 10))}` });
  if (has(supply) && has(vat) && has(total) && supply + vat !== total) issues.push({ code: "R07", field: tf, message: `${L[tf]} ${won(total)} ≠ ${won(supply)} + ${won(vat)} = ${won(supply + vat)}` });
  for (const f of s.biz_fields) {
    if (data[f] && !bizNoValid(data[f])) issues.push({ code: "R08", field: f, message: `${L[f]} ${data[f]} 검증번호 불일치(오인식 또는 오기 가능)` });
  }
  return issues;
}

const REASON_OF = (code) => (code === "S01" ? "SCHEMA_MISMATCH" : code === "C01" ? "LOW_CONFIDENCE" : "RULE_VIOLATION");

const out = [];
const items = $input.all();
for (let i = 0; i < items.length; i++) {
  const item = items[i];
  const src = $(SOURCE_NODE).itemMatching(i).json;
  const base = { doc_id: src.doc_id, doc_type: src.doc_type };
  if (item.json.error) {
    out.push({ json: { ...base, status: "review", reason_code: "PROVIDER_ERROR", detail: `LLM 호출 실패(재시도 후): ${JSON.stringify(item.json.error).slice(0, 200)}`, data: null } });
    continue;
  }
  let parsed;
  try {
    parsed = parseJson(item.json.text ?? (item.json.response && item.json.response.text));
  } catch (e) {
    out.push({ json: { ...base, status: "review", reason_code: "SCHEMA_MISMATCH", detail: `응답 형식 오류: ${e.message}`, data: null } });
    continue;
  }
  const uncertain = Array.isArray(parsed.uncertain_fields) ? parsed.uncertain_fields : [];
  delete parsed.uncertain_fields;
  let issues = schemaIssues(src.doc_type, parsed);
  if (!issues.length) {
    issues = ruleIssues(src.doc_type, parsed);
    const req = new Set(SCHEMAS[src.doc_type].required_values);
    for (const f of uncertain) if (req.has(f)) issues.push({ code: "C01", field: f, message: `${SCHEMAS[src.doc_type].labels[f] || f}(${f}) — 추출기가 확신 없음으로 표시` });
  }
  if (!issues.length) {
    out.push({ json: { ...base, status: "saved", reason_code: null, detail: "", data: parsed, data_json: JSON.stringify(parsed) } });
    continue;
  }
  const main = issues.reduce((m, x) => (ORDER.indexOf(REASON_OF(x.code)) < ORDER.indexOf(REASON_OF(m.code)) ? x : m));
  const reason = REASON_OF(main.code);
  const same = issues.filter((x) => REASON_OF(x.code) === reason);
  const detail = same.slice(0, 3).map((x) => `${x.code}: ${x.message}`).join(" / ") + (same.length > 3 ? ` 외 ${same.length - 3}건` : "");
  out.push({ json: { ...base, status: "review", reason_code: reason, detail, issues, data: parsed, data_json: JSON.stringify(parsed) } });
}
return out;
