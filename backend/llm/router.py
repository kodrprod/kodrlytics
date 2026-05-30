"""
OpenRouter abstraction layer.

Exposes three methods:
  extract(prompt, schema)  — enforced JSON-schema response for data extraction
  reason(prompt)           — free-form reasoning (returns str)
  narrate(prompt)          — final narrative generation (returns str)

Design constraints:
  - DATA_MODE=real blocks free models (any model containing ":free")
  - Exponential backoff on 429 (2s, 4s, 8s, 16s, give up)
  - Fallback model on primary failure
  - Response cache (SQLite) when DATA_MODE=test
  - Logs cost + latency per call to stderr
  - Keeps total calls per run to ~2-3 (caller's responsibility to batch)
"""
from __future__ import annotations
import os, json, time, hashlib, sqlite3, asyncio, logging
from pathlib import Path
from typing import Any
import httpx
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

_API_BASE = "https://openrouter.ai/api/v1/chat/completions"
_CACHE_PATH = Path(__file__).parent.parent.parent / "dev.db"

_API_KEY   = os.getenv("OPENROUTER_API_KEY", "")
_MODEL     = os.getenv("MODEL_NAME", "meta-llama/llama-3.1-8b-instruct:free")
_FALLBACK  = os.getenv("FALLBACK_MODEL", "mistralai/mistral-7b-instruct:free")
_DATA_MODE = os.getenv("DATA_MODE", "test")


class LLMError(Exception):
    pass


class RouterConfig:
    def __init__(self):
        self.api_key   = _API_KEY
        self.model     = _MODEL
        self.fallback  = _FALLBACK
        self.data_mode = _DATA_MODE
        self.use_cache = (_DATA_MODE == "test")

    def _check_real_mode(self, model: str) -> None:
        if self.data_mode == "real" and ":free" in model:
            raise LLMError(
                f"DATA_MODE=real: free model '{model}' is blocked. "
                "Set MODEL_NAME to a paid model with no-logging policy."
            )


_config = RouterConfig()


# ── Cache ──────────────────────────────────────────────────────────────────────

def _cache_key(model: str, messages: list) -> str:
    payload = json.dumps({"model": model, "messages": messages}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _cache_get(key: str) -> str | None:
    if not _config.use_cache:
        return None
    try:
        con = sqlite3.connect(_CACHE_PATH)
        row = con.execute("SELECT response FROM llm_cache WHERE key=?", (key,)).fetchone()
        con.close()
        return row[0] if row else None
    except Exception:
        return None


def _cache_set(key: str, response: str) -> None:
    if not _config.use_cache:
        return
    try:
        con = sqlite3.connect(_CACHE_PATH)
        con.execute("CREATE TABLE IF NOT EXISTS llm_cache (key TEXT PRIMARY KEY, response TEXT)")
        con.execute("INSERT OR REPLACE INTO llm_cache VALUES (?,?)", (key, response))
        con.commit()
        con.close()
    except Exception:
        pass


# ── HTTP call ─────────────────────────────────────────────────────────────────

async def _call(model: str, messages: list[dict], response_format: dict | None = None,
                temperature: float = 0.2) -> tuple[str, float, float]:
    """Returns (content, cost_usd, latency_s). Raises LLMError on failure."""
    _config._check_real_mode(model)

    key = _cache_key(model, messages)
    cached = _cache_get(key)
    if cached is not None:
        log.info("LLM cache hit model=%s key=%s…", model, key[:8])
        return cached, 0.0, 0.0

    headers = {
        "Authorization": f"Bearer {_config.api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://kodrlytics.local",
        "X-Title": "Kodrlytics Financial Analyst",
    }
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        body["response_format"] = response_format

    backoff = [2, 4, 8, 16]
    last_err: Exception | None = None

    async with httpx.AsyncClient(timeout=120) as client:
        for attempt, wait in enumerate([0] + backoff):
            if wait:
                await asyncio.sleep(wait)
            t0 = time.perf_counter()
            try:
                resp = await client.post(_API_BASE, headers=headers, json=body)
                latency = time.perf_counter() - t0
                if resp.status_code == 429:
                    log.warning("LLM 429 rate-limit model=%s attempt=%d, backing off %ds", model, attempt, backoff[min(attempt, len(backoff)-1)])
                    last_err = LLMError(f"Rate limited after {attempt+1} attempts")
                    continue
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                # Cost: OpenRouter returns usage.total_tokens; rough estimate
                tokens = data.get("usage", {}).get("total_tokens", 0)
                cost = tokens * 0.000002  # placeholder; real cost in data["usage"]["cost"] on some models
                if "usage" in data and "cost" in data["usage"]:
                    cost = float(data["usage"]["cost"])
                log.info("LLM call model=%s tokens=%d cost=$%.5f latency=%.2fs",
                         model, tokens, cost, latency)
                _cache_set(key, content)
                return content, cost, latency
            except httpx.HTTPStatusError as e:
                last_err = LLMError(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
                if e.response.status_code not in (429, 500, 502, 503):
                    break
            except Exception as e:
                last_err = LLMError(str(e))
                break

    raise last_err or LLMError("Unknown LLM error")


async def _call_with_fallback(messages: list[dict], response_format: dict | None = None,
                               temperature: float = 0.2) -> tuple[str, float, float]:
    try:
        return await _call(_config.model, messages, response_format, temperature)
    except LLMError as e:
        log.warning("Primary model failed (%s), trying fallback: %s", _config.model, e)
        return await _call(_config.fallback, messages, response_format, temperature)


# ── Public API ────────────────────────────────────────────────────────────────

async def extract(prompt: str, schema: dict) -> dict:
    """
    Extract structured data from text. Enforces JSON-schema output.
    Returns parsed dict. Raises LLMError if output is invalid JSON or fails schema.
    """
    import jsonschema

    messages = [
        {
            "role": "system",
            "content": (
                "You are a financial data extraction assistant. "
                "Extract the requested data from the provided text and return ONLY valid JSON "
                "matching the schema. Do not include any explanation or markdown fences. "
                "If a value is not present in the source, use null."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    response_format = {"type": "json_object"}

    content, cost, latency = await _call_with_fallback(messages, response_format, temperature=0.0)

    # Strip markdown fences if present
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise LLMError(f"LLM returned invalid JSON: {e}\nContent: {content[:300]}")

    try:
        jsonschema.validate(parsed, schema)
    except jsonschema.ValidationError as e:
        raise LLMError(f"LLM output failed schema validation: {e.message}")

    return parsed


async def reason(prompt: str) -> str:
    """Free-form reasoning. Returns raw string."""
    messages = [
        {"role": "system", "content": "You are a financial analysis assistant. Be concise and precise."},
        {"role": "user", "content": prompt},
    ]
    content, _, _ = await _call_with_fallback(messages, temperature=0.3)
    return content


async def narrate(prompt: str) -> str:
    """Final narrative generation. Returns raw string."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a financial analyst writing a professional report for a German Mittelstand company. "
                "Write in clear business English. Be specific and reference the provided findings directly. "
                "Do NOT invent numbers — use only the figures provided in the prompt."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    content, _, _ = await _call_with_fallback(messages, temperature=0.4)
    return content
