"""
Grounding gate: verifies every number in LLM-generated prose traces to a
computed value. Ungrounded numbers trigger a rejection.

v1 uses regex extraction of numbers from prose. A future upgrade can use
finding_id placeholders so ungrounded numbers are structurally impossible.
"""
from __future__ import annotations
import re
import logging
from typing import Optional
from backend.analysis.ratios import AnalysisResult
from backend.benchmark.flags import BenchmarkResult

log = logging.getLogger(__name__)

# Regex: match numbers like 12.3, 12,3 (German), 1.234.567, €1.2M, 45%, -3.2
_NUM_RE = re.compile(
    r"""
    (?:€\s*)?                    # optional currency prefix
    -?                           # optional negative
    \d{1,3}(?:[.,]\d{3})*        # integer part (with thousand separators)
    (?:[.,]\d+)?                 # optional decimal part
    (?:\s*[MKBmkb])?             # optional magnitude suffix
    (?:\s*%)?                    # optional percent
    """,
    re.VERBOSE,
)

# Magnitude multipliers
_MAGNITUDE = {"m": 1_000_000, "k": 1_000, "b": 1_000_000_000}


def _normalize(raw: str) -> float | None:
    """Parse a matched number string to float, handling German/English formatting."""
    s = raw.strip().lstrip("€").strip()
    # Extract magnitude suffix
    mult = 1.0
    lower = s.lower()
    for suffix, m in _MAGNITUDE.items():
        if lower.endswith(suffix):
            mult = m
            s = s[:-1].strip()
            break
    # Remove % sign
    is_pct = s.endswith("%")
    if is_pct:
        s = s[:-1].strip()
    # Handle German decimal comma (1.234,56 → 1234.56) vs English (1,234.56)
    if "," in s and "." in s:
        if s.index(",") < s.index("."):
            s = s.replace(",", "")  # 1,234.56 → English thousand sep
        else:
            s = s.replace(".", "").replace(",", ".")  # 1.234,56 → German thousand sep
    elif "," in s:
        # Could be decimal comma (1,5) or thousand separator (12,500,000)
        # Detect thousand separator: comma-separated groups of exactly 3 digits
        parts = s.split(",")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            # Thousand separator pattern: remove commas
            s = s.replace(",", "")
        else:
            # Decimal comma
            s = s.replace(",", ".")
    elif "." in s:
        # Could be decimal point (1.5) or German thousand separator (1.234.567)
        parts = s.split(".")
        if len(parts) > 2 and all(len(p) == 3 for p in parts[1:]):
            # German thousand separator: remove periods
            s = s.replace(".", "")
        # else: normal decimal point, leave as-is
    try:
        v = float(s) * mult
        return v
    except ValueError:
        return None


def _build_allowed_values(analysis: AnalysisResult, benchmark: BenchmarkResult) -> dict[str, float]:
    """Collect all computed numbers that are allowed to appear in the narrative."""
    allowed: dict[str, float] = {}

    for r in analysis.ratios:
        if not r.not_derivable and r.value is not None:
            allowed[r.finding_id] = r.value

    for f in benchmark.flags:
        allowed[f"flag.{f.finding_id}.company"] = f.company_value
        allowed[f"flag.{f.finding_id}.median"] = f.peer_median
        allowed[f"flag.{f.finding_id}.delta"] = f.delta_vs_median

    return allowed


def _is_grounded(value: float, allowed: dict[str, float], tolerance: float = 0.015) -> bool:
    """Check if value is within tolerance of any allowed computed value."""
    if value == 0:
        return True  # 0 is always grounded
    for av in allowed.values():
        if av == 0:
            continue
        if abs(value - av) / max(abs(av), 1e-9) <= tolerance:
            return True
        # Also check if value is the negative of an allowed value
        if abs(value + av) / max(abs(av), 1e-9) <= tolerance:
            return True
    return False


class GroundingResult:
    def __init__(self, passed: bool, ungrounded: list[str], checked: int):
        self.passed = passed
        self.ungrounded = ungrounded  # list of ungrounded number strings
        self.checked = checked


def check_grounding(prose: str, analysis: AnalysisResult,
                    benchmark: BenchmarkResult) -> GroundingResult:
    """
    Extract all numbers from prose and verify each traces to a computed value.
    Returns GroundingResult with pass/fail and list of ungrounded numbers.
    """
    allowed = _build_allowed_values(analysis, benchmark)
    matches = _NUM_RE.findall(prose)

    ungrounded = []
    checked = 0

    for raw in matches:
        raw = raw.strip()
        if not raw or raw in ("0", "1", "2", "3"):
            continue  # skip trivial integers (years, counts)
        # Skip pure year references (4-digit years like 2023)
        if re.fullmatch(r"\d{4}", raw):
            continue
        # Skip 3-digit numbers that look like year fragments (e.g. "202" from "2023")
        if re.fullmatch(r"20\d", raw):
            continue
        value = _normalize(raw)
        if value is None:
            continue
        # Skip very small numbers (e.g. multipliers, counts)
        if abs(value) < 0.5:
            continue
        checked += 1
        if not _is_grounded(value, allowed):
            ungrounded.append(raw)
            log.warning("Grounding: ungrounded number '%s' (normalized: %s)", raw, value)

    passed = len(ungrounded) == 0
    return GroundingResult(passed=passed, ungrounded=ungrounded, checked=checked)


NUMBER_RE = re.compile(r"""
    (?:€\s*)?                      # optional euro sign
    -?                             # optional negative
    \d{1,3}(?:[.,]\d{3})*         # integer part with optional thousand separators
    (?:[.,]\d+)?                   # optional decimal
    (?:\s*%|\s*[xX]|\s*days?)?    # optional unit
""", re.VERBOSE)

TOLERANCE = 0.015  # 1.5% — allows for prose rounding


def _normalize_simple(s: str) -> float:
    """Strip currency/unit symbols and parse to float (simple version for verify_grounding)."""
    s = re.sub(r"[€%xXdays\s]", "", s)
    s = s.replace(",", ".")
    # Handle thousand-separator dots: 1.234.567 → 1234567
    parts = s.split(".")
    if len(parts) > 2:
        s = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _extract_numbers_simple(text: str) -> list[tuple[str, float]]:
    """Return list of (raw_match, normalized_value) from prose."""
    results = []
    for m in NUMBER_RE.finditer(text):
        raw = m.group().strip()
        if not raw:
            continue
        val = _normalize_simple(raw)
        if val != val:  # NaN check
            continue
        results.append((raw, val))
    return results


def _is_grounded_simple(val: float, computed: dict[str, float]) -> bool:
    """Check if val is within tolerance of any computed value."""
    if abs(val) < 0.001:  # skip near-zeros (years, page numbers etc.)
        return True
    for cv in computed.values():
        if cv is None or cv == 0:
            continue
        if abs(val - cv) / max(abs(cv), 1e-6) <= TOLERANCE:
            return True
        # Also allow values expressed in millions
        if abs(val * 1_000_000 - cv) / max(abs(cv), 1e-6) <= TOLERANCE:
            return True
        if abs(val * 1_000 - cv) / max(abs(cv), 1e-6) <= TOLERANCE:
            return True
    return False


def verify_grounding(
    narrative: str,
    analysis: AnalysisResult,
    projections: Optional[list] = None,
) -> list[str]:
    """
    Returns list of ungrounded number strings.
    Empty list = all numbers are grounded = safe to publish.
    Compatible with the strategy.projections.ProjectionResult interface.
    """
    computed = analysis.all_values()
    if projections:
        for p in projections:
            if hasattr(p, "as_dict"):
                computed.update(p.as_dict())

    ungrounded = []
    for raw, val in _extract_numbers_simple(narrative):
        # Skip year-like numbers (4-digit numbers starting with 20xx or 19xx)
        if re.fullmatch(r"(?:19|20)\d{2}", raw.strip()):
            continue
        # Skip very small absolute values
        if abs(val) < 0.5:
            continue
        if not _is_grounded_simple(val, computed):
            ungrounded.append(raw)

    if ungrounded:
        log.warning("Grounding check found %d ungrounded numbers: %s",
                    len(ungrounded), ungrounded)
    return ungrounded
