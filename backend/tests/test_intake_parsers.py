"""Tests for document parsers (no LLM needed)."""
import pytest
from pathlib import Path
from backend.intake.parsers import parse_csv, parse_document


SAMPLE_CSV = """Company,Metric,2023,2022
Mustermann GmbH,Revenue,9800000,9100000
Mustermann GmbH,COGS,6370000,5915000
"""


def test_parse_csv_returns_string():
    result = parse_csv(SAMPLE_CSV)
    assert "9800000" in result
    assert "Revenue" in result


def test_parse_document_csv():
    result = parse_document("test.csv", SAMPLE_CSV.encode())
    assert "9800000" in result


def test_parse_document_txt():
    result = parse_document("test.txt", b"Revenue: 9,800,000")
    assert "Revenue" in result
