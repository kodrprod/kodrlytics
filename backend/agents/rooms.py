"""6 concrete pipeline rooms."""
from __future__ import annotations
import logging
from pathlib import Path
from backend.agents.models import Task, PipelineContext
from backend.agents.room import Room

log = logging.getLogger(__name__)

_BENCH_DIR = Path(__file__).parent.parent.parent / "data" / "benchmarks"


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
        preview = ctx.document_text[:500] if ctx.document_text else "(no text yet)"
        return [
            Task("intake-fmt", "Document Format Analysis",
                 f"Analyse '{ctx.filename}' (extension: {ext}). "
                 f"Identify: file format, language, document type (annual report / management accounts / etc). "
                 f"Preview: {preview[:300]}",
                 [f"German financial statement {ext[1:]} format structure",
                  "HGB IFRS annual report document structure"]),
            Task("intake-meta", "Company & Period Identification",
                 f"From this document preview, identify: company name, legal form, "
                 f"reporting standard (HGB/IFRS), currency, fiscal year(s) covered. "
                 f"Text: {preview[:500]}",
                 ["German GmbH annual report company information",
                  "HGB fiscal year reporting requirements Germany"]),
        ]

    def build_context_str(self, ctx: PipelineContext) -> str:
        return (f"Filename: {ctx.filename}\n"
                f"Document length: {len(ctx.document_text):,} chars\n"
                f"Preview:\n{ctx.document_text[:600]}")


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
                         "Document extraction failed. Analyse why and recommend solutions.",
                         ["financial statement extraction troubleshooting"])]
        f = ctx.financials
        periods = f.income_statement.periods
        latest = periods[-1] if periods else "N/A"
        rev = f.income_statement.revenue.get(latest, 0)
        ebit = f.income_statement.ebit.get(latest, 0)
        ta = f.balance_sheet.total_assets.get(latest, 0)
        te = f.balance_sheet.total_equity.get(latest, 0)

        tasks = [
            Task("extract-is", "Income Statement Review",
                 f"Review income statement for {f.company_name} ({latest}): "
                 f"Revenue={rev:,.0f} {f.currency}, EBIT={ebit:,.0f}. "
                 f"Comment on revenue scale, cost structure coherence, and EBIT margin level for this sector.",
                 [f"German {f.nace_code} sector revenue profitability benchmarks",
                  "income statement HGB structure validation"]),
            Task("extract-bs", "Balance Sheet Review",
                 f"Review balance sheet: Total Assets={ta:,.0f}, Equity={te:,.0f} {f.currency}. "
                 f"Is this balance sheet structure typical for a {f.nace_code} company? "
                 f"Comment on equity ratio and asset composition.",
                 ["German Mittelstand balance sheet structure",
                  f"NACE {f.nace_code} typical balance sheet composition"]),
        ]
        if ctx.reconciliation and ctx.reconciliation.errors:
            errs = "; ".join(f"{e.check}: delta {e.delta:+,.0f}" for e in ctx.reconciliation.errors[:3])
            tasks.append(Task("extract-recon", "Reconciliation Discrepancies",
                              f"Accounting identity errors found: {errs}. "
                              f"Are these likely rounding differences or data quality issues? "
                              f"How material are they?",
                              ["HGB accounting reconciliation rounding",
                               "financial statement data quality reconciliation"]))
        return tasks

    def build_context_str(self, ctx: PipelineContext) -> str:
        if not ctx.financials:
            return "Extraction failed."
        f = ctx.financials
        return (f"Company: {f.company_name} | NACE: {f.nace_code} | "
                f"Standard: {f.reporting_standard} | Currency: {f.currency}\n"
                f"Periods: {f.income_statement.periods}")


# ── Room 3: Analysis ───────────────────────────────────────────────────────────

class AnalysisRoom(Room):
    name = "Analysis"
    stage = 2

    async def setup(self, ctx: PipelineContext) -> None:
        if ctx.financials:
            from backend.analysis.ratios import run_analysis
            ctx.analysis = run_analysis(ctx.financials)

    def make_tasks(self, ctx: PipelineContext) -> list[Task]:
        if not ctx.analysis:
            return []
        f = ctx.financials
        groups = {
            "Profitability": ("ebit_margin", "gross_margin", "roe", "roa", "roce"),
            "Liquidity":     ("current_ratio", "quick_ratio", "cash_ratio"),
            "Efficiency":    ("dso", "dpo", "inventory_days", "ccc", "asset_turnover"),
            "Leverage":      ("debt_to_equity", "interest_coverage", "net_debt_ebitda"),
            "Growth":        ("revenue_growth_yoy", "revenue_cagr", "ebit_growth_yoy"),
        }
        tasks = []
        for group, prefixes in groups.items():
            relevant = [
                r for r in ctx.analysis.ratios
                if not r.not_derivable and r.value is not None
                and any(r.finding_id.startswith(p) for p in prefixes)
            ]
            if not relevant:
                continue
            ratio_text = "; ".join(f"{r.name}={r.value:.2f}{r.unit}" for r in relevant[:5])
            tasks.append(Task(
                f"analysis-{group[:4].lower()}",
                f"Interpret {group} Ratios",
                f"Interpret {group.lower()} ratios for {f.company_name}: {ratio_text}. "
                f"Are these healthy for a German {f.nace_code} sector company? "
                f"What do they indicate about operational and financial health?",
                [f"German {f.nace_code} {group.lower()} ratio benchmarks 2023",
                 f"financial {group.lower()} ratio interpretation manufacturing Germany"],
            ))
        return tasks

    def build_context_str(self, ctx: PipelineContext) -> str:
        if not ctx.analysis:
            return "No analysis data."
        ratios = [r for r in ctx.analysis.ratios if not r.not_derivable and r.value is not None]
        return "\n".join(f"{r.finding_id}: {r.value:.2f} {r.unit}" for r in ratios[:20])


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
        if not ctx.benchmark:
            return []
        f = ctx.financials
        flags = ctx.benchmark.flags
        tasks = [
            Task("bench-ovr", "Peer Comparison Overview",
                 f"Compare {f.company_name} (NACE {f.nace_code}) against German industry peers. "
                 f"Total flags: {len(flags)}. "
                 f"Which areas outperform and which underperform the peer median?",
                 [f"German NACE {f.nace_code} industry peer benchmarks",
                  "Bundesbank BACH German company financial data"]),
        ]
        for flag in flags[:5]:
            tasks.append(Task(
                f"bench-{flag.flag_type[:10]}",
                f"Flag: {flag.flag_type.replace('_', ' ').title()}",
                f"Analyse this flag: {flag.message}. "
                f"Company value: {flag.company_value:.2f}, Peer median: {flag.peer_median:.2f} "
                f"(delta: {flag.company_value - flag.peer_median:+.2f}). "
                f"What are likely root causes and business implications?",
                [f"{flag.metric} improvement manufacturing Germany",
                 f"German Mittelstand {flag.metric} best practices"],
            ))
        return tasks

    def build_context_str(self, ctx: PipelineContext) -> str:
        if not ctx.benchmark:
            return "No benchmark data."
        flags_text = "\n".join(f"- {f.flag_type}: {f.message}" for f in ctx.benchmark.flags)
        return f"Company: {ctx.financials.company_name}\nFlags:\n{flags_text}"


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
        if not ctx.actions:
            return [Task("strategy-maint", "Performance Maintenance",
                         f"Company metrics are within peer ranges. "
                         f"Suggest 3 opportunistic improvements to maintain competitive position for {getattr(ctx.financials, 'company_name', 'the company')}.",
                         ["financial performance optimisation German Mittelstand",
                          "proactive financial management strategies"])]
        tasks = []
        for action in ctx.actions[:8]:
            # Find matching projection
            proj = next((p for p in ctx.projections if p.action.finding_id == action.finding_id), None)
            base = next((s for s in proj.scenarios if s.label == "base"), None) if proj else None
            impact = f"EUR {base.impact_eur:,.0f} base-case impact" if base and base.impact_eur else ""
            tasks.append(Task(
                f"strat-{action.action_type.value[:10]}",
                f"Plan: {action.action_type.value.replace('_', ' ').title()}",
                f"Develop an implementation plan: {action.description}. "
                f"Current: {action.current_value:.2f}{action.unit}, Target: {action.target_base:.2f}{action.unit}. "
                f"{impact}. "
                f"Provide 3-4 concrete action steps with short/medium/long-term timeline.",
                [f"{action.action_type.value.replace('_', ' ')} implementation case study",
                 f"German Mittelstand {action.action_type.value.replace('_', ' ')} improvement guide"],
            ))
        return tasks

    def build_context_str(self, ctx: PipelineContext) -> str:
        return ctx.proj_summary or "No projections available."


# ── Room 6: Reporting ──────────────────────────────────────────────────────────

class ReportingRoom(Room):
    name = "Reporting"
    stage = 5

    async def setup(self, ctx: PipelineContext) -> None:
        pass  # all data is in ctx from previous rooms

    def make_tasks(self, ctx: PipelineContext) -> list[Task]:
        company = getattr(ctx.financials, "company_name", "the company")
        bench_report  = ctx.room_reports.get("Benchmarking", "")[:400]
        analysis_report = ctx.room_reports.get("Analysis", "")[:400]
        strategy_report = ctx.room_reports.get("Strategy", "")[:400]
        flag_count = len(getattr(ctx.benchmark, "flags", []))

        return [
            Task("report-exec", "Executive Summary",
                 f"Write a 150-200 word executive summary for {company}. "
                 f"Cover: top 2-3 strengths, main risks ({flag_count} flags raised), "
                 f"and priority recommendations. "
                 f"Key findings: {analysis_report}",
                 ["executive summary financial analysis German company",
                  "financial report executive summary structure"]),
            Task("report-findings", "Key Financial Findings",
                 f"Write a structured 'Key Findings' section for {company} — "
                 f"list 4-6 specific findings with supporting numbers. "
                 f"Source: {analysis_report}",
                 ["financial analysis key findings format",
                  "ratio analysis findings German manufacturing"]),
            Task("report-recs", "Strategic Recommendations",
                 f"Write a 'Recommendations' section. For each recommendation: "
                 f"what to do, why, expected benefit, and first 2 steps. "
                 f"Source: {strategy_report}",
                 ["strategic recommendations financial report",
                  "financial improvement implementation roadmap"]),
            Task("report-risk", "Risk Assessment",
                 f"Write a 'Risk Assessment' section covering the {flag_count} flags raised. "
                 f"For each risk: severity, root cause, mitigation. "
                 f"Source: {bench_report}",
                 ["financial risk assessment German SME",
                  "manufacturing company financial risk factors"]),
        ]

    def build_context_str(self, ctx: PipelineContext) -> str:
        parts = []
        if ctx.financials:
            parts.append(f"Company: {ctx.financials.company_name}")
        if ctx.analysis:
            key_ratios = [r for r in ctx.analysis.ratios if not r.not_derivable and r.value is not None]
            parts.append("Key ratios: " + "; ".join(f"{r.name}={r.value:.1f}{r.unit}" for r in key_ratios[:8]))
        if ctx.benchmark and ctx.benchmark.flags:
            parts.append("Flags: " + ", ".join(f.flag_type for f in ctx.benchmark.flags))
        if ctx.proj_summary:
            parts.append(ctx.proj_summary[:300])
        return "\n".join(parts)
