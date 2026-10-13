from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.extract import DEMO_FAILURE_PLAN, SimulatedFailures
from pipeline.providers import MockExtractor
from pipeline.route import Notifier
from pipeline.run import RunSummary, run_pipeline

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "data" / "samples"


@pytest.fixture(scope="session")
def samples() -> Path:
    return SAMPLES


@pytest.fixture(scope="session")
def gold() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((SAMPLES / "gold").glob("*.json"))}


@pytest.fixture(scope="session")
def texts() -> dict[str, str]:
    from pipeline.pdftext import extract_text

    return {p.stem: extract_text(p).text for p in sorted((SAMPLES / "docs").glob("*.pdf"))}


@pytest.fixture(scope="session")
def demo_run(tmp_path_factory) -> RunSummary:
    """저장소 생성본 30건을 모의 추출기 + 공급자 오류 시뮬레이션으로 한 번 돌린다(여러 테스트가 공유)."""
    out = tmp_path_factory.mktemp("run")
    provider = SimulatedFailures(MockExtractor(), DEMO_FAILURE_PLAN)
    return run_pipeline(SAMPLES / "docs", out, provider, notifier=Notifier(console=None, webhook_url=None),
                        sleep=lambda _s: None)
