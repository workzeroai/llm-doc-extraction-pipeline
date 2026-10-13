"""추출 공급자: 모의 추출기(기본, 키 불필요)와 실제 LLM(Gemini·Claude·OpenAI, 키가 있을 때만)."""
from __future__ import annotations

from pipeline.providers.base import (
    MissingCredentialError,
    OutputFormatError,
    Provider,
    ProviderError,
    ProviderOutput,
)
from pipeline.providers.mock import MockExtractor

PROVIDERS = ("mock", "gemini", "anthropic", "openai")
ALIASES = {"claude": "anthropic", "gpt": "openai", "offline": "mock"}


def get_provider(name: str) -> Provider:
    """이름으로 공급자 생성. 실제 공급자는 키가 없으면 MissingCredentialError."""
    key = ALIASES.get(name, name)
    if key == "mock":
        return MockExtractor()
    if key == "gemini":
        from pipeline.providers.gemini import GeminiExtractor

        return GeminiExtractor()
    if key == "anthropic":
        from pipeline.providers.anthropic import AnthropicExtractor

        return AnthropicExtractor()
    if key == "openai":
        from pipeline.providers.openai import OpenAIExtractor

        return OpenAIExtractor()
    raise ValueError(f"알 수 없는 공급자: {name} (가능: {', '.join(PROVIDERS)})")


__all__ = ["PROVIDERS", "MissingCredentialError", "MockExtractor", "OutputFormatError", "Provider", "ProviderError",
           "ProviderOutput", "get_provider"]
