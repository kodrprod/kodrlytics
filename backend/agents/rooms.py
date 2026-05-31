"""6 concrete pipeline rooms — 20 workers each, full dataset context."""
from __future__ import annotations
import logging
from pathlib import Path
from backend.agents.models import Task, PipelineContext
from backend.agents.room import Room

log = logging.getLogger(__name__)
_BENCH_DIR = Path(__file__).parent.parent.parent / "data" / "benchmarks"


def _financial_table(ctx: PipelineContext) -> str:
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
        "", header, sep,
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
        if not ctx.document_text and ctx.dataset:
            ctx.document_text = ctx.dataset.summary()
        elif not ctx.document_text:
            from backend.intake import parsers
            ctx.document_text = parsers.parse_document(ctx.filename, ctx.content)

    def make_tasks(self, ctx: PipelineContext) -> list[Task]:
        ds = ctx.dataset
        ext = Path(ctx.filename).suffix.lower()
        doc = ctx.document_text or ""
        size_kb = len(ctx.content) // 1024

        if ds:
            years = ds.years
            company = ds.company_name
            tasks = [
                Task("intake-overview", "Dataset Overview & Scale",
                     f"Analyse the full dataset for {company}: {ds.total_files} files, "
                     f"years {years[0] if years else '?'}-{years[-1] if years else '?'}. "
                     f"Scale, comprehensiveness, analytical potential. Most valuable data? Gaps?",
                     [f"{company} construction company Germany",
                      "company dataset financial analysis"]),
                Task("intake-annual", "Annual Reports Quality",
                     f"Analyse {len(ds.annual_reports)} annual reports ({', '.join(sorted(ds.annual_reports))}). "
                     f"Statements present? Reporting standard? Completeness across years?",
                     ["German Jahresbericht HGB financial statements",
                      "annual report data quality"]),
                Task("intake-accounting", "Accounting Journals",
                     f"Analyse {len(ds.accounting_journals)} accounting journals. "
                     f"Transaction detail, cost categories, analytical value?",
                     ["Buchungsjournal accounting journal Germany",
                      "general ledger analysis"]),
                Task("intake-payroll", "Payroll & HR Data",
                     f"Assess {len(ds.payroll_journals)} years of payroll data. "
                     f"Headcount, salary data, workforce trends accessible?",
                     ["German Lohnjournal payroll analysis",
                      "workforce cost HR data"]),
                Task("intake-compliance", "Compliance Reports",
                     f"Assess {len(ds.compliance_reports)} compliance reports. "
                     f"Areas covered, recurring issues, regulatory risks?",
                     ["German compliance report GmbH",
                      "compliance risk assessment construction"]),
                Task("intake-projects", "Project Portfolio",
                     f"Analyse project portfolio: {len(ds.project_reports)} projects. "
                     f"Project mix, long vs short term, profitability data available?",
                     ["construction project portfolio Germany",
                      "project profitability reporting"]),
                Task("intake-invoices", "Invoice & Revenue Data",
                     f"Assess invoices across {len(ds.invoices)} years. "
                     f"Customer detail, revenue patterns, average invoice sizes?",
                     ["accounts receivable invoice analysis",
                      "customer concentration revenue"]),
                Task("intake-contracts", "Contracts & Legal",
                     f"Review {len(ds.contracts)} contracts. "
                     f"Contract types, financial obligations, concentration risks?",
                     ["contract analysis financial obligations Germany",
                      "legal document risk assessment"]),
                Task("intake-minutes", "Meeting Minutes",
                     f"Analyse {len(ds.meeting_minutes)} meeting minutes. "
                     f"Strategic decisions, management concerns, correlation with financials?",
                     ["board meeting minutes strategic decisions",
                      "management meeting financial correlation"]),
                Task("intake-qa", "Quality Assurance",
                     f"Assess {len(ds.qa_reports)} QA reports. "
                     f"Operational quality issues, recurring problems, cost of quality?",
                     ["quality assurance construction",
                      "QA cost operational efficiency"]),
                Task("intake-timeline", "15-Year Data Coherence",
                     f"Assess coherence across {len(years)} years for {company}. "
                     f"Gaps, format changes, inconsistencies? Best-covered years?",
                     [f"{company} business history",
                      "longitudinal financial data quality"]),
                Task("intake-crossref", "Cross-Document Consistency",
                     f"Check consistency between sources for {company}. "
                     f"Do annual reports match journals? Payroll vs financials?",
                     ["financial statement cross-reference",
                      "audit data consistency"]),
                Task("intake-sectors", "Business Model Analysis",
                     f"Characterise {company}'s business model from documents. "
                     f"Sectors, B2B/B2C, public/private, domestic/export?",
                     [f"{company} construction GmbH business model Germany",
                      "German construction business segments"]),
                Task("intake-risks", "Initial Risk Flags",
                     f"Identify top 5 preliminary risk signals for {company} "
                     f"from intake analysis. Red flags before deep analysis?",
                     ["financial risk early warning signals",
                      "preliminary risk assessment"]),
                Task("intake-value", "High-Value Analysis Opportunities",
                     f"Identify top 5 most valuable analysis opportunities "
                     f"in the {company} dataset. Unique data combinations?",
                     ["financial dataset analysis opportunities",
                      "data-driven business intelligence"]),
                Task("intake-seasonal", "Seasonality & Revenue Cycles",
                     f"Identify seasonal patterns in {company}'s business. "
                     f"Are invoices, costs, or headcount concentrated in certain months/quarters? "
                     f"Revenue seasonality vs construction sector norms?",
                     ["construction seasonality Germany",
                      "revenue cycle seasonal patterns"]),
                Task("intake-macro", "Macro-Economic Context",
                     f"Frame {company}'s 15-year history ({years[0] if years else '?'}-{years[-1] if years else '?'}) "
                     f"against major macro events: 2008 crisis, COVID-2020, 2022 construction slowdown, "
                     f"German housing market shifts. Which events show in data?",
                     ["German construction market 2010-2024",
                      "macroeconomic impact German SME"]),
                Task("intake-digital", "Digitalisation & Technology Signals",
                     f"Look for technology and digitalisation signals in {company}'s documents. "
                     f"Any IT investments, software costs, digital project references, BIM mentions?",
                     ["construction digitalisation Germany BIM",
                      "Mittelstand digital transformation costs"]),
                Task("intake-esg", "ESG & Sustainability Signals",
                     f"Identify ESG and sustainability signals in {company}'s documents. "
                     f"Environmental fines, energy reporting, carbon mentions, social commitments?",
                     ["German construction ESG sustainability reporting",
                      "GmbH environmental compliance requirements"]),
                Task("intake-credit", "Credit & Banking Relationship Signals",
                     f"Identify banking and credit relationship signals for {company}. "
                     f"Loan documents, bank references, credit lines, covenant mentions "
                     f"in contracts or meeting minutes?",
                     ["German Mittelstand bank financing",
                      "GmbH credit facilities construction"]),
            ]
        else:
            prev = doc[:800]
            tasks = [
                Task("intake-fmt", "Document Format & Structure",
                     f"Analyse '{ctx.filename}' ({size_kb:,} KB, {ext}). "
                     f"Format, document type, reporting standard, data quality. Preview:\n{prev[:600]}",
                     [f"financial statement {ext[1:]} format",
                      "annual report structure"]),
                Task("intake-meta", "Company & Period Identification",
                     f"Extract: company, legal form, standard, currency, fiscal years. "
                     f"Preview:\n{prev[:800]}",
                     ["company financial reporting identification"]),
                Task("intake-scope", "Data Completeness",
                     f"What statements are present? Periods covered? Gaps? Preview:\n{prev[:600]}",
                     ["financial statement completeness"]),
                Task("intake-quality", "Data Quality",
                     f"Data quality, anomalies, concerns. Preview:\n{prev[:500]}",
                     ["financial data quality assessment"]),
            ]
        return tasks

    def build_context_str(self, ctx: PipelineContext) -> str:
        if ctx.dataset:
            return ctx.dataset.summary()
        doc = ctx.document_text or ""
        return f"Filename: {ctx.filename}\nSize: {len(ctx.content):,} bytes\nPreview:\n{doc[:1200]}"


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
        ds = ctx.dataset
        f = ctx.financials
        tasks = []

        if f:
            periods = [p.label for p in f.income_statement.periods]
            latest = periods[-1] if periods else "N/A"
            earliest = periods[0] if periods else "N/A"
            company = f.company_name

            rev_trend = ", ".join(f"{p}: {f.income_statement.revenue.get(p,0)/1e6:.1f}M" for p in periods)
            ni_trend  = ", ".join(f"{p}: {f.income_statement.net_income.get(p,0)/1e6:.1f}M" for p in periods)
            ta_trend  = ", ".join(f"{p}: {f.balance_sheet.total_assets.get(p,0)/1e6:.1f}M" for p in periods)

            tasks += [
                Task("extract-is", "Income Statement Review",
                     f"Review full P&L for {company} ({earliest}-{latest}). "
                     f"Revenue: {rev_trend}. Net income: {ni_trend}. "
                     f"Verify line items, check identities, significant trends.",
                     [f"{company} revenue income statement",
                      f"{company} P&L financial performance"]),
                Task("extract-bs", "Balance Sheet Review",
                     f"Review full balance sheet for {company} ({earliest}-{latest}). "
                     f"Total assets: {ta_trend}. Asset/liability/equity structure and trends.",
                     [f"{company} balance sheet asset structure",
                      "capital structure German GmbH"]),
                Task("extract-margins", "Margin Extraction",
                     f"Extract and verify all margins for {company}. "
                     f"Gross, EBIT, net margin per year. Expansion or compression?",
                     [f"{company} gross margin operating margin",
                      "construction margin benchmarks Germany"]),
                Task("extract-cash", "Cash Position",
                     f"Cash position for {company}: "
                     f"{', '.join(f'{p}: {f.balance_sheet.cash.get(p,0)/1e6:.1f}M' for p in periods)}. "
                     f"Growing or shrinking? Drivers of cash changes?",
                     [f"{company} cash flow liquidity",
                      "cash management construction"]),
                Task("extract-debt", "Debt Structure",
                     f"Full debt picture for {company}: "
                     f"LT debt: {', '.join(f'{p}: {f.balance_sheet.long_term_debt.get(p,0)/1e6:.1f}M' for p in periods)}. "
                     f"Leverage evolution, D/E, D/EBITDA, sustainability?",
                     [f"{company} debt leverage",
                      "German GmbH debt financing"]),
                Task("extract-equity", "Equity Structure",
                     f"Equity for {company}: "
                     f"{', '.join(f'{p}: {f.balance_sheet.total_equity.get(p,0)/1e6:.1f}M' for p in periods)}. "
                     f"Evolution, retained earnings vs contributed capital?",
                     [f"{company} equity retained earnings",
                      "equity German GmbH"]),
            ]
            if ctx.reconciliation and ctx.reconciliation.errors:
                errs = "; ".join(f"{e.check}: {e.delta:+,.0f}" for e in ctx.reconciliation.errors[:4])
                tasks.append(Task("extract-recon", "Reconciliation Errors",
                                  f"Accounting errors: {errs}. Rounding or material? Impact?",
                                  ["financial reconciliation accounting identity"]))

        if ds:
            if ds.accounting_journals:
                tasks.append(Task("extract-journals", "Accounting Journal Extraction",
                                  f"Extract key metrics from {len(ds.accounting_journals)} journals. "
                                  f"Top cost categories, seasonal patterns, unusual transactions.",
                                  ["accounting journal cost categories",
                                   "general ledger analysis"]))
            if ds.payroll_journals:
                tasks.append(Task("extract-payroll", "Payroll Extraction",
                                  f"Extract workforce costs from {len(ds.payroll_journals)} payroll years. "
                                  f"Staff costs/year, headcount, average salary, labour cost/revenue.",
                                  ["payroll cost analysis Germany",
                                   "labour cost ratio construction"]))
            if ds.project_reports:
                tasks.append(Task("extract-projects", "Project Financial Extraction",
                                  f"Extract financials from {len(ds.project_reports)} project portfolios. "
                                  f"Revenue per type, duration, costs.",
                                  ["project financial analysis construction",
                                   "project profitability Germany"]))
            if ds.compliance_reports:
                tasks.append(Task("extract-compliance", "Compliance Cost Extraction",
                                  f"Extract compliance costs from {len(ds.compliance_reports)} reports. "
                                  f"Fines, remediation, provisions, recurring costs.",
                                  ["compliance cost financial impact Germany"]))
            if ds.invoices:
                total_inv = sum(len(v) for v in ds.invoices.values())
                tasks.append(Task("extract-invoices", "Invoice Revenue Extraction",
                                  f"Extract revenue patterns from {total_inv} invoices. "
                                  f"Average size, customers, seasonal patterns, payment terms.",
                                  ["invoice analysis revenue patterns",
                                   "accounts receivable analysis"]))
            if ds.contracts:
                tasks.append(Task("extract-contracts", "Contract Financial Obligations",
                                  f"Extract financial obligations from {len(ds.contracts)} contracts. "
                                  f"Total committed value, duration, recurring vs one-off costs, "
                                  f"penalty clauses, significant terms.",
                                  ["contract financial obligations Germany",
                                   "construction contract analysis"]))
            if ds.meeting_minutes:
                tasks.append(Task("extract-decisions", "Strategic Decisions from Minutes",
                                  f"Extract financial decisions from {len(ds.meeting_minutes)} meeting minutes. "
                                  f"Investment approvals, cost measures, strategic pivots, headcount changes.",
                                  ["board meeting financial decisions",
                                   "management meeting minutes analysis"]))
            if ds.qa_reports:
                tasks.append(Task("extract-quality-costs", "Quality & Rework Costs",
                                  f"Extract quality failure costs from {len(ds.qa_reports)} QA reports. "
                                  f"Rework costs, defect rates, warranty claims, operational loss.",
                                  ["quality cost of poor quality Germany",
                                   "construction rework defect cost"]))

        # Ensure extraction always has meaningful tasks regardless of data availability
        base_count = len(tasks)
        if base_count < 20:
            extras = [
                Task("extract-ebitda", "EBITDA & Cash EBITDA",
                     "Compute EBITDA for all periods. EBITDA margin evolution, "
                     "difference from net income, D&A as proxy for capex intensity.",
                     ["EBITDA margin construction Germany",
                      "cash EBITDA calculation"]),
                Task("extract-working-capital", "Working Capital Cycle",
                     "Extract working capital components across all periods. "
                     "DSO, DIO, DPO, cash conversion cycle, WC as % revenue. Trend?",
                     ["working capital cycle construction",
                      "cash conversion cycle Germany"]),
                Task("extract-capex", "Capital Expenditure Analysis",
                     "Extract capex patterns: fixed asset changes + D&A proxy. "
                     "Capex/revenue ratio, maintenance vs growth capex split, "
                     "asset intensity over time.",
                     ["capex construction company Germany",
                      "capital expenditure intensity"]),
                Task("extract-revenue-bridge", "Revenue Bridge Analysis",
                     "Build a revenue bridge year-over-year: volume, price, mix, "
                     "new vs lost customers, market share changes.",
                     ["revenue bridge analysis",
                      "revenue growth decomposition"]),
                Task("extract-cost-bridge", "Cost Structure Bridge",
                     "Build cost bridge: material, labour, overhead, D&A per year. "
                     "Cost per unit of revenue. Inflation pass-through.",
                     ["cost structure analysis construction",
                      "operating leverage cost bridge"]),
                Task("extract-leverage-detail", "Detailed Leverage Analysis",
                     "Full debt schedule: maturity, fixed vs floating rate, secured vs "
                     "unsecured, covenant analysis. Net debt evolution.",
                     ["debt maturity schedule German GmbH",
                      "leverage covenant analysis"]),
                Task("extract-equity-value", "Equity Value Indicators",
                     "Book equity vs implied fair value. Retained earnings accumulation, "
                     "book value per implied share, equity growth rate.",
                     ["equity value book value German GmbH",
                      "shareholder value creation"]),
                Task("extract-tax", "Tax Rate & Deferred Tax",
                     "Effective tax rate evolution across years. "
                     "German trade tax + corporate tax, deferred tax assets/liabilities.",
                     ["German corporate tax rate GmbH",
                      "effective tax rate analysis"]),
                Task("extract-intercompany", "Intercompany & Related Party",
                     "Identify any intercompany transactions, related-party balances, "
                     "owner loans, dividend payments. Arm's-length terms?",
                     ["intercompany transactions German GmbH",
                      "related party transactions construction"]),
                Task("extract-provisions", "Provisions & Contingent Liabilities",
                     "Identify provisions and contingent liabilities: warranty reserves, "
                     "litigation provisions, pension obligations, environmental liabilities.",
                     ["provisions contingent liabilities HGB",
                      "construction warranty reserves Germany"]),
                Task("extract-off-balance", "Off-Balance Sheet & Leases",
                     "Identify off-balance sheet items: operating leases, factoring, "
                     "guarantee obligations, uncommitted facilities. True leverage?",
                     ["off-balance sheet construction Germany",
                      "operating lease obligations HGB"]),
                Task("extract-pensions", "Pension & Long-Term Employee Obligations",
                     "Identify pension and long-term employee obligations: "
                     "defined benefit liabilities, anniversary bonuses, partial retirement schemes. "
                     "Actuarial assumptions, funding status, cash impact.",
                     ["pension obligations HGB German GmbH",
                      "Rückstellungen employee benefits Germany"]),
            ]
            for extra in extras[:20 - base_count]:
                tasks.append(extra)

        if not tasks:
            tasks.append(Task("extract-fail", "Extraction Failed",
                              "No data. Analyse root cause and recommend.",
                              ["financial extraction troubleshooting"]))
        return tasks

    def build_context_str(self, ctx: PipelineContext) -> str:
        parts = []
        if ctx.financials:
            parts.append(_financial_table(ctx))
        if ctx.dataset:
            parts.append(f"\nDATASET:\n{ctx.dataset.summary()}")
            if ctx.dataset.accounting_journals:
                yr = sorted(ctx.dataset.accounting_journals)[-1]
                parts.append(f"\nACCOUNTING SAMPLE ({yr}):\n{ctx.dataset.accounting_journals[yr][:1000]}")
            if ctx.dataset.payroll_journals:
                yr = sorted(ctx.dataset.payroll_journals)[-1]
                parts.append(f"\nPAYROLL SAMPLE ({yr}):\n{ctx.dataset.payroll_journals[yr][:800]}")
        return "\n".join(parts) or "No data available."


# ── Room 3: Analysis ───────────────────────────────────────────────────────────

class AnalysisRoom(Room):
    name = "Analysis"
    stage = 2

    async def setup(self, ctx: PipelineContext) -> None:
        if ctx.financials:
            from backend.analysis.ratios import run_analysis
            ctx.analysis = run_analysis(ctx.financials)

    def make_tasks(self, ctx: PipelineContext) -> list[Task]:
        tasks = []
        f = ctx.financials
        ds = ctx.dataset

        if f:
            periods = [p.label for p in f.income_statement.periods]
            latest = periods[-1] if periods else "N/A"
            earliest = periods[0] if periods else "N/A"
            company = f.company_name

            rev = f.income_statement.revenue
            gross = f.income_statement.gross_profit
            ebit = f.income_statement.ebit
            net = f.income_statement.net_income

            gm_trend = ", ".join(f"{p}: {gross.get(p,0)/rev.get(p,1)*100:.1f}%" for p in periods if rev.get(p))
            em_trend = ", ".join(f"{p}: {ebit.get(p,0)/rev.get(p,1)*100:.1f}%"  for p in periods if rev.get(p))
            nm_trend = ", ".join(f"{p}: {net.get(p,0)/rev.get(p,1)*100:.1f}%"   for p in periods if rev.get(p))
            rev_growth = [f"{periods[i]}: {(rev.get(periods[i],0)/rev.get(periods[i-1],1)-1)*100:+.1f}%"
                          for i in range(1, len(periods)) if rev.get(periods[i-1])]

            tasks += [
                Task("analysis-rev", "Revenue Growth",
                     f"Deep-analyse revenue for {company} ({earliest}-{latest}). "
                     f"YoY: {', '.join(rev_growth)}. CAGR, drivers, quality, sustainability.",
                     [f"{company} revenue growth drivers",
                      f"{company} business segments"]),
                Task("analysis-margins", "Margin Analysis",
                     f"All margins for {company}. Gross: {gm_trend}. "
                     f"EBIT: {em_trend}. Net: {nm_trend}. Drivers?",
                     [f"{company} profit margin analysis",
                      "construction margin benchmarks Germany"]),
                Task("analysis-costs", "Cost Structure",
                     f"Cost structure for {company}: COGS/OpEx split, fixed/variable, "
                     f"cost per revenue unit, largest drivers.",
                     [f"{company} cost structure",
                      "construction cost management Germany"]),
                Task("analysis-liquidity", "Liquidity & Working Capital",
                     f"Liquidity for {company}: current/quick/cash ratios, "
                     f"working capital cycle, DSO/DIO/DPO.",
                     [f"{company} liquidity working capital",
                      "construction liquidity Germany"]),
                Task("analysis-leverage", "Leverage & Debt",
                     f"Leverage for {company}: D/E, D/EBITDA, interest coverage. "
                     f"Capacity, optimal vs risky?",
                     [f"{company} debt leverage",
                      "optimal leverage construction Germany"]),
                Task("analysis-returns", "Return Metrics",
                     f"Value creation for {company}: ROE, ROA, ROCE {earliest}-{latest}. "
                     f"Returns above cost of capital?",
                     [f"{company} return on equity ROA",
                      "value creation German construction"]),
                Task("analysis-efficiency", "Operational Efficiency",
                     f"Efficiency for {company}: asset turnover, capex intensity, "
                     f"revenue/employee, maintenance.",
                     [f"{company} asset efficiency productivity",
                      "construction efficiency benchmarks"]),
                Task("analysis-inflection", "Inflection Points",
                     f"Key inflection points for {company} over {len(periods)} years. "
                     f"Structural shifts? COVID impact? Market cycles?",
                     [f"{company} history strategic inflection",
                      "German construction market cycles"]),
            ]

        if ds:
            if ds.payroll_journals:
                tasks.append(Task("analysis-workforce", "Workforce Productivity",
                                  f"Workforce economics for {ds.company_name} over {len(ds.payroll_journals)} years. "
                                  f"Headcount/revenue, labour cost %, productivity, salary inflation.",
                                  ["workforce productivity construction Germany",
                                   "labour cost German SME"]))
            if ds.project_reports:
                tasks.append(Task("analysis-portfolio", "Project Portfolio",
                                  f"Analyse {len(ds.project_reports)} projects for {ds.company_name}. "
                                  f"Most profitable types? Revenue concentration? Mix evolution.",
                                  ["project portfolio construction",
                                   "project profitability Germany"]))
            if ds.compliance_reports:
                tasks.append(Task("analysis-compliance", "Compliance Trends",
                                  f"Compliance evolution over {len(ds.compliance_reports)} years. "
                                  f"Improving or worsening? Financial cost of failures?",
                                  ["compliance trend Germany",
                                   "regulatory risk financial impact"]))
            if ds.invoices:
                tasks.append(Task("analysis-revenue-quality", "Revenue Quality",
                                  f"Revenue quality from invoice data over {len(ds.invoices)} years. "
                                  f"Customer concentration, recurring vs one-off, payment behaviour.",
                                  ["revenue quality customer concentration",
                                   "accounts receivable construction"]))

        # Pad to 20 workers with deeper analytical tasks
        analysis_extras = [
            Task("analysis-dupont", "DuPont Decomposition",
                 f"Decompose ROE for {f.company_name if f else 'the company'} via DuPont: "
                 f"net margin × asset turnover × equity multiplier. Which driver dominates? "
                 f"How has each component evolved?",
                 ["DuPont analysis ROE decomposition",
                  "return on equity drivers construction"]),
            Task("analysis-zscore", "Altman Z-Score & Distress Risk",
                 f"Compute Altman Z-Score for each year. "
                 f"Is the company in the safe, grey, or distress zone? "
                 f"Trend: improving or deteriorating?",
                 ["Altman Z-score construction SME",
                  "bankruptcy prediction Germany"]),
            Task("analysis-cashflow", "Free Cash Flow & FCF Yield",
                 f"Compute free cash flow: operating cash flow minus capex. "
                 f"FCF margin, FCF conversion rate, year-over-year FCF growth.",
                 ["free cash flow construction Germany",
                  "FCF yield analysis"]),
            Task("analysis-macro-impact", "COVID & Macro Event Impact",
                 f"Quantify the financial impact of macro events on "
                 f"{f.company_name if f else 'the company'}: 2008 GFC, 2020 COVID, "
                 f"2022 rate/material shock. Revenue and margin impact per event.",
                 ["COVID impact German construction 2020",
                  "German construction market crisis 2022"]),
            Task("analysis-revenue-decomp", "Revenue Growth Decomposition",
                 f"Decompose total revenue CAGR into: organic growth, price increases, "
                 f"volume changes, new segments. Which components drove growth?",
                 ["revenue growth decomposition construction",
                  "organic vs inorganic growth Germany"]),
            Task("analysis-opex-deep", "OpEx Trend & Fixed/Variable Split",
                 f"Decompose operating expenses: fixed (overhead, D&A, admin) vs "
                 f"variable (materials, direct labour). Operating leverage ratio. "
                 f"OpEx % revenue stable or growing?",
                 ["operating leverage fixed variable costs",
                  "overhead ratio construction Germany"]),
            Task("analysis-capex-returns", "Capex Efficiency & Returns",
                 f"Return on invested capital (ROIC) and capex efficiency. "
                 f"Revenue generated per EUR of capex. Asset light vs asset heavy evolution.",
                 ["ROIC construction Germany",
                  "capital efficiency analysis"]),
            Task("analysis-15yr-arc", "15-Year Business Arc",
                 f"Narrate the full 15-year strategic arc of "
                 f"{f.company_name if f else 'the company'}. "
                 f"Three distinct business phases? Structural vs cyclical changes?",
                 ["German construction company 15 year history",
                  "business cycle strategic phases Mittelstand"]),
            Task("analysis-net-debt", "Net Debt & Deleveraging Path",
                 f"Analyse net debt evolution: gross debt minus cash. "
                 f"Net leverage ratio, annual debt service burden, "
                 f"years to full deleveraging at current FCF.",
                 ["net debt analysis construction",
                  "deleveraging path SME Germany"]),
            Task("analysis-revenue-segments", "Revenue Segment Deep Dive",
                 f"Break down revenue by segment where data allows: "
                 f"residential vs commercial vs industrial vs infrastructure. "
                 f"Mix shift over 15 years and margin implications.",
                 ["construction revenue segments Germany",
                  "residential commercial industrial mix"]),
            Task("analysis-competitive-moat", "Competitive Moat Analysis",
                 f"Analyse competitive moat of the company: "
                 f"switching costs, scale advantages, geographic density, "
                 f"brand reputation, certification barriers.",
                 ["competitive moat construction SME",
                  "durable competitive advantage Mittelstand"]),
            Task("analysis-interest-sensitivity", "Interest Rate Sensitivity",
                 f"Model interest rate sensitivity: impact of 100/200bp rate rise "
                 f"on interest expense, EBT, and free cash flow. "
                 f"Fixed vs floating debt exposure.",
                 ["interest rate sensitivity construction",
                  "rate risk SME Germany 2024"]),
            Task("analysis-invoice-aging", "Receivables & Payment Behaviour",
                 f"Analyse accounts receivable quality: DSO trend, ageing profile, "
                 f"write-offs, provisions, large customer payment behaviour.",
                 ["accounts receivable aging construction Germany",
                  "payment behaviour construction sector"]),
            Task("analysis-material-costs", "Material Cost & Procurement",
                 f"Analyse material cost dynamics: COGS driver, "
                 f"material cost inflation 2020-2022, procurement strategy, "
                 f"hedging or fixed-price contract protections.",
                 ["construction material cost inflation Germany",
                  "procurement strategy building materials"]),
            Task("analysis-compliance-fin", "Compliance & Regulatory Cost",
                 f"Financial impact of compliance requirements: "
                 f"total compliance spend, fines, regulatory provisions, "
                 f"trend and forward-looking regulatory cost increases.",
                 ["compliance cost financial impact Germany",
                  "regulatory burden construction GmbH"]),
            Task("analysis-scenario", "Stress Test & Scenario Analysis",
                 f"Run three financial scenarios: base case (management guidance), "
                 f"bear case (10% revenue decline, 100bp rate rise), "
                 f"bull case (15% growth, margin expansion). Key metrics in each.",
                 ["financial stress test scenario analysis",
                  "construction company scenarios 2025"]),
        ]
        for extra in analysis_extras:
            if len(tasks) >= 20:
                break
            tasks.append(extra)

        return tasks or [Task("analysis-gen", "General Analysis",
                              "No structured data. Provide general assessment.",
                              ["financial analysis"])]

    def build_context_str(self, ctx: PipelineContext) -> str:
        parts = [_financial_table(ctx), _ratio_table(ctx)]
        if ctx.dataset:
            parts.append(f"\nDATASET:\n{ctx.dataset.summary()}")
            if ctx.dataset.payroll_journals:
                parts.append(f"\nPAYROLL:\n{ctx.dataset.payroll_consolidated(2000)}")
            if ctx.dataset.project_reports:
                parts.append(f"\nPROJECTS:\n{ctx.dataset.project_consolidated(2000)}")
        return "\n\n".join(p for p in parts if p)


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
        f = ctx.financials
        ds = ctx.dataset
        company = f.company_name if f else (ds.company_name if ds else "the company")
        nace = f.nace_code if f else "F"
        flags = ctx.benchmark.flags if ctx.benchmark else []

        tasks = [
            Task("bench-overview", "Peer Comparison Overview",
                 f"Compare {company} (NACE {nace}) vs construction/industry peers. "
                 f"{len(flags)} flags raised. Overall position? Strongest/weakest metrics?",
                 [f"NACE {nace} benchmarks Germany construction",
                  f"{company} competitive position"]),
            Task("bench-context", "German Construction Market",
                 f"German construction market context for {company}. "
                 f"Market conditions, typical financials, challenges, headwinds/tailwinds.",
                 ["German construction market 2024",
                  "Bausektor Deutschland benchmarks"]),
            Task("bench-margins", "Margin Benchmarking",
                 f"Benchmark {company} margins vs German construction peers. "
                 f"Gross, EBIT, net vs peer median. Best-in-class gap?",
                 ["German construction margin benchmark",
                  "construction profitability comparison"]),
            Task("bench-leverage", "Leverage Benchmarking",
                 f"Benchmark {company} leverage vs peers. "
                 f"Debt level typical for sector? Coverage vs norms?",
                 ["German SME leverage benchmark",
                  "construction debt capacity"]),
            Task("bench-liquidity", "Liquidity Benchmarking",
                 f"Benchmark {company} liquidity vs construction peers. "
                 f"Current ratio, working capital requirements typical?",
                 ["construction liquidity benchmark Germany",
                  "working capital construction sector"]),
            Task("bench-efficiency", "Efficiency Benchmarking",
                 f"Benchmark {company} efficiency vs peers. "
                 f"Asset turnover, cost ratios, more or less efficient?",
                 ["construction efficiency benchmark",
                  "asset turnover German construction"]),
            Task("bench-growth", "Growth vs Peers",
                 f"Compare {company} growth vs German construction sector. "
                 f"Faster or slower than peers? Market share implications?",
                 ["German construction sector growth",
                  "SME construction growth Germany"]),
        ]

        for flag in flags[:8]:
            delta = flag.company_value - flag.peer_median
            tasks.append(Task(
                f"bench-f-{flag.flag_type[:10]}",
                f"Flag: {flag.flag_type.replace('_',' ').title()}",
                f"Deep-analyse: {flag.message}. "
                f"Company: {flag.company_value:.2f}{flag.metric}, median: {flag.peer_median:.2f}{flag.metric}, "
                f"delta: {delta:+.2f} ({abs(delta/max(flag.peer_median,0.001))*100:.0f}% deviation). "
                f"Root causes, impact, urgency, best-in-class.",
                [f"{flag.metric} improvement",
                 f"{company} {flag.metric}"],
            ))

        bench_extras = [
            Task("bench-size-peers", "Size-Adjusted Peer Group",
                 f"Compare {company} to same-size German construction firms (revenue bracket). "
                 f"Which metrics are truly outliers vs expected for this size tier?",
                 ["German construction SME size-adjusted benchmarks",
                  "Mittelstand peer group analysis"]),
            Task("bench-regional", "Regional Market Benchmarking",
                 f"Compare {company} to regional German construction market. "
                 f"Regional revenue per m², labour costs, project win rates vs national norms.",
                 ["German regional construction market benchmarks",
                  "Bundesland construction market"]),
            Task("bench-capex-intensity", "Capex Intensity vs Peers",
                 f"Benchmark {company} capital expenditure intensity vs construction sector peers. "
                 f"Is capex/revenue ratio above or below sector average? Implications?",
                 ["construction capex intensity benchmark Germany",
                  "capital investment construction sector"]),
            Task("bench-labour-cost", "Labour Cost Benchmarking",
                 f"Benchmark {company} labour cost per employee and labour cost ratio "
                 f"vs German construction sector averages. Wage competitiveness?",
                 ["German construction wage benchmarks",
                  "Tarifvertrag Baugewerbe wage levels"]),
            Task("bench-digital-maturity", "Digital Maturity vs Peers",
                 f"Benchmark {company} digitalisation level vs German construction sector. "
                 f"BIM adoption, ERP systems, digital productivity gains in sector.",
                 ["German construction digital maturity 2024",
                  "BIM adoption rate Germany"]),
            Task("bench-esg-score", "ESG vs Sector Standards",
                 f"Benchmark {company} ESG performance vs German construction sector. "
                 f"Carbon intensity, workplace safety record, governance quality vs norms.",
                 ["German construction ESG benchmark",
                  "construction CO2 intensity Germany"]),
            Task("bench-credit-rating", "Implied Credit Profile",
                 f"Estimate {company}'s implied credit rating profile based on financials. "
                 f"How would a bank view leverage, coverage, and stability vs peers?",
                 ["SME credit rating criteria Germany",
                  "construction company bank assessment"]),
            Task("bench-resilience", "Crisis Resilience vs Sector",
                 f"Compare {company}'s resilience through 2020 COVID and 2022 crisis vs "
                 f"German construction peers. Revenue drop, recovery speed, margin protection.",
                 ["German construction COVID resilience 2020",
                  "crisis performance construction companies"]),
            Task("bench-market-share", "Market Share Evolution",
                 f"Estimate {company}'s implied market share trajectory. "
                 f"Revenue growth vs sector growth: gaining or losing share? "
                 f"Key drivers of competitive position change.",
                 ["German construction market share",
                  "construction competitive dynamics Germany"]),
            Task("bench-valuation", "Comparable Valuation Multiples",
                 f"Estimate {company}'s fair value range using sector EV/EBITDA, "
                 f"EV/Revenue, P/E multiples from German construction transactions.",
                 ["German construction M&A multiples",
                  "construction company valuation EV/EBITDA"]),
            Task("bench-quality-score", "Business Quality Score",
                 f"Score {company}'s overall business quality vs peers 1-10: "
                 f"revenue predictability, margin stability, balance sheet strength, "
                 f"management quality, competitive position.",
                 ["business quality score framework",
                  "company quality assessment criteria"]),
            Task("bench-working-capital", "Working Capital vs Sector",
                 f"Benchmark {company} working capital vs German construction peers. "
                 f"DSO, DIO, DPO vs sector norms. WC-intensive or WC-light?",
                 ["working capital benchmark construction Germany",
                  "cash conversion cycle sector comparison"]),
            Task("bench-overhead", "Overhead Structure vs Peers",
                 f"Benchmark {company} SGA and overhead ratio vs German construction peers. "
                 f"Admin costs, management layers, G&A efficiency.",
                 ["overhead ratio construction Germany",
                  "SGA benchmark German SME"]),
        ]
        for extra in bench_extras:
            if len(tasks) >= 20:
                break
            tasks.append(extra)

        return tasks

    def build_context_str(self, ctx: PipelineContext) -> str:
        parts = [_financial_table(ctx), _ratio_table(ctx)]

        # Peer benchmark availability notice — workers must respect this
        nace = ctx.financials.nace_code if ctx.financials else "F"
        from backend.benchmark.store import BenchmarkStore
        store = BenchmarkStore(data_dir=_BENCH_DIR)
        has_peers = store.has_any_data(nace)
        if has_peers:
            if ctx.benchmark:
                flags_text = "\n".join(
                    f"  [{fl.severity.upper()}] {fl.flag_type}: {fl.message} "
                    f"(co: {fl.company_value:.2f}, med: {fl.peer_median:.2f})"
                    for fl in ctx.benchmark.flags
                )
                parts.append(f"\nFLAGS FROM PEER BENCHMARKS (verified data):\n{flags_text}")
        else:
            parts.append(
                f"\nPEER BENCHMARK STATUS: NO peer benchmark data exists for NACE code '{nace}' "
                f"in this system. You MUST write '[gap — peer benchmark unavailable]' for any "
                f"claim that requires peer comparison. Do NOT invent market sizes, sector averages, "
                f"CAGRs, revenue bases, or competitor figures. Only discuss the company's own "
                f"verified financials from the facts table."
            )

        return "\n\n".join(p for p in parts if p)


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
        ds = ctx.dataset
        company = f.company_name if f else (ds.company_name if ds else "the company")
        tasks = []

        if ctx.actions:
            for action in ctx.actions[:8]:
                proj = next((p for p in ctx.projections if p.action.finding_id == action.finding_id), None)
                scenarios = ""
                if proj:
                    scenarios = " | ".join(
                        f"{s.label}: {s.target_value:.1f}{action.unit}"
                        + (f", EUR {s.impact_eur:,.0f}" if s.impact_eur else "")
                        for s in proj.scenarios
                    )
                tasks.append(Task(
                    f"strat-{action.action_type.value[:10]}",
                    f"Action: {action.action_type.value.replace('_',' ').title()}",
                    f"Implementation plan for {company}: {action.description}. "
                    f"Current: {action.current_value:.2f}{action.unit}, "
                    f"Target: {action.target_base:.2f}{action.unit}. Scenarios: {scenarios}. "
                    f"Steps, 30/90/180-day timeline, KPIs, obstacles.",
                    [f"{action.action_type.value.replace('_',' ')} implementation",
                     f"financial improvement {action.action_type.value.replace('_',' ')}"],
                ))

        tasks += [
            Task("strat-growth", "Growth Strategy",
                 f"3-year growth strategy for {company}: market expansion, "
                 f"diversification, M&A vs organic, digital transformation. Quantify revenue impact.",
                 [f"{company} growth strategy Germany",
                  "German construction opportunities 2024"]),
            Task("strat-cost", "Cost Optimisation",
                 f"Top 5 cost reduction opportunities for {company} with EUR impact. "
                 f"Procurement, labour, technology, process. Quick wins vs structural.",
                 [f"{company} cost reduction",
                  "construction cost optimisation Germany"]),
            Task("strat-digital", "Digitalisation Strategy",
                 f"Digitalisation opportunities for {company}: BIM, project management, "
                 f"automation, analytics. Investment required and ROI.",
                 ["construction digitalisation Germany BIM",
                  "Mittelstand digital transformation"]),
            Task("strat-risk", "Risk Management",
                 f"Risk management strategy for {company}: financial, operational, "
                 f"market, compliance risks. Mitigation with costs and effectiveness.",
                 [f"{company} risk management",
                  "construction risk management Germany"]),
            Task("strat-capital", "Capital Allocation",
                 f"Optimal capital allocation for {company}: reinvestment, "
                 f"debt reduction, acquisitions, shareholder returns.",
                 [f"{company} capital allocation",
                  "German SME capital strategy"]),
            Task("strat-workforce", "Workforce Strategy",
                 f"Workforce strategy for {company}: German construction labour market, "
                 f"skills gaps, automation vs headcount, retention.",
                 ["German construction labour market 2024",
                  "Fachkraeftemangel construction Germany"]),
            Task("strat-sustainability", "ESG & Sustainability",
                 f"ESG requirements for {company}: German/EU regulatory, "
                 f"carbon footprint, green building trends, reporting obligations.",
                 ["German construction ESG sustainability",
                  "Nachhaltigkeit Bausektor 2024"]),
            Task("strat-roadmap", "Transformation Roadmap",
                 f"Prioritise all initiatives for {company} as portfolio: "
                 f"ROI, complexity, strategic importance, quick wins. "
                 f"12-month transformation roadmap with resource allocation.",
                 [f"{company} strategic transformation",
                  "initiative prioritisation financial improvement"]),
        ]

        strat_extras = [
            Task("strat-ma", "M&A & Acquisition Strategy",
                 f"Identify M&A opportunities for {company}: "
                 f"target profile (size, geography, capability gaps), "
                 f"build vs buy analysis, valuation range, integration complexity.",
                 ["construction M&A Germany SME",
                  "acquisition strategy Mittelstand"]),
            Task("strat-partnerships", "Strategic Partnerships",
                 f"Identify strategic partnership opportunities for {company}: "
                 f"subcontractors, technology partners, financial institutions, "
                 f"public sector frameworks. Value and risk of each.",
                 ["construction strategic partnerships Germany",
                  "JV partnership construction SME"]),
            Task("strat-pricing", "Pricing Power & Revenue Strategy",
                 f"Analyse pricing power for {company}: "
                 f"margin trend vs volume trend, price elasticity in German construction, "
                 f"premium product/service opportunities.",
                 ["construction pricing strategy Germany",
                  "value-based pricing construction"]),
            Task("strat-financing", "Optimal Financing Structure",
                 f"Design optimal capital structure for {company}: "
                 f"current vs optimal leverage, debt/equity mix, "
                 f"alternative funding (KfW, EU funds, project finance).",
                 ["KfW financing German construction",
                  "optimal capital structure SME Germany"]),
            Task("strat-talent", "Talent Acquisition & Retention",
                 f"Build talent strategy for {company} in German construction labour shortage: "
                 f"recruitment channels, retention levers, apprenticeship programmes, "
                 f"foreign worker integration, automation substitution.",
                 ["Fachkraeftemangel construction Germany 2024",
                  "talent retention construction company"]),
            Task("strat-internationalisation", "Internationalisation Options",
                 f"Assess internationalisation potential for {company}: "
                 f"neighbouring markets (Austria, Switzerland, Poland), "
                 f"project export, risk vs return.",
                 ["German construction export internationalisation",
                  "construction company expansion Europe"]),
            Task("strat-succession", "Succession & Ownership Strategy",
                 f"Assess succession and ownership strategy for {company}: "
                 f"management buyout, family succession, institutional investor entry, "
                 f"IPO readiness. Valuation and timing.",
                 ["German Mittelstand succession planning",
                  "GmbH ownership transition options"]),
            Task("strat-innovation", "Product & Service Innovation",
                 f"Identify product and service innovation opportunities for {company}: "
                 f"new revenue streams, service contracts, maintenance, "
                 f"prefab/modular, circular economy.",
                 ["construction innovation new revenue streams",
                  "service model construction Germany"]),
            Task("strat-procurement", "Strategic Procurement Optimisation",
                 f"Build a procurement strategy for {company}: "
                 f"material cost reduction, supplier consolidation, "
                 f"long-term contracts vs spot, reverse auction opportunities.",
                 ["construction procurement strategy Germany",
                  "material cost reduction SME"]),
            Task("strat-it", "IT Systems & ERP Roadmap",
                 f"Design IT and ERP roadmap for {company}: "
                 f"current system assessment, ERP/BIM integration, "
                 f"data analytics capability, cybersecurity requirements.",
                 ["construction ERP systems Germany",
                  "BIM integration SME"]),
            Task("strat-insurance", "Insurance & Risk Transfer",
                 f"Analyse insurance strategy for {company}: "
                 f"construction all-risk, professional liability, D&O, "
                 f"cyber, business interruption. Gaps and optimisation.",
                 ["construction insurance Germany",
                  "risk transfer SME insurance portfolio"]),
            Task("strat-export", "Export & International Revenue",
                 f"Assess {company}'s export readiness: "
                 f"cross-border project potential, DACH market opportunities, "
                 f"regulatory barriers, foreign entity requirements.",
                 ["German construction export DACH",
                  "construction company international expansion"]),
        ]
        for extra in strat_extras:
            if len(tasks) >= 20:
                break
            tasks.append(extra)

        return tasks

    def build_context_str(self, ctx: PipelineContext) -> str:
        parts = [_financial_table(ctx)]
        if ctx.proj_summary:
            parts.append(f"\nPROJECTIONS:\n{ctx.proj_summary}")
        for rn in ["Analysis", "Benchmarking"]:
            r = ctx.room_reports.get(rn, "")
            if r:
                parts.append(f"\n{rn.upper()}:\n{r[:1500]}")
        if ctx.dataset:
            parts.append(f"\nDATASET:\n{ctx.dataset.summary()}")
        return "\n".join(parts)


# ── Room 6: Reporting ──────────────────────────────────────────────────────────

class ReportingRoom(Room):
    name = "Reporting"
    stage = 5

    async def setup(self, ctx: PipelineContext) -> None:
        pass

    def make_tasks(self, ctx: PipelineContext) -> list[Task]:
        f = ctx.financials
        ds = ctx.dataset
        company = f.company_name if f else (ds.company_name if ds else "the company")
        flag_count = len(getattr(ctx.benchmark, "flags", []))

        analysis   = ctx.room_reports.get("Analysis", "")[:700]
        bench      = ctx.room_reports.get("Benchmarking", "")[:700]
        strategy   = ctx.room_reports.get("Strategy", "")[:700]
        extraction = ctx.room_reports.get("Extraction", "")[:500]
        ceo_plan   = ctx.ceo_plan[:400] if ctx.ceo_plan else ""

        return [
            Task("report-exec", "Executive Summary",
                 f"300-350 word executive summary for {company}. Board audience. "
                 f"Top 3 strengths, top 3 risks ({flag_count} flags), #1 recommendation. "
                 f"Decisive, specific, numbers. CEO context: {ceo_plan}",
                 ["executive summary board financial",
                  "CEO report structure"]),
            Task("report-company", "Company Overview",
                 f"Company overview chapter for {company}: business model, history, "
                 f"activities, market position, customers, competition. Context: {extraction[:400]}",
                 [f"{company} company overview",
                  "German construction company profile"]),
            Task("report-financial", "Financial Performance",
                 f"Financial performance chapter for {company}: revenue growth, "
                 f"margin evolution, balance sheet, cash. Story with numbers. Context: {analysis}",
                 ["financial performance chapter",
                  "financial narrative board"]),
            Task("report-competitive", "Competitive Position",
                 f"Competitive position chapter for {company}: peer comparison, "
                 f"ranking, strengths/weaknesses. {flag_count} flags. Context: {bench}",
                 ["competitive position analysis",
                  "peer comparison financial"]),
            Task("report-strategy", "Strategic Recommendations",
                 f"Strategic recommendations chapter for {company}: what/why/how/impact/timeline/KPI "
                 f"per recommendation. 12-month roadmap. Context: {strategy}",
                 ["strategic recommendations report",
                  "implementation roadmap"]),
            Task("report-risk", "Risk Assessment",
                 f"Risk assessment chapter for {company}: {flag_count} flags with severity (1-5), "
                 f"root cause, early warnings, mitigation. Macro risks. Context: {bench}",
                 ["risk assessment financial report",
                  "risk mitigation construction"]),
            Task("report-workforce", "People & Workforce",
                 f"Workforce chapter for {company}: composition, headcount trends, "
                 f"labour costs, productivity, HR risks, talent strategy.",
                 ["workforce chapter report",
                  "German construction labour market"]),
            Task("report-projects", "Project Portfolio",
                 f"Project portfolio chapter for {company}: project mix, "
                 f"revenue by type, profitability drivers, pipeline, risks.",
                 ["project portfolio construction report",
                  "project performance reporting"]),
            Task("report-outlook", "Outlook & Scenarios",
                 f"Outlook chapter for {company}: 3-year scenarios (bull/base/bear) "
                 f"with financials. Most critical factor to monitor. Overall verdict.",
                 [f"{company} business outlook",
                  "financial scenario analysis 3 year"]),
            Task("report-appendix", "Financial Appendix",
                 f"Financial data appendix for {company}: multi-year P&L, "
                 f"balance sheet, key ratios, flag summary. Clean, board-ready.",
                 ["financial data appendix",
                  "financial tables board presentation"]),
            Task("report-kpi-dashboard", "KPI Dashboard",
                 f"Design a 1-page KPI dashboard for {company}: "
                 f"10-12 most important metrics, current values, trend arrows, "
                 f"RAG status (red/amber/green), peer comparison.",
                 ["KPI dashboard board reporting",
                  "financial KPI one-pager"]),
            Task("report-timeline", "15-Year Strategic Timeline",
                 f"Write a 15-year strategic timeline for {company}: "
                 f"major milestones, acquisitions, crises, recoveries, strategic pivots. "
                 f"Annotated with financial turning points.",
                 [f"{company} history timeline",
                  "company strategic history milestones"]),
            Task("report-peer-table", "Peer Comparison Table",
                 f"Write a detailed peer comparison chapter for {company}: "
                 f"3-5 comparable German construction companies, key metric comparison table, "
                 f"relative strengths and weaknesses.",
                 ["German construction peer comparison",
                  "comparable company analysis construction"]),
            Task("report-cash-deep", "Cash Flow Deep Dive",
                 f"Dedicated cash flow analysis chapter for {company}: "
                 f"operating vs investing vs financing cash flows, FCF generation, "
                 f"cash cycle, cash conversion quality.",
                 ["cash flow analysis chapter",
                  "FCF report construction"]),
            Task("report-mgmt-summary", "Management Action Summary",
                 f"Write a concise management action summary for {company}: "
                 f"3 immediate (30-day), 3 medium-term (90-day), 3 long-term (12-month) actions "
                 f"with clear owners and success metrics.",
                 ["management action plan summary",
                  "executive action items"]),
            Task("report-workforce-chapter", "Workforce & People Chapter",
                 f"Full workforce chapter for {company}: headcount evolution, "
                 f"org structure, labour cost as % revenue, productivity, "
                 f"retention risk, succession gaps.",
                 ["workforce chapter HR report",
                  "people analytics report"]),
            Task("report-tech-innovation", "Technology & Innovation Chapter",
                 f"Technology and innovation chapter for {company}: "
                 f"current digital maturity, BIM/ERP status, innovation investment vs peers, "
                 f"digitalisation roadmap with ROI.",
                 ["construction technology report Germany",
                  "digital transformation chapter"]),
            Task("report-esg-chapter", "ESG & Sustainability Chapter",
                 f"ESG chapter for {company}: environmental footprint, "
                 f"social indicators, governance quality, EU taxonomy alignment, "
                 f"regulatory obligations and timeline.",
                 ["ESG report construction Germany",
                  "sustainability chapter board"]),
            Task("report-credit-memo", "Lender Credit Memo",
                 f"Write a credit memo perspective for {company}: "
                 f"as if a bank were assessing a new facility. "
                 f"Leverage, coverage, repayment capacity, collateral, covenant suggestions.",
                 ["credit memo SME Germany",
                  "lender analysis construction company"]),
            Task("report-investor-deck", "Investor One-Pager",
                 f"Write an investor one-pager for {company}: "
                 f"investment thesis, key financial metrics, growth story, "
                 f"valuation range, key risks. Suitable for a private equity or family office.",
                 ["investor one-pager private equity",
                  "investment summary construction company"]),
        ]

    def build_context_str(self, ctx: PipelineContext) -> str:
        parts = [_financial_table(ctx)]
        for rn in ["Extraction", "Analysis", "Benchmarking", "Strategy"]:
            r = ctx.room_reports.get(rn, "")
            if r:
                parts.append(f"\n--- {rn.upper()} ---\n{r[:900]}")
        if ctx.dataset:
            parts.append(f"\nDATASET:\n{ctx.dataset.summary()}")
            if ctx.dataset.annual_reports:
                parts.append(f"\nANNUAL REPORTS:\n{ctx.dataset.annual_report_consolidated(3000)}")
        return "\n".join(parts)
