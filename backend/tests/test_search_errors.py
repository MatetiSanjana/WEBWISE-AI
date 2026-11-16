"""Failure handling for search + LLM timeouts. Fakes replace the network ONLY here, to exercise our own error paths;
the live auth-error behaviour was verified separately against the real Tavily and Gemini APIs."""
import asyncio

import pytest
from tavily import errors as te

from app.errors import ResearchError
from app.schemas.llm import PlanOutput
from app.services import llm, search
from app.services.modes import MODES

from .helpers import raw_result

QUICK = MODES["quick"]


@pytest.mark.parametrize(
    "exc, code, retryable",
    [
        (te.InvalidAPIKeyError("bad"), "TAVILY_AUTH", False),
        (te.MissingAPIKeyError(), "TAVILY_AUTH", False),
        (te.UsageLimitExceededError("limit"), "TAVILY_QUOTA", False),
        (te.ForbiddenError("no"), "TAVILY_FORBIDDEN", False),
        (te.TimeoutError(30), "TAVILY_TIMEOUT", True),
        (te.BadRequestError("bad req"), "TAVILY_BAD_REQUEST", False),
        (RuntimeError("socket closed"), "TAVILY_FAILED", True),
    ],
)
def test_tavily_errors_map_to_clear_messages(exc, code, retryable):
    mapped = search._map_tavily_error(exc)
    assert mapped.code == code and mapped.retryable is retryable and mapped.message


class FakeTavily:
    """results_by_query: query -> list[dict] | Exception"""

    def __init__(self, results_by_query):
        FakeTavily.table = results_by_query

    def __call__(self, api_key=None):
        return self

    async def search(self, query, **kw):
        out = FakeTavily.table[query]
        if isinstance(out, Exception):
            raise out
        return {"results": [dict(r) for r in out]}


async def test_all_queries_failing_raises_instead_of_inventing_results(monkeypatch):
    monkeypatch.setattr(search, "AsyncTavilyClient", FakeTavily({"a": te.TimeoutError(5), "b": te.TimeoutError(5)}))
    with pytest.raises(ResearchError) as ei:
        await search.search_web(["a", "b"], QUICK)
    assert ei.value.code == "TAVILY_TIMEOUT"


async def test_empty_results_raise_no_results(monkeypatch):
    monkeypatch.setattr(search, "AsyncTavilyClient", FakeTavily({"a": [], "b": []}))
    with pytest.raises(ResearchError) as ei:
        await search.search_web(["a", "b"], QUICK)
    assert ei.value.code == "NO_RESULTS" and ei.value.status_code == 422


async def test_results_without_usable_content_raise(monkeypatch):
    junk = [raw_result("https://x.com/1", content="hi"), raw_result("ftp://x.com/2")]
    monkeypatch.setattr(search, "AsyncTavilyClient", FakeTavily({"a": junk}))
    with pytest.raises(ResearchError) as ei:
        await search.search_web(["a"], QUICK)
    assert ei.value.code == "NO_USABLE_SOURCES"


async def test_partial_failure_degrades_with_warning(monkeypatch):
    good = [raw_result("https://ok.com/1"), raw_result("https://ok.com/1?utm_source=z")]
    monkeypatch.setattr(search, "AsyncTavilyClient", FakeTavily({"a": good, "b": te.TimeoutError(5), "c": []}))
    out = await search.search_web(["a", "b", "c"], QUICK)
    assert len(out.sources) == 1 and out.duplicates_removed == 1
    assert any("b" in w for w in out.warnings) and any("No results" in w for w in out.warnings)


async def test_missing_tavily_key_is_a_clear_503(monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("TAVILY_API_KEY", "")
    get_settings.cache_clear()
    with pytest.raises(ResearchError) as ei:
        await search.search_web(["a"], QUICK)
    assert ei.value.code == "TAVILY_NOT_CONFIGURED" and ei.value.status_code == 503


class _TimeoutClient:
    def __init__(self):
        self.calls = 0
        self.aio = type("Aio", (), {"models": self})()

    async def generate_content(self, **kw):
        self.calls += 1
        raise asyncio.TimeoutError()


async def test_gemini_timeout_is_retried_then_reported(monkeypatch):
    fake = _TimeoutClient()
    monkeypatch.setattr(llm, "_get_client", lambda: fake)

    async def no_sleep(_): return None
    monkeypatch.setattr(llm.asyncio, "sleep", no_sleep)
    with pytest.raises(ResearchError) as ei:
        await llm.generate_json(prompt="x", schema=PlanOutput, system_instruction="y")
    assert ei.value.code == "GEMINI_TIMEOUT" and ei.value.retryable and fake.calls == llm.MAX_ATTEMPTS


async def test_missing_gemini_key_is_a_clear_503(monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()
    with pytest.raises(ResearchError) as ei:
        await llm.generate_json(prompt="x", schema=PlanOutput, system_instruction="y")
    assert ei.value.code == "GEMINI_NOT_CONFIGURED" and ei.value.status_code == 503
