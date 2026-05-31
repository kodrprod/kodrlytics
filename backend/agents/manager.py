"""Room manager: synthesises worker results into a room report."""
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
            f"Worker {t.assigned_worker} - {t.title}:\n{t.result}"
            for t in done
        )
        prompt = (
            f"You are the manager of the {self.room} team room.\n"
            "Your workers have completed their tasks. Write a clear, structured summary "
            "report for the next team room. Include all key findings and facts. "
            "Be precise and complete.\n\n"
            f"WORKER RESULTS:\n{worker_block[:4000]}\n\n"
            "Write the room handover report now."
        )
        try:
            return (await _llm.narrate(prompt)).strip()
        except Exception as e:
            log.warning("Manager report failed for %s: %s", self.room, e)
            return "\n".join(f"- {t.title}: {t.result[:200]}" for t in done)
