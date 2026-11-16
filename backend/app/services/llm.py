"""Thin wrapper around the official google-genai SDK: structured JSON output, retries, error mapping."""
import asyncio
import logging
import re
from typing import TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.errors import ResearchError

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

MAX_ATTEMPTS = 3
_RETRY_CODES = {429, 500, 502, 503, 504}
_client: genai.Client | None = None
_client_key: tuple[str, int] | None = None


def _get_client() -> genai.Client:
    global _client, _client_key
    s = get_settings()
    if not s.gemini_configured:
        raise ResearchError(
            "GEMINI_NOT_CONFIGURED",
            "GEMINI_API_KEY is not set. Add it to the .env file and restart the backend.",
            status_code=503,
        )
    # The SDK's async transport is bound to the event loop that first used it, so the cache is keyed by (key, loop).
    # Reusing a client across loops raised "Event loop is closed" (found in live QA when tests ran back to back).
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        loop_id = 0
    key = (s.gemini_api_key, loop_id)
    if _client is None or _client_key != key:
        _client = genai.Client(
            api_key=s.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(s.llm_timeout_seconds * 1000)),
        )
        _client_key = key
    return _client


def _parse_retry_seconds(text: str) -> float | None:
    """Gemini says e.g. 'Please retry in 13h4m32.7s' or 'retry in 21.5s'."""
    m = re.search(r"retry in (?:(\d+)h)?(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?", text, re.I)
    if not m or not any(m.groups()):
        return None
    h, mi, s = (float(g) if g else 0.0 for g in m.groups())
    return h * 3600 + mi * 60 + s


def _human_duration(seconds: float) -> str:
    if seconds >= 3600:
        return f"{seconds / 3600:.0f} h"
    if seconds >= 60:
        return f"{seconds / 60:.0f} min"
    return f"{seconds:.0f} s"


def _is_daily_quota(text: str) -> bool:
    t = text.lower()
    return "per day" in t or "perday" in t.replace(" ", "")


def _map_api_error(e: genai_errors.APIError) -> ResearchError:
    code = getattr(e, "code", None)
    full = getattr(e, "message", None) or str(e)
    detail = full[:300]
    if code in (401, 403) or (code == 400 and "api key" in detail.lower()):
        return ResearchError("GEMINI_AUTH", "Gemini rejected the API key. Check GEMINI_API_KEY.", status_code=502)
    if code == 404:
        return ResearchError(
            "GEMINI_MODEL_NOT_FOUND",
            f"Gemini model '{get_settings().gemini_model}' was not found. Check GEMINI_MODEL.",
            status_code=502,
        )
    if code == 429:
        wait = _parse_retry_seconds(full)
        if _is_daily_quota(full):
            # Retrying cannot help for hours: fail fast with an actionable message.
            when = f" It resets in about {_human_duration(wait)}." if wait else ""
            return ResearchError(
                "GEMINI_QUOTA_DAILY",
                f"The daily Gemini quota for model '{get_settings().gemini_model}' is used up.{when} "
                "Set GEMINI_MODEL to a different model (or enable billing in Google AI Studio) and retry.",
                retryable=False,
            )
        err = ResearchError(
            "GEMINI_RATE_LIMIT", "Gemini's per-minute rate limit was hit. Wait a moment and retry.", retryable=True
        )
        err.retry_after = wait  # type: ignore[attr-defined]
        return err
    if code == 400:
        return ResearchError("GEMINI_BAD_REQUEST", f"Gemini rejected the request: {detail}")
    return ResearchError(
        "GEMINI_UNAVAILABLE", "Gemini is temporarily unavailable. Please retry.", retryable=True
    )


async def generate_json(
    *,
    prompt: str,
    schema: type[T],
    system_instruction: str,
    temperature: float = 0.2,
    max_output_tokens: int = 8192,
    thinking_level: types.ThinkingLevel | None = types.ThinkingLevel.LOW,
    label: str = "llm",
) -> T:
    """Call Gemini and return a validated pydantic object. Never returns unvalidated text.

    NOTE: on Gemini 3/4 models, hidden "thinking" tokens count against max_output_tokens. Extraction-style
    work does not need deep reasoning, so thinking is kept low and the output cap is generous; otherwise the
    JSON gets truncated mid-string (observed in live testing).
    """
    s = get_settings()
    client = _get_client()

    def make_config(with_thinking: bool) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            response_json_schema=schema.model_json_schema(),
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level) if (with_thinking and thinking_level) else None,
        )

    use_thinking = True
    last: ResearchError | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        finish_reason = None
        try:
            resp = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=s.gemini_model, contents=prompt, config=make_config(use_thinking)
                ),
                timeout=s.llm_timeout_seconds + 10,
            )
            if resp.candidates:
                finish_reason = getattr(resp.candidates[0], "finish_reason", None)
            text = resp.text
            if not text:
                raise ResearchError(
                    "GEMINI_EMPTY",
                    f"Gemini returned no content (finish reason: {finish_reason}). Please retry.",
                    retryable=True,
                )
            return schema.model_validate_json(text)
        except ValidationError as e:
            truncated = "MAX_TOKENS" in str(finish_reason)
            log.warning(
                "[%s] attempt %d: output failed schema validation (finish_reason=%s): %s",
                label, attempt, finish_reason, str(e)[:200],
            )
            last = ResearchError(
                "GEMINI_OUTPUT_TRUNCATED" if truncated else "GEMINI_BAD_OUTPUT",
                "Gemini's answer was cut off because it was too long. Please retry, or use Quick mode."
                if truncated
                else "Gemini returned malformed output. Please retry.",
                retryable=True,
            )
        except asyncio.TimeoutError:
            log.warning("[%s] attempt %d: timed out", label, attempt)
            last = ResearchError("GEMINI_TIMEOUT", "Gemini took too long to respond. Please retry.", retryable=True)
        except genai_errors.APIError as e:
            if use_thinking and thinking_level and getattr(e, "code", None) == 400 and "think" in str(e).lower():
                # This model doesn't accept thinking settings: retry once without them.
                log.warning("[%s] model rejected thinking_config; retrying without it", label)
                use_thinking = False
                continue
            mapped = _map_api_error(e)
            log.warning("[%s] attempt %d: Gemini API error code=%s -> %s", label, attempt, getattr(e, "code", "?"), mapped.code)
            if getattr(e, "code", None) not in _RETRY_CODES or not mapped.retryable:
                raise mapped  # includes daily-quota 429s: retrying cannot help
            last = mapped
        except ResearchError as e:
            if not e.retryable:
                raise
            last = e
        if attempt < MAX_ATTEMPTS:
            wait = getattr(last, "retry_after", None)  # honour Gemini's own "retry in Ns" hint (capped)
            await asyncio.sleep(min(wait + 1, 45) if wait else 2 ** attempt)
    assert last is not None
    raise last
