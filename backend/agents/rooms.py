"""6 concrete pipeline rooms — deep analysis with full financial data context."""
from __future__ import annotations
import logging
from pathlib import Path
from backend.agents.models import Task, PipelineContext
from backend.agents.room import Room

log = logging.getLogger(__name__)
_BENCH_DIR = Path(__file__).parent.parent.parent / "data" / "benchmarks"


def _financial_table(ctx: PipelineContext) -> str:
    """Build a multi-year financial data table for worker context."""
    if not ctx.financials:
        return ""
    f = ctx.financials
    periods = [p.label for p in f.income_statement.periods]
    if not periods:
        return ""

    M = 1_000_000
    is_ = f.income_statement
    bs = f.balance_sheet

    def row(label: str, data: dict, scale: float = M) -> str:
        vals = "  ".join(f"{data.get(p, 0)/scale:>10,.1f}" for p in periods)
        return f"  {label:<35} {vals}"

    header = "  " + " " * 35 + "  ".join(f"{p:>10}" for p in periods)
    sep    = "  " + "-" * (35 + 12 * len(periods))

    lines = [
        f"COMPANY: {f.company_name} | NACE: {f.nace_code} | STD: {f.reporting_standard} | CCY: {f.currency}",
        f"PERIODS: {', '.join(periods)} (values in {f.currency} millions)",
        "",
        header, sep,
        row("Revenue", is_.revenue),
        row("Cost of Goods Sold", is_.cost_of_goods_sold),
        row("Gross Profit", is_.gross_profit),
        row("Operating Expenses", is_.operating_expenses),
        row("EBIT", is_.ebit),
        row("Interest Expense", is_.interest_expense),
        row("EBT", is_.ebt),
        row("Income Tax", is_.income_tax),
        row("Net Income", is_.net_income),
        sep,
        row("Cash", bs.cash),
        row("Accounts Receivable", bs.accounts_receivable),
        row("Inventory", bs.inventory),
        row("Current Assets", bs.current_assets),
        row("Fixed Assets", bs.fixed_assets),
        row("Total Assets", bs.total_assets),
        sep,
        row("Accounts Payable", bs.accounts_payable),
        row("Current Liabilities", bs.current_liabilities),
        row("Long-Term Debt", bs.long_term_debt),
        row("Total Liabilities", bs.total_liabilities),
        row("Total Equity", bs.total_equity),
    ]
    return "\n".join(lines)


def _ratio_table(ctx: PipelineContext) -> str:
    """Build a formatted table of all computed ratios."""
    if not ctx.analysis:
        return ""
    ratios = [r for r in ctx.analysis.ratios if not r.not_derivable and r.value is not None]
    if not ratios:
        return ""
    lines = ["COMPUTED RATIOS:"]
    for r in ratios:
        lines.append(f"  {r.name:<40} {r.value:>8.2f} {r.unit:<8}  ({r.period})")
    return "\n".join(lines)


# ── Room 1: Intake ─────────────────────────────────────────────────────────────

class IntakeRoom(Room):
    name = "Intake"
    stage = 0

    async def setup(self, ctx: PipelineContext) -> None:
        if not ctx.document_text:
            from backend.intake import parsers
            ctx.document_text = parsers.parse_document(ctx.filename, ctx.content)

    def make_tasks(self, ctx: PipelineContext) -> list[Task]:
        ext = Path(ctx.filename).suffix.lower()
        doc  = ctx.document_text or ""
        prev = doc[:800]
        size_kb = len(ctx.content) // 1024
        return [
            Task("intake-fmt", "Document Format & Structure Analysis",
                 f"Analyse '{ctx.filename}' ({size_kb:,} KB, {ext} format). "
                 f"Identify: file format, document type, reporting standard, language, "
                 f"data density, and structural quality. Preview:\n{prev[:600]}",
                 [f"financial statement {ext[1:]} format structure analysis",
                  "SEC EDGAR XBRL JSON format annual report structure"]),
            Task("intake-meta", "Company & Reporting Period Identification",
                 f"From this document, extract: company name, legal form, country, "
                 f"reporting standard (HGB/IFRS/US-GAAP), currency, and all fiscal years covered. "
                 f"How many years of history are available? Preview:\n{prev[:800]}",
                 ["SEC EDGAR company facts annual report identification",
                  "XBRL company financial reporting periods"]),
            Task("intake-scope", "Data Completeness & Coverage Assessment",
                 f"Assess the scope and completeness of this {size_kb:,} KB document. "
                 f"What financial statements are present (P&L, balance sheet, cash flow)? "
                 f"What periods are covered? Are there gaps or missing data? "
                 f"How many individual data concepts/line items are available? Preview:\n{prev[:600]}",
                 ["financial statement completeness assessment",
                  "annual report data quality assessment"]),
            Task("intake-quality", "Data Quality & Reliability Assessment",
                 f"Evaluate the data quality and reliability of this financial dataset. "
                 f"Are there obvious anomalies, inconsistencies, or unusual patterns "
                 f"in the first look at this document? Flag any concerns. Preview:\n{prev[:500]}",
                 ["financial data quality assessment",
                  "financial statement anomaly detection"]),
        ]

    def build_context_str(self, ctx: PipelineContext) -> str:
        doc = ctx.document_text or ""
        return (
            f"Filename: {ctx.filename}\n"
            f"File size: {len(ctx.content):,} bytes\n"
            f"Document length: {len(doc):,} chars\n"
            f"Preview:\n{doc[:1200]}"
        )


# ── Room 2: Extraction ─────────────────────────────────────────────────────────

class ExtractionRoom(Room):
    name = "Extraction"
    stage = 1

    async def setup(self, ctx: PipelineContext) -> None:
        from backend.intake.extractor import extract_financials
        result = await extract_financials(ctx.filename, ctx.content, ctx.company_hint)
        ctx.financials = result.financials
        ctx.reconciliation = result.reconciliation

    def make_tasks(self, ctx: PipelineContext) -> list[Task]:
        if ctx.financials is None:
            return [Task("extract-fail", "Extraction Failed",
                         "Document extraction failed. Analyse the root cause and recommend solutions.",
                         ["financial statement extraction troubleshooting"])]

        f = ctx.financials
        periods = [p.label for p in f.income_statement.periods]
        latest = periods[-1] if periods else "N/A"
        earliest = periods[0] if periods else "N/A"
        years_span = len(periods)

        # Build multi-year summary strings for tasks
        rev_trend = ", ".join(
            f"{p}: {f.income_statement.revenue.get(p, 0)/1e9:.2f}B"
            for p in periods
        )
        ni_trend = ", ".join(
            f"{p}: {f.income_statement.net_income.get(p, 0)/1e9:.2f}B"
            for p in periods
        )
        ta_trend = ", ".join(
            f"{p}: {f.balance_sheet.total_assets.get(p, 0)/1e9:.2f}B"
            for p in periods
        )
        eq_trend = ", ".join(
            f"{p}: {f.balance_sheet.total_equity.get(p, 0)/1e9:.2f}B"
            for p in periods
        )

        tasks = [
            Task("extract-is", "Income Statement Deep Review",
                 f"Analyse the full income statement for {f.company_name} across {years_span} years "
                 f"({earliest}-{latest}). Revenue trend: {rev_trend}. Net income: {ni_trend}. "
                 f"Comment on: revenue scale and growth trajectory, cost structure evolution, "
                 f"margin trends, any inflection points or anomalies.",
                 [f"{f.company_name} revenue growth history",
                  f"{f.company_name} income statement analysis"]),

            Task("extract-bs", "Balance Sheet Evolution",
                 f"Analyse balance sheet evolution for {f.company_name} ({earliest}-{latest}). "
                 f"Total assets: {ta_trend}. Total equity: {eq_trend}. "
                 f"How has the asset base grown? How has the capital structure changed? "
                 f"Is the company becoming more or less asset-heavy over time?",
                 [f"{f.company_name} balance sheet structure history",
                  f"capital structure evolution analysis"]),

            Task("extract-cf", "Cash Flow & Liquidity Position",
                 f"Assess the cash generation and liquidity of {f.company_name}. "
                 f"Cash position trend: {', '.join(f'{p}: {f.balance_sheet.cash.get(p,0)/1e9:.2f}B' for p in periods)}. "
                 f"What does the cash position reveal about financial strength? "
                 f"Is the company accumulating or deploying cash?",
                 [f"{f.company_name} cash flow free cash flow",
                  "technology company cash management strategy"]),

            Task("extract-debt", "Debt Structure & Leverage Analysis",
                 f"Analyse the debt and leverage of {f.company_name}. "
                 f"Long-term debt: {', '.join(f'{p}: {f.balance_sheet.long_term_debt.get(p,0)/1e9:.2f}B' for p in periods)}. "
                 f"How has leverage changed? Is the debt load manageable given earnings? "
                 f"What is the debt-to-equity trend?",
                 [f"{f.company_name} debt leverage capital structure",
                  "corporate debt strategy technology companies"]),
        ]

        if ctx.reconciliation and ctx.reconciliation.errors:
            errs = "; ".join(f"{e.check}: delta {e.delta:+,.0f}" for e in ctx.reconciliation.errors[:4])
            tasks.append(Task("extract-recon", "Reconciliation & Data Integrity",
                              f"Accounting identity errors found: {errs}. "
                              f"Are these rounding differences or material data issues? "
                              f"What is the impact on the reliability of downstream analysis?",
                              ["financial statement reconciliation data quality",
                               "accounting identity balance sheet reconciliation"]))
        return tasks

    def build_context_str(self, ctx: PipelineContext) -> str:
        if not ctx.financials:
            return "Extraction failed — no financial data available."
        return _financial_table(ctx)


# ── Room 3: Analysis ───────────────────────────────────────────────────────────

class AnalysisRoom(Room):
    name = "Analysis"
    stage = 2

    async def setup(self, ctx: PipelineContext) -> None:
        if ctx.financials:
            from backend.analysis.ratios import run_analysis
            ctx.analysis = run_analysis(ctx.financials)

    def make_tasks(self, ctx: PipelineContext) -> list[Task]:
        if not ctx.analysis or not ctx.financials:
            return []
        f = ctx.financials
        periods = [p.label for p in f.income_statement.periods]
        latest = periods[-1] if periods else "N/A"
        earliest = periods[0] if periods else "N/A"

        def _ratio_trend(prefix: str) -> str:
            relevant = [r for r in ctx.analysis.ratios
                        if not r.not_derivable and r.value is not None
                        and r.finding_id.startswith(prefix)]
            return "; ".join(f"{r.name} ({r.period}): {r.value:.2f}{r.unit}" for r in relevant[:8])

        rev = f.income_statement.revenue
        gross = f.income_statement.gross_profit
        ebit = f.income_statement.ebit
        net = f.income_statement.net_income

        gm_trend = ", ".join(
            f"{p}: {gross.get(p,0)/rev.get(p,1)*100:.1f}%" for p in periods if rev.get(p)
        )
        em_trend = ", ".join(
            f"{p}: {ebit.get(p,0)/rev.get(p,1)*100:.1f}%" for p in periods if rev.get(p)
        )
        nm_trend = ", ".join(
            f"{p}: {net.get(p,0)/rev.get(p,1)*100:.1f}%" for p in periods if rev.get(p)
        )

        # Revenue growth rates
        rev_growth = []
        for i in range(1, len(periods)):
            p_curr, p_prev = periods[i], periods[i-1]
            r_curr, r_prev = rev.get(p_curr, 0), rev.get(p_prev, 0)
            if r_prev:
                rev_growth.append(f"{p_curr}: {(r_curr/r_prev - 1)*100:+.1f}%")

        tasks = [
            Task("analysis-rev", "Revenue Growth & Trajectory",
                 f"Deep-analyse revenue growth for {f.company_name} ({earliest}-{latest}). "
                 f"YoY growth rates: {', '.join(rev_growth)}. "
                 f"Identify acceleration/deceleration periods, compute CAGR, and explain drivers. "
                 f"Is growth organic or acquisition-driven? What is the quality of revenue growth?",
                 [f"{f.company_name} revenue growth drivers analysis",
                  f"{f.company_name} business model revenue segments"]),

            Task("analysis-prof", "Profitability & Margin Analysis",
                 f"Analyse all profitability margins for {f.company_name} ({earliest}-{latest}). "
                 f"Gross margins: {gm_trend}. EBIT margins: {em_trend}. Net margins: {nm_trend}. "
                 f"Are margins expanding or compressing? What is causing the trend? "
                 f"How does this compare to industry standards?",
                 [f"{f.company_name} profit margin analysis",
                  "technology company gross margin EBIT margin benchmark"]),

            Task("analysis-liq", "Liquidity & Working Capital",
                 f"Assess liquidity and working capital for {f.company_name}. "
                 f"Ratios: {_ratio_trend('current_ratio') or _ratio_trend('quick_ratio') or 'computing...'}. "
                 f"Is the company in a strong or stressed liquidity position? "
                 f"How has working capital management evolved?",
                 [f"{f.company_name} liquidity working capital",
                  "technology company liquidity ratio benchmark"]),

            Task("analysis-lev", "Leverage & Capital Structure",
                 f"Analyse leverage and capital structure for {f.company_name}. "
                 f"Ratios: {_ratio_trend('debt_to_equity') or _ratio_trend('interest_coverage') or 'computing...'}. "
                 f"Is the company over- or under-leveraged? How has financial risk evolved? "
                 f"What is the interest coverage trend?",
                 [f"{f.company_name} leverage debt capital structure",
                  "optimal capital structure technology company"]),

            Task("analysis-eff", "Operational Efficiency",
                 f"Evaluate operational efficiency for {f.company_name}. "
                 f"Ratios: {_ratio_trend('asset_turnover') or _ratio_trend('dso') or 'computing...'}. "
                 f"How efficiently is the company using its assets? "
                 f"What is the cash conversion cycle trend?",
                 [f"{f.company_name} asset turnover operational efficiency",
                  "asset-light business model efficiency metrics"]),

            Task("analysis-ret", "Return Metrics & Value Creation",
                 f"Assess value creation metrics for {f.company_name}. "
                 f"ROE/ROA/ROCE trends: {_ratio_trend('roe') or _ratio_trend('roa') or 'computing...'}. "
                 f"Is the company generating adequate returns on capital? "
                 f"Is value being created or destroyed over time?",
                 [f"{f.company_name} return on equity ROE analysis",
                  "shareholder value creation technology company"]),

            Task("analysis-trend", "Multi-Year Trend & Inflection Point Analysis",
                 f"Identify key inflection points and long-term trends for {f.company_name} "
                 f"across all {len(periods)} years ({earliest}-{latest}). "
                 f"What years saw major changes? What structural shifts have occurred? "
                 f"What is the overall trajectory and what does it predict about the future?",
                 [f"{f.company_name} long-term financial performance history",
                  f"{f.company_name} strategic inflection points"]),
        ]
        return tasks

    def build_context_str(self, ctx: PipelineContext) -> str:
        table = _financial_table(ctx)
        ratios = _ratio_table(ctx)
        return f"{table}\n\n{ratios}"


# ── Room 4: Benchmarking ───────────────────────────────────────────────────────

class BenchmarkingRoom(Room):
    name = "Benchmarking"
    stage = 3

    async def setup(self, ctx: PipelineContext) -> None:
        if ctx.analysis and ctx.financials:
            from backend.benchmark.store import BenchmarkStore
            from backend.benchmark.flags import run_benchmark
            store = BenchmarkStore(data_dir=_BENCH_DIR)
            ctx.benchmark = run_benchmark(ctx.analysis, ctx.financials.nace_code, store)

    def make_tasks(self, ctx: PipelineContext) -> list[Task]:
        if not ctx.benchmark or not ctx.financials:
            return []
        f = ctx.financials
        flags = ctx.benchmark.flags

        tasks = [
            Task("bench-ovr", "Industry Peer Comparison Overview",
                 f"Compare {f.company_name} (NACE {f.nace_code}) against industry peers. "
                 f"Total flags raised: {len(flags)}. "
                 f"Give a comprehensive overview: where does the company rank? "
                 f"Which metrics are strongest vs weakest vs peers? "
                 f"What does this peer comparison reveal about competitive positioning?",
                 [f"NACE {f.nace_code} industry financial benchmarks peer comparison",
                  f"{f.company_name} competitive position industry analysis"]),

            Task("bench-ctx", "Industry Context & Market Position",
                 f"Provide industry context for {f.company_name} in NACE {f.nace_code} sector. "
                 f"What are the key financial characteristics of this industry? "
                 f"What are typical margin profiles, capital intensity, and growth rates? "
                 f"How does the company's profile fit or deviate from industry norms?",
                 [f"NACE {f.nace_code} industry financial characteristics",
                  f"{f.company_name} industry market position competitive landscape"]),
        ]

        for flag in flags[:8]:
            delta = flag.company_value - flag.peer_median
            tasks.append(Task(
                f"bench-{flag.flag_type[:12]}",
                f"Flag Analysis: {flag.flag_type.replace('_', ' ').title()}",
                f"Deep-analyse this flag for {f.company_name}: {flag.message}. "
                f"Company value: {flag.company_value:.2f}{flag.metric}, "
                f"Peer median: {flag.peer_median:.2f}{flag.metric}, "
                f"Delta vs peers: {delta:+.2f} ({abs(delta/flag.peer_median)*100:.0f}% deviation). "
                f"What are the root causes? What is the business impact? "
                f"How urgent is remediation? What would best-in-class look like?",
                [f"{flag.metric} improvement strategy best practices",
                 f"{f.company_name} {flag.metric} analysis"],
            ))
        return tasks

    def build_context_str(self, ctx: PipelineContext) -> str:
        if not ctx.benchmark:
            return "No benchmark data."
        f = ctx.financials
        flags_text = "\n".join(
            f"  [{fl.severity.upper()}] {fl.flag_type}: {fl.message} "
            f"(company: {fl.company_value:.2f}, peer median: {fl.peer_median:.2f})"
            for fl in ctx.benchmark.flags
        )
        ratios = _ratio_table(ctx)
        return f"Company: {f.company_name} | NACE: {f.nace_code}\n\nFLAGS:\n{flags_text}\n\n{ratios}"


# ── Room 5: Strategy ───────────────────────────────────────────────────────────

class StrategyRoom(Room):
    name = "Strategy"
    stage = 4

    async def setup(self, ctx: PipelineContext) -> None:
        if ctx.benchmark and ctx.financials:
            from backend.benchmark.store import BenchmarkStore
            from backend.strategy.actions import build_actions_from_flags
            from backend.strategy.projections import compute_projections, format_projections_summary
            store = BenchmarkStore(data_dir=_BENCH_DIR)
            ctx.actions = build_actions_from_flags(ctx.benchmark.flags, store, ctx.financials.nace_code)
            ctx.projections = compute_projections(ctx.actions, ctx.financials)
            ctx.proj_summary = format_projections_summary(ctx.projections)

    def make_tasks(self, ctx: PipelineContext) -> list[Task]:
        f = ctx.financials
        company = getattr(f, "company_name", "the company") if f else "the company"

        if not ctx.actions:
            return [
                Task("strat-maint", "Competitive Positioning & Growth Strategy",
                     f"Company metrics are within peer ranges. Develop a forward-looking growth "
                     f"strategy for {company}. Identify 3-5 opportunistic improvements to build "
                     f"sustainable competitive advantage. Consider market trends and industry dynamics.",
                     [f"{company} growth strategy competitive advantage",
                      "value creation strategy financial performance"]),
                Task("strat-risk", "Risk Management & Resilience",
                     f"Even without critical flags, assess the strategic risk landscape for {company}. "
                     f"What are the key macro, competitive, and operational risks? "
                     f"What resilience measures should be in place?",
                     [f"{company} risk factors strategic risks",
                      "enterprise risk management financial resilience"]),
            ]

        tasks = []
        for action in ctx.actions[:10]:
            proj = next((p for p in ctx.projections if p.action.finding_id == action.finding_id), None)
            scenarios_text = ""
            if proj:
                scenarios_text = " | ".join(
                    f"{s.label}: target {s.target_value:.1f}{action.unit}"
                    + (f", EUR {s.impact_eur:,.0f} impact" if s.impact_eur else "")
                    for s in proj.scenarios
                )

            tasks.append(Task(
                f"strat-{action.action_type.value[:12]}",
                f"Strategy: {action.action_type.value.replace('_', ' ').title()}",
                f"Develop a comprehensive implementation plan for {company}: {action.description}. "
                f"Current: {action.current_value:.2f}{action.unit}, "
                f"Target: {action.target_base:.2f}{action.unit}. "
                f"Scenarios: {scenarios_text}. "
                f"Provide: specific action steps, timeline (30/90/180 days), "
                f"resource requirements, KPIs to track, and potential obstacles.",
                [f"{action.action_type.value.replace('_', ' ')} implementation strategy",
                 f"financial performance improvement {action.action_type.value.replace('_', ' ')}"],
            ))

        tasks.append(Task(
            "strat-synergy", "Cross-Initiative Synergies & Prioritisation",
            f"Analyse the {len(ctx.actions)} improvement initiatives for {company} as a portfolio. "
            f"Which initiatives have the highest ROI? Which have synergies or dependencies? "
            f"Build a prioritised 12-month roadmap with resource allocation guidance.",
            [f"{company} strategic transformation roadmap",
             "financial improvement initiative prioritisation"],
        ))
        return tasks

    def build_context_str(self, ctx: PipelineContext) -> str:
        parts = [_financial_table(ctx)]
        if ctx.proj_summary:
            parts.append(f"\nPROJECTIONS SUMMARY:\n{ctx.proj_summary}")
        bench_report = ctx.room_reports.get("Benchmarking", "")
        if bench_report:
            parts.append(f"\nBENCHMARKING FINDINGS:\n{bench_report[:1500]}")
        return "\n".join(parts)


# ── Room 6: Reporting ──────────────────────────────────────────────────────────

class ReportingRoom(Room):
    name = "Reporting"
    stage = 5

    async def setup(self, ctx: PipelineContext) -> None:
        pass

    def make_tasks(self, ctx: PipelineContext) -> list[Task]:
        f = ctx.financials
        company = getattr(f, "company_name", "the company") if f else "the company"

        analysis_report  = ctx.room_reports.get("Analysis", "")[:600]
        bench_report     = ctx.room_reports.get("Benchmarking", "")[:600]
        strategy_report  = ctx.room_reports.get("Strategy", "")[:600]
        extraction_report = ctx.room_reports.get("Extraction", "")[:400]
        flag_count = len(getattr(ctx.benchmark, "flags", []))

        return [
            Task("report-exec", "Executive Summary",
                 f"Write a compelling 250-300 word executive summary for {company}. "
                 f"Cover: company overview, top 3 strengths, main risks ({flag_count} flags), "
                 f"and the single most important recommendation. "
                 f"Write for a board audience — be decisive and specific. "
                 f"Key context: {extraction_report}",
                 ["executive summary financial analysis board report",
                  "CEO CFO executive summary structure best practice"]),

            Task("report-fin", "Financial Performance Chapter",
                 f"Write a detailed 'Financial Performance' chapter for {company}. "
                 f"Cover: revenue growth, margin trends, balance sheet strength, and cash generation. "
                 f"Use specific numbers and years. Include a narrative that tells the financial story. "
                 f"Context: {analysis_report}",
                 ["financial performance chapter annual report",
                  "financial narrative analysis board presentation"]),

            Task("report-bench", "Competitive Position Chapter",
                 f"Write a detailed 'Competitive Position' chapter for {company}. "
                 f"Cover: peer comparison, industry ranking, competitive strengths and weaknesses. "
                 f"{flag_count} flags were raised. Discuss each area of underperformance with context. "
                 f"Context: {bench_report}",
                 ["competitive position analysis industry benchmark",
                  "peer comparison financial analysis chapter"]),

            Task("report-strat", "Strategic Recommendations Chapter",
                 f"Write a comprehensive 'Strategic Recommendations' chapter for {company}. "
                 f"For each recommendation: what, why, how, expected impact, timeline, and KPIs. "
                 f"Prioritise by impact and feasibility. Include a visual roadmap description. "
                 f"Context: {strategy_report}",
                 ["strategic recommendations chapter financial report",
                  "implementation roadmap financial improvement"]),

            Task("report-risk", "Risk Assessment Chapter",
                 f"Write a detailed 'Risk Assessment' chapter for {company}. "
                 f"{flag_count} quantitative flags were raised. For each: severity rating, "
                 f"root cause analysis, early warning indicators, and mitigation plan. "
                 f"Also cover qualitative/macro risks not captured by ratios. "
                 f"Context: {bench_report}",
                 ["risk assessment chapter financial report",
                  "financial risk mitigation strategy"]),

            Task("report-outlook", "Outlook & Conclusions",
                 f"Write a 'Outlook & Conclusions' chapter for {company}. "
                 f"Synthesise: where is the company headed based on all analysis? "
                 f"What are the 3-year scenarios (bull/base/bear)? "
                 f"What is the single most critical factor to monitor? "
                 f"End with a clear overall assessment verdict.",
                 [f"{company} business outlook financial forecast",
                  "financial scenario analysis outlook 3 year"]),
        ]

    def build_context_str(self, ctx: PipelineContext) -> str:
        parts = [_financial_table(ctx)]
        for room_name in ["Extraction", "Analysis", "Benchmarking", "Strategy"]:
            report = ctx.room_reports.get(room_name, "")
            if report:
                parts.append(f"\n--- {room_name.upper()} ROOM REPORT ---\n{report[:800]}")
        return "\n".join(parts)
