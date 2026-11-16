"""Research Planner: topic -> objective + diverse search queries (mode-dependent count)."""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.errors import ResearchError
from app.schemas.llm import PlanOutput
from app.services import llm
from app.services.modes import ModeConfig
from app.utils.text import clean_text

log = logging.getLogger(__name__)

SYSTEM = (
    "You are a research planner. You design web search queries that together cover a topic "
    "from different angles. You do not answer the topic; you only plan the searching."
)


@dataclass
class ResearchPlan:
    objective: str
    queries: list[str]


def _build_prompt(topic: str, cfg: ModeConfig) -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    return f"""Today's date: {today}

Research topic / question:
\"\"\"{topic}\"\"\"

Write the research objective (1-2 sentences) and exactly {cfg.num_queries} distinct web search queries.

Requirements:
- Each query must target a DIFFERENT angle, for example: overview/definition, latest developments,
  data and statistics, expert or official sources, criticism or opposing views, comparisons.
- Do not repeat or lightly reword another query.
- Queries must be short, natural search-engine phrasing (under 120 characters), no quotes or operators unless essential.
- If the topic is time-sensitive, include the current year ({today[:4]}) in at least one query.
- Stay faithful to the topic; do not add unrelated subjects."""


def _tidy_queries(raw: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for q in raw:
        q = clean_text(q).replace("\n", " ").strip(" \"'")[:200]
        key = " ".join(q.lower().split())
        if len(q) < 3 or key in seen:
            continue
        seen.add(key)
        out.append(q)
    return out[:limit]


async def plan_research(topic: str, cfg: ModeConfig) -> ResearchPlan:
    out = await llm.generate_json(
        prompt=_build_prompt(topic, cfg),
        schema=PlanOutput,
        system_instruction=SYSTEM,
        temperature=0.4,
        max_output_tokens=1024,
        label="planner",
    )
    queries = _tidy_queries(out.queries, cfg.num_queries)
    if not queries:
        raise ResearchError(
            "PLAN_EMPTY", "The planner did not produce any usable search queries. Please retry.", retryable=True
        )
    objective = clean_text(out.objective) or f"Research: {topic}"
    log.info("planned %d queries (mode=%s)", len(queries), cfg.name)
    return ResearchPlan(objective=objective, queries=queries)
