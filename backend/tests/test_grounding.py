"""Tests for the grounding gate."""
import pytest
from backend.analysis.ratios import AnalysisResult, RatioResult
from backend.benchmark.flags import BenchmarkResult, BenchmarkFlag
from backend.briefing.grounding import check_grounding


def _make_analysis(values: dict) -> AnalysisResult:
    """Build a minimal AnalysisResult with given finding_id → value pairs."""
    result = AnalysisResult(company_name="Test GmbH")
    for fid, val in values.items():
        period = fid.split(".")[-1] if "." in fid else "2023"
        result.ratios.append(RatioResult(
            finding_id=fid, name=fid, period=period,
            value=val, unit="%", formula="test"
        ))
    return result


def _empty_benchmark() -> BenchmarkResult:
    return BenchmarkResult(company_name="Test GmbH", nace_code="C")


def test_grounded_prose_passes():
    analysis = _make_analysis({"gross_margin.2023": 35.0, "ebit_margin.2023": 18.2})
    bench = _empty_benchmark()
    prose = "The gross margin was 35.0% and EBIT margin reached 18.2%."
    result = check_grounding(prose, analysis, bench)
    assert result.passed, f"Ungrounded: {result.ungrounded}"


def test_invented_number_fails():
    analysis = _make_analysis({"gross_margin.2023": 35.0})
    bench = _empty_benchmark()
    prose = "The gross margin was 35.0% but operating costs rose 99.9%."
    result = check_grounding(prose, analysis, bench)
    assert not result.passed
    assert len(result.ungrounded) > 0


def test_year_references_ignored():
    analysis = _make_analysis({"gross_margin.2023": 35.0})
    bench = _empty_benchmark()
    prose = "In 2023 and 2022, the gross margin was 35.0%."
    result = check_grounding(prose, analysis, bench)
    assert result.passed


def test_zero_always_grounded():
    analysis = _make_analysis({"gross_margin.2023": 35.0})
    bench = _empty_benchmark()
    prose = "Growth was 0% this year."
    result = check_grounding(prose, analysis, bench)
    assert result.passed


def test_tolerance_works():
    # 35.0 in allowed, 35.1 in prose — within 1.5% tolerance
    analysis = _make_analysis({"gross_margin.2023": 35.0})
    bench = _empty_benchmark()
    prose = "Gross margin was approximately 35.1%."
    result = check_grounding(prose, analysis, bench)
    assert result.passed


def test_large_invented_number_fails():
    analysis = _make_analysis({"gross_margin.2023": 35.0})
    bench = _empty_benchmark()
    prose = "The company has €12,500,000 in hidden reserves."
    result = check_grounding(prose, analysis, bench)
    assert not result.passed
