"""구조화 추출: 공급자 호출 + 일시 오류 재시도 + (데모용) 공급자 오류 시뮬레이션."""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pipeline.providers import Provider, ProviderError, ProviderOutput
from schemas import load_schema

MAX_ATTEMPTS = 3          # 첫 시도 + 재시도 2회
BACKOFF_SEC = (0.5, 2.0)  # 재시도 전 대기(지수 백오프 단순판)


@dataclass
class ExtractAttempt:
    output: ProviderOutput | None
    attempts: int
    errors: list[str] = field(default_factory=list)


def extract_with_retry(provider: Provider, *, doc_id: str, text: str, doc_type: str,
                       max_attempts: int = MAX_ATTEMPTS, sleep: Callable[[float], None] = time.sleep) -> ExtractAttempt:
    """일시 오류(429·5xx·연결)만 재시도하고, 영구 오류나 재시도 소진은 ProviderError로 올린다."""
    schema = load_schema(doc_type)
    errors: list[str] = []
    for attempt in range(1, max_attempts + 1):
        try:
            out = provider.extract(doc_id=doc_id, text=text, doc_type=doc_type, schema=schema)
            return ExtractAttempt(out, attempt, errors)
        except ProviderError as e:
            errors.append(str(e))
            if not e.transient or attempt == max_attempts:
                final = ProviderError(f"{e} (시도 {attempt}회)", transient=e.transient)
                final.attempts = attempt
                final.errors = errors
                raise final from e
            sleep(BACKOFF_SEC[min(attempt - 1, len(BACKOFF_SEC) - 1)])
    raise AssertionError("도달하지 않음")  # pragma: no cover


class SimulatedFailures:
    """데모용: 지정한 문서에서 처음 N번 호출을 일시 오류(503)로 실패시킨다. 실제 공급자 장애를 흉내 낸다."""

    def __init__(self, inner: Provider, plan: dict[str, int]):
        self.inner = inner
        self.plan = dict(plan)
        self.calls: dict[str, int] = {}
        self.name, self.model, self.is_llm = inner.name, inner.model, inner.is_llm
        self.label = getattr(inner, "label", inner.name)

    def extract(self, *, doc_id: str, text: str, doc_type: str, schema: dict[str, Any]) -> ProviderOutput:
        n = self.calls[doc_id] = self.calls.get(doc_id, 0) + 1
        if n <= self.plan.get(doc_id, 0):
            raise ProviderError("공급자 일시 오류 503(시뮬레이션)", transient=True)
        return self.inner.extract(doc_id=doc_id, text=text, doc_type=doc_type, schema=schema)


# 데모 기본 시뮬레이션: QT-04는 한 번 실패 후 재시도 성공, IV-05는 재시도까지 모두 실패 → 공급자 오류로 확인 대기열
DEMO_FAILURE_PLAN = {"QT-04": 1, "IV-05": MAX_ATTEMPTS}
