from app.schemas.research import Source
from app.utils.text import strip_markdown


def test_headings_emphasis_links_and_lists_become_plain_prose():
    md = "## Toyota solid-state Battery timeline: production plans\n\n**Bold** and *italic* and __also bold__ and _also italic_.\n- item one\n- item two\nSee [the report](https://x.example/a?b=1) and ![chart](https://x.example/c.png) `code`."
    out = strip_markdown(md)
    assert out == "Toyota solid-state Battery timeline: production plans Bold and italic and also bold and also italic. item one item two See the report and `code`.".replace("`", "")
    for token in ("##", "**", "__", "](", "!["):
        assert token not in out


def test_plain_text_and_identifiers_are_left_alone():
    assert strip_markdown("Plain sentence, 5 * 3 = 15 and snake_case_name stays.") == "Plain sentence, 5 * 3 = 15 and snake_case_name stays."
    assert strip_markdown("") == "" and strip_markdown(None) == ""


def test_tables_and_rules_do_not_leave_noise():
    out = strip_markdown("| a | b |\n|---|---|\n| 1 | 2 |\n\n---\nend")
    assert out == "a b 1 2 end"


def test_source_model_cleans_snippet_on_creation_and_on_load():
    s = Source(id="S1", title="t", url="https://a.example/x", domain="a.example", snippet="## Heading\n**bold** text")
    assert s.snippet == "Heading bold text"
    reloaded = Source(**{**s.model_dump(), "snippet": "### Old stored\n*markdown* text"})
    assert reloaded.snippet == "Old stored markdown text"
