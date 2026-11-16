"""Evidence and Citation Checker.

Everything the LLM returns is untrusted. This module:
  * normalises citation IDs and drops any that do not correspond to a retrieved source,
  * strips invalid inline [S#] markers from prose,
  * checks that each finding's supporting_quote really appears in one of its cited sources,
  * moves findings with no valid citation out of `key_findings` into `unsupported_claims`.
"""
import re
from dataclasses import dataclass, field

from app.schemas.llm import LLMAnalysis, LLMFinding
from app.schemas.research import (
    CitationReport,
    ComparisonItem,
    Conflict,
    EvidenceSource,
    Finding,
    OutdatedItem,
    Position,
    Section,
)
from app.utils.text import normalize_for_match

_ID = re.compile(r"^\s*\[?\s*[Ss]\s*0*(\d+)\s*\]?\s*$")
# Matches [S1], [S1, S2], [S1][S2] groups; we canonicalise every group.
_MARKER_GROUP = re.compile(r"\[\s*[Ss]\d+(?:\s*[,;]\s*[Ss]?\d+)*\s*\]")
_MARKER_ID = re.compile(r"[Ss]?(\d+)")


@dataclass
class _Tally:
    invalid_ids: int = 0
    invalid_markers: int = 0
    notes: list[str] = field(default_factory=list)


def normalize_id(raw: str) -> str | None:
    m = _ID.match(str(raw))
    return f"S{int(m.group(1))}" if m else None


def clean_ids(ids: list[str], valid: set[str], tally: _Tally) -> list[str]:
    out: list[str] = []
    for raw in ids or []:
        sid = normalize_id(raw)
        if sid and sid in valid:
            if sid not in out:
                out.append(sid)
        else:
            tally.invalid_ids += 1
    return out


def clean_markers(text: str, valid: set[str], tally: _Tally) -> tuple[str, list[str]]:
    """Rewrite inline markers to canonical '[S1][S2]', dropping any ID that is not a real source."""
    found: list[str] = []

    def repl(m: re.Match) -> str:
        kept: list[str] = []
        for num in _MARKER_ID.findall(m.group(0)):
            sid = f"S{int(num)}"
            if sid in valid:
                kept.append(sid)
                if sid not in found:
                    found.append(sid)
            else:
                tally.invalid_markers += 1
        return "".join(f"[{s}]" for s in kept)

    cleaned = _MARKER_GROUP.sub(repl, text or "")
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).replace(" .", ".").replace(" ,", ",")
    return cleaned.strip(), found


def _merge(a: list[str], b: list[str]) -> list[str]:
    return a + [x for x in b if x not in a]


def quote_in_sources(quote: str, source_ids: list[str], by_id: dict[str, EvidenceSource]) -> bool:
    """True if the (normalised) quote appears verbatim in at least one cited source's text."""
    q = normalize_for_match(quote)
    if len(q) < 12:
        return False
    # Allow the model to elide with "..." as long as every substantial segment is present.
    segments = [seg.strip() for seg in re.split(r"…|\.\.\.", q) if len(seg.strip()) >= 12] or [q]
    for sid in source_ids:
        src = by_id.get(sid)
        if not src:
            continue
        haystack = normalize_for_match(f"{src.title} {src.evidence_text}")
        if all(seg in haystack for seg in segments):
            return True
    return False


def _support_level(ids: list[str], quote_ok: bool, by_id: dict[str, EvidenceSource]) -> str:
    if not quote_ok:
        return "quote_unverified"
    domains = {by_id[i].domain for i in ids if i in by_id}
    return "multi_source" if len(domains) >= 2 else "single_source"


def _build_finding(f: LLMFinding, valid: set[str], by_id: dict[str, EvidenceSource], tally: _Tally) -> Finding:
    ids = clean_ids(f.source_ids, valid, tally)
    statement, inline = clean_markers(f.statement, valid, tally)
    ids = _merge(ids, inline)
    quote = (f.supporting_quote or "").strip()[:400]
    quote_ok = bool(ids) and quote_in_sources(quote, ids, by_id)
    return Finding(
        statement=statement,
        source_ids=ids,
        claim_type=f.claim_type,
        support_level=_support_level(ids, quote_ok, by_id),
        supporting_quote=quote if quote_ok else "",
        quote_verified=quote_ok,
    )


@dataclass
class ValidatedAnalysis:
    executive_summary: str
    conclusion: str
    key_findings: list[Finding]
    unsupported_claims: list[Finding]
    detailed_analysis: list[Section]
    comparison: list[ComparisonItem]
    conflicts: list[Conflict]
    outdated_info: list[OutdatedItem]
    limitations: list[str]
    cited_ids: set[str]
    report: CitationReport


def validate_analysis(analysis: LLMAnalysis, sources: list[EvidenceSource]) -> ValidatedAnalysis:
    valid = {s.id for s in sources}
    by_id = {s.id: s for s in sources}
    tally = _Tally()
    cited: set[str] = set()

    summary, ids = clean_markers(analysis.executive_summary, valid, tally)
    cited.update(ids)
    conclusion, ids = clean_markers(analysis.conclusion, valid, tally)
    cited.update(ids)

    findings: list[Finding] = []
    unsupported: list[Finding] = []
    for f in analysis.key_findings:
        built = _build_finding(f, valid, by_id, tally)
        if not built.statement:
            continue
        if built.source_ids:
            findings.append(built)
            cited.update(built.source_ids)
        else:
            unsupported.append(built)
    if unsupported:
        tally.notes.append(
            f"{len(unsupported)} claim(s) from the model had no valid citation and were excluded from key findings."
        )

    sections: list[Section] = []
    for s in analysis.detailed_analysis:
        body, inline = clean_markers(s.body, valid, tally)
        ids = _merge(clean_ids(s.source_ids, valid, tally), inline)
        if not body:
            continue
        cited.update(ids)
        sections.append(Section(heading=s.heading.strip(), body=body, source_ids=ids, uncited=not ids))

    comparison: list[ComparisonItem] = []
    for c in analysis.comparison:
        text, inline = clean_markers(c.summary, valid, tally)
        ids = _merge(clean_ids(c.source_ids, valid, tally), inline)
        if not text:
            continue
        cited.update(ids)
        comparison.append(ComparisonItem(topic=c.topic.strip(), summary=text, source_ids=ids, uncited=not ids))

    conflicts: list[Conflict] = []
    for c in analysis.conflicts:
        positions: list[Position] = []
        for p in c.positions:
            text, inline = clean_markers(p.summary, valid, tally)
            ids = _merge(clean_ids(p.source_ids, valid, tally), inline)
            if text and ids:
                positions.append(Position(summary=text, source_ids=ids))
        if len(positions) >= 2:
            assessment, _ = clean_markers(c.assessment, valid, tally)
            for p in positions:
                cited.update(p.source_ids)
            conflicts.append(Conflict(topic=c.topic.strip(), positions=positions, assessment=assessment))
        else:
            tally.notes.append(
                f"A possible conflict about “{c.topic.strip()[:80]}” was dropped because it did not have two separately cited positions."
            )

    outdated: list[OutdatedItem] = []
    for o in analysis.outdated_info:
        text, inline = clean_markers(o.statement, valid, tally)
        ids = _merge(clean_ids(o.source_ids, valid, tally), inline)
        reason, _ = clean_markers(o.reason, valid, tally)
        if text and ids and reason:
            cited.update(ids)
            outdated.append(OutdatedItem(statement=text, reason=reason, source_ids=ids))

    limitations = [clean_markers(x, valid, tally)[0] for x in analysis.limitations if x and x.strip()]

    report = CitationReport(
        total_citations=sum(len(f.source_ids) for f in findings)
        + sum(len(s.source_ids) for s in sections)
        + sum(len(c.source_ids) for c in comparison),
        invalid_ids_removed=tally.invalid_ids,
        invalid_inline_markers_removed=tally.invalid_markers,
        findings_total=len(findings),
        findings_quote_verified=sum(1 for f in findings if f.quote_verified),
        findings_dropped_unsupported=len(unsupported),
        notes=tally.notes,
    )
    return ValidatedAnalysis(
        executive_summary=summary,
        conclusion=conclusion,
        key_findings=findings,
        unsupported_claims=unsupported,
        detailed_analysis=sections,
        comparison=comparison,
        conflicts=conflicts,
        outdated_info=outdated,
        limitations=limitations,
        cited_ids=cited,
        report=report,
    )


def validate_followup(answer_ids: list[str], text: str, quote: str, sources: list[EvidenceSource]):
    """Validate a follow-up answer. Returns (clean_text, ids, quote_verified, invalid_count)."""
    valid = {s.id for s in sources}
    by_id = {s.id: s for s in sources}
    tally = _Tally()
    clean, inline = clean_markers(text, valid, tally)
    ids = _merge(clean_ids(answer_ids, valid, tally), inline)
    ok = bool(ids) and quote_in_sources(quote, ids, by_id)
    return clean, ids, ok, tally.invalid_ids + tally.invalid_markers
