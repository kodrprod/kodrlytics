"""
Briefing stage: LLM writes narrative from computed findings.
Grounding gate verifies every number. Max 2 attempts.
"""
from __future__ import annotations
import logging
from backend.analysis.ratios import AnalysisResult
from backend.benchmark.flags import BenchmarkResult
from backend.briefing.grounding import check_grounding
from backend.llm import router

log = logging.getLogger(__name__)


def _format_findings(analysis: AnalysisResult, benchmark: BenchmarkResult) -> str:
    """Serialize computed findings into a prompt-friendly block."""
    lines = [f"Company: {analysis.company_name}", ""]
    lines.append("=== COMPUTED RATIOS (use only these numbers) ===")
    for r in sorted(analysis.ratios, key=lambda x: (x.name, x.period)):
        if r.not_derivable:
            lines.append(f"  {r.finding_id}: NOT DERIVABLE ({r.not_derivable_reason})")
        else:
            lines.append(f"  {r.finding_id}: {r.value:.2f} {r.unit}  [{r.formula}]")

    lines.append("")
    lines.append("=== BENCHMARK FLAGS ===")
    if not benchmark.flags:
        lines.append("  No flags raised.")
    for f in benchmark.flags:
        lines.append(f"  [{f.severity.upper()}] {f.flag_type} ({f.period}): {f.message}")
        if f.quantified_impact:
            lines.append(f"    Impact: {f.quantified_impact}")

    return "\n".join(lines)


def _build_narration_prompt(findings: str) -> str:
    return f"""Write a concise executive-summary financial report (400-600 words) for the company below.

STRICT RULES:
1. Use ONLY the numbers provided in the findings block — do not compute, estimate, or invent any figures.
2. Reference specific finding IDs when citing numbers (e.g. "gross margin [gross_margin.2023] of X%").
3. Structure: (a) Overview, (b) Profitability, (c) Liquidity & Efficiency, (d) Leverage, (e) Key risks / flags.
4. End with a one-paragraph forward-looking note that is clearly labeled "PROJECTION NOTE (not a guarantee)."

FINDINGS:
{findings}"""


async def generate_briefing(analysis: AnalysisResult, benchmark: BenchmarkResult,
                             max_attempts: int = 2) -> tuple[str, bool]:
    """
    Generate narrative and verify grounding.
    Returns (narrative_text, grounding_passed).
    On grounding failure after max_attempts, returns the last attempt with a warning prefix.
    """
    findings = _format_findings(analysis, benchmark)
    prompt = _build_narration_prompt(findings)

    for attempt in range(max_attempts):
        log.info("Briefing: narration attempt %d", attempt + 1)
        narrative = await router.narrate(prompt)
        result = check_grounding(narrative, analysis, benchmark)
        log.info("Briefing: grounding check — passed=%s, checked=%d, ungrounded=%d",
                 result.passed, result.checked, len(result.ungrounded))

        if result.passed:
            return narrative, True

        # Retry prompt strips ungrounded numbers
        if attempt < max_attempts - 1:
            prompt = (
                f"{prompt}\n\n"
                f"WARNING: Your previous response contained numbers not traceable to the findings: "
                f"{result.ungrounded}. Remove or replace them with only figures from the FINDINGS block."
            )
            log.warning("Briefing: retrying due to ungrounded numbers: %s", result.ungrounded)

    # Return last attempt with warning
    warning = (
        "[GROUNDING WARNING: This narrative may contain unverified figures. "
        "The following numbers could not be traced to computed values: "
        f"{result.ungrounded}]\n\n"
    )
    return warning + narrative, False
