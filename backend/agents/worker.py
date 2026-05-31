"""Worker AI: web search (learn) + LLM narration (work)."""
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
        """Run web searches for each query (max 2), return up to 1000 chars."""
        snippets: list[str] = []
        for q in queries[:2]:
            results = await ddg_search(q, max_results=3)
            for r in results:
                text = r.get("Text", "")
                if text:
                    snippets.append(text)
        combined = " | ".join(snippets)
        return combined[:1000]

    async def work(self, task: Task, room_context: str, learned: str) -> str:
        """Narrate the task result using room context and research. Returns 3-6 sentences."""
        prompt = (
            f"You are worker {self.worker_id} in the {self.room_name} room of a financial analysis pipeline.\n\n"
            f"TASK: {task.title}\n"
            f"DESCRIPTION: {task.description}\n\n"
            f"ROOM CONTEXT:\n{room_context}\n\n"
            f"RESEARCH FINDINGS:\n{learned or 'No web research available.'}\n\n"
            f"Complete your task in 3-6 sentences. Be specific, professional, and reference the data provided. "
            f"Do NOT invent numbers not in the context."
        )
        try:
            return await _llm.narrate(prompt)
        except Exception as e:
            log.warning("Worker %s work() failed: %s", self.worker_id, e)
            return f"[Worker {self.worker_id} error: {e}]"
