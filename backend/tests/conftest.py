import pytest

from app.config import get_settings
from app.models import db
from app.utils import ratelimit


def _real_keys_available() -> bool:
    get_settings.cache_clear()
    s = get_settings()
    return s.tavily_configured and s.gemini_configured


@pytest.fixture(autouse=True)
def isolated_env(request, tmp_path, monkeypatch):
    """Every test gets its own SQLite file. Non-live tests also get fake keys (never real ones)."""
    live = request.node.get_closest_marker("live") or request.node.get_closest_marker("live_deep")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1000")
    if live:
        if not _real_keys_available():
            pytest.skip("live test: TAVILY_API_KEY / GEMINI_API_KEY not configured in .env")
    else:
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-fake-key-0000")
        monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key-for-unit-tests")
    get_settings.cache_clear()
    ratelimit.reset()
    db.init_db()
    yield
    get_settings.cache_clear()
