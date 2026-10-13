# n8n 워크플로 가져오기

`workflow.json`은 Python 기준 구현(`pipeline/`)과 같은 흐름을 n8n으로 옮긴 것입니다. 자격증명은 비워 두었습니다.

![n8n 흐름](../assets/diagrams/n8n-flow.png)

## 가져오기

1. n8n 편집기 → 오른쪽 위 메뉴 → **Import from File** → `n8n/workflow.json`
2. **Gemini 모델** 노드: Google Gemini(PaLM) API 자격증명을 연결합니다. 다른 모델을 쓰려면 이 하위 노드만 Anthropic·OpenAI 채팅 모델로 바꿉니다.
3. **저장 (Google Sheets: extracted)** · **확인 대기열 (Google Sheets: review_queue)**: Google Sheets 자격증명과 시트 ID(`REPLACE_WITH_GOOGLE_SHEET_ID`)를 넣고, 시트에 `extracted`·`review_queue` 탭을 만듭니다. 다른 저장소(DB·Airtable 등)를 쓰려면 이 두 노드만 바꿉니다.
4. **알림 (웹훅)**: URL을 Slack·Discord 수신 웹훅으로 바꿉니다. 본문은 `{"text", "content"}` 둘 다 보내므로 어느 쪽이든 받습니다.
5. 입력은 둘 중 하나입니다.
   - **Webhook**: `POST /webhook/doc-extract`에 multipart 필드 이름 `data`로 PDF를 보냅니다.
     `curl -F "data=@data/samples/docs/QT-01.pdf" http://localhost:5678/webhook-test/doc-extract`
   - **폴더 감시**: 컨테이너 안 `/data/inbox`에 PDF를 넣습니다(경로는 노드에서 바꿀 수 있음).

## 노드별 역할

| 노드 | 하는 일 | Python 기준 구현 |
|---|---|---|
| PDF 텍스트 추출 | Extract from File(PDF) | `pipeline/pdftext.py` |
| 텍스트 확인·유형 분류 (Code) | 30자 미만 → `TEXT_EXTRACTION_FAILED`, 유형 분류, 프롬프트 생성 | `classify.py`, `prompts.py` |
| 추출 가능? (IF) | 아니면 바로 확인 대기열 | `run.py` |
| LLM 구조화 추출 + Gemini 모델 | 시스템 프롬프트(Python과 같은 문장), 실패 시 3회 재시도, 그래도 실패하면 멈추지 않고 다음 노드로 | `extract.py` |
| 스키마·업무 규칙 검증 (Code) | 응답 JSON 해석 → S01·R01~R08·C01 → `PROVIDER_ERROR`·`SCHEMA_MISMATCH`·`RULE_VIOLATION`·`LOW_CONFIDENCE` | `validate.py` |
| 검증 통과? (IF) | 통과 → 저장, 아니면 확인 대기열 | `route.py` |

## 고칠 때

Code 노드의 JS 원본은 `n8n/code/classify.js`, `n8n/code/validate.js`입니다. 원본을 고친 뒤 `python scripts/build_n8n.py`로 `workflow.json`을 다시 만듭니다(스키마의 필드·필수값이 자동으로 들어감). `pytest tests/test_n8n_workflow.py`가 JS를 node로 실행해 Python 검증과 같은 판정을 내는지 확인합니다.

이 워크플로는 구조 테스트와 Code 노드 실행 테스트까지 했고, 실제 n8n 인스턴스에서의 실행 검증은 하지 않았습니다.
