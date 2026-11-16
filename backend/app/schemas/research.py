"""Public API + persisted report schemas."""
import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.utils.text import strip_markdown

ResearchMode = Literal["quick", "deep"]
JobStatus = Literal["queued", "running", "completed", "failed"]
ClaimType = Literal["fact", "opinion", "prediction"]
# Deliberately NOT "verified": we only report how many sources a claim cites and whether
# the quoted evidence was found in the retrieved text.
SupportLevel = Literal["multi_source", "single_source", "quote_unverified"]

DATE_UNAVAILABLE = "Date unavailable"
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class ResearchRequest(BaseModel):
    topic: str = Field(description="Research topic or question")
    mode: ResearchMode = "quick"

    @field_validator("topic")
    @classmethod
    def _topic(cls, v: str) -> str:
        v = _CTRL.sub("", v or "").strip()
        v = re.sub(r"\s+", " ", v)
        if len(v) < 5:
            raise ValueError("Topic must be at least 5 characters.")
        if len(v) > 500:
            raise ValueError("Topic must be at most 500 characters.")
        return v


class FollowUpRequest(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def _q(cls, v: str) -> str:
        v = re.sub(r"\s+", " ", _CTRL.sub("", v or "")).strip()
        if len(v) < 3:
            raise ValueError("Question must be at least 3 characters.")
        if len(v) > 1000:
            raise ValueError("Question must be at most 1000 characters.")
        return v


class SavedRequest(BaseModel):
    saved: bool


# ---------------------------------------------------------------- sources


class Source(BaseModel):
    id: str  # S1, S2, ... stable for the lifetime of the research
    title: str
    url: str
    domain: str
    published_date: str = DATE_UNAVAILABLE
    snippet: str = ""  # short excerpt for source cards
    # Tavily's retrieval relevance score. It is NOT a measure of credibility.
    relevance_score: Optional[float] = None
    found_by_queries: list[str] = Field(default_factory=list)

    @field_validator("snippet", mode="before")
    @classmethod
    def _plain_snippet(cls, v):
        # Web extraction returns markdown ("## Heading", "**bold**"); cards show plain prose. Applies on load too,
        # so snippets already stored in history are cleaned as well.
        return strip_markdown(v) if isinstance(v, str) else v


class EvidenceSource(Source):
    """Internal: Source + the full text the LLM saw. Never sent to the browser."""

    evidence_text: str = ""

    def public(self) -> Source:
        return Source(**self.model_dump(exclude={"evidence_text"}))


# ---------------------------------------------------------------- report


class Finding(BaseModel):
    statement: str
    source_ids: list[str]
    claim_type: ClaimType = "fact"
    support_level: SupportLevel = "single_source"
    supporting_quote: str = ""
    quote_verified: bool = False


class Section(BaseModel):
    heading: str
    body: str
    source_ids: list[str] = Field(default_factory=list)
    uncited: bool = False


class ComparisonItem(BaseModel):
    topic: str
    summary: str
    source_ids: list[str] = Field(default_factory=list)
    uncited: bool = False


class Position(BaseModel):
    summary: str
    source_ids: list[str]


class Conflict(BaseModel):
    topic: str
    positions: list[Position]
    assessment: str


class OutdatedItem(BaseModel):
    statement: str
    reason: str
    source_ids: list[str]


class Reference(BaseModel):
    id: str
    title: str
    url: str
    domain: str
    published_date: str = DATE_UNAVAILABLE
    cited: bool = False


class CitationReport(BaseModel):
    total_citations: int = 0
    invalid_ids_removed: int = 0
    invalid_inline_markers_removed: int = 0
    findings_total: int = 0
    findings_quote_verified: int = 0
    findings_dropped_unsupported: int = 0
    notes: list[str] = Field(default_factory=list)


class Report(BaseModel):
    title: str
    objective: str
    executive_summary: str
    key_findings: list[Finding]
    detailed_analysis: list[Section]
    comparison: list[ComparisonItem]
    conflicts: list[Conflict]
    outdated_info: list[OutdatedItem]
    unsupported_claims: list[Finding] = Field(
        default_factory=list,
        description="Model claims that had no valid citation; shown separately, never as findings.",
    )
    limitations: list[str]
    conclusion: str
    insufficient_evidence: bool = False
    references: list[Reference]
    citation_report: CitationReport
    disclaimer: str
    mode: ResearchMode
    model: str
    queries: list[str]
    generated_at: datetime


# ---------------------------------------------------------------- follow-ups


class FollowUpAnswer(BaseModel):
    question: str
    answer: str
    answer_type: Literal["evidence_based", "partially_supported", "not_in_research", "unsupported"]
    source_ids: list[str] = Field(default_factory=list)
    supporting_quote: str = ""
    quote_verified: bool = False
    note: str = ""
    created_at: datetime


# ---------------------------------------------------------------- API envelopes


class ErrorInfo(BaseModel):
    code: str
    message: str
    retryable: bool = False


class ResearchCreated(BaseModel):
    research_id: str
    status: JobStatus


class ResearchStatus(BaseModel):
    id: str
    topic: str
    mode: ResearchMode
    status: JobStatus
    stage: str
    progress: int
    saved: bool = False
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[ErrorInfo] = None
    warnings: list[str] = Field(default_factory=list)
    objective: str = ""
    queries: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    report: Optional[Report] = None
    follow_ups: list[FollowUpAnswer] = Field(default_factory=list)


class HistoryItem(BaseModel):
    id: str
    topic: str
    mode: ResearchMode
    status: JobStatus
    title: str = ""
    sources_count: int = 0
    saved: bool = False
    created_at: datetime
    completed_at: Optional[datetime] = None


class HealthStatus(BaseModel):
    status: Literal["ok", "degraded"]
    tavily_configured: bool
    gemini_configured: bool
    gemini_model: str
