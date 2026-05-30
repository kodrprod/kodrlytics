"""Demo runner: runs the full pipeline on the Mustermann sample and prints events."""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.pipeline.orchestrator import run_pipeline

SAMPLE = Path(__file__).parent.parent.parent / "data" / "samples" / "mustermann_gmbh.json"


async def main():
    print(f"Running pipeline on: {SAMPLE.name}\n{'='*60}")
    content = SAMPLE.read_bytes()
    async for event in run_pipeline("mustermann_gmbh.json", content):
        d = event.model_dump()
        et = d.get("event_type", "?")
        if et == "stage_started":
            print(f"\n▶  STAGE {d['stage_index']+1}/5: {d['stage'].upper()}")
        elif et == "stage_done":
            print(f"   ✓ done in {d['duration_ms']}ms")
        elif et == "finding_created":
            print(f"   📊 {d['name']}: {d['value']} {d['unit']} ({d['period']})")
        elif et == "flag_raised":
            icon = "🚨" if d['severity'] == 'critical' else "⚠️ "
            print(f"   {icon} [{d['severity'].upper()}] {d['message']}")
        elif et == "data_passed":
            print(f"   → {d['summary']}")
        elif et == "run_complete":
            print(f"\n{'='*60}")
            print(f"✅ COMPLETE: {d['company_name']}")
            print(f"   {d['finding_count']} findings, {d['flag_count']} flags, {d['total_duration_ms']}ms")
            print(f"\nNARRATIVE:\n{d['narrative'][:800]}...")
        elif et == "run_error":
            print(f"\n❌ ERROR in {d['stage']}: {d['error']}")
            break


if __name__ == "__main__":
    asyncio.run(main())
