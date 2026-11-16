"""Tiny in-memory sliding-window rate limiter (per client IP). Fine for a single-process MVP."""
import time
from collections import defaultdict, deque

from fastapi import Request

from app.config import get_settings
from app.errors import ResearchError

_hits: dict[str, deque[float]] = defaultdict(deque)


def reset() -> None:
    _hits.clear()


async def rate_limit(request: Request) -> None:
    limit = get_settings().rate_limit_per_minute
    if limit <= 0:
        return
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    q = _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= limit:
        raise ResearchError(
            "RATE_LIMITED",
            f"Too many requests. Limit is {limit} per minute; please wait a moment.",
            retryable=True,
            status_code=429,
        )
    q.append(now)
