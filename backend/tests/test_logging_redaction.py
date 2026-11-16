import logging

from app.utils.logging import configure_logging

# Fake credentials, assembled at runtime so no key-shaped literal sits in the source
# (secret scanners, including GitHub push protection, match on the shape of the string).
FAKE_TAVILY = "tvly" + "-" + "abcdefghijklmnop1234"
FAKE_GEMINI = "AIza" + "Sy" + "A1234567890abcdefghijklmnopqrstu"
FAKE_QUERY_KEY = "SECRETVALUE123"


def test_api_keys_are_redacted_from_logs(caplog):
    configure_logging("INFO")
    handler = logging.getLogger().handlers[-1]
    rec = logging.LogRecord(
        "t", logging.WARNING, __file__, 1,
        f"request to https://x/v1?api_key={FAKE_QUERY_KEY} failed; key {FAKE_TAVILY} and {FAKE_GEMINI}",
        None, None,
    )
    for f in handler.filters:
        f.filter(rec)
    out = rec.getMessage()
    assert FAKE_QUERY_KEY not in out and FAKE_TAVILY not in out and FAKE_GEMINI not in out
    assert out.count("[REDACTED]") == 3
