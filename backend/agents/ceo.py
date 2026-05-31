"""CEO agent: orchestrates department briefs and synthesises the final executive summary."""
from __future__ import annotations

import logging
import re

from backend.intake.zip_ingester import DatasetContext
from backend.llm import router as _llm

log = logging.getLogger(__name__)

# The six canonical department names the CEO addresses.
_DEPARTMENTS = [
    "Intake",
    "Extraction",
    "Analysis",
    "Benchmarking",
    "Strategy",
    "Reporting",
]


class CEO:
    """
    High-level orchestrator that produces per-department briefs and the final
    executive synthesis for a Kodrlytics analysis run.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def plan_and_brief(
        self,
        dataset: DatasetContext,
        room_names: list[str],
    ) -> dict[str, str]:
        """
        Generate one comprehensive CEO plan via a single LLM call, then parse it
        into per-room briefs.

        Parameters
        ----------
        dataset:
            The ingested company dataset.
        room_names:
            Ordered list of exactly 6 room names that map to the six departments.

        Returns
        -------
        dict mapping each room name to its brief text.
        """
        summary = dataset.summary()
        dept_list = "\n".join(
            f"  {i + 1}. {dept}" for i, dept in enumerate(_DEPARTMENTS)
        )

        prompt = f"""You are the CEO of Kodrlytics, a leading financial intelligence firm.
A new company dataset has just arrived. Below is a full inventory of the available data.

---
DATASET SUMMARY
{summary}
---

You must now brief the managers of our six analysis departments.
Each department has 20 specialist workers who will dive deep into their assigned area.
The departments, in pipeline order, are:

{dept_list}

For EACH department, write a brief of exactly ~150 words addressed to its manager.
The brief must cover:
1. What specific data that department has direct access to
2. What specific questions their 20 workers must answer
3. What the most critical findings or red-flags to look for are
4. What outputs and insights to hand on to the next department in the pipeline

Format your response with each department's name as a level-2 heading followed by its brief,
like this:

## Intake
<brief text>

## Extraction
<brief text>

## Analysis
<brief text>

## Benchmarking
<brief text>

## Strategy
<brief text>

## Reporting
<brief text>

Be specific, rigorous, and data-driven. Reference actual year ranges, document counts,
and category names from the dataset summary above wherever possible.
"""

        log.info("CEO.plan_and_brief: sending plan prompt for company=%r", dataset.company_name)
        raw_plan = await _llm.narrate(prompt)
        log.info("CEO plan received: %d chars", len(raw_plan))

        briefs = self._parse_briefs(raw_plan, room_names)
        return briefs

    # ------------------------------------------------------------------

    async def final_synthesis(
        self,
        room_reports: dict[str, str],
        dataset: DatasetContext,
        facts_store=None,
    ) -> str:
        """
        Write a single unified analyst report from all 6 room outputs.

        Rather than summarising summaries, this prompt asks Claude to read all
        department findings and write ONE coherent document in a single analyst
        voice — as if one senior analyst had access to all the data simultaneously.
        """
        # Exclude the CEO key if a previous synthesis exists
        dept_reports = {k: v for k, v in room_reports.items() if k != "CEO"}
        reports_block = "\n\n".join(
            f"=== {dept} Department Findings ===\n{text}"
            for dept, text in dept_reports.items()
            if text and text.strip()
        )

        facts_section = ""
        if facts_store is not None:
            try:
                facts_section = f"\n\n=== VERIFIED FACTS TABLE ===\n{facts_store.render_tables()}"
            except Exception:
                pass

        prompt = f"""You are a senior financial analyst who has just received the full research output \
from six specialist departments on {dataset.company_name!r}.

Your job is to write a single, unified, board-ready analyst report. Do NOT write "the Analysis department found..." \
or reference departments at all. Write as if YOU conducted the entire analysis. One voice. One document.

---
DEPARTMENT RESEARCH FINDINGS
{reports_block}{facts_section}
---

Write the unified analyst report with these sections:

# {dataset.company_name} — Financial & Strategic Analysis

## Executive Summary
3-4 sentences. Overall financial health, key verdict, one critical risk.

## Financial Performance
Revenue, profitability margins, EBIT, net income. Year-over-year trends. \
Use exact figures from the verified facts table wherever available. \
Write [gap] for any metric not confirmed in the source data.

## Balance Sheet & Liquidity
Asset base, debt structure, equity ratio, liquidity position.

## Operational Highlights
Workforce, key projects, capacity utilisation, operational risks.

## Compliance & Governance
Regulatory status, audit findings, key compliance risks.

## Strategic Outlook
Top 2 opportunities. Top 2 risks. Single most important action for leadership.

Rules:
- Every number must come from the verified facts table or the department findings. \
Never invent a figure. Write [gap] if data is absent.
- Do not mention departments, rooms, or the analysis pipeline.
- Write for a bank credit committee or board — precise, direct, no filler.
- Target 600-900 words total.
"""

        log.info(
            "CEO.final_synthesis: writing unified report for company=%r (%d dept reports)",
            dataset.company_name, len(dept_reports),
        )
        synthesis = await _llm.narrate(prompt)
        log.info("CEO unified report complete: %d chars", len(synthesis))
        return synthesis

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_briefs(self, raw_plan: str, room_names: list[str]) -> dict[str, str]:
        """
        Extract per-department briefs from the raw LLM response.

        The parser looks for ``## <DepartmentName>`` headings (case-insensitive)
        and treats everything up to the next heading as that department's brief.

        If fewer than 6 sections are found the full plan is assigned to every
        room so that no room is left without context.
        """
        # Build a pattern that matches any of the six department names as headings
        dept_pattern = "|".join(re.escape(d) for d in _DEPARTMENTS)
        heading_re = re.compile(
            r"^#{1,3}\s*(" + dept_pattern + r")\s*$",
            re.IGNORECASE | re.MULTILINE,
        )

        sections: list[tuple[str, str]] = []
        matches = list(heading_re.finditer(raw_plan))

        for i, m in enumerate(matches):
            dept_label = m.group(1).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_plan)
            brief_text = raw_plan[start:end].strip()
            sections.append((dept_label, brief_text))

        if len(sections) < len(_DEPARTMENTS):
            log.warning(
                "CEO plan parsing found only %d/%d sections; "
                "falling back to full plan for all rooms",
                len(sections),
                len(_DEPARTMENTS),
            )
            return {name: raw_plan for name in room_names}

        # Map department names -> briefs; then assign to room_names in order
        dept_to_brief: dict[str, str] = {
            dept.lower(): brief for dept, brief in sections
        }

        result: dict[str, str] = {}
        for i, room_name in enumerate(room_names):
            if i < len(_DEPARTMENTS):
                key = _DEPARTMENTS[i].lower()
                result[room_name] = dept_to_brief.get(key, raw_plan)
            else:
                result[room_name] = raw_plan

        return result
