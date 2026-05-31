"""Room manager: synthesises worker results into a comprehensive room report."""
from __future__ import annotations
import logging
from backend.agents.models import Task
from backend.llm import router as _llm

log = logging.getLogger(__name__)


class RoomManager:
    def __init__(self, room_name: str):
        self.room = room_name

    async def write_report(self, tasks: list[Task], context: str) -> str:
        done = [t for t in tasks if t.status == "done" and t.result]
        if not done:
            return f"[{self.room} room: no worker results available]"

        worker_block = "\n\n".join(
            f"=== Worker {t.assigned_worker}: {t.title} ===\n{t.result}"
            for t in done
        )
        prompt = (
            f"You are the manager of the {self.room} analysis room. "
            f"Your team of {len(done)} senior analysts has completed their work. "
            f"Synthesise ALL their findings into a comprehensive room report.\n\n"
            f"WORKER ANALYSES:\n{worker_block[:8000]}\n\n"
            f"ROOM CONTEXT:\n{context[:1500]}\n\n"
            f"Write a comprehensive handover report with these sections:\n\n"
            f"**{self.room.upper()} ROOM SUMMARY**\n"
            f"Overall conclusions and the most important takeaways (150-200 words).\n\n"
            f"**KEY FINDINGS**\n"
            f"Top 6-8 findings ranked by importance, with specific numbers, citing which analyst found each.\n\n"
            f"**CRITICAL ISSUES**\n"
            f"High-risk items, anomalies, anything requiring urgent attention.\n\n"
            f"**HANDOVER TO NEXT ROOM**\n"
            f"Specific data, context, and open questions the next team must know and focus on.\n\n"
            f"REQUIREMENTS: 700-1000 words, comprehensive, cite specific analyst findings and numbers."
        )
        try:
            report = (await _llm.narrate(prompt)).strip()
            log.info("[MGR] %s room report: %d chars from %d workers", self.room, len(report), len(done))
            return report
        except Exception as e:
            log.warning("Manager report failed for %s: %s", self.room, e)
            return "\n".join(f"- {t.title}: {t.result[:300]}" for t in done)
