"""ZIP ingestion module: opens a company dataset ZIP and produces a structured DatasetContext."""
from __future__ import annotations

import io
import logging
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Union

from backend.intake.parsers import parse_csv, parse_docx, parse_excel, parse_pdf

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Folder-name routing patterns (case-insensitive substring matches)
# ---------------------------------------------------------------------------
_ANNUAL_PATS    = ("jahresbericht", "annual")
_ACCOUNTING_PATS = ("buchhaltung", "accounting", "buchungsjournal")
_PAYROLL_PATS   = ("personal", "lohn", "hr", "payroll")
_COMPLIANCE_PATS = ("compliance",)
_PROJECT_PATS   = ("projekt", "project")
_INVOICE_PATS   = ("rechnung", "invoice")
_CONTRACT_PATS  = ("vertrag", "contract")
_MINUTES_PATS   = ("protokoll", "minutes", "meeting")
_QA_PATS        = ("qualit", "qa", "quality")

_YEAR_RE = re.compile(r"((?:19|20)\d{2})")


def _extract_year(path_str: str) -> str | None:
    """Return the first 4-digit year found in *path_str*, or None."""
    m = _YEAR_RE.search(path_str)
    return m.group(1) if m else None


def _normalize_german(text: str) -> str:
    """Strip German umlauts/ß to ASCII base chars for substring pattern matching.

    Stripping (ä→a) rather than expanding (ä→ae) ensures patterns like "vertrag"
    still match "Verträge" (vertrage) after normalization.
    """
    return (text.lower()
            .replace("ä", "a").replace("ö", "o").replace("ü", "u")
            .replace("ß", "ss"))


def _folder_matches(folder: str, patterns: tuple[str, ...]) -> bool:
    folder_lower = folder.lower()
    folder_norm = _normalize_german(folder)
    return any(p in folder_lower or p in folder_norm for p in patterns)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[truncated]"


def _parse_file(name: str, data: bytes) -> str:
    """Dispatch to the right parser based on file extension."""
    ext = PurePosixPath(name).suffix.lower()
    try:
        if ext == ".pdf":
            return parse_pdf(data)
        if ext in (".xlsx", ".xls", ".xlsm"):
            return parse_excel(data)
        if ext == ".csv":
            return parse_csv(data)
        if ext == ".docx":
            return parse_docx(data)
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to parse %s: %s", name, exc)
        return ""
    log.debug("Skipping unsupported extension %s for %s", ext, name)
    return ""


def _fix_zip_filename(name: str) -> str:
    """Recover UTF-8 filenames that were stored without the UTF-8 flag.

    Python's zipfile decodes untagged filenames using cp437. When the creator
    used UTF-8 bytes without setting bit 11 of the general-purpose bit flag
    (common in Windows-created ZIPs), non-ASCII chars become mojibake.
    Re-encoding as cp437 and decoding as UTF-8 recovers the original name.
    """
    try:
        return name.encode("cp437").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return name


# ---------------------------------------------------------------------------
# DatasetContext
# ---------------------------------------------------------------------------

@dataclass
class DatasetContext:
    """Structured representation of all data extracted from a company ZIP."""

    company_name: str
    total_files: int = 0
    years: list[str] = field(default_factory=list)

    # year -> text (max chars enforced at ingest time)
    annual_reports: dict[str, str] = field(default_factory=dict)
    accounting_journals: dict[str, str] = field(default_factory=dict)
    payroll_journals: dict[str, str] = field(default_factory=dict)
    compliance_reports: dict[str, str] = field(default_factory=dict)

    # project_id -> list[text]
    project_reports: dict[str, list[str]] = field(default_factory=dict)

    # year -> list[text]
    invoices: dict[str, list[str]] = field(default_factory=dict)

    contracts: list[str] = field(default_factory=list)
    meeting_minutes: list[str] = field(default_factory=list)
    qa_reports: list[str] = field(default_factory=list)
    other_docs: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """Return a human-readable summary of all available data."""
        lines: list[str] = [
            f"Company: {self.company_name}",
            f"Total files processed: {self.total_files}",
        ]
        if self.years:
            lines.append(f"Years covered: {self.years[0]} – {self.years[-1]}")

        def _yr_range(d: dict) -> str:
            keys = sorted(d.keys())
            if not keys:
                return "none"
            return f"{keys[0]}–{keys[-1]} ({len(keys)} year(s))"

        lines.append(f"Annual reports:       {_yr_range(self.annual_reports)}")
        lines.append(f"Accounting journals:  {_yr_range(self.accounting_journals)}")
        lines.append(f"Payroll journals:     {_yr_range(self.payroll_journals)}")
        lines.append(f"Compliance reports:   {_yr_range(self.compliance_reports)}")

        if self.project_reports:
            total_proj = sum(len(v) for v in self.project_reports.values())
            lines.append(
                f"Project reports:      {len(self.project_reports)} project(s), "
                f"{total_proj} document(s)"
            )
        else:
            lines.append("Project reports:      none")

        if self.invoices:
            total_inv = sum(len(v) for v in self.invoices.values())
            lines.append(
                f"Invoices:             {_yr_range(self.invoices)}, "
                f"{total_inv} document(s)"
            )
        else:
            lines.append("Invoices:             none")

        lines.append(f"Contracts:            {len(self.contracts)} document(s)")
        lines.append(f"Meeting minutes:      {len(self.meeting_minutes)} document(s)")
        lines.append(f"QA reports:           {len(self.qa_reports)} document(s)")
        lines.append(f"Other docs:           {len(self.other_docs)} document(s)")
        return "\n".join(lines)

    # ------------------------------------------------------------------

    def annual_report_consolidated(self, max_chars: int = 8000) -> str:
        """Concatenate all annual reports, most recent first, up to *max_chars*."""
        if not self.annual_reports:
            return ""
        parts: list[str] = []
        remaining = max_chars
        for year in sorted(self.annual_reports.keys(), reverse=True):
            header = f"\n\n=== Annual Report {year} ===\n"
            body = self.annual_reports[year]
            chunk = header + body
            if remaining <= 0:
                break
            parts.append(chunk[:remaining])
            remaining -= len(chunk)
        return "".join(parts)

    def payroll_consolidated(self, max_chars: int = 4000) -> str:
        """Concatenate all payroll journals, most recent first, up to *max_chars*."""
        if not self.payroll_journals:
            return ""
        parts: list[str] = []
        remaining = max_chars
        for year in sorted(self.payroll_journals.keys(), reverse=True):
            header = f"\n\n=== Payroll {year} ===\n"
            body = self.payroll_journals[year]
            chunk = header + body
            if remaining <= 0:
                break
            parts.append(chunk[:remaining])
            remaining -= len(chunk)
        return "".join(parts)

    def project_consolidated(self, max_chars: int = 4000) -> str:
        """Concatenate all project reports up to *max_chars*."""
        if not self.project_reports:
            return ""
        parts: list[str] = []
        remaining = max_chars
        for proj_id, texts in sorted(self.project_reports.items()):
            header = f"\n\n=== Project {proj_id} ===\n"
            body = "\n---\n".join(texts)
            chunk = header + body
            if remaining <= 0:
                break
            parts.append(chunk[:remaining])
            remaining -= len(chunk)
        return "".join(parts)

    def compliance_consolidated(self, max_chars: int = 4000) -> str:
        """Concatenate all compliance reports, most recent first, up to *max_chars*."""
        if not self.compliance_reports:
            return ""
        parts: list[str] = []
        remaining = max_chars
        for year in sorted(self.compliance_reports.keys(), reverse=True):
            header = f"\n\n=== Compliance {year} ===\n"
            body = self.compliance_reports[year]
            chunk = header + body
            if remaining <= 0:
                break
            parts.append(chunk[:remaining])
            remaining -= len(chunk)
        return "".join(parts)


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def ingest_zip(filename: str, content: bytes) -> DatasetContext:
    """
    Open *content* as a ZIP archive, parse all recognisable files, and return
    a populated :class:`DatasetContext`.

    If *content* is not a valid ZIP the function returns a minimal context
    with only ``company_name`` set (derived from *filename*).
    """
    # Derive a fallback company name from the ZIP filename
    stem = PurePosixPath(filename).stem
    # Replace common separators with spaces for readability
    company_name_fallback = re.sub(r"[_\-]+", " ", stem).strip()

    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        log.warning("ingest_zip: %s is not a valid ZIP file – returning empty context", filename)
        return DatasetContext(company_name=company_name_fallback)

    with zf:
        # Fix cp437 mojibake on filenames stored without the UTF-8 flag
        all_names = [_fix_zip_filename(n) for n in zf.namelist() if not n.endswith("/")]
        # Build mapping: fixed name → original name (for zf.read)
        _name_map = {_fix_zip_filename(n): n for n in zf.namelist()}

        # Detect company name from the top-level folder (if present)
        company_name = company_name_fallback
        top_folders = {n.split("/")[0] for n in all_names if "/" in n}
        if len(top_folders) == 1:
            company_name = re.sub(r"[_\-]+", " ", top_folders.pop()).strip()
        elif top_folders:
            # Multiple top-level dirs: use the stem of the ZIP filename
            log.debug("Multiple top-level dirs detected; using ZIP filename as company name")

        ctx = DatasetContext(company_name=company_name, total_files=len(all_names))
        all_years: set[str] = set()

        for name in all_names:
            parts = name.split("/")
            # The folder segment just below the company root (or the first segment
            # if there is no company root).
            if len(parts) >= 2:
                category_folder = parts[1] if len(top_folders) <= 1 else parts[0]
            else:
                category_folder = ""

            year = _extract_year(name)
            if year:
                all_years.add(year)

            # Read raw bytes using the original (un-fixed) filename as stored in ZIP
            try:
                data = zf.read(_name_map.get(name, name))
            except Exception as exc:  # noqa: BLE001
                log.warning("Cannot read %s from ZIP: %s", name, exc)
                continue

            # Parse text
            text = _parse_file(name, data)
            if not text:
                continue

            # ----------------------------------------------------------------
            # Route by category folder
            # ----------------------------------------------------------------

            if _folder_matches(category_folder, _ANNUAL_PATS):
                key = year or "unknown"
                existing = ctx.annual_reports.get(key, "")
                if not existing:
                    ctx.annual_reports[key] = _truncate(text, 4000)
                    log.debug("[OK] annual_report year=%s file=%s", key, name)

            elif _folder_matches(category_folder, _ACCOUNTING_PATS):
                key = year or "unknown"
                existing = ctx.accounting_journals.get(key, "")
                if not existing:
                    ctx.accounting_journals[key] = _truncate(text, 3000)
                    log.debug("[OK] accounting_journal year=%s file=%s", key, name)

            elif _folder_matches(category_folder, _PAYROLL_PATS):
                key = year or "unknown"
                existing = ctx.payroll_journals.get(key, "")
                if not existing:
                    ctx.payroll_journals[key] = _truncate(text, 3000)
                    log.debug("[OK] payroll_journal year=%s file=%s", key, name)

            elif _folder_matches(category_folder, _COMPLIANCE_PATS):
                key = year or "unknown"
                existing = ctx.compliance_reports.get(key, "")
                if not existing:
                    ctx.compliance_reports[key] = _truncate(text, 3000)
                    log.debug("[OK] compliance_report year=%s file=%s", key, name)

            elif _folder_matches(category_folder, _PROJECT_PATS):
                # Project ID: the immediate parent directory of the file
                proj_parts = name.split("/")
                # Find a subfolder that looks like a project id (non-category folder)
                if len(proj_parts) >= 3:
                    proj_id = proj_parts[-2]  # e.g. Projektberichte/PRJ-001/report.pdf
                else:
                    proj_id = year or "unknown"
                bucket = ctx.project_reports.setdefault(proj_id, [])
                if len(bucket) < 5:
                    bucket.append(_truncate(text, 1000))
                    log.debug("[OK] project_report proj=%s file=%s", proj_id, name)

            elif _folder_matches(category_folder, _INVOICE_PATS):
                key = year or "unknown"
                bucket = ctx.invoices.setdefault(key, [])
                if len(bucket) < 10:
                    bucket.append(_truncate(text, 500))
                    log.debug("[OK] invoice year=%s file=%s", key, name)

            elif _folder_matches(category_folder, _CONTRACT_PATS):
                if len(ctx.contracts) < 20:
                    ctx.contracts.append(_truncate(text, 1000))
                    log.debug("[OK] contract file=%s", name)

            elif _folder_matches(category_folder, _MINUTES_PATS):
                if len(ctx.meeting_minutes) < 20:
                    ctx.meeting_minutes.append(_truncate(text, 1000))
                    log.debug("[OK] meeting_minutes file=%s", name)

            elif _folder_matches(category_folder, _QA_PATS):
                if len(ctx.qa_reports) < 20:
                    ctx.qa_reports.append(_truncate(text, 1000))
                    log.debug("[OK] qa_report file=%s", name)

            else:
                if len(ctx.other_docs) < 10:
                    ctx.other_docs.append(_truncate(text, 500))
                    log.debug("[OK] other_doc file=%s", name)

        # Finalise year list
        ctx.years = sorted(all_years)

    log.info(
        "ingest_zip complete: company=%r files=%d years=%s "
        "annual=%d accounting=%d payroll=%d compliance=%d "
        "projects=%d invoices_buckets=%d contracts=%d "
        "minutes=%d qa=%d other=%d",
        ctx.company_name,
        ctx.total_files,
        ctx.years,
        len(ctx.annual_reports),
        len(ctx.accounting_journals),
        len(ctx.payroll_journals),
        len(ctx.compliance_reports),
        len(ctx.project_reports),
        len(ctx.invoices),
        len(ctx.contracts),
        len(ctx.meeting_minutes),
        len(ctx.qa_reports),
        len(ctx.other_docs),
    )
    return ctx
