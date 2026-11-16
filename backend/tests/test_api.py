"""API tests. External services (Tavily/Gemini) are replaced with in-test fakes ONLY here, to test our own
orchestration, validation and error handling. Real-API behaviour is covered by tests/test_live.py."""
import pytest
from fastapi.testclient import TestClient

from app.errors import ResearchError
from app.main import create_app
from app.models import db
from app.schemas.llm import LLMFinding, LLMFollowUp
from app.services import analyzer, llm, planner, search
from app.services.report import build_report
from app.services.search import SearchOutcome

from .helpers import QUICK, make_analysis, make_plan, make_source


CID = "test-client-0000000001"
OTHER_CID = "other-client-000000002"


@pytest.fixture
def client():
    with TestClient(create_app(), headers={"X-Client-Id": CID}) as c:
        yield c


def seed_completed(client_id: str = CID) -> str:
    srcs = [make_source(1), make_source(2), make_source(3)]
    rep = build_report("solar", make_plan(), make_analysis(), srcs, QUICK)
    rid = db.create_research("solar efficiency trends", "quick", client_id)
    db.save_sources(rid, [s.model_dump() for s in srcs], [])
    db.complete(rid, rep.model_dump(mode="json"), [])
    return rid


def fake_pipeline(monkeypatch, analysis=None, search_error: ResearchError | None = None, analyzer_error=None):
    srcs = [make_source(1), make_source(2), make_source(3)]

    async def fake_plan(topic, cfg):
        return make_plan()

    async def fake_search(queries, cfg):
        if search_error:
            raise search_error
        return SearchOutcome(sources=srcs, warnings=["w"])

    async def fake_analyze(topic, plan, sources, cfg, on_stage=None):
        if analyzer_error:
            raise analyzer_error
        return analysis or make_analysis()

    monkeypatch.setattr(planner, "plan_research", fake_plan)
    monkeypatch.setattr(search, "search_web", fake_search)
    monkeypatch.setattr(analyzer, "analyze", fake_analyze)


# ----------------------------------------------------------------- validation / basics


def test_health_never_exposes_keys(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["tavily_configured"] and body["gemini_configured"]
    assert "tvly" not in r.text and "fake-gemini" not in r.text


@pytest.mark.parametrize("payload", [{"topic": "hi"}, {"topic": "x" * 501}, {"topic": "valid topic here", "mode": "turbo"}, {}])
def test_invalid_input_rejected_with_useful_error(client, payload):
    r = client.post("/api/research", json=payload)
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "INVALID_INPUT" and err["message"]


def test_missing_api_keys_give_clear_503(client, monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    from app.config import get_settings
    get_settings.cache_clear()
    r = client.post("/api/research", json={"topic": "valid topic here"})
    assert r.status_code == 503
    assert "TAVILY_API_KEY" in r.json()["error"]["message"]


def test_unknown_research_404_and_report_not_ready_409(client):
    assert client.get("/api/research/nope").status_code == 404
    assert client.get("/api/research/nope/pdf").status_code == 404
    rid = db.create_research("valid topic here", "quick")
    r = client.get(f"/api/research/{rid}/report")
    assert r.status_code == 409 and r.json()["error"]["code"] == "NOT_READY"
    assert client.get(f"/api/research/{rid}/pdf").status_code == 409


def test_rate_limit(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    fake_pipeline(monkeypatch)
    codes = [client.post("/api/research", json={"topic": "valid topic here"}).status_code for _ in range(3)]
    assert codes == [202, 202, 429]


# ----------------------------------------------------------------- pipeline via API (fake externals)


def test_full_flow_with_fabricated_citations_is_cleaned(client, monkeypatch):
    analysis = make_analysis(
        executive_summary="Fine [S1] but fake [S42].",
        key_findings=[
            LLMFinding(statement="Good [S1].", source_ids=["S1"], claim_type="fact",
                       supporting_quote="Solar panel efficiency reached 21 percent in laboratory"),
            LLMFinding(statement="Invented [S77].", source_ids=["S77"], claim_type="fact", supporting_quote="nope nope nope nope"),
        ],
    )
    fake_pipeline(monkeypatch, analysis=analysis)
    r = client.post("/api/research", json={"topic": "solar efficiency trends", "mode": "quick"})
    assert r.status_code == 202
    rid = r.json()["research_id"]

    st = client.get(f"/api/research/{rid}").json()
    assert st["status"] == "completed" and st["progress"] == 100 and st["error"] is None
    assert [s["id"] for s in st["sources"]] == ["S1", "S2", "S3"]
    assert "evidence_text" not in st["sources"][0]  # internal text never leaves the server
    rep = client.get(f"/api/research/{rid}/report").json()
    assert "S42" not in rep["executive_summary"]
    assert len(rep["key_findings"]) == 1 and len(rep["unsupported_claims"]) == 1
    valid = {s["id"] for s in st["sources"]}
    for f in rep["key_findings"]:
        assert set(f["source_ids"]) <= valid
    assert {ref["url"] for ref in rep["references"]} == {s["url"] for s in st["sources"]}


def test_tavily_failure_gives_clear_error_and_no_report(client, monkeypatch):
    fake_pipeline(monkeypatch, search_error=ResearchError("TAVILY_AUTH", "Tavily rejected the API key. Check TAVILY_API_KEY."))
    rid = client.post("/api/research", json={"topic": "valid topic here"}).json()["research_id"]
    st = client.get(f"/api/research/{rid}").json()
    assert st["status"] == "failed" and st["report"] is None
    assert st["error"]["code"] == "TAVILY_AUTH" and "Tavily" in st["error"]["message"]
    assert client.get(f"/api/research/{rid}/report").status_code == 409


def test_gemini_failure_then_retry_succeeds(client, monkeypatch):
    fake_pipeline(monkeypatch, analyzer_error=ResearchError("GEMINI_UNAVAILABLE", "Gemini is temporarily unavailable.", retryable=True))
    rid = client.post("/api/research", json={"topic": "valid topic here"}).json()["research_id"]
    st = client.get(f"/api/research/{rid}").json()
    assert st["status"] == "failed" and st["error"]["retryable"] is True and st["report"] is None

    fake_pipeline(monkeypatch)  # Gemini recovers
    assert client.post(f"/api/research/{rid}/retry").status_code == 202
    assert client.get(f"/api/research/{rid}").json()["status"] == "completed"


def test_unexpected_exception_never_leaves_job_hanging(client, monkeypatch):
    fake_pipeline(monkeypatch, analyzer_error=RuntimeError("kaboom with secret"))
    rid = client.post("/api/research", json={"topic": "valid topic here"}).json()["research_id"]
    st = client.get(f"/api/research/{rid}").json()
    assert st["status"] == "failed" and st["error"]["code"] == "INTERNAL_ERROR"
    assert "secret" not in st["error"]["message"]


def test_mode_is_passed_through_to_pipeline(client, monkeypatch):
    seen = {}
    fake_pipeline(monkeypatch)

    async def spy_plan(topic, cfg):
        seen["mode"], seen["n"] = cfg.name, cfg.num_queries
        return make_plan()

    monkeypatch.setattr(planner, "plan_research", spy_plan)
    client.post("/api/research", json={"topic": "valid topic here", "mode": "deep"})
    assert seen == {"mode": "deep", "n": 7}


# ----------------------------------------------------------------- pdf / history / saved / follow-up


def test_pdf_download(client):
    rid = seed_completed()
    r = client.get(f"/api/research/{rid}/pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and "attachment" in r.headers["content-disposition"]


def test_history_is_private_per_browser(client):
    """QA finding S2: any visitor used to be able to list everyone's research topics."""
    mine = seed_completed(CID)
    theirs = seed_completed(OTHER_CID)
    assert [h["id"] for h in client.get("/api/history").json()] == [mine]
    other = client.get("/api/history", headers={"X-Client-Id": OTHER_CID}).json()
    assert [h["id"] for h in other] == [theirs]
    # a stranger with no / malformed identity sees nothing
    assert client.get("/api/history", headers={"X-Client-Id": ""}).json() == []
    assert client.get("/api/history", headers={"X-Client-Id": "short"}).json() == []
    assert client.get("/api/history?saved=true", headers={"X-Client-Id": "x" * 100}).json() == []
    # legacy rows with no owner are never listed
    legacy = db.create_research("legacy topic here", "quick", None)
    assert legacy not in {h["id"] for h in client.get("/api/history").json()}


def test_start_requires_client_id(client):
    for hdr in ({"X-Client-Id": ""}, {"X-Client-Id": "short"}, {"X-Client-Id": "bad chars here!!!!!!!!"}):
        r = client.post("/api/research", json={"topic": "valid topic here"}, headers=hdr)
        assert r.status_code == 400 and r.json()["error"]["code"] == "CLIENT_ID_REQUIRED"


def test_shared_link_still_works_for_other_browser(client):
    """History is scoped, but an unguessable report link can still be opened by someone else (sharing)."""
    rid = seed_completed(OTHER_CID)
    assert client.get(f"/api/research/{rid}").status_code == 200


def test_security_headers_present(client):
    h = client.get("/api/health").headers
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
    assert h["referrer-policy"] == "no-referrer" and h["cache-control"] == "no-store"


def test_docs_can_be_disabled(monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("ENABLE_DOCS", "false")
    get_settings.cache_clear()
    with TestClient(create_app()) as c:
        assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404


def test_history_saved_delete(client):
    rid = seed_completed()
    h = client.get("/api/history").json()
    assert h[0]["id"] == rid and h[0]["title"] == "Test report" and h[0]["sources_count"] == 3
    assert client.get("/api/history?saved=true").json() == []
    assert client.patch(f"/api/research/{rid}/saved", json={"saved": True}).json()["saved"] is True
    assert len(client.get("/api/history?saved=true").json()) == 1
    assert client.delete(f"/api/research/{rid}").status_code == 204
    assert client.get(f"/api/research/{rid}").status_code == 404


def _patch_followup(monkeypatch, out: LLMFollowUp):
    seen = {}

    async def fake(**kw):
        seen["prompt"] = kw["prompt"]
        return out

    monkeypatch.setattr(llm, "generate_json", fake)
    return seen


def test_followup_uses_stored_evidence_as_context(client, monkeypatch):
    rid = seed_completed()
    seen = _patch_followup(monkeypatch, LLMFollowUp(
        answer="Efficiency hit 21 percent [S1].", answer_type="evidence_based", source_ids=["S1"],
        supporting_quote="Solar panel efficiency reached 21 percent in laboratory tests"))
    r = client.post(f"/api/research/{rid}/follow-up", json={"question": "What efficiency was reached?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer_type"] == "evidence_based" and body["quote_verified"] and body["source_ids"] == ["S1"]
    # the prompt contained this research's report + source text
    assert "Test report" in seen["prompt"] and "=== SOURCE S1 ===" in seen["prompt"] and "What efficiency" in seen["prompt"]
    assert len(client.get(f"/api/research/{rid}").json()["follow_ups"]) == 1


def test_followup_with_fake_citation_is_downgraded(client, monkeypatch):
    rid = seed_completed()
    _patch_followup(monkeypatch, LLMFollowUp(answer="Totally sure [S99].", answer_type="evidence_based", source_ids=["S99"], supporting_quote=""))
    body = client.post(f"/api/research/{rid}/follow-up", json={"question": "Anything else?"}).json()
    assert body["answer_type"] == "unsupported" and body["source_ids"] == [] and body["note"]


def test_followup_not_in_research(client, monkeypatch):
    rid = seed_completed()
    _patch_followup(monkeypatch, LLMFollowUp(answer="", answer_type="not_in_research", source_ids=[], supporting_quote=""))
    body = client.post(f"/api/research/{rid}/follow-up", json={"question": "Who won the 1990 World Cup?"}).json()
    assert body["answer_type"] == "not_in_research" and "did not find" in body["answer"]


def test_followup_requires_completed_research_and_valid_question(client):
    rid = db.create_research("valid topic here", "quick")
    assert client.post(f"/api/research/{rid}/follow-up", json={"question": "hello there"}).status_code == 409
    done = seed_completed()
    assert client.post(f"/api/research/{done}/follow-up", json={"question": "x"}).status_code == 422
