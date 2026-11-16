"""Schemas the LLM must produce (Gemini structured output).

Kept deliberately flat/simple: Gemini compiles the schema into a grammar and rejects very deep
or branching schemas. Everything the model returns is untrusted until `services/citations.py`
has validated it against the retrieved sources.
"""
from typing import Literal

from pydantic import BaseModel, Field

ClaimType = Literal["fact", "opinion", "prediction"]


class PlanOutput(BaseModel):
    objective: str = Field(description="One or two sentences stating the research objective.")
    queries: list[str] = Field(description="Distinct web search queries, each covering a different angle.")


class SourceNote(BaseModel):
    source_id: str = Field(description="Source ID exactly as given, e.g. S3.")
    summary: str = Field(description="What this source says about the topic, in 1-3 sentences.")
    claims: list[str] = Field(description="Specific claims made by this source, each stated neutrally.")
    viewpoint: str = Field(description="The source's apparent perspective, e.g. vendor, news report, academic, opinion.")


class SourceNotesOutput(BaseModel):
    notes: list[SourceNote]


class LLMFinding(BaseModel):
    statement: str = Field(description="One finding, written as 'According to ...' / 'Source X reports ...' where appropriate. Include inline [S#] markers.")
    source_ids: list[str] = Field(description="IDs of the sources that support the statement.")
    claim_type: ClaimType = Field(description="fact, opinion, or prediction.")
    supporting_quote: str = Field(description="A VERBATIM excerpt (max 300 characters) copied exactly from one cited source. Empty string if none.")


class LLMSection(BaseModel):
    heading: str
    body: str = Field(description="Analysis text with inline [S#] markers.")
    source_ids: list[str]


class LLMComparison(BaseModel):
    topic: str = Field(description="The point on which sources are being compared.")
    summary: str = Field(description="How the sources compare: where they agree, differ, or add detail. Inline [S#] markers.")
    source_ids: list[str]


class LLMPosition(BaseModel):
    summary: str = Field(description="One side's position, stated neutrally. Inline [S#] markers.")
    source_ids: list[str]


class LLMConflict(BaseModel):
    topic: str
    positions: list[LLMPosition] = Field(description="At least two conflicting, separately sourced positions.")
    assessment: str = Field(description="Why they may differ (date, scope, method...). Do NOT declare a winner without evidence.")


class LLMOutdated(BaseModel):
    statement: str = Field(description="The information that appears outdated. Inline [S#] markers.")
    reason: str = Field(description="Evidence from the sources (dates or newer reports) that it is superseded.")
    source_ids: list[str]


class LLMAnalysis(BaseModel):
    title: str
    objective: str
    executive_summary: str = Field(description="3-6 sentences with inline [S#] markers.")
    key_findings: list[LLMFinding]
    detailed_analysis: list[LLMSection]
    comparison: list[LLMComparison]
    conflicts: list[LLMConflict]
    outdated_info: list[LLMOutdated]
    limitations: list[str] = Field(description="Evidence gaps and limits of this research.")
    conclusion: str = Field(description="Short conclusion with inline [S#] markers.")
    insufficient_evidence: bool = Field(description="True if the sources are too thin to answer the topic reliably.")


class LLMFollowUp(BaseModel):
    answer: str = Field(description="Answer using ONLY the provided report and sources. Inline [S#] markers.")
    answer_type: Literal["evidence_based", "partially_supported", "not_in_research"]
    source_ids: list[str]
    supporting_quote: str = Field(description="VERBATIM excerpt (max 300 chars) from a cited source, or empty string.")
