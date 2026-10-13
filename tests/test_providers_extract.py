"""공급자 어댑터: 실제 API를 부르지 않고 가짜 클라이언트로 요청 모양·응답 해석·오류 분류만 확인한다."""
import json
from types import SimpleNamespace

import httpx
import pytest

from pipeline.extract import SimulatedFailures, extract_with_retry
from pipeline.providers import (
    MissingCredentialError,
    MockExtractor,
    OutputFormatError,
    ProviderError,
    ProviderOutput,
    get_provider,
)
from pipeline.providers.anthropic import AnthropicExtractor
from pipeline.providers.base import parse_json_output
from pipeline.providers.gemini import GeminiExtractor
from pipeline.providers.openai import OpenAIExtractor
from schemas import load_schema

ANSWER = {"quote_no": "Q1", "issue_date": "2026-01-01", "valid_until": None, "supplier_name": "가", "supplier_biz_no": None,
          "client_name": "나", "manager": None, "items": [], "subtotal": 0, "vat": 0, "total": 0,
          "uncertain_fields": ["total"]}
REQ = httpx.Request("POST", "https://api.invalid/v1")


def _call(p):
    return p.extract(doc_id="QT-01", text="견적서 본문", doc_type="quote", schema=load_schema("quote"))


# ---------------------------------------------------------------- 공통 파싱

def test_parse_json_output_variants():
    out = parse_json_output("```json\n" + json.dumps(ANSWER) + "\n```")
    assert out.data["quote_no"] == "Q1" and out.uncertain_fields == ["total"]
    assert "uncertain_fields" not in out.data
    assert parse_json_output('{"a": 1, "uncertain_fields": "x"}').uncertain_fields == []
    with pytest.raises(OutputFormatError):
        parse_json_output("[1, 2]")
    with pytest.raises(OutputFormatError):
        parse_json_output("not json")


def test_missing_keys_raise(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    for name in ("gemini", "anthropic", "claude", "openai"):
        with pytest.raises(MissingCredentialError):
            get_provider(name)
    assert isinstance(get_provider("offline"), MockExtractor)
    with pytest.raises(ValueError):
        get_provider("nope")


def test_real_clients_construct_with_key(monkeypatch):
    """키가 있으면 SDK 클라이언트를 만든다(네트워크 호출 없음)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # qa-scan: allow
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")  # qa-scan: allow
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")  # qa-scan: allow
    assert get_provider("anthropic").model == "claude-opus-5-5"
    assert get_provider("gemini").model.startswith("gemini")
    assert get_provider("openai").name == "openai"


# ---------------------------------------------------------------- Claude

class _AnthropicFake:
    def __init__(self, result=None, exc=None):
        self.kw = None
        self.result, self.exc = result, exc
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.kw = kw
        if self.exc:
            raise self.exc
        return self.result


def _claude_msg(text, stop="end_turn"):
    return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=text)],
                           usage=SimpleNamespace(input_tokens=11, output_tokens=7))


def test_anthropic_request_and_parse():
    fake = _AnthropicFake(_claude_msg(json.dumps(ANSWER)))
    out = _call(AnthropicExtractor(client=fake))
    assert out.data["client_name"] == "나" and out.usage == {"input_tokens": 11, "output_tokens": 7}
    kw = fake.kw
    assert kw["model"] == "claude-opus-5-5"
    assert kw["output_config"]["format"]["type"] == "json_schema"
    assert kw["output_config"]["effort"] == "low"
    assert kw["fallbacks"] == "default" and kw["betas"] == ["server-side-fallback-2026-07-01"]
    assert "견적서 본문" in kw["messages"][0]["content"]


@pytest.mark.parametrize(("stop", "msg"), [("refusal", "거절"), ("max_tokens", "잘렸")])
def test_anthropic_stop_reasons(stop, msg):
    with pytest.raises(ProviderError, match=msg):
        _call(AnthropicExtractor(client=_AnthropicFake(_claude_msg("{}", stop))))


def test_anthropic_error_mapping():
    import anthropic

    rate = anthropic.RateLimitError("rate", response=httpx.Response(429, request=REQ), body=None)
    with pytest.raises(ProviderError) as e:
        _call(AnthropicExtractor(client=_AnthropicFake(exc=rate)))
    assert e.value.transient
    bad = anthropic.BadRequestError("bad", response=httpx.Response(400, request=REQ), body=None)
    with pytest.raises(ProviderError) as e:
        _call(AnthropicExtractor(client=_AnthropicFake(exc=bad)))
    assert not e.value.transient


# ---------------------------------------------------------------- Gemini

class _GeminiFake:
    def __init__(self, result=None, exc=None):
        self.kw = None
        self.result, self.exc = result, exc
        self.models = SimpleNamespace(generate_content=self.generate_content)

    def generate_content(self, **kw):
        self.kw = kw
        if self.exc:
            raise self.exc
        return self.result


def test_gemini_request_and_parse():
    resp = SimpleNamespace(text=json.dumps(ANSWER),
                           usage_metadata=SimpleNamespace(prompt_token_count=5, candidates_token_count=3))
    fake = _GeminiFake(resp)
    out = _call(GeminiExtractor(client=fake))
    assert out.data["quote_no"] == "Q1" and out.usage["input_tokens"] == 5
    cfg = fake.kw["config"]
    assert cfg.response_mime_type == "application/json" and cfg.response_json_schema["additionalProperties"] is False


def test_gemini_errors():
    from google.genai import errors

    with pytest.raises(ProviderError) as e:
        _call(GeminiExtractor(client=_GeminiFake(exc=errors.ServerError(503, {"error": {"message": "x"}}))))
    assert e.value.transient
    with pytest.raises(ProviderError) as e:
        _call(GeminiExtractor(client=_GeminiFake(exc=errors.ClientError(400, {"error": {"message": "x"}}))))
    assert not e.value.transient
    with pytest.raises(ProviderError, match="텍스트가 없"):
        _call(GeminiExtractor(client=_GeminiFake(SimpleNamespace(text=None))))


# ---------------------------------------------------------------- OpenAI

class _OpenAIFake:
    def __init__(self, result=None, exc=None):
        self.kw = None
        self.result, self.exc = result, exc
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.kw = kw
        if self.exc:
            raise self.exc
        return self.result


def _oa(content, refusal=None):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, refusal=refusal))],
                           usage=SimpleNamespace(prompt_tokens=9, completion_tokens=4))


def test_openai_request_and_parse():
    fake = _OpenAIFake(_oa(json.dumps(ANSWER)))
    out = _call(OpenAIExtractor(client=fake))
    assert out.data["supplier_name"] == "가" and out.usage["output_tokens"] == 4
    rf = fake.kw["response_format"]
    assert rf["type"] == "json_schema" and rf["json_schema"]["strict"] is True


def test_openai_errors():
    import openai

    with pytest.raises(ProviderError, match="거절"):
        _call(OpenAIExtractor(client=_OpenAIFake(_oa(None, refusal="no"))))
    conn = openai.APIConnectionError(request=REQ)
    with pytest.raises(ProviderError) as e:
        _call(OpenAIExtractor(client=_OpenAIFake(exc=conn)))
    assert e.value.transient
    nf = openai.NotFoundError("nf", response=httpx.Response(404, request=REQ), body=None)
    with pytest.raises(ProviderError) as e:
        _call(OpenAIExtractor(client=_OpenAIFake(exc=nf)))
    assert not e.value.transient


# ---------------------------------------------------------------- 재시도

class _Flaky:
    name, model, is_llm = "flaky", "x", False

    def __init__(self, errors):
        self.errors = list(errors)
        self.calls = 0

    def extract(self, **kw):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return ProviderOutput(data={"ok": True})


def test_retry_transient_then_success():
    p = _Flaky([ProviderError("503", transient=True)])
    waits = []
    att = extract_with_retry(p, doc_id="A", text="t", doc_type="quote", sleep=waits.append)
    assert att.attempts == 2 and att.errors == ["503"] and waits == [0.5]


def test_retry_exhausted_and_permanent():
    p = _Flaky([ProviderError("503", transient=True)] * 3)
    with pytest.raises(ProviderError) as e:
        extract_with_retry(p, doc_id="A", text="t", doc_type="quote", sleep=lambda _s: None)
    assert e.value.attempts == 3 and len(e.value.errors) == 3
    p = _Flaky([ProviderError("400")])
    with pytest.raises(ProviderError) as e:
        extract_with_retry(p, doc_id="A", text="t", doc_type="quote", sleep=lambda _s: None)
    assert e.value.attempts == 1 and p.calls == 1


def test_simulated_failures_wrapper():
    sim = SimulatedFailures(MockExtractor(), {"QT-01": 1})
    assert sim.is_llm is False and "LLM 아님" in sim.label
    with pytest.raises(ProviderError):
        _call(sim)
    assert _call(sim).data is not None
