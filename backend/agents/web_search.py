"""DuckDuckGo search via duckduckgo-search library (DDGS). No API key required."""
from __future__ import annotations
import asyncio
import logging

log = logging.getLogger(__name__)


async def ddg_search(query: str, max_results: int = 3) -> list[dict]:
    """Search DuckDuckGo via DDGS. Returns list of result dicts with 'Text' key."""
    try:
        from ddgs import DDGS

        def _sync_search() -> list[dict]:
            raw = list(DDGS().text(query, max_results=max_results))
            return [
                {
                    "Text": f"{r.get('title', '')}: {r.get('body', '')}".strip(": "),
                    "href": r.get("href", ""),
                }
                for r in raw
                if r.get("body") or r.get("title")
            ]

        return await asyncio.to_thread(_sync_search)
    except Exception as e:
        log.warning("ddg_search failed for query %r: %s", query, e)
        return []
