"""
Grounding gate: enforce that every number in LLM prose traces to the FactsStore.

Usage:
    clean_text = enforce_grounding(raw_text, facts_store)
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.facts.facts_store import FactsStore

log = logging.getLogger(__name__)

# Matches numbers with optional euro prefix, sign, magnitude suffix, %
_NUM_RE = re.compile(
    r"""
    (?:EUR\s*|€\s*)?          # optional currency prefix
    -?                         # optional negative sign
    \d{1,3}(?:[.,]\d{3})*     # integer part (possibly with thousand separators)
    (?:[.,]\d+)?               # optional decimal
    (?:\s*[MKBmkb])?           # optional magnitude suffix
    (?:\s*%)?                  # optional percent
    """,
    re.VERBOSE,
)
_MAGNITUDE: dict[str, float] = {"m": 1_000_000.0, "k": 1_000.0, "b": 1_000_000_000.0}
_TOLERANCE = 0.015          # 1.5% rounding tolerance
_MIN_INTERESTING = 0.5      # ignore trivial values below this


def _parse_num(raw: str) -> float | None:
    """Parse a matched token to float, handling German/English formatting and magnitude suffixes."""
    s = raw.strip()
    s = re.sub(r"[€\s]", "", s)  # remove euro sign and spaces
    s = re.sub(r"^EUR", "", s, flags=re.IGNORECASE).strip()

    # Magnitude suffix
    mult = 1.0
    if s and s[-1].lower() in _MAGNITUDE:
        mult = _MAGNITUDE[s[-1].lower()]
        s = s[:-1].strip()

    # Percent
    if s.endswith("%"):
        s = s[:-1].strip()

    # German vs English decimal/thousand separators
    if "," in s and "." in s:
        if s.index(",") < s.index("."):
            s = s.replace(",", "")               # 1,234.56 → English thousand sep
        else:
            s = s.replace(".", "").replace(",", ".")  # 1.234,56 → German
    elif "," in s:
        parts = s.split(",")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            s = s.replace(",", "")               # thousand sep
        else:
            s = s.replace(",", ".")              # decimal comma
    elif "." in s:
        parts = s.split(".")
        if len(parts) > 2 and all(len(p) == 3 for p in parts[1:]):
            s = s.replace(".", "")               # German thousand sep

    try:
        return float(s) * mult
    except ValueError:
        return None


def _is_grounded(val: float, allowed: dict[str, float]) -> bool:
    if abs(val) < _MIN_INTERESTING:
        return True   # small/zero values always allowed
    for av in allowed.values():
        if av is None or av == 0:
            continue
        ratio = abs(val - av) / max(abs(av), 1e-9)
        if ratio <= _TOLERANCE:
            return True
        # Also check magnitude-scaled versions (report may say "4.2M" for 4_200_000)
        for scale in (1_000_000.0, 1_000.0, 1_000_000_000.0):
            if abs(val * scale - av) / max(abs(av), 1e-9) <= _TOLERANCE:
                return True
            if abs(val - av / scale) / max(abs(av / scale), 1e-9) <= _TOLERANCE:
                return True
    return False


def _is_year(raw: str) -> bool:
    return bool(re.fullmatch(r"(?:19|20)\d{2}", raw.strip()))


def _extract_numbers(text: str) -> list[tuple[str, float]]:
    results = []
    for m in _NUM_RE.finditer(text):
        raw = m.group().strip()
        if not raw or _is_year(raw) or raw in ("0", "1", "2", "3"):
            continue
        val = _parse_num(raw)
        if val is None or abs(val) < _MIN_INTERESTING:
            continue
        results.append((raw, val))
    return results


def _strip_ungrounded_sentences(text: str, allowed: dict[str, float]) -> tuple[str, int]:
    """
    Split text into sentences, strip any sentence where >50% of its numeric
    tokens are ungrounded. Returns (cleaned_text, num_stripped).
    """
    # Rough sentence splitter: split on ". " or ".\n" keeping delimiter
    sentences = re.split(r"(?<=[.!?])\s+", text)
    clean: list[str] = []
    stripped = 0
    for sent in sentences:
        nums = _extract_numbers(sent)
        if not nums:
            clean.append(sent)
            continue
        bad = [n for n in nums if not _is_grounded(n[1], allowed)]
        if len(bad) > len(nums) * 0.5:
            log.warning("Grounding gate stripped sentence with %d/%d ungrounded numbers: %s",
                        len(bad), len(nums), sent[:100])
            stripped += 1
            continue
        clean.append(sent)
    return " ".join(clean), stripped


def enforce_grounding(text: str, facts_store: "FactsStore") -> str:
    """
    Verify every number in *text* against *facts_store*.
    Sentences with >50% ungrounded numbers are stripped.
    Returns cleaned text.

    If facts_store is empty or has no values, text is returned unchanged
    (avoids stripping everything when no facts were computed).
    """
    if not text:
        return text
    allowed = facts_store.all_values() if facts_store else {}
    if not allowed:
        return text  # no facts to check against — skip gate

    clean, n_stripped = _strip_ungrounded_sentences(text, allowed)
    if n_stripped:
        log.info("Grounding gate: stripped %d sentence(s) from report", n_stripped)
    return clean


def cross_section_consistency_check(room_reports: dict[str, str]) -> dict[str, list[float]]:
    """
    Find metrics (numeric tokens) that appear in ≥2 sections with different values.
    Returns {token: [distinct_values]} for any token with >1 distinct value.
    """
    # Simple approach: collect all numbers from each section and find numeric tokens
    # that appear in multiple sections with different magnitudes.
    token_sections: dict[str, set[float]] = {}

    for room_name, text in room_reports.items():
        for raw, val in _extract_numbers(text):
            key = raw.strip().lower()
            if _is_year(key):
                continue
            token_sections.setdefault(key, set()).add(round(val, 4))

    inconsistent: dict[str, list[float]] = {}
    for tok, vals in token_sections.items():
        if len(vals) > 1:
            inconsistent[tok] = sorted(vals)

    if inconsistent:
        log.warning(
            "Cross-section consistency: %d numeric tokens appear with different values across sections",
            len(inconsistent),
        )
    return inconsistent
