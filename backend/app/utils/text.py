import re
import unicodedata

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACES = re.compile(r"[ \t ]+")
_NEWLINES = re.compile(r"\n{3,}")


def clean_text(text: str | None) -> str:
    """Strip control characters and collapse whitespace, preserving paragraph breaks."""
    if not text:
        return ""
    text = _CTRL.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    text = _SPACES.sub(" ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return _NEWLINES.sub("\n\n", text).strip()


def clip(text: str, limit: int) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # prefer cutting at a sentence/word boundary
    for sep in (". ", "\n", " "):
        idx = cut.rfind(sep)
        if idx > limit * 0.6:
            return cut[: idx + 1].rstrip() + " …"
    return cut.rstrip() + " …"


_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def normalize_for_match(text: str) -> str:
    """Aggressive normalisation used to check that a quote really appears in a source."""
    text = unicodedata.normalize("NFKC", text or "").translate(_QUOTES).lower()
    text = re.sub(r"[\*_`#>]+", "", text)  # markdown noise
    return re.sub(r"\s+", " ", text).strip()


_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_MD_HEADING = re.compile(r"(?m)^\s{0,3}#{1,6}\s*")
_MD_BULLET = re.compile(r"(?m)^\s*(?:[-*+]|\d+\.)\s+")
_MD_RULE = re.compile(r"(?m)^\s*(?:[-*_]\s*){3,}$")
_MD_TABLE_SEP = re.compile(r"(?m)^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?\s*$")
_MD_BOLD = re.compile(r"(\*\*|__)(.+?)\1")
_MD_ITALIC_STAR = re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")
_MD_ITALIC_UNDER = re.compile(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])")


def strip_markdown(text: str | None) -> str:
    """Turn the markdown that web-extraction tools return into plain prose for display (snippets, cards).

    Only used for DISPLAY text. Evidence text sent to the LLM and used for quote checks is left untouched.
    """
    if not text:
        return ""
    t = _MD_IMAGE.sub("", text)
    t = _MD_LINK.sub(r"\1", t)
    t = _MD_HEADING.sub("", t)
    t = _MD_TABLE_SEP.sub("", t)
    t = _MD_RULE.sub("", t)
    t = _MD_BULLET.sub("", t)
    t = _MD_BOLD.sub(r"\2", t)
    t = _MD_ITALIC_STAR.sub(r"\1", t)
    t = _MD_ITALIC_UNDER.sub(r"\1", t)
    t = t.replace("`", "").replace("|", " ")
    t = re.sub(r"\s*\n\s*", " ", t)  # snippets are single-paragraph previews
    return re.sub(r"\s{2,}", " ", t).strip()
