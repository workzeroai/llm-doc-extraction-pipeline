"""OpenAI 공급자 — OPENAI_API_KEY가 있을 때만 실제로 호출한다.

response_format = json_schema(strict)로 스키마에 맞는 JSON만 받는다.
설치: pip install -e ".[llm]"
"""
from __future__ import annotations

import os
from typing import Any

from pipeline.prompts import SYSTEM_PROMPT, llm_schema, user_prompt
from pipeline.providers.base import MissingCredentialError, ProviderError, ProviderOutput, parse_json_output

DEFAULT_MODEL = "gpt-4.1-mini"


class OpenAIExtractor:
    name = "openai"
    is_llm = True

    def __init__(self, api_key: str | None = None, model: str | None = None, client: Any = None):
        self.model = model or os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL
        self.label = f"OpenAI ({self.model})"
        if client is not None:
            self.client = client
            return
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise MissingCredentialError("OPENAI_API_KEY가 없습니다. 키 없이 실행하려면 --offline(모의 추출기)을 쓰세요.")
        from openai import OpenAI

        self.client = OpenAI(api_key=key, max_retries=0)

    def extract(self, *, doc_id: str, text: str, doc_type: str, schema: dict[str, Any]) -> ProviderOutput:
        import openai

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": user_prompt(text, doc_type)}],
                response_format={"type": "json_schema",
                                 "json_schema": {"name": f"{doc_type}_extraction", "schema": llm_schema(doc_type),
                                                 "strict": True}},
                temperature=0,
            )
        except (openai.RateLimitError, openai.InternalServerError, openai.APIConnectionError) as e:
            raise ProviderError(f"OpenAI 일시 오류: {type(e).__name__}", transient=True) from e
        except openai.APIStatusError as e:
            raise ProviderError(f"OpenAI 오류 {e.status_code}: {type(e).__name__}") from e
        msg = resp.choices[0].message
        if getattr(msg, "refusal", None):
            raise ProviderError("OpenAI가 요청을 거절했습니다(refusal)")
        out = parse_json_output(msg.content or "")
        usage = getattr(resp, "usage", None)
        if usage is not None:
            out.usage = {"input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                         "output_tokens": getattr(usage, "completion_tokens", 0) or 0}
        return out
