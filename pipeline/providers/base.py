"""추출 공급자 공통 인터페이스.

모든 공급자(모의 추출기, Gemini, Claude, OpenAI)는 같은 입력(문서 텍스트·유형·스키마)을 받아
같은 모양의 출력(스키마 필드 + uncertain_fields)을 낸다. 파이프라인의 나머지 단계는 공급자를 모른다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """공급자 호출 실패. transient=True(429·5xx·연결 오류)면 재시도 대상."""

    def __init__(self, message: str, *, transient: bool = False):
        super().__init__(message)
        self.transient = transient
        self.attempts = 1
        self.errors: list[str] = [message]


class OutputFormatError(ValueError):
    """응답이 JSON 객체가 아니거나 해석할 수 없음 → 스키마 불일치로 분기."""


class MissingCredentialError(RuntimeError):
    """API 키가 없음. 키가 없으면 실제 공급자를 쓰지 않는다."""


@dataclass
class ProviderOutput:
    data: dict[str, Any]
    uncertain_fields: list[str] = field(default_factory=list)
    raw_text: str = ""
    usage: dict[str, int] = field(default_factory=dict)


class Provider(Protocol):
    name: str
    model: str
    is_llm: bool

    def extract(self, *, doc_id: str, text: str, doc_type: str, schema: dict[str, Any]) -> ProviderOutput: ...


def parse_json_output(raw: str) -> ProviderOutput:
    """LLM 응답 텍스트 → ProviderOutput. 코드 블록 울타리(```json)가 있으면 벗긴다."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        raise OutputFormatError(f"JSON 해석 실패: {e.msg} (위치 {e.pos})") from e
    if not isinstance(obj, dict):
        raise OutputFormatError(f"JSON 객체가 아님: {type(obj).__name__}")
    uncertain = obj.pop("uncertain_fields", []) or []
    if not isinstance(uncertain, list):
        uncertain = []
    return ProviderOutput(data=obj, uncertain_fields=[str(u) for u in uncertain], raw_text=raw)
