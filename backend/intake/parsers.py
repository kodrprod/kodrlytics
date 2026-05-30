"""Document parsers: PDF, Excel, CSV → raw text / dict for LLM extraction."""
from __future__ import annotations
import csv
import io
from pathlib import Path
from typing import Union


def parse_csv(source: Union[str, bytes, Path]) -> str:
    """Return CSV content as a formatted string for the LLM."""
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8-sig")
    elif isinstance(source, bytes):
        text = source.decode("utf-8-sig")
    else:
        text = source
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    return "\n".join("\t".join(row) for row in rows)


def parse_excel(source: Union[bytes, Path]) -> str:
    """Return all sheets as tab-separated text."""
    import openpyxl
    if isinstance(source, Path):
        wb = openpyxl.load_workbook(source, data_only=True)
    else:
        wb = openpyxl.load_workbook(io.BytesIO(source), data_only=True)
    parts = []
    for name in wb.sheetnames:
        ws = wb[name]
        parts.append(f"=== Sheet: {name} ===")
        for row in ws.iter_rows(values_only=True):
            parts.append("\t".join("" if v is None else str(v) for v in row))
    return "\n".join(parts)


def parse_pdf(source: Union[bytes, Path]) -> str:
    """Extract text from all pages of a PDF."""
    import pdfplumber
    if isinstance(source, Path):
        pdf = pdfplumber.open(source)
    else:
        pdf = pdfplumber.open(io.BytesIO(source))
    pages = []
    with pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n\n".join(pages)


def parse_document(filename: str, content: bytes) -> str:
    """Dispatch to the right parser based on file extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return parse_pdf(content)
    elif ext in (".xlsx", ".xls"):
        return parse_excel(content)
    elif ext == ".csv":
        return parse_csv(content)
    else:
        # Try as UTF-8 text (e.g. .txt, .tsv)
        return content.decode("utf-8", errors="replace")
