"""Deep narrative generation — detailed recommendation chapters."""
from __future__ import annotations
import logging
from backend.llm import router
from backend.analysis.ratios import AnalysisResult
from backend.benchmark.flags import BenchmarkResult
from backend.strategy.projections import ProjectionResult

log = logging.getLogger(__name__)


async def generate_deep_recommendations(
    analysis: AnalysisResult,
    benchmark: BenchmarkResult,
    projections: list[ProjectionResult],
) -> str:
    """
    Generate a detailed recommendations chapter.
    One focused LLM call per projection/action.
    Returns combined text for the PDF report.
    """
    sections = []

    for proj in projections:
        action = proj.action
        base_scenario = next((s for s in proj.scenarios if s.label == "base"), None)
        impact_str = (f"EUR {base_scenario.impact_eur:,.0f}" if base_scenario and base_scenario.impact_eur else "undetermined")

        prompt = f"""You are writing one chapter of a detailed financial improvement report (Doktorarbeit style).

COMPANY: {analysis.company_name}
FINDING: {action.finding_id}
PROBLEM: {action.description}
CURRENT VALUE: {action.current_value:.2f} {action.unit}
BASE CASE TARGET: {action.target_base:.2f} {action.unit}
ESTIMATED BASE CASE IMPACT: {impact_str}
ASSUMPTIONS: {'; '.join(action.assumptions)}

Write a detailed 400-600 word recommendation chapter covering:
1. Root cause analysis — why is this metric underperforming?
2. Specific action steps (3-5 concrete, actionable steps)
3. Implementation timeline (short/medium/long term)
4. Key performance indicators to track progress
5. Risks and mitigants
6. Expected financial outcomes across all three scenarios

Reference ONLY these computed values (do not invent numbers):
{chr(10).join(f'  {r.finding_id}: {r.value:.2f} {r.unit}' for r in analysis.ratios if not r.not_derivable and r.value is not None)[:3000]}

Write in professional business English. Be specific and actionable. Label projections as estimates."""

        try:
            text = await router.narrate(prompt)
            sections.append(f"### Recommendation: {action.description}\n\n{text}\n\n---\n")
        except Exception as e:
            log.warning("Deep narration failed for %s: %s", action.finding_id, e)
            sections.append(f"### Recommendation: {action.description}\n\n[Detailed analysis unavailable: {e}]\n\n---\n")

    return "\n".join(sections)
