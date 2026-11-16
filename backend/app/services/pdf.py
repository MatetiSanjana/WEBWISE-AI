"""PDF export with ReportLab. Uses a Unicode TTF font so non-ASCII text renders correctly."""
import io
import logging
import os
import re
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer

from app.schemas.research import Report

log = logging.getLogger(__name__)

_FONT_SETS = [
    # (regular, bold, italic, bold-italic)
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/ariali.ttf", "C:/Windows/Fonts/arialbi.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf", "/Library/Fonts/Arial Italic.ttf", "/Library/Fonts/Arial Bold Italic.ttf"),
]
_FAMILY = "DRSans"
_registered = False

_NON_BMP = re.compile(r"[\U00010000-\U0010FFFF]")  # emoji etc. — most TTFs can't render them
_MARKER = re.compile(r"\[(S\d+)\]")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _ensure_font() -> str:
    global _registered
    if _registered:
        return _FAMILY
    chosen = next((fs for fs in _FONT_SETS if all(os.path.exists(p) for p in fs)), None)
    if chosen is None:
        d = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
        chosen = tuple(os.path.join(d, f) for f in ("Vera.ttf", "VeraBd.ttf", "VeraIt.ttf", "VeraBI.ttf"))
        log.warning("No system Unicode font found; falling back to bundled Vera (limited glyph coverage).")
    for suffix, path in zip(("", "-Bold", "-Italic", "-BoldItalic"), chosen):
        pdfmetrics.registerFont(TTFont(_FAMILY + suffix, path))
    pdfmetrics.registerFontFamily(
        _FAMILY, normal=_FAMILY, bold=_FAMILY + "-Bold", italic=_FAMILY + "-Italic", boldItalic=_FAMILY + "-BoldItalic"
    )
    _registered = True
    return _FAMILY


def _t(text: str) -> str:
    """Escape for ReportLab mini-markup and colour inline [S#] citation markers."""
    text = _NON_BMP.sub("", _CTRL.sub("", text or ""))
    text = escape(text)
    return _MARKER.sub(r'<font color="#8A5A0B">[\1]</font>', text)


def _styles(font: str) -> dict[str, ParagraphStyle]:
    base = dict(fontName=font, fontSize=10, leading=14.5, textColor=colors.HexColor("#1F2937"), alignment=TA_LEFT)
    return {
        "title": ParagraphStyle("t", **{**base, "fontName": font + "-Bold", "fontSize": 20, "leading": 25, "spaceAfter": 4}),
        "meta": ParagraphStyle("m", **{**base, "fontSize": 8.5, "leading": 12, "textColor": colors.HexColor("#6B7280")}),
        "h1": ParagraphStyle("h1", **{**base, "fontName": font + "-Bold", "fontSize": 13, "leading": 17, "spaceBefore": 14, "spaceAfter": 5, "textColor": colors.HexColor("#111827")}),
        "h2": ParagraphStyle("h2", **{**base, "fontName": font + "-Bold", "fontSize": 10.5, "spaceBefore": 8, "spaceAfter": 2}),
        "body": ParagraphStyle("b", **{**base, "spaceAfter": 5}),
        "bullet": ParagraphStyle("bl", **{**base, "leftIndent": 12, "bulletIndent": 2, "spaceAfter": 4}),
        "quote": ParagraphStyle("q", **{**base, "fontName": font + "-Italic", "fontSize": 9, "leading": 12.5, "leftIndent": 18, "textColor": colors.HexColor("#4B5563"), "spaceAfter": 5}),
        "ref": ParagraphStyle("r", **{**base, "fontSize": 9, "leading": 12.5, "leftIndent": 22, "firstLineIndent": -22, "spaceAfter": 4}),
        "warn": ParagraphStyle("w", **{**base, "fontSize": 8.5, "leading": 12, "textColor": colors.HexColor("#92400E")}),
    }


_TYPE_LABEL = {"fact": "Fact", "opinion": "Opinion", "prediction": "Prediction"}
_SUPPORT_LABEL = {
    "multi_source": "cited by multiple independent domains",
    "single_source": "single source domain",
    "quote_unverified": "quoted evidence not found in source text",
}


def build_pdf(report: Report, topic: str) -> bytes:
    font = _ensure_font()
    st = _styles(font)
    story: list = []

    def h(text: str) -> None:
        story.append(Paragraph(_t(text), st["h1"]))
        story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#E5E7EB"), spaceAfter=4))

    story.append(Paragraph(_t(report.title), st["title"]))
    story.append(Paragraph(
        _t(f"Topic: {topic}  ·  Mode: {report.mode.title()}  ·  Model: {report.model}  ·  "
           f"Generated {report.generated_at:%Y-%m-%d %H:%M} UTC"), st["meta"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(_t(report.disclaimer), st["warn"]))

    if report.insufficient_evidence:
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Insufficient evidence found.</b> Treat this report as incomplete.", st["warn"]))

    h("Executive Summary")
    story.append(Paragraph(_t(report.executive_summary), st["body"]))

    h("Research Objective")
    story.append(Paragraph(_t(report.objective), st["body"]))

    h("Key Findings")
    if report.key_findings:
        for i, f in enumerate(report.key_findings, 1):
            tag = f"{_TYPE_LABEL.get(f.claim_type, f.claim_type)} · {_SUPPORT_LABEL.get(f.support_level, '')}"
            block = [Paragraph(f"{i}. {_t(f.statement)}", st["bullet"])]
            meta = f"<i>{escape(tag)}</i>"
            block.append(Paragraph(meta, st["meta"]))
            if f.quote_verified and f.supporting_quote:
                block.append(Paragraph(f"“{_t(f.supporting_quote)}”", st["quote"]))
            story.append(KeepTogether(block))
    else:
        story.append(Paragraph("Insufficient evidence found.", st["body"]))

    h("Detailed Analysis")
    for s in report.detailed_analysis or []:
        story.append(Paragraph(_t(s.heading), st["h2"]))
        story.append(Paragraph(_t(s.body) + (" <i>(uncited)</i>" if s.uncited else ""), st["body"]))
    if not report.detailed_analysis:
        story.append(Paragraph("Insufficient evidence found.", st["body"]))

    h("Comparison of Findings")
    for c in report.comparison or []:
        story.append(Paragraph(f"<b>{_t(c.topic)}</b>", st["body"]))
        story.append(Paragraph(_t(c.summary) + (" <i>(uncited)</i>" if c.uncited else ""), st["body"]))
    if not report.comparison:
        story.append(Paragraph("No cross-source comparison could be supported by the retrieved evidence.", st["body"]))

    h("Conflicting Information")
    if report.conflicts:
        for c in report.conflicts:
            story.append(Paragraph(f"<b>{_t(c.topic)}</b>", st["body"]))
            for p in c.positions:
                story.append(Paragraph("• " + _t(p.summary), st["bullet"]))
            if c.assessment:
                story.append(Paragraph(_t(c.assessment), st["quote"]))
    else:
        story.append(Paragraph("No conflicting information was identified between the retrieved sources.", st["body"]))
    for o in report.outdated_info:
        story.append(Paragraph(f"<b>Possibly outdated:</b> {_t(o.statement)} — {_t(o.reason)}", st["body"]))

    h("Limitations and Evidence Gaps")
    for item in report.limitations or ["None identified by the analysis; this does not mean none exist."]:
        story.append(Paragraph("• " + _t(item), st["bullet"]))
    if report.unsupported_claims:
        story.append(Paragraph(
            f"{len(report.unsupported_claims)} model-generated claim(s) were excluded because they had no valid citation.", st["meta"]))

    h("Conclusion")
    story.append(Paragraph(_t(report.conclusion), st["body"]))

    h("References")
    for r in report.references:
        date = r.published_date
        link = escape(r.url, {'"': "&quot;"})
        line = (f'<font color="#8A5A0B">[{r.id}]</font> {_t(r.title)} — '
                f'<a href="{link}" color="#8A5A0B">{escape(r.url)}</a> — {escape(date)}'
                + ("" if r.cited else " — <i>retrieved, not cited</i>"))
        story.append(Paragraph(line, st["ref"]))

    cr = report.citation_report
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        _t(f"Citation check: {cr.findings_quote_verified}/{cr.findings_total} key findings have supporting quotes "
           f"located in the cited source text; {cr.invalid_ids_removed + cr.invalid_inline_markers_removed} invalid citation(s) removed."),
        st["meta"]))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.HexColor("#9CA3AF"))
        canvas.drawString(18 * mm, 10 * mm, "Webwise AI — AI-generated; verify against the cited sources")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
        title=report.title[:120], author="Webwise AI",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
