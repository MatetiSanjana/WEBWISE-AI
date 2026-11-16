import logging
import re

_SECRET_PATTERNS = [
    re.compile(r"tvly-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"(?i)(api[_-]?key=)[^&\s]+"),
]


class _RedactFilter(logging.Filter):
    """Defence in depth: never let an API key reach the logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for pat in _SECRET_PATTERNS:
            msg = pat.sub(lambda m: (m.group(1) if m.lastindex else "") + "[REDACTED]", msg)
        record.msg, record.args = msg, ()
        return True


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    for handler in logging.getLogger().handlers:
        handler.addFilter(_RedactFilter())
    logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx logs full URLs
