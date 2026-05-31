"""Worker AI: web search (learn) + deep LLM analysis (work)."""
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
        """Produce a thorough multi-section financial analysis (400-600 words)."""
        prompt = (
            f"You are a senior financial analyst, Worker {self.worker_id}, "
            f"in the {self.room_name} room of a financial analysis team.\n\n"
            f"YOUR TASK: {task.title}\n"
            f"TASK DETAILS: {task.description}\n\n"
            f"FINANCIAL DATA:\n{room_context[:6000]}\n\n"
            f"EXTERNAL RESEARCH:\n{learned or '(No external research available.)'}\n\n"
            f"Write a thorough, professional financial analysis structured as follows:\n\n"
            f"**FINDINGS**\n"
            f"4-6 numbered findings with exact figures, specific years, and percentage changes "
            f"from the data. Each finding must cite specific numbers.\n\n"
            f"**ANALYSIS**\n"
            f"Deep interpretation: root causes, multi-year trends, anomalies, patterns. "
            f"What does the trajectory tell us? Compare periods explicitly.\n\n"
            f"**RISKS & OPPORTUNITIES**\n"
            f"Concrete risks and opportunities with specific figures and timeframes.\n\n"
            f"**RECOMMENDATIONS**\n"
            f"2-3 prioritised, actionable steps with expected financial impact.\n\n"
            f"REQUIREMENTS: minimum 400 words, cite specific numbers and years throughout, "
            f"professional board-level tone. Do NOT fabricate any figures not in the data above."
        )
        try:
            result = await _llm.narrate(prompt)
            log.info("  Worker %s [%s] completed: %d chars", self.worker_id, task.title[:30], len(result))
            return result
        except Exception as e:
            log.warning("Worker %s work() failed: %s", self.worker_id, e)
            return f"[Worker {self.worker_id} error: {e}]"
