"""Base Room class — all 6 pipeline rooms extend this."""
from __future__ import annotations
import asyncio
import logging
from typing import Callable, Awaitable
from backend.agents.models import Task, PipelineContext
from backend.agents.worker import Worker
from backend.agents.manager import RoomManager

log = logging.getLogger(__name__)

_BATCH_SIZE = 6   # max concurrent LLM calls per batch (raised from 4)


class Room:
    name: str = "Room"
    stage: int = 0

    async def setup(self, ctx: PipelineContext) -> None:
        """Deterministic Python work (parsing, ratio computation, etc.)."""
        pass

    def make_tasks(self, ctx: PipelineContext) -> list[Task]:
        """Return the worker task list for this room."""
        return []

    def build_context_str(self, ctx: PipelineContext) -> str:
        """Context string given to every worker in this room."""
        return ""

    async def run(self, ctx: PipelineContext, run_id: str, emit: Callable[..., Awaitable[None]]) -> None:
        # 1. Deterministic setup
        try:
            await self.setup(ctx)
        except Exception as e:
            log.error("Room %s setup failed: %s", self.name, e)

        # 2. Plan tasks
        try:
            tasks = self.make_tasks(ctx)
        except Exception as e:
            log.error("Room %s make_tasks failed: %s", self.name, e)
            tasks = []

        # 3. Open room
        await emit({
            "event_type": "room_opened", "run_id": run_id,
            "room_name": self.name, "stage": self.stage,
            "worker_count": len(tasks), "task_count": len(tasks),
        })

        if not tasks:
            await emit({"event_type": "room_closed", "run_id": run_id,
                        "room_name": self.name, "stage": self.stage, "worker_count": 0})
            return

        context_str = self.build_context_str(ctx)

        # Prepend CEO brief if available
        ceo_brief = ctx.room_briefs.get(self.name, "")
        if ceo_brief:
            context_str = f"CEO BRIEF FOR {self.name.upper()} DEPARTMENT:\n{ceo_brief}\n\n{context_str}"

        # Build facts table for prompt injection
        facts_table = ""
        if ctx.facts_store is not None:
            try:
                facts_table = ctx.facts_store.render_tables()
            except Exception as e:
                log.warning("Room %s: failed to render facts table: %s", self.name, e)

        # 4. Spawn workers
        workers: list[Worker] = []
        for i, task in enumerate(tasks):
            wid = f"W{self.stage + 1}-{i + 1:02d}"
            task.assigned_worker = wid
            workers.append(Worker(wid, self.name))
            await emit({
                "event_type": "worker_spawned", "run_id": run_id,
                "room_name": self.name, "stage": self.stage,
                "worker_id": wid, "task_title": task.title,
            })

        # 5. Workers learn + work in batches
        async def run_one(w: Worker, t: Task) -> None:
            try:
                await emit({
                    "event_type": "worker_learning", "run_id": run_id,
                    "room_name": self.name, "stage": self.stage,
                    "worker_id": w.worker_id, "queries": t.search_queries[:2],
                })
                learned = await w.learn(t.search_queries)

                await emit({
                    "event_type": "worker_working", "run_id": run_id,
                    "room_name": self.name, "stage": self.stage,
                    "worker_id": w.worker_id, "task_title": t.title,
                })

                await asyncio.sleep(0)  # yield to event loop

                result = await w.work(t, context_str, learned, facts_table=facts_table)
                # Errors must never become content
                if "error:" in result.lower() and result.startswith("["):
                    result = "[gap — analysis unavailable for this section]"
                t.result = result
                t.status = "done"
            except Exception as e:
                log.warning("Worker %s failed: %s", w.worker_id, e)
                t.result = "[gap — analysis unavailable for this section]"
                t.status = "failed"
            finally:
                await emit({
                    "event_type": "worker_done", "run_id": run_id,
                    "room_name": self.name, "stage": self.stage,
                    "worker_id": w.worker_id, "task_title": t.title,
                })

        for i in range(0, len(workers), _BATCH_SIZE):
            batch = list(zip(workers[i:i + _BATCH_SIZE], tasks[i:i + _BATCH_SIZE]))
            await asyncio.gather(*[run_one(w, t) for w, t in batch])

        # 6. Manager writes room report
        await emit({"event_type": "manager_writing", "run_id": run_id,
                    "room_name": self.name, "stage": self.stage})
        manager = RoomManager(self.name)
        ctx.room_reports[self.name] = await manager.write_report(
            tasks, context_str,
            facts_table=facts_table,
            facts_store=ctx.facts_store,
        )

        # 7. Close room
        await emit({
            "event_type": "room_closed", "run_id": run_id,
            "room_name": self.name, "stage": self.stage, "worker_count": len(tasks),
        })
