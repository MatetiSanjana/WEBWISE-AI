"""Gemini quota/error mapping. Messages below are copied from real Gemini 429 responses seen during QA."""
import pytest
from google.genai import errors as genai_errors

from app.errors import ResearchError
from app.schemas.llm import PlanOutput
from app.services import llm

DAILY = (
    "You exceeded your current quota, please check your plan and billing details. "
    "* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, "
    "limit: 20, model: gemini-4-hydrogen, description: Generate content requests per day limit exceeded on Free Tier. "
    "Please retry in 13h4m32.753094743s."
)
PER_MINUTE = "Quota exceeded for metric ... requests per minute ... Please retry in 21.5s."


def _err(code, msg, status="RESOURCE_EXHAUSTED"):
    return genai_errors.ClientError(code, {"error": {"code": code, "message": msg, "status": status}})


def test_parse_retry_seconds():
    assert llm._parse_retry_seconds("Please retry in 13h4m32.7s.") == pytest.approx(13 * 3600 + 4 * 60 + 32.7)
    assert llm._parse_retry_seconds("retry in 21.5s") == pytest.approx(21.5)
    assert llm._parse_retry_seconds("retry in 2m") == 120
    assert llm._parse_retry_seconds("no hint here") is None


def test_daily_quota_is_actionable_and_not_retryable():
    mapped = llm._map_api_error(_err(429, DAILY))
    assert mapped.code == "GEMINI_QUOTA_DAILY" and mapped.retryable is False
    assert "13 h" in mapped.message and "GEMINI_MODEL" in mapped.message


def test_per_minute_limit_is_retryable_with_hint():
    mapped = llm._map_api_error(_err(429, PER_MINUTE))
    assert mapped.code == "GEMINI_RATE_LIMIT" and mapped.retryable is True
    assert mapped.retry_after == pytest.approx(21.5)


class _FakeModels:
    def __init__(self, exc): self.exc, self.calls = exc, 0

    async def generate_content(self, **kw):
        self.calls += 1
        raise self.exc


class _FakeClient:
    def __init__(self, exc):
        self.models = _FakeModels(exc)
        self.aio = type("Aio", (), {"models": self.models})()


async def test_daily_quota_is_not_retried(monkeypatch):
    fake = _FakeClient(_err(429, DAILY))
    monkeypatch.setattr(llm, "_get_client", lambda: fake)
    with pytest.raises(ResearchError) as ei:
        await llm.generate_json(prompt="x", schema=PlanOutput, system_instruction="y")
    assert ei.value.code == "GEMINI_QUOTA_DAILY"
    assert fake.models.calls == 1  # failed fast instead of 3 pointless attempts


async def test_server_errors_are_still_retried(monkeypatch):
    fake = _FakeClient(genai_errors.ServerError(503, {"error": {"code": 503, "message": "overloaded", "status": "UNAVAILABLE"}}))
    monkeypatch.setattr(llm, "_get_client", lambda: fake)

    async def no_sleep(_): return None
    monkeypatch.setattr(llm.asyncio, "sleep", no_sleep)
    with pytest.raises(ResearchError) as ei:
        await llm.generate_json(prompt="x", schema=PlanOutput, system_instruction="y")
    assert ei.value.code == "GEMINI_UNAVAILABLE" and fake.models.calls == llm.MAX_ATTEMPTS
