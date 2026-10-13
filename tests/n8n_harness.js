// 테스트용: n8n Code 노드 jsCode를 n8n 밖에서 실행한다($input, $ 흉내).
// 입력(stdin JSON): {code, items: [{json}], source: [{json}]}  출력: Code 노드가 돌려준 items
const chunks = [];
process.stdin.on("data", (c) => chunks.push(c));
process.stdin.on("end", () => {
  const { code, items, source } = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  const $input = { all: () => items };
  const $ = (_name) => ({ itemMatching: (i) => source[i] });
  const fn = new Function("$input", "$", code);
  process.stdout.write(JSON.stringify(fn($input, $)));
});
