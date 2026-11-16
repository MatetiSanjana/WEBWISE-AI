"""Orchestrates the whole research run and records progress. Runs as a background task."""
import logging

from app.errors import ResearchError
from app.models import db
from app.services import analyzer, planner, report as report_service, search
from app.services.modes import get_mode

log = logging.getLogger(__name__)


async def run_research(research_id: str) -> None:
    row = db.get_research(research_id)
    if not row:
        return
    topic, cfg = row["topic"], get_mode(row["mode"])
    log.info("[%s] start mode=%s", research_id, cfg.name)

    async def stage(name: str, pct: int) -> None:
        db.update_progress(research_id, name, pct)

    try:
        await stage("Understanding your topic and planning searches", 5)
        plan = await planner.plan_research(topic, cfg)
        db.save_plan(research_id, plan.objective, plan.queries)

        await stage(f"Searching the web ({len(plan.queries)} queries)", 25)
        outcome = await search.search_web(plan.queries, cfg)
        db.save_sources(research_id, [s.model_dump() for s in outcome.sources], outcome.warnings)

        await stage(f"Collected {len(outcome.sources)} unique sources", 45)
        analysis = await analyzer.analyze(topic, plan, outcome.sources, cfg, on_stage=stage)

        await stage("Checking every citation against the retrieved sources", 90)
        final = report_service.build_report(topic, plan, analysis, outcome.sources, cfg)

        db.complete(research_id, final.model_dump(mode="json"), outcome.warnings)
        log.info(
            "[%s] done: %d sources, %d findings, %d invalid ids removed",
            research_id, len(outcome.sources), len(final.key_findings),
            final.citation_report.invalid_ids_removed + final.citation_report.invalid_inline_markers_removed,
        )
    except ResearchError as e:
        log.warning("[%s] failed: %s (%s)", research_id, e.code, e.message)
        db.fail(research_id, e.code, e.message, e.retryable)
    except Exception:  # noqa: BLE001 - last-resort guard so a job never hangs in 'running'
        log.exception("[%s] unexpected error", research_id)
        db.fail(research_id, "INTERNAL_ERROR", "Something went wrong while generating the report. Please retry.", True)
