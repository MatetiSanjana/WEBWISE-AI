from app.schemas.llm import LLMConflict, LLMFinding, LLMOutdated, LLMPosition
from app.services.citations import clean_markers, normalize_id, quote_in_sources, validate_analysis, _Tally

from .helpers import make_analysis, make_source


def sources(n=3):
    return [make_source(i) for i in range(1, n + 1)]


def test_normalize_id_variants():
    assert normalize_id("S1") == "S1"
    assert normalize_id("s03") == "S3"
    assert normalize_id("[S12]") == "S12"
    assert normalize_id("source 1") is None
    assert normalize_id("S1; DROP") is None


def test_clean_markers_drops_invalid_and_canonicalises():
    t = _Tally()
    out, found = clean_markers("A [S1, S9] B [S2][S7] C [S9]", {"S1", "S2"}, t)
    assert out == "A [S1] B [S2] C"
    assert found == ["S1", "S2"]
    assert t.invalid_markers == 3


def test_fabricated_source_ids_are_removed_from_findings():
    a = make_analysis(key_findings=[
        LLMFinding(statement="Real claim [S1] and fake [S99].", source_ids=["S1", "S99", "S404"], claim_type="fact",
                   supporting_quote="Solar panel efficiency reached 21 percent")
    ])
    v = validate_analysis(a, sources())
    f = v.key_findings[0]
    assert f.source_ids == ["S1"]
    assert "S99" not in f.statement
    assert v.report.invalid_ids_removed == 2
    assert v.report.invalid_inline_markers_removed == 1


def test_finding_with_only_fake_citations_is_not_a_key_finding():
    a = make_analysis(key_findings=[
        LLMFinding(statement="Invented claim [S50].", source_ids=["S50"], claim_type="fact", supporting_quote="whatever text here")
    ])
    v = validate_analysis(a, sources())
    assert v.key_findings == []
    assert len(v.unsupported_claims) == 1
    assert v.report.findings_dropped_unsupported == 1


def test_finding_with_no_citation_at_all_is_unsupported():
    a = make_analysis(key_findings=[
        LLMFinding(statement="Uncited assertion.", source_ids=[], claim_type="fact", supporting_quote="")
    ])
    v = validate_analysis(a, sources())
    assert v.key_findings == [] and len(v.unsupported_claims) == 1


def test_quote_verification_true_and_false():
    srcs = sources()
    by_id = {s.id: s for s in srcs}
    assert quote_in_sources("Solar panel efficiency reached 21 percent in laboratory", ["S1"], by_id)
    # case / whitespace / curly punctuation tolerant
    assert quote_in_sources("SOLAR   panel\nefficiency reached 21 percent", ["S1"], by_id)
    # quote that exists only in a source that is NOT cited must fail
    assert not quote_in_sources("Solar panel efficiency reached 22 percent", ["S1"], by_id)
    assert quote_in_sources("Solar panel efficiency reached 22 percent", ["S2"], by_id)
    # fabricated quote
    assert not quote_in_sources("Solar panels now convert 99 percent of sunlight", ["S1", "S2", "S3"], by_id)
    # too short / empty
    assert not quote_in_sources("", ["S1"], by_id)
    assert not quote_in_sources("solar", ["S1"], by_id)


def test_quote_with_ellipsis_requires_all_segments():
    by_id = {s.id: s for s in sources()}
    assert quote_in_sources("Solar panel efficiency reached ... in laboratory tests during 2024", ["S1"], by_id)
    assert not quote_in_sources("Solar panel efficiency reached ... on the moon base landing", ["S1"], by_id)


def test_fabricated_quote_marks_finding_unverified_and_hides_quote():
    a = make_analysis(key_findings=[
        LLMFinding(statement="Claim [S1].", source_ids=["S1"], claim_type="fact", supporting_quote="This sentence never appears anywhere.")
    ])
    v = validate_analysis(a, sources())
    f = v.key_findings[0]
    assert not f.quote_verified and f.support_level == "quote_unverified" and f.supporting_quote == ""
    assert v.report.findings_quote_verified == 0


def test_support_level_single_vs_multi_domain():
    same = [make_source(1, "a.com"), make_source(2, "a.com")]
    diff = [make_source(1, "a.com"), make_source(2, "b.com")]
    mk = lambda: make_analysis(key_findings=[LLMFinding(
        statement="X.", source_ids=["S1", "S2"], claim_type="fact",
        supporting_quote="Solar panel efficiency reached 21 percent")])
    assert validate_analysis(mk(), same).key_findings[0].support_level == "single_source"
    assert validate_analysis(mk(), diff).key_findings[0].support_level == "multi_source"


def test_conflict_needs_two_cited_positions():
    good = LLMConflict(topic="Cost", positions=[
        LLMPosition(summary="Cheap [S1].", source_ids=["S1"]), LLMPosition(summary="Dear [S2].", source_ids=["S2"])],
        assessment="Different years.")
    bad = LLMConflict(topic="Speed", positions=[
        LLMPosition(summary="Fast [S1].", source_ids=["S1"]), LLMPosition(summary="Slow.", source_ids=["S77"])],
        assessment="?")
    v = validate_analysis(make_analysis(conflicts=[good, bad]), sources())
    assert [c.topic for c in v.conflicts] == ["Cost"]
    assert any("Speed" in n for n in v.report.notes)


def test_outdated_needs_valid_ids():
    ok = LLMOutdated(statement="Old figure [S1].", reason="S2 reports a newer figure [S2].", source_ids=["S1"])
    bad = LLMOutdated(statement="Old.", reason="Because.", source_ids=["S9"])
    v = validate_analysis(make_analysis(outdated_info=[ok, bad]), sources())
    assert len(v.outdated_info) == 1


def test_uncited_sections_are_flagged_not_hidden():
    from app.schemas.llm import LLMSection
    a = make_analysis(detailed_analysis=[LLMSection(heading="H", body="No citation here.", source_ids=[])])
    v = validate_analysis(a, sources())
    assert v.detailed_analysis[0].uncited is True


def test_cited_ids_tracked_for_references():
    v = validate_analysis(make_analysis(), sources(4))
    assert {"S1", "S2"} <= v.cited_ids and "S4" not in v.cited_ids
