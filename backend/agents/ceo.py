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
    ) -> str:
        """
        Synthesise all room reports into a CEO-level executive summary.

        Parameters
        ----------
        room_reports:
            Mapping of room/department name -> full analysis report text.
        dataset:
            The original dataset context (used for company name and metadata).

        Returns
        -------
        A 300-400 word executive summary string.
        """
        reports_block = "\n\n".join(
            f"=== {dept} Report ===\n{text}" for dept, text in room_reports.items()
        )

        prompt = f"""You are the CEO of Kodrlytics.
Your six analysis departments have completed their deep-dive into {dataset.company_name!r}.
Below are their full reports.

---
{reports_block}
---

Write a CEO-level executive summary of 300-400 words. Structure it as follows:

**Overall Verdict** (2-3 sentences): Is this company financially healthy, at risk, or in crisis?

**Top 3 Strengths**
- Strength 1
- Strength 2
- Strength 3

**Top 3 Risks**
- Risk 1
- Risk 2
- Risk 3

**Single Most Critical Action** (1-2 sentences): The one thing leadership must do immediately.

Be precise, use numbers from the reports wherever possible, and write for a board-level audience.
"""

        log.info(
            "CEO.final_synthesis: synthesising %d room reports for company=%r",
            len(room_reports),
            dataset.company_name,
        )
        synthesis = await _llm.narrate(prompt)
        log.info("CEO synthesis complete: %d chars", len(synthesis))
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
