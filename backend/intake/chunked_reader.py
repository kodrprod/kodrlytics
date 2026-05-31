"""Chunked reading for large financial files. Avoids loading GBs into memory at once."""
from __future__ import annotations
import io
import logging
from typing import Iterator
import pandas as pd

log = logging.getLogger(__name__)

CHUNK_ROWS = 50_000


def read_csv_chunked(content: bytes, encoding: str = "utf-8") -> Iterator[pd.DataFrame]:
    """Yield DataFrames in chunks of CHUNK_ROWS rows."""
    try:
        text = content.decode(encoding)
    except UnicodeDecodeError:
        text = content.decode("latin-1", errors="replace")

    reader = pd.read_csv(io.StringIO(text), chunksize=CHUNK_ROWS,
                         thousands=",", decimal=".")
    for chunk in reader:
        yield chunk


def read_excel_chunked(content: bytes) -> Iterator[pd.DataFrame]:
    """Read each sheet of an Excel file, yielding one DataFrame per sheet."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        headers = [str(c) if c is not None else f"col_{i}" for i, c in enumerate(rows[0])]
        data = rows[1:]
        # Yield in chunks
        for i in range(0, len(data), CHUNK_ROWS):
            chunk_data = data[i:i + CHUNK_ROWS]
            df = pd.DataFrame(chunk_data, columns=headers)
            df.name = sheet_name  # type: ignore
            log.info("Excel chunk: sheet=%s rows=%d-%d", sheet_name, i, i + len(chunk_data))
            yield df
    wb.close()


def dataframe_to_text_summary(df: pd.DataFrame, max_rows: int = 200) -> str:
    """Convert a DataFrame to a compact text representation for LLM extraction."""
    sample = df.head(max_rows)
    lines = [f"Columns: {', '.join(str(c) for c in sample.columns)}",
             f"Rows shown: {len(sample)} of {len(df)}",
             sample.to_string(index=False, max_cols=20)]
    return "\n".join(lines)
