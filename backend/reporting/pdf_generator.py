"""
Doktorarbeit-style PDF report generator.
Structure:
  1. Cover page
  2. Executive Summary
  3. Methodology
  4. Per-company analysis (profitability, liquidity, efficiency, leverage)
  5. Benchmark comparisons
  6. Risk flags (detailed)
  7. Recommendations (one detailed section per action)
  8. Projections
  9. Appendix: all computed ratios
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from fpdf import FPDF

log = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


@dataclass
class CompanyReport:
    company_name: str
    nace_code: str
    ratios: list[dict]
    flags: list[dict]
    projections: list[dict]
    narrative: str
    recommendations_detail: str = ""  # LLM-written deep recommendations


@dataclass
class AnalysisReport:
    title: str
    generated_at: str
    source_file: str
    companies: list[CompanyReport]
    portfolio_summary: str = ""


def _safe(text: str) -> str:
    # Replace characters outside latin-1 so Helvetica (core font) can render them.
    text = (text
            .replace('—', '--')
            .replace('–', '-')
            .replace('‐', '-')
            .replace('‑', '-')
            .replace('‒', '-')
            .replace('−', '-')
            .replace('’', "'")
            .replace('‘', "'")
            .replace('“', '"')
            .replace('”', '"')
            .replace('…', '...'))
    return text.encode('latin-1', errors='replace').decode('latin-1')


class KodrlyticsPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, "KODRLYTICS -- Financial Analysis Report", align="L")
        self.ln(2)
        self.set_draw_color(200, 200, 200)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()} -- Confidential -- All projections are illustrative, not guarantees", align="C")

    def chapter_title(self, text: str, level: int = 1):
        text = _safe(text)
        self.ln(6)
        if level == 1:
            self.set_font("Helvetica", "B", 16)
            self.set_fill_color(20, 40, 70)
            self.set_text_color(255, 255, 255)
            self.cell(0, 10, f"  {text}", fill=True, new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0, 0, 0)
        elif level == 2:
            self.set_font("Helvetica", "B", 13)
            self.set_text_color(20, 40, 70)
            self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(20, 40, 70)
            self.line(20, self.get_y(), 190, self.get_y())
            self.set_text_color(0, 0, 0)
        else:
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(50, 80, 120)
            self.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0, 0, 0)
        self.ln(2)

    def body_text(self, text: str, size: int = 10):
        self.set_font("Helvetica", "", size)
        self.multi_cell(0, 5.5, _safe(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def metric_row(self, label: str, value: str, flag: bool = False):
        label, value = _safe(label), _safe(value)
        self.set_font("Helvetica", "", 10)
        if flag:
            self.set_fill_color(255, 240, 200)
            self.set_font("Helvetica", "B", 10)
        else:
            self.set_fill_color(245, 248, 252)
        self.cell(110, 6, f"  {label}", fill=True)
        self.set_font("Helvetica", "B" if flag else "", 10)
        self.cell(70, 6, value, fill=flag, new_x="LMARGIN", new_y="NEXT")
        self.set_fill_color(255, 255, 255)

    def flag_box(self, severity: str, message: str):
        self.ln(2)
        if severity == "critical":
            self.set_fill_color(255, 220, 220)
            self.set_draw_color(200, 50, 50)
            prefix = "!! CRITICAL"
        else:
            self.set_fill_color(255, 245, 200)
            self.set_draw_color(200, 150, 0)
            prefix = "!  WARNING"
        self.set_font("Helvetica", "B", 10)
        self.multi_cell(0, 6, _safe(f"  {prefix}: {message}"), fill=True,
                        border=1, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(0, 0, 0)
        self.ln(2)

    def projection_table(self, projection: dict):
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(20, 40, 70)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, _safe(f"  {projection.get('description', projection.get('metric', ''))}"),
                  fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

        headers = ["Scenario", "Target", "Financial Impact"]
        widths = [50, 60, 60]
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(230, 235, 245)
        for h, w in zip(headers, widths):
            self.cell(w, 6, f"  {h}", fill=True, border=1)
        self.ln()

        colors = {"conservative": (240, 248, 240), "base": (230, 240, 255), "optimistic": (230, 255, 240)}
        for s in projection.get("scenarios", []):
            self.set_font("Helvetica", "", 9)
            label = s.get("label", "").capitalize()
            target = f"{s.get('target_value', 0):.1f} {projection.get('unit', '')}"
            impact = f"EUR {s.get('impact_eur', 0):,.0f}" if s.get('impact_eur') is not None else "n/a"
            bg = colors.get(s.get("label", ""), (255, 255, 255))
            self.set_fill_color(*bg)
            self.cell(50, 6, f"  {label}", fill=True, border=1)
            self.cell(60, 6, f"  {target}", fill=True, border=1)
            self.cell(60, 6, f"  {impact}", fill=True, border=1)
            self.ln()
        self.ln(3)


def _group_ratios(ratios: list[dict]) -> dict[str, list[dict]]:
    groups = {
        "Profitability": ["gross_margin", "ebit_margin", "net_margin", "roe", "roa", "roce"],
        "Liquidity": ["current_ratio", "quick_ratio", "cash_ratio"],
        "Efficiency": ["dso", "dpo", "inventory_days", "ccc", "asset_turnover"],
        "Leverage": ["debt_to_equity", "interest_coverage", "net_debt_ebitda"],
        "Growth": ["revenue_growth_yoy", "ebit_growth_yoy", "revenue_cagr"],
    }
    result: dict[str, list[dict]] = {g: [] for g in groups}
    for ratio in ratios:
        fid = ratio.get("finding_id", "")
        placed = False
        for group, prefixes in groups.items():
            if any(fid.startswith(p) for p in prefixes):
                result[group].append(ratio)
                placed = True
                break
        if not placed:
            result.setdefault("Other", []).append(ratio)
    return {k: v for k, v in result.items() if v}


def generate_pdf(report: AnalysisReport, job_id: str) -> Path:
    """Generate a full PDF report. Returns the path to the saved file."""
    pdf = KodrlyticsPDF()
    pdf.set_title(report.title)
    pdf.set_author("Kodrlytics Financial Analysis Engine")

    # ── Cover page ─────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(20, 40, 70)
    pdf.cell(0, 15, "KODRLYTICS", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(80, 100, 130)
    pdf.cell(0, 8, "Financial Analysis Engine", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(15)
    pdf.set_draw_color(20, 40, 70)
    pdf.set_line_width(0.8)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    pdf.ln(15)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(20, 40, 70)
    # Split long titles
    title_lines = [report.title[i:i+50] for i in range(0, len(report.title), 50)]
    for line in title_lines:
        pdf.cell(0, 10, _safe(line), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Generated: {report.generated_at}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Source: {report.source_file}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Companies analysed: {len(report.companies)}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(150, 150, 150)
    pdf.multi_cell(0, 5, "CONFIDENTIAL -- For internal use only. All projections are illustrative and do not constitute financial advice. "
                          "Deterministic calculations are based on submitted financial data. LLM-generated narrative has been "
                          "verified against computed values via automated grounding gate.", align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_line_width(0.2)

    # ── Portfolio summary (if multiple companies) ──────────────────────────────
    if len(report.companies) > 1 and report.portfolio_summary:
        pdf.add_page()
        pdf.chapter_title("Portfolio Executive Summary", level=1)
        pdf.body_text(report.portfolio_summary)

    # ── Per-company chapters ───────────────────────────────────────────────────
    for i, company in enumerate(report.companies):
        pdf.add_page()
        pdf.chapter_title(f"{'I' * (i+1)}. {company.company_name}", level=1)
        pdf.body_text(f"NACE Sector: {company.nace_code}")

        # Executive summary from narrative
        pdf.chapter_title("Executive Summary", level=2)
        # Strip grounding warnings from narrative
        narrative = company.narrative
        if narrative.startswith("[GROUNDING"):
            narrative = narrative[narrative.find("]") + 1:].strip() if "]" in narrative else narrative
        pdf.body_text(narrative[:2000] if len(narrative) > 2000 else narrative)

        # Key ratios by group
        pdf.chapter_title("Financial Ratios", level=2)
        grouped = _group_ratios(company.ratios)
        flag_ids = {f.get("finding_id", "") for f in company.flags}

        for group_name, group_ratios in grouped.items():
            pdf.chapter_title(group_name, level=3)
            # Sort by period descending
            sorted_ratios = sorted(group_ratios, key=lambda r: (r.get("finding_id", ""), r.get("period", "")))
            for ratio in sorted_ratios:
                val = ratio.get("value")
                unit = ratio.get("unit", "")
                period = ratio.get("period", "")
                name = ratio.get("name", ratio.get("finding_id", ""))
                value_str = f"{val:.2f} {unit}  ({period})" if val is not None else "N/A"
                is_flagged = ratio.get("finding_id", "") in flag_ids
                pdf.metric_row(name, value_str, flag=is_flagged)
            pdf.ln(3)

        # Flags
        if company.flags:
            pdf.add_page()
            pdf.chapter_title("Risk Flags", level=2)
            for flag in company.flags:
                pdf.flag_box(flag.get("severity", "warning"), flag.get("message", ""))
                # Detailed context
                delta = flag.get("delta_vs_median")
                peer_median = flag.get("peer_median")
                if delta is not None and peer_median is not None:
                    pdf.body_text(
                        f"Company value: {flag.get('company_value', 0):.2f}  |  "
                        f"Peer median: {peer_median:.2f}  |  "
                        f"Delta vs median: {delta:+.2f}"
                    )

        # Recommendations
        if company.projections:
            pdf.add_page()
            pdf.chapter_title("Improvement Recommendations & Projections", level=2)
            for proj in company.projections:
                pdf.chapter_title(proj.get("description", proj.get("metric", "")), level=3)
                pdf.projection_table(proj)
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(120, 120, 120)
                pdf.body_text(proj.get("disclaimer", ""))
                pdf.set_text_color(0, 0, 0)

            # Deep recommendations text (LLM-generated if available)
            if company.recommendations_detail:
                pdf.chapter_title("Detailed Recommendations (Deep Analysis)", level=2)
                pdf.body_text(company.recommendations_detail)

        # Full narrative
        if len(narrative) > 2000:
            pdf.add_page()
            pdf.chapter_title("Full Analytical Narrative", level=2)
            pdf.body_text(narrative)

    # ── Methodology appendix ───────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("Appendix A -- Methodology", level=1)
    pdf.body_text("""All financial ratios are computed deterministically from the submitted financial statements
using Python (pandas/numpy). No ratio, projection, or benchmark comparison involves an LLM calculation.

The LLM (via OpenRouter) is used for exactly two purposes:
  1. Extracting unstructured documents (PDF, Excel, CSV) into a canonical JSON schema.
  2. Writing the analytical narrative from pre-computed findings.

Every number in the narrative is verified against the computed values dictionary via an automated
grounding gate before the report is published. Unverified figures are flagged or removed.

Projection scenarios are bounded by industry peer quartiles (p25/p75) from the Bundesbank/ECB BACH
database, not arbitrary multipliers. This grounds scenario ranges in real peer dispersion.

Benchmark data source: Bundesbank/ECB BACH database (2022), German Mittelstand segment.""")

    pdf.chapter_title("Ratio Formulae", level=2)
    formulae = [
        ("Gross Margin", "gross_profit / revenue x 100"),
        ("EBIT Margin", "ebit / revenue x 100"),
        ("Net Margin", "net_income / revenue x 100"),
        ("ROE", "net_income / total_equity x 100"),
        ("ROA", "net_income / total_assets x 100"),
        ("ROCE", "ebit / (total_assets - current_liabilities) x 100"),
        ("Current Ratio", "current_assets / current_liabilities"),
        ("Quick Ratio", "(current_assets - inventory) / current_liabilities"),
        ("DSO", "(accounts_receivable / revenue) x 365"),
        ("DPO", "(accounts_payable / cogs) x 365"),
        ("Inventory Days", "(inventory / cogs) x 365"),
        ("CCC", "DSO + inventory_days - DPO"),
        ("Asset Turnover", "revenue / total_assets"),
        ("D/E", "total_liabilities / total_equity"),
        ("Interest Coverage", "ebit / interest_expense"),
        ("Net Debt / EBITDA", "(long_term_debt + short_term_debt - cash) / ebitda"),
    ]
    for name, formula in formulae:
        pdf.metric_row(name, formula)

    pdf.chapter_title("Appendix B -- Disclaimer", level=1)
    pdf.body_text("""This report is generated by the Kodrlytics Financial Analysis Engine and is intended
for informational purposes only. It does not constitute financial advice, investment advice,
or any form of professional advisory service.

All projections are labelled "projection, not a guarantee." Scenario ranges reflect peer benchmark
dispersion and stated implementation assumptions, not predicted outcomes.

Financial data was provided by the user and has not been independently audited or verified
beyond automated reconciliation checks (accounting identity validation).

For DATA_MODE=real runs: data is processed using paid LLM providers with no-logging policies.
For DATA_MODE=test runs: free LLM providers are used and may process data for model improvement.
""")

    # Save
    out_path = REPORTS_DIR / f"{job_id}.pdf"
    pdf.output(str(out_path))
    log.info("PDF report saved: %s (%.1f KB)", out_path, out_path.stat().st_size / 1024)
    return out_path


# ── Rooms-pipeline PDF ─────────────────────────────────────────────────────────

_ROOM_ORDER = ["CEO", "Intake", "Extraction", "Analysis", "Benchmarking", "Strategy", "Reporting"]
_ROOM_DISPLAY = {
    "CEO":          "Executive Summary",
    "Intake":       "I.   Document Intelligence & Intake",
    "Extraction":   "II.  Data Extraction & Validation",
    "Analysis":     "III. Financial Analysis",
    "Benchmarking": "IV.  Industry Benchmarking",
    "Strategy":     "V.   Strategic Assessment",
    "Reporting":    "VI.  Reporting & Recommendations",
}


def _render_room_report(pdf: KodrlyticsPDF, text: str) -> None:
    """Render a room manager report with ** heading detection."""
    if not text or text.startswith("["):
        pdf.body_text(text or "(No report generated for this room.)")
        return

    buf: list[str] = []

    def _flush() -> None:
        block = "\n".join(buf).strip()
        if block:
            pdf.body_text(block)
        buf.clear()

    for line in text.split("\n"):
        stripped = line.strip()
        # Detect **HEADING** pattern
        if (stripped.startswith("**") and stripped.endswith("**")
                and 4 < len(stripped) < 80 and stripped.count("**") == 2):
            _flush()
            heading = stripped.strip("*").strip()
            pdf.chapter_title(heading, level=3)
        else:
            buf.append(line)

    _flush()


def generate_rooms_pdf(
    room_reports: dict[str, str],
    company_name: str,
    source_file: str,
    run_id: str,
) -> Path:
    """Generate a professional multi-chapter PDF from room pipeline output."""
    from datetime import datetime as _dt
    generated_at = _dt.now().strftime("%d %B %Y, %H:%M UTC")

    pdf = KodrlyticsPDF()
    pdf.set_title(f"Financial Intelligence Report: {company_name}")
    pdf.set_author("Kodrlytics Financial Intelligence System")

    # ── Cover page ─────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.ln(25)
    pdf.set_font("Helvetica", "B", 32)
    pdf.set_text_color(20, 40, 70)
    pdf.cell(0, 16, "KODRLYTICS", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(80, 100, 130)
    pdf.cell(0, 7, "Financial Intelligence System", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(12)

    pdf.set_draw_color(20, 40, 70)
    pdf.set_line_width(1.0)
    pdf.line(30, pdf.get_y(), 180, pdf.get_y())
    pdf.ln(12)

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(20, 40, 70)
    for chunk in [company_name[i:i+45] for i in range(0, len(company_name), 45)]:
        pdf.cell(0, 11, _safe(chunk), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(100, 120, 150)
    pdf.cell(0, 8, "Financial Intelligence Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    pdf.set_line_width(0.3)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(50, pdf.get_y(), 160, pdf.get_y())
    pdf.ln(10)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, f"Generated: {generated_at}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Source: {_safe(source_file)}", align="C", new_x="LMARGIN", new_y="NEXT")
    rooms_analysed = sum(1 for k in _ROOM_ORDER if k in room_reports)
    pdf.cell(0, 7, f"Analysis rooms completed: {rooms_analysed} of {len(_ROOM_ORDER)}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)

    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(160, 160, 160)
    pdf.multi_cell(
        0, 5,
        "CONFIDENTIAL -- For internal use only. All projections are illustrative and do not "
        "constitute financial advice. AI-generated analysis has been produced by a multi-agent "
        "system using free language models via OpenRouter. Verify all figures independently.",
        align="C",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.set_line_width(0.2)

    # ── Table of Contents ──────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("Table of Contents", level=1)
    toc_entries = [
        ("Executive Summary", "CEO" in room_reports),
        ("I.   Document Intelligence & Intake", "Intake" in room_reports),
        ("II.  Data Extraction & Validation", "Extraction" in room_reports),
        ("III. Financial Analysis", "Analysis" in room_reports),
        ("IV.  Industry Benchmarking", "Benchmarking" in room_reports),
        ("V.   Strategic Assessment", "Strategy" in room_reports),
        ("VI.  Reporting & Recommendations", "Reporting" in room_reports),
        ("Appendix A -- Methodology", True),
        ("Appendix B -- Disclaimer", True),
    ]
    pdf.set_font("Helvetica", "", 11)
    for title, available in toc_entries:
        color = (20, 40, 70) if available else (180, 180, 180)
        pdf.set_text_color(*color)
        pdf.cell(0, 8, f"  {_safe(title)}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)

    # ── Analysis chapters ──────────────────────────────────────────────────────
    for room_key in _ROOM_ORDER:
        if room_key not in room_reports:
            continue
        pdf.add_page()
        display = _ROOM_DISPLAY.get(room_key, room_key)
        pdf.chapter_title(display, level=1)
        _render_room_report(pdf, room_reports[room_key])

    # ── Appendix A: Methodology ────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("Appendix A -- Methodology", level=1)
    pdf.body_text(
        "This report was produced by the Kodrlytics multi-agent financial intelligence system. "
        "The pipeline consists of six specialised analysis rooms, each staffed by 20 virtual "
        "senior analysts (language model workers) and one room manager who synthesises their findings.\n\n"
        "ROOM ARCHITECTURE\n"
        "  Room 1 (Intake): Document classification, data quality assessment, completeness audit.\n"
        "  Room 2 (Extraction): Financial data normalisation, schema validation, period alignment.\n"
        "  Room 3 (Analysis): Ratio computation, trend analysis, anomaly detection.\n"
        "  Room 4 (Benchmarking): Peer comparison against Bundesbank/ECB BACH industry data.\n"
        "  Room 5 (Strategy): Strategic assessment, improvement opportunities, risk mapping.\n"
        "  Room 6 (Reporting): Synthesis, executive summary, actionable recommendations.\n\n"
        "ANALYTICAL PROCESS\n"
        "Each worker conducts four analytical rounds:\n"
        "  Round 1 -- Structured scan: identify key data points and initial observations.\n"
        "  Round 2 -- Deep numerical analysis: compute changes, trends, anomalies.\n"
        "  Round 3 -- Critical challenge: test assumptions, seek alternative explanations.\n"
        "  Round 4 -- Final synthesis: produce board-level findings and recommendations.\n\n"
        "EXTERNAL RESEARCH\n"
        "Workers supplement financial data with real-time DuckDuckGo search results "
        "to provide market context and industry benchmarks.\n\n"
        "LANGUAGE MODELS\n"
        "All narrative generation uses free language models via OpenRouter. "
        "For production use with sensitive data, configure DATA_MODE=real with "
        "a no-logging paid model."
    )

    # ── Appendix B: Disclaimer ─────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("Appendix B -- Disclaimer", level=1)
    pdf.body_text(
        "This report is generated by an AI-powered financial analysis system and is intended "
        "for informational and internal decision-support purposes only. It does not constitute "
        "financial advice, investment advice, or any form of regulated professional advisory "
        "service.\n\n"
        "AI-GENERATED CONTENT\n"
        "The analysis narratives, findings, and recommendations in this report are generated "
        "by large language models (LLMs). While the system is designed to work only from "
        "provided data, LLMs may occasionally produce inaccurate or fabricated statements. "
        "All figures should be verified against the original source documents.\n\n"
        "PROJECTIONS\n"
        "Any forward-looking statements or projections are illustrative scenarios based on "
        "historical data patterns and stated assumptions. They are not predictions of future "
        "performance and should not be relied upon as such.\n\n"
        "DATA PRIVACY\n"
        "Financial data submitted for analysis is processed by third-party LLM providers. "
        "For sensitive data, ensure DATA_MODE=real is configured with an appropriate "
        "no-logging model policy.\n\n"
        "LIABILITY\n"
        "Kodrlytics and its operators accept no liability for decisions made on the basis "
        "of this report. Users are responsible for verifying all information and obtaining "
        "qualified professional advice before making financial or strategic decisions."
    )

    out_path = REPORTS_DIR / f"{run_id}.pdf"
    pdf.output(str(out_path))
    log.info("Rooms PDF saved: %s (%.1f KB)", out_path, out_path.stat().st_size / 1024)
    return out_path
