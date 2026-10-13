"""Gemini 공급자 — GEMINI_API_KEY가 있을 때만 실제로 호출한다.

response_mime_type=application/json + response_json_schema로 스키마에 맞는 JSON만 받는다.
설치: pip install -e ".[llm]"
"""
from __future__ import annotations

import os
from typing import Any

from pipeline.prompts import SYSTEM_PROMPT, llm_schema, user_prompt
from pipeline.providers.base import MissingCredentialError, ProviderError, ProviderOutput, parse_json_output

DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiExtractor:
    name = "gemini"
    is_llm = True

    def __init__(self, api_key: str | None = None, model: str | None = None, client: Any = None):
        self.model = model or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
        self.label = f"Gemini ({self.model})"
        if client is not None:
            self.client = client
            return
        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise MissingCredentialError("GEMINI_API_KEY가 없습니다. 키 없이 실행하려면 --offline(모의 추출기)을 쓰세요.")
        from google import genai

        self.client = genai.Client(api_key=key)

    def extract(self, *, doc_id: str, text: str, doc_type: str, schema: dict[str, Any]) -> ProviderOutput:
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_json_schema=llm_schema(doc_type),
            temperature=0,
        )
        try:
            resp = self.client.models.generate_content(model=self.model, contents=user_prompt(text, doc_type),
                                                       config=config)
        except errors.APIError as e:
            code = getattr(e, "code", 0) or 0
            raise ProviderError(f"Gemini 오류 {code}", transient=code == 429 or code >= 500) from e
        raw = getattr(resp, "text", None)
        if not raw:
            raise ProviderError("Gemini 응답에 텍스트가 없습니다(차단 또는 빈 응답)")
        out = parse_json_output(raw)
        meta = getattr(resp, "usage_metadata", None)
        if meta is not None:
            out.usage = {"input_tokens": getattr(meta, "prompt_token_count", 0) or 0,
                         "output_tokens": getattr(meta, "candidates_token_count", 0) or 0}
        return out
