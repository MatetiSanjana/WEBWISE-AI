"""Synthetic fixtures for UNIT tests only (the live tests never use these)."""
from app.schemas.llm import (
    LLMAnalysis, LLMComparison, LLMConflict, LLMFinding, LLMPosition, LLMSection,
)
from app.schemas.research import EvidenceSource
from app.services.modes import MODES
from app.services.planner import ResearchPlan

QUICK = MODES["quick"]
DEEP = MODES["deep"]


def make_source(i: int, domain: str | None = None, text: str | None = None, date: str = "Date unavailable") -> EvidenceSource:
    domain = domain or f"site{i}.example.com"
    return EvidenceSource(
        id=f"S{i}", title=f"Title {i}", url=f"https://{domain}/page{i}", domain=domain,
        published_date=date, snippet="snippet",
        evidence_text=text or f"Solar panel efficiency reached {20 + i} percent in laboratory tests during 2024.",
    )


def make_analysis(**over) -> LLMAnalysis:
    base = dict(
        title="Test report", objective="Test objective",
        executive_summary="Efficiency is rising [S1][S2].",
        key_findings=[
            LLMFinding(
                statement="Efficiency reached 21 percent [S1].", source_ids=["S1"], claim_type="fact",
                supporting_quote="Solar panel efficiency reached 21 percent in laboratory tests",
            )
        ],
        detailed_analysis=[LLMSection(heading="Efficiency", body="Lab results improved [S1].", source_ids=["S1"])],
        comparison=[LLMComparison(topic="Efficiency numbers", summary="S1 and S2 agree on direction [S1][S2].", source_ids=["S1", "S2"])],
        conflicts=[], outdated_info=[], limitations=["Only lab results."], conclusion="Rising [S1].",
        insufficient_evidence=False,
    )
    base.update(over)
    return LLMAnalysis(**base)


def make_plan() -> ResearchPlan:
    return ResearchPlan(objective="Test objective", queries=["q1", "q2"])


def raw_result(url: str, query: str = "q1", score: float = 0.5, content: str | None = None, **extra) -> dict:
    return {
        "title": f"Result for {url}", "url": url, "score": score, "_query": query,
        "content": content if content is not None else "Some meaningful content about the topic that is long enough.",
        **extra,
    }
