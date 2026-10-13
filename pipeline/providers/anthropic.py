"""Claude(Anthropic) 공급자 — ANTHROPIC_API_KEY가 있을 때만 실제로 호출한다.

구조화 출력(output_config.format = json_schema)으로 스키마에 맞는 JSON만 받는다.
설치: pip install -e ".[llm]"
"""
from __future__ import annotations

import os
from typing import Any

from pipeline.prompts import SYSTEM_PROMPT, llm_schema, user_prompt
from pipeline.providers.base import MissingCredentialError, ProviderError, ProviderOutput, parse_json_output

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicExtractor:
    name = "anthropic"
    is_llm = True

    def __init__(self, api_key: str | None = None, model: str | None = None, client: Any = None,
                 effort: str | None = None):
        self.model = model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
        self.effort = effort or os.environ.get("ANTHROPIC_EFFORT") or "low"   # 추출은 단순 작업이라 low부터
        self.label = f"Claude ({self.model})"
        if client is not None:
            self.client = client
            return
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise MissingCredentialError("ANTHROPIC_API_KEY가 없습니다. 키 없이 실행하려면 --offline(모의 추출기)을 쓰세요.")
        import anthropic

        # 재시도는 파이프라인(extract.py)이 한 곳에서 관리한다
        self.client = anthropic.Anthropic(api_key=key, max_retries=0)

    def extract(self, *, doc_id: str, text: str, doc_type: str, schema: dict[str, Any]) -> ProviderOutput:
        import anthropic

        try:
            resp = self.client.beta.messages.create(
                model=self.model,
                max_tokens=8000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt(text, doc_type)}],
                output_config={"effort": self.effort,
                               "format": {"type": "json_schema", "schema": llm_schema(doc_type)}},
                # 안전 분류기가 거절하면 서버가 대체 모델로 다시 실행한다(거절 사유별 자동 선택)
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError) as e:
            raise ProviderError(f"Claude 일시 오류: {type(e).__name__}", transient=True) from e
        except anthropic.APIStatusError as e:
            raise ProviderError(f"Claude 오류 {e.status_code}: {type(e).__name__}") from e
        if resp.stop_reason == "refusal":
            raise ProviderError("Claude가 요청을 거절했습니다(refusal)")
        if resp.stop_reason == "max_tokens":
            raise ProviderError("응답이 max_tokens에서 잘렸습니다")
        text_out = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), "")
        out = parse_json_output(text_out)
        usage = getattr(resp, "usage", None)
        if usage is not None:
            out.usage = {"input_tokens": getattr(usage, "input_tokens", 0) or 0,
                         "output_tokens": getattr(usage, "output_tokens", 0) or 0}
        return out
