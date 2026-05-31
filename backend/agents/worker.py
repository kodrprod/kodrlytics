"""Worker AI: web search (learn) + 4-round deep LLM analysis (work)."""
from __future__ import annotations
import logging

from backend.agents.models import Task
from backend.agents.web_search import ddg_search
from backend.llm import router as _llm

log = logging.getLogger(__name__)


class Worker:
    def __init__(self, worker_id: str, room_name: str) -> None:
        self.worker_id = worker_id
        self.room_name = room_name

    async def learn(self, queries: list[str]) -> str:
        """Run web searches for each query (max 3), return up to 2000 chars."""
        snippets: list[str] = []
        for q in queries[:3]:
            results = await ddg_search(q, max_results=4)
            for r in results:
                text = r.get("Text", "")
                if text:
                    snippets.append(text)
        return " | ".join(snippets)[:2000]

    async def work(self, task: Task, room_context: str, learned: str) -> str:
        """4-round deep analysis. Each round builds on the previous.
        Round 1: scan & structure findings
        Round 2: deep numerical analysis
        Round 3: cross-reference & challenge assumptions
        Round 4: final synthesis & recommendations
        """
        base = (
            f"You are a senior financial analyst, Worker {self.worker_id}, "
            f"in the {self.room_name} department of a financial intelligence firm.\n\n"
            f"YOUR ASSIGNED TASK: {task.title}\n"
            f"TASK DETAILS: {task.description}\n\n"
            f"COMPANY DATA:\n{room_context[:6000]}\n\n"
            f"EXTERNAL RESEARCH:\n{learned or '(No external research available.)'}\n\n"
        )

        # Round 1: Structured scan
        try:
            r1 = (await _llm.narrate(
                base +
                "ROUND 1 — STRUCTURED SCAN\n"
                "Read all data carefully. Identify and list:\n"
                "1. Key data points available (exact figures and years)\n"
                "2. Immediate observations — what stands out?\n"
                "3. What is missing or unclear?\n"
                "4. Initial hypotheses about the situation\n"
                "Write 200-300 words. Be specific with numbers."
            )).strip()
            log.info("  Worker %s [%s] R1: %d chars", self.worker_id, task.title[:25], len(r1))
        except Exception as e:
            log.warning("Worker %s R1 failed: %s", self.worker_id, e)
            r1 = f"[Round 1 error: {e}]"

        # Round 2: Deep numerical analysis
        try:
            r2 = (await _llm.narrate(
                base +
                f"YOUR ROUND 1 SCAN:\n{r1}\n\n"
                "ROUND 2 — DEEP NUMERICAL ANALYSIS\n"
                "Go deeper on the numbers. For each key metric:\n"
                "1. Compute year-over-year changes and CAGRs\n"
                "2. Identify trend inflection points with specific years\n"
                "3. Explain the root cause of each major trend\n"
                "4. Flag anomalies, reversals, or suspicious figures\n"
                "Write 300-400 words. Cite exact figures throughout. Do not fabricate data."
            )).strip()
            log.info("  Worker %s [%s] R2: %d chars", self.worker_id, task.title[:25], len(r2))
        except Exception as e:
            log.warning("Worker %s R2 failed: %s", self.worker_id, e)
            r2 = f"[Round 2 error: {e}]"

        # Round 3: Cross-reference & critical challenge
        try:
            r3 = (await _llm.narrate(
                base +
                f"YOUR PREVIOUS ANALYSIS:\n{r1[:800]}\n{r2[:1000]}\n\n"
                "ROUND 3 — CROSS-REFERENCE & CRITICAL CHALLENGE\n"
                "Challenge your own analysis:\n"
                "1. Does data from different sources corroborate? Any contradictions?\n"
                "2. What alternative explanations exist for the trends found?\n"
                "3. What context is needed to correctly interpret these numbers?\n"
                "4. Risk factors and opportunities not yet surfaced\n"
                "Write 200-300 words. Be a rigorous, sceptical analyst."
            )).strip()
            log.info("  Worker %s [%s] R3: %d chars", self.worker_id, task.title[:25], len(r3))
        except Exception as e:
            log.warning("Worker %s R3 failed: %s", self.worker_id, e)
            r3 = f"[Round 3 error: {e}]"

        # Round 4: Final synthesis
        try:
            final = (await _llm.narrate(
                base +
                f"YOUR ANALYSIS SO FAR:\n{r1[:600]}\n{r2[:800]}\n{r3[:600]}\n\n"
                "ROUND 4 — FINAL SYNTHESIS\n"
                "Write your final professional analysis report:\n\n"
                "**FINDINGS**\n"
                "5-7 numbered key findings with exact figures, years, and % changes.\n\n"
                "**ANALYSIS**\n"
                "Deep interpretation: trajectory, root causes, multi-year patterns. "
                "Compare periods explicitly.\n\n"
                "**RISKS & OPPORTUNITIES**\n"
                "Concrete risks and opportunities with specific figures and timeframes.\n\n"
                "**RECOMMENDATIONS**\n"
                "3 prioritised, actionable steps with expected financial impact.\n\n"
                "REQUIREMENTS: minimum 500 words, specific numbers throughout, "
                "professional board-level tone. Do NOT fabricate figures not in the data."
            )).strip()
            log.info("  Worker %s [%s] FINAL: %d chars", self.worker_id, task.title[:25], len(final))
            return final
        except Exception as e:
            log.warning("Worker %s R4 failed: %s", self.worker_id, e)
            best = r2 if len(r2) > len(r1) else r1
            return best or f"[Worker {self.worker_id} error: {e}]"
