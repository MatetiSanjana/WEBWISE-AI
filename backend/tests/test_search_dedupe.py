from app.services.search import dedupe_and_select
from app.utils.urls import normalize_url

from .helpers import DEEP, QUICK, raw_result


def test_normalize_url_equivalents():
    variants = [
        "https://www.Example.com/a/b/",
        "http://example.com/a/b",
        "https://example.com/a/b?utm_source=x&fbclid=1",
        "https://example.com//a//b#section",
    ]
    assert len({normalize_url(v) for v in variants}) == 1


def test_normalize_url_rejects_bad():
    assert normalize_url("") is None
    assert normalize_url("javascript:alert(1)") is None
    assert normalize_url("ftp://example.com/x") is None
    assert normalize_url(None) is None


def test_normalize_keeps_meaningful_query_params():
    assert normalize_url("https://example.com/p?id=1") != normalize_url("https://example.com/p?id=2")


def test_duplicates_removed_and_queries_merged():
    raw = [
        raw_result("https://www.example.com/a/", query="q1", score=0.4),
        raw_result("http://example.com/a?utm_campaign=z", query="q2", score=0.9),
        raw_result("https://other.org/b", query="q1", score=0.3),
    ]
    sources, dupes = dedupe_and_select(raw, QUICK)
    assert dupes == 1
    assert len(sources) == 2
    top = sources[0]
    assert top.id == "S1" and top.domain == "example.com"
    assert set(top.found_by_queries) == {"q1", "q2"}
    assert top.relevance_score == 0.9


def test_ids_are_sequential_and_stable_order():
    raw = [raw_result(f"https://d{i}.com/x", score=1 - i / 100) for i in range(5)]
    sources, _ = dedupe_and_select(raw, QUICK)
    assert [s.id for s in sources] == ["S1", "S2", "S3", "S4", "S5"]
    assert [s.domain for s in sources] == [f"d{i}.com" for i in range(5)]


def test_unusable_results_skipped():
    raw = [
        raw_result("", content="x" * 100),
        raw_result("https://a.com/1", content=""),
        raw_result("https://a.com/2", content="tiny"),
        raw_result("ftp://a.com/3"),
        raw_result("https://ok.com/4"),
    ]
    sources, _ = dedupe_and_select(raw, QUICK)
    assert [s.url for s in sources] == ["https://ok.com/4"]


def test_missing_date_is_marked_not_invented():
    raw = [raw_result("https://a.com/1"), raw_result("https://b.com/2", published_date="2024-03-01")]
    by_domain = {s.domain: s for s in dedupe_and_select(raw, QUICK)[0]}
    assert by_domain["a.com"].published_date == "Date unavailable"
    assert by_domain["b.com"].published_date == "2024-03-01"


def test_per_domain_and_total_caps_differ_between_modes():
    raw = [raw_result(f"https://same.com/{i}", score=0.9) for i in range(10)]
    raw += [raw_result(f"https://d{i}.com/x", score=0.5) for i in range(30)]
    quick, _ = dedupe_and_select(raw, QUICK)
    deep, _ = dedupe_and_select(raw, DEEP)
    assert len(quick) == QUICK.max_sources == 8
    assert len(deep) == DEEP.max_sources == 18
    assert sum(1 for s in quick if s.domain == "same.com") == QUICK.max_per_domain
    assert sum(1 for s in deep if s.domain == "same.com") == DEEP.max_per_domain


def test_evidence_text_is_size_limited():
    raw = [raw_result("https://a.com/1", content="word " * 5000)]
    (s,), _ = dedupe_and_select(raw, QUICK)
    assert len(s.evidence_text) <= QUICK.chars_per_source + 5
    assert len(s.snippet) <= 410


def test_deep_uses_raw_content_quick_does_not():
    raw = [raw_result("https://a.com/1", content="short snippet about the topic here ok ok ok",
                      raw_content="FULL PAGE TEXT " * 20)]
    (q,), _ = dedupe_and_select(raw, QUICK)
    (d,), _ = dedupe_and_select(raw, DEEP)
    assert "FULL PAGE TEXT" not in q.evidence_text
    assert "FULL PAGE TEXT" in d.evidence_text
