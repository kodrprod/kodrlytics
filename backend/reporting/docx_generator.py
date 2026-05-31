"""DOCX report generator for the rooms pipeline output."""
from __future__ import annotations
import logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

_ROOM_ORDER = ["CEO", "Intake", "Extraction", "Analysis", "Benchmarking", "Strategy", "Reporting"]
_ROOM_DISPLAY = {
    "CEO":          "Executive Summary",
    "Intake":       "I. Document Intelligence & Intake",
    "Extraction":   "II. Data Extraction & Validation",
    "Analysis":     "III. Financial Analysis",
    "Benchmarking": "IV. Industry Benchmarking",
    "Strategy":     "V. Strategic Assessment",
    "Reporting":    "VI. Reporting & Recommendations",
}


def _add_room_report(doc, text: str) -> None:
    """Add room report text to document with heading detection."""
    if not text or text.startswith("["):
        doc.add_paragraph(text or "(No report generated for this room.)")
        return

    buf: list[str] = []

    def _flush() -> None:
        block = "\n".join(buf).strip()
        if block:
            doc.add_paragraph(block)
        buf.clear()

    for line in text.split("\n"):
        stripped = line.strip()
        if (stripped.startswith("**") and stripped.endswith("**")
                and 4 < len(stripped) < 80 and stripped.count("**") == 2):
            _flush()
            heading = stripped.strip("*").strip()
            doc.add_heading(heading, level=2)
        else:
            buf.append(line)

    _flush()


def generate_rooms_docx(
    room_reports: dict[str, str],
    company_name: str,
    source_file: str,
    run_id: str,
) -> Path:
    """Generate a professional DOCX report from room pipeline output."""
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    generated_at = datetime.now().strftime("%d %B %Y, %H:%M UTC")
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.25)

    # ── Cover page ─────────────────────────────────────────────────────────────
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title_para.add_run("KODRLYTICS")
    run.bold = True
    run.font.size = Pt(36)
    run.font.color.rgb = RGBColor(20, 40, 70)

    sub_para = doc.add_paragraph()
    sub_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub_para.add_run("Financial Intelligence System")
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(80, 100, 130)

    doc.add_paragraph()

    company_para = doc.add_paragraph()
    company_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = company_para.add_run(company_name)
    run.bold = True
    run.font.size = Pt(22)
    run.font.color.rgb = RGBColor(20, 40, 70)

    report_type_para = doc.add_paragraph()
    report_type_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = report_type_para.add_run("Financial Intelligence Report")
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(100, 120, 150)

    doc.add_paragraph()

    meta_para = doc.add_paragraph()
    meta_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = meta_para.add_run(f"Generated: {generated_at}\nSource: {source_file}")
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(100, 100, 100)

    doc.add_paragraph()

    disc_para = doc.add_paragraph()
    disc_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = disc_para.add_run(
        "CONFIDENTIAL -- For internal use only. All projections are illustrative "
        "and do not constitute financial advice."
    )
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(160, 160, 160)

    doc.add_page_break()

    # ── Analysis chapters ──────────────────────────────────────────────────────
    for room_key in _ROOM_ORDER:
        if room_key not in room_reports:
            continue
        display = _ROOM_DISPLAY.get(room_key, room_key)
        doc.add_heading(display, level=1)
        _add_room_report(doc, room_reports[room_key])
        doc.add_page_break()

    # ── Appendix A: Methodology ────────────────────────────────────────────────
    doc.add_heading("Appendix A -- Methodology", level=1)
    doc.add_paragraph(
        "This report was produced by the Kodrlytics multi-agent financial intelligence system. "
        "The pipeline consists of six specialised analysis rooms, each staffed by 20 virtual "
        "senior analysts (language model workers) and one room manager who synthesises their findings.\n\n"
        "Each worker conducts four analytical rounds: Structured Scan, Deep Numerical Analysis, "
        "Critical Challenge, and Final Synthesis. Workers supplement financial data with real-time "
        "DuckDuckGo search results to provide market context and industry benchmarks.\n\n"
        "All narrative generation uses language models via OpenRouter. For production use with "
        "sensitive data, configure DATA_MODE=real with a no-logging paid model."
    )

    # ── Appendix B: Disclaimer ─────────────────────────────────────────────────
    doc.add_heading("Appendix B -- Disclaimer", level=1)
    doc.add_paragraph(
        "This report is generated by an AI-powered financial analysis system and is intended "
        "for informational and internal decision-support purposes only. It does not constitute "
        "financial advice, investment advice, or any form of regulated professional advisory service.\n\n"
        "AI-generated narratives, findings, and recommendations should be verified against "
        "original source documents before being acted upon. All projections are illustrative "
        "scenarios, not predictions of future performance.\n\n"
        "Kodrlytics and its operators accept no liability for decisions made on the basis "
        "of this report."
    )

    out_path = REPORTS_DIR / f"{run_id}.docx"
    doc.save(str(out_path))
    log.info("Rooms DOCX saved: %s (%.1f KB)", out_path, out_path.stat().st_size / 1024)
    return out_path
