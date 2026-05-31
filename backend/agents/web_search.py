"""DuckDuckGo instant answers — no API key required."""
from __future__ import annotations
import logging
from urllib.parse import quote

import httpx

log = logging.getLogger(__name__)

_DDG_URL = "https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"


async def ddg_search(query: str, max_results: int = 3) -> list[dict]:
    """Search DuckDuckGo instant answers. Returns list of result dicts."""
    try:
        url = _DDG_URL.format(query=quote(query))
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            data = resp.json()

        results = []

        abstract = data.get("Abstract", "")
        if abstract:
            results.append({"Text": abstract, "source": "abstract"})

        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append({"Text": topic["Text"], "source": "related"})

        return results[:max_results]
    except Exception as e:
        log.warning("ddg_search failed for query %r: %s", query, e)
        return []
