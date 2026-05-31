"""ZIP extraction and multi-company file routing."""
from __future__ import annotations
import io
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".xlsm", ".pdf", ".json"}
MAX_SINGLE_FILE_MB = 500


@dataclass
class CompanyBatch:
    """All files belonging to one company, ready for processing."""
    company_hint: str          # derived from directory or filename prefix
    files: list[tuple[str, bytes]] = field(default_factory=list)  # (filename, content)
    total_bytes: int = 0


def extract_zip(zip_bytes: bytes) -> list[CompanyBatch]:
    """
    Extract a ZIP archive and group files into CompanyBatch objects.

    Grouping logic (in order of priority):
    1. If files are in subdirectories → each subdirectory = one company
    2. If all files are flat → group by filename prefix before first underscore/dash/dot
    3. If only one type of file → treat entire ZIP as one company

    Returns list of CompanyBatch objects, each ready for pipeline processing.
    Skips: hidden files, __MACOSX/, unsupported extensions, files > MAX_SINGLE_FILE_MB.
    """
    batches: dict[str, CompanyBatch] = {}

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        entries = [e for e in zf.infolist()
                   if not e.is_dir()
                   and not PurePosixPath(e.filename).parts[0].startswith((".", "__MACOSX"))
                   and Path(e.filename).suffix.lower() in SUPPORTED_EXTENSIONS
                   and e.file_size <= MAX_SINGLE_FILE_MB * 1024 * 1024]

        if not entries:
            raise ValueError("ZIP contains no supported financial files (.csv, .xlsx, .pdf, .json)")

        # Determine grouping strategy
        dirs = {str(PurePosixPath(e.filename).parent) for e in entries}
        use_dirs = len(dirs) > 1 and not all(d == "." for d in dirs)

        for entry in entries:
            path = PurePosixPath(entry.filename)
            filename = path.name

            if use_dirs:
                group_key = str(path.parent).replace("/", "_").strip("_") or "root"
                company_hint = group_key.replace("_", " ").title()
            else:
                # Flat: group by prefix before first separator
                stem = Path(filename).stem
                for sep in ("_", "-", "."):
                    if sep in stem:
                        group_key = stem.split(sep)[0]
                        break
                else:
                    group_key = "company"
                company_hint = group_key.replace("_", " ").title()

            content = zf.read(entry.filename)
            if group_key not in batches:
                batches[group_key] = CompanyBatch(company_hint=company_hint)
            batches[group_key].files.append((filename, content))
            batches[group_key].total_bytes += len(content)
            log.info("ZIP: assigned %s → group '%s' (%d bytes)", filename, group_key, len(content))

    result = list(batches.values())
    log.info("ZIP: extracted %d company batch(es) from archive", len(result))
    return result
