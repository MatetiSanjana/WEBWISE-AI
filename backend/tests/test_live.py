"""LIVE tests: real Tavily + real Gemini. No mocks. Skipped automatically when keys are missing.

Run:  pytest -m live -s         (planner, search, full quick-mode user journey)
      pytest -m live_deep -s    (Deep-mode run; slower, uses more quota)
Output of the last full run is written to backend/data/live_last_run*.json for manual citation checks.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import PROJECT_ROOT
from app.main import create_app
from app.schemas.research import Report
from app.services import planner, search
from app.services.modes import MODES
from app.utils.urls import normalize_url

TOPIC = "Current status of solid-state battery commercialization for electric vehicles"
OUT_DIR = PROJECT_ROOT / "backend" / "data"


def _check_report_integrity(client: TestClient, rid: str) -> dict:
    """Shared assertions: every citation must point at a source that was really retrieved."""
    st = client.get(f"/api/research/{rid}").json()
    assert st["status"] == "completed", st.get("error")
    report = Report(**client.get(f"/api/research/{rid}/report").json())
    ids = {s["id"] for s in st["sources"]}
    urls = [s["url"] for s in st["sources"]]

    assert len(ids) >= 2, "expected multiple sources from the live web"
    assert len({normalize_url(u) for u in urls}) == len(urls), "duplicate URLs survived dedupe"
    assert all(u.startswith(("http://", "https://")) for u in urls)
    assert ids == {f"S{i}" for i in range(1, len(ids) + 1)}

    # references are exactly the retrieved sources — nothing invented
    assert {r.url for r in report.references} == set(urls)
    for f in report.key_findings:
        assert f.source_ids and set(f.source_ids) <= ids
    for s in [*report.detailed_analysis, *report.comparison]:
        assert set(s.source_ids) <= ids
    for c in report.conflicts:
        assert len(c.positions) >= 2
        for p in c.positions:
            assert p.source_ids and set(p.source_ids) <= ids
    import re
    prose = " ".join([report.executive_summary, report.conclusion, *[f.statement for f in report.key_findings],
                      *[s.body for s in report.detailed_analysis]])
    assert set(re.findall(r"\[(S\d+)\]", prose)) <= ids, "report prose cites an ID that was never retrieved"
    # every source either has a real date string or the explicit marker
    for s in st["sources"]:
        assert s["published_date"]
    return {"status": st, "report": report.model_dump(mode="json")}


@pytest.mark.live
async def test_live_planner_makes_distinct_queries():
    plan = await planner.plan_research(TOPIC, MODES["quick"])
    assert plan.objective
    assert len(plan.queries) == MODES["quick"].num_queries
    assert len({q.lower() for q in plan.queries}) == len(plan.queries)
    print("\nPLAN:", plan.queries)


@pytest.mark.live
async def test_live_tavily_search_returns_deduped_sources():
    out = await search.search_web([TOPIC, "solid state battery 2026 production timeline"], MODES["quick"])
    assert len(out.sources) >= 3
    assert out.raw_results >= len(out.sources)
    urls = [s.url for s in out.sources]
    assert len({normalize_url(u) for u in urls}) == len(urls)
    assert all(s.evidence_text for s in out.sources)
    print(f"\nSEARCH: raw={out.raw_results} dupes_merged={out.duplicates_removed} kept={len(out.sources)}")
    print("dates:", [s.published_date for s in out.sources])


@pytest.mark.live
def test_live_full_quick_journey_with_followup_and_pdf():
    with TestClient(create_app(), headers={"X-Client-Id": "live-test-client-00000001"}) as client:
        r = client.post("/api/research", json={"topic": TOPIC, "mode": "quick"})
        assert r.status_code == 202, r.text
        rid = r.json()["research_id"]
        result = _check_report_integrity(client, rid)
        report = result["report"]
        cr = report["citation_report"]
        print(f"\nQUICK: {len(result['status']['sources'])} sources, {len(report['key_findings'])} findings, "
              f"quotes verified {cr['findings_quote_verified']}/{cr['findings_total']}, "
              f"invalid ids removed {cr['invalid_ids_removed']}, inline markers removed {cr['invalid_inline_markers_removed']}, "
              f"conflicts {len(report['conflicts'])}, insufficient={report['insufficient_evidence']}")

        # follow-up grounded in the stored evidence
        fu = client.post(f"/api/research/{rid}/follow-up", json={"question": "Which companies are mentioned as leading this effort?"})
        assert fu.status_code == 200, fu.text
        ans = fu.json()
        assert ans["answer_type"] in {"evidence_based", "partially_supported", "not_in_research", "unsupported"}
        valid = {s["id"] for s in result["status"]["sources"]}
        assert set(ans["source_ids"]) <= valid
        print("FOLLOW-UP:", ans["answer_type"], ans["source_ids"], ans["answer"][:200].replace("\n", " "))

        # off-topic question must not be answered from the model's own knowledge
        off = client.post(f"/api/research/{rid}/follow-up", json={"question": "What is the capital city of Australia?"}).json()
        print("OFF-TOPIC:", off["answer_type"], off["answer"][:120])
        assert off["answer_type"] in {"not_in_research", "unsupported", "partially_supported"} or off["source_ids"]

        pdf = client.get(f"/api/research/{rid}/pdf")
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF") and len(pdf.content) > 5000
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "live_last_run.pdf").write_bytes(pdf.content)
        (OUT_DIR / "live_last_run.json").write_text(json.dumps({**result, "followups": [ans, off]}, indent=2, default=str), encoding="utf-8")


@pytest.mark.live_deep
def test_live_deep_mode_behaves_differently_from_quick():
    with TestClient(create_app(), headers={"X-Client-Id": "live-test-client-00000001"}) as client:
        rid = client.post("/api/research", json={"topic": TOPIC, "mode": "deep"}).json()["research_id"]
        result = _check_report_integrity(client, rid)
        st = result["status"]
        assert len(st["queries"]) == MODES["deep"].num_queries
        assert len(st["queries"]) > MODES["quick"].num_queries
        assert len(st["sources"]) > MODES["quick"].max_sources or len(st["sources"]) >= 6
        print(f"\nDEEP: {len(st['queries'])} queries, {len(st['sources'])} sources, "
              f"{len(result['report']['key_findings'])} findings, {len(result['report']['detailed_analysis'])} sections")
        (OUT_DIR / "live_last_run_deep.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
