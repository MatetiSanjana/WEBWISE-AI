"""Web Search Engine: Tavily search -> deduplicated, capped, ID-stamped EvidenceSource list."""
import asyncio
import logging
from dataclasses import dataclass, field

from tavily import AsyncTavilyClient
from tavily import errors as tavily_errors

from app.config import get_settings
from app.errors import ResearchError
from app.schemas.research import DATE_UNAVAILABLE, EvidenceSource
from app.services.modes import ModeConfig
from app.utils.text import clean_text, clip
from app.utils.urls import domain_of, normalize_url

log = logging.getLogger(__name__)

MIN_CONTENT_CHARS = 40


@dataclass
class SearchOutcome:
    sources: list[EvidenceSource]
    warnings: list[str] = field(default_factory=list)
    raw_results: int = 0
    duplicates_removed: int = 0


def _map_tavily_error(e: Exception) -> ResearchError:
    if isinstance(e, tavily_errors.InvalidAPIKeyError | tavily_errors.MissingAPIKeyError):
        return ResearchError("TAVILY_AUTH", "Tavily rejected the API key. Check TAVILY_API_KEY.")
    if isinstance(e, tavily_errors.UsageLimitExceededError):
        return ResearchError("TAVILY_QUOTA", "Tavily usage limit reached. Check your Tavily plan or credits.")
    if isinstance(e, tavily_errors.ForbiddenError):
        return ResearchError("TAVILY_FORBIDDEN", "Tavily refused the request (forbidden). Check your key's permissions.")
    if isinstance(e, tavily_errors.TimeoutError):
        return ResearchError("TAVILY_TIMEOUT", "The web search timed out. Please retry.", retryable=True)
    if isinstance(e, tavily_errors.BadRequestError):
        return ResearchError("TAVILY_BAD_REQUEST", f"Tavily rejected a search request: {str(e)[:200]}")
    return ResearchError("TAVILY_FAILED", "The web search failed. Please retry.", retryable=True)


async def _search_one(client: AsyncTavilyClient, query: str, cfg: ModeConfig, timeout: float) -> list[dict]:
    kwargs: dict = dict(
        query=query,
        search_depth=cfg.search_depth,
        max_results=cfg.results_per_query,
        topic="general",
        timeout=timeout,
    )
    if cfg.include_raw_content:
        kwargs["include_raw_content"] = "markdown"
    resp = await client.search(**kwargs)
    results = resp.get("results") or []
    for r in results:
        r["_query"] = query
    return results


def dedupe_and_select(raw_results: list[dict], cfg: ModeConfig) -> tuple[list[EvidenceSource], int]:
    """Merge results sharing a canonical URL, rank, cap per-domain and overall, assign S-IDs.

    Ranking uses Tavily's relevance score (plus a small bonus for being found by several queries).
    That ordering only decides which sources to *keep* — it is not a credibility judgement.
    """
    merged: dict[str, dict] = {}
    duplicates = 0
    for r in raw_results:
        key = normalize_url(r.get("url"))
        content = clean_text(r.get("content"))
        raw = clean_text(r.get("raw_content"))
        if not key or len(content) + len(raw) < MIN_CONTENT_CHARS:
            continue
        entry = merged.get(key)
        if entry is None:
            merged[key] = {
                "url": r["url"].strip(),
                "title": clean_text(r.get("title")) or domain_of(r["url"]),
                "content": content,
                "raw": raw,
                "score": float(r.get("score") or 0.0),
                "date": clean_text(str(r.get("published_date") or "")) or None,
                "queries": [r.get("_query", "")],
            }
        else:
            duplicates += 1
            if r.get("_query") and r["_query"] not in entry["queries"]:
                entry["queries"].append(r["_query"])
            entry["score"] = max(entry["score"], float(r.get("score") or 0.0))
            if len(content) > len(entry["content"]):
                entry["content"] = content
            if len(raw) > len(entry["raw"]):
                entry["raw"] = raw
            entry["date"] = entry["date"] or clean_text(str(r.get("published_date") or "")) or None

    ranked = sorted(
        merged.values(),
        key=lambda e: e["score"] + 0.05 * (len(e["queries"]) - 1),
        reverse=True,
    )

    per_domain: dict[str, int] = {}
    selected: list[dict] = []
    for e in ranked:
        d = domain_of(e["url"])
        if per_domain.get(d, 0) >= cfg.max_per_domain:
            continue
        per_domain[d] = per_domain.get(d, 0) + 1
        selected.append(e)
        if len(selected) >= cfg.max_sources:
            break

    # Fair share of the prompt budget so one huge page can't crowd out the others.
    per_source_limit = max(500, min(cfg.chars_per_source, cfg.prompt_char_budget // max(1, len(selected))))
    sources: list[EvidenceSource] = []
    for i, e in enumerate(selected, start=1):
        evidence = e["content"]
        if cfg.include_raw_content and e["raw"]:
            evidence = f"{e['content']}\n\n{e['raw']}" if e["content"] else e["raw"]
        sources.append(
            EvidenceSource(
                id=f"S{i}",
                title=e["title"][:300],
                url=e["url"],
                domain=domain_of(e["url"]),
                published_date=e["date"] or DATE_UNAVAILABLE,
                snippet=clip(e["content"] or e["raw"], 400),
                relevance_score=round(e["score"], 4) if e["score"] else None,
                found_by_queries=e["queries"],
                evidence_text=clip(evidence, per_source_limit),
            )
        )
    return sources, duplicates


async def search_web(queries: list[str], cfg: ModeConfig) -> SearchOutcome:
    s = get_settings()
    if not s.tavily_configured:
        raise ResearchError(
            "TAVILY_NOT_CONFIGURED",
            "TAVILY_API_KEY is not set. Add it to the .env file and restart the backend.",
            status_code=503,
        )
    client = AsyncTavilyClient(api_key=s.tavily_api_key)
    outcomes = await asyncio.gather(
        *(_search_one(client, q, cfg, s.http_timeout_seconds) for q in queries),
        return_exceptions=True,
    )

    raw: list[dict] = []
    warnings: list[str] = []
    errors: list[Exception] = []
    for q, res in zip(queries, outcomes):
        if isinstance(res, BaseException):
            if isinstance(res, asyncio.CancelledError):
                raise res
            errors.append(res)
            log.warning("search failed for %r: %s", q, type(res).__name__)
            warnings.append(f"Search failed for query “{q}”.")
        elif not res:
            warnings.append(f"No results returned for query “{q}”.")
        else:
            raw.extend(res)

    if not raw:
        # Every query failed or came back empty: say so plainly instead of fabricating anything.
        if errors:
            raise _map_tavily_error(errors[0])
        raise ResearchError(
            "NO_RESULTS",
            "The web search returned no results for this topic. Try rephrasing it or making it broader.",
            status_code=422,
        )

    sources, dupes = dedupe_and_select(raw, cfg)
    if not sources:
        raise ResearchError(
            "NO_USABLE_SOURCES",
            "Search results were found but none contained usable content. Try rephrasing the topic.",
            status_code=422,
        )
    log.info("search: %d raw results, %d duplicates merged, %d sources kept", len(raw), dupes, len(sources))
    return SearchOutcome(sources=sources, warnings=warnings, raw_results=len(raw), duplicates_removed=dupes)
