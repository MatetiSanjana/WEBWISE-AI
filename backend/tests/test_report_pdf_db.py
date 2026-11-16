import io

from app.models import db
from app.schemas.llm import LLMFinding
from app.services.pdf import build_pdf
from app.services.report import build_report

from .helpers import QUICK, make_analysis, make_plan, make_source


def _report(**over):
    srcs = [make_source(1), make_source(2), make_source(3)]
    return build_report("solar efficiency", make_plan(), make_analysis(**over), srcs, QUICK), srcs


# ----------------------------------------------------------------- report


def test_report_has_all_required_sections_and_references():
    r, srcs = _report()
    assert r.title and r.objective and r.executive_summary and r.conclusion
    assert r.key_findings and r.detailed_analysis and r.comparison is not None
    assert r.conflicts == [] and isinstance(r.limitations, list)
    assert [x.id for x in r.references] == ["S1", "S2", "S3"]
    assert [x.url for x in r.references] == [s.url for s in srcs]  # references come only from retrieved sources
    assert r.references[0].cited and not r.references[2].cited
    assert r.disclaimer and "not guaranteed" in r.disclaimer


def test_missing_dates_reported_in_limitations():
    r, _ = _report()
    assert any("publication date" in x.lower() for x in r.limitations)
    assert all(ref.published_date == "Date unavailable" for ref in r.references)


def test_insufficient_evidence_when_no_finding_survives():
    a = make_analysis(key_findings=[LLMFinding(statement="Fake [S9].", source_ids=["S9"], claim_type="fact", supporting_quote="")])
    r, _ = _report(key_findings=a.key_findings)
    assert r.insufficient_evidence is True
    assert r.limitations[0] == "Insufficient evidence found."
    assert r.key_findings == [] and len(r.unsupported_claims) == 1


def test_insufficient_evidence_with_single_source():
    r = build_report("t", make_plan(), make_analysis(), [make_source(1)], QUICK)
    assert r.insufficient_evidence is True


def test_model_flag_insufficient_evidence_respected():
    r, _ = _report(insufficient_evidence=True)
    assert r.insufficient_evidence and r.limitations[0] == "Insufficient evidence found."


# ----------------------------------------------------------------- pdf


def test_pdf_generates_valid_file_with_unicode_and_markup_chars():
    r, _ = _report(
        title="Café <b>& “quotes” — naïve</b> 日本",
        executive_summary="Costs rose 5% & fell <2% [S1]. Émigré façade ✓ 😀",
    )
    data = build_pdf(r, "topic with <angle> & ampersand")
    assert data.startswith(b"%PDF") and len(data) > 3000
    assert data.rstrip().endswith(b"%%EOF")


def test_pdf_contains_clickable_reference_links():
    r, srcs = _report()
    data = build_pdf(r, "t")
    assert b"/URI" in data and srcs[0].url.encode() in data


def test_pdf_for_insufficient_report():
    r = build_report("t", make_plan(), make_analysis(key_findings=[], detailed_analysis=[], comparison=[]), [make_source(1)], QUICK)
    assert build_pdf(r, "t").startswith(b"%PDF")


# ----------------------------------------------------------------- db


def test_db_lifecycle_history_and_followups():
    rid = db.create_research("a topic here", "quick", "client-aaaaaaaaaaaaaaaa")
    row = db.get_research(rid)
    assert row["status"] == "queued" and row["saved"] == 0
    db.update_progress(rid, "Searching", 25)
    assert db.get_research(rid)["status"] == "running"
    db.fail(rid, "X", "boom", True)
    assert db.get_research(rid)["status"] == "failed"
    db.reset_for_retry(rid)
    assert db.get_research(rid)["status"] == "queued" and db.get_research(rid)["error_json"] is None
    db.complete(rid, {"title": "T"}, [])
    assert db.get_research(rid)["status"] == "completed"

    assert db.set_saved(rid, True)
    assert [h["id"] for h in db.list_history(10, 0, True, "client-aaaaaaaaaaaaaaaa")] == [rid]
    other = db.create_research("another topic", "deep", "client-aaaaaaaaaaaaaaaa")
    assert {h["id"] for h in db.list_history(10, 0, False, "client-aaaaaaaaaaaaaaaa")} == {rid, other}
    assert [h["id"] for h in db.list_history(10, 0, True, "client-aaaaaaaaaaaaaaaa")] == [rid]
    assert db.list_history(10, 0, False, "client-bbbbbbbbbbbbbbbb") == []  # different browser
    assert db.list_history(10, 0, False, None) == []

    db.add_followup(rid, {"question": "q", "answer": "a"})
    assert db.list_followups(rid)[0]["answer"] == "a"
    assert db.delete_research(rid)
    assert db.get_research(rid) is None and db.list_followups(rid) == []


def test_interrupted_jobs_marked_failed_on_startup():
    rid = db.create_research("a topic here", "quick")
    db.update_progress(rid, "Searching", 30)
    assert db.mark_interrupted() == 1
    row = db.get_research(rid)
    assert row["status"] == "failed" and "restarted" in row["error_json"]
