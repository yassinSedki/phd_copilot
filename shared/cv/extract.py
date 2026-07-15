"""CV text extraction. Follows the ingest guide §2 ("Load") pattern:
a small pure function with optional dependencies imported INSIDE the
branch that needs them — so `pypdf` and `python-docx` are not loaded
unless the user actually uploads a PDF or DOCX.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


SUPPORTED = (".pdf", ".docx", ".txt", ".md")


def _extract_page_text(page) -> str:
    # "layout" mode preserves left-to-right reading order for multi-column
    # CVs (a common resume layout) — pypdf's default mode frequently
    # interleaves columns line-by-line, scrambling the text. Fall back to
    # default extraction on older pypdf versions or pages layout mode
    # chokes on.
    try:
        text = page.extract_text(extraction_mode="layout")
        if text and text.strip():
            return text
    except Exception:
        pass
    try:
        return page.extract_text() or ""
    except Exception:
        return ""


_RUN_OF_SPACES = re.compile(r"[ \t]{2,}")
_RUN_OF_BLANK_LINES = re.compile(r"\n{3,}")


def _normalize_layout_whitespace(text: str) -> str:
    """"layout" extraction pads text with spaces/blank lines to mirror each
    glyph's x/y position on the page — designer CVs with letter-spacing or
    justified headers turn into "Sed     ki" and pages of empty lines.
    Collapsing runs of spaces/blank lines keeps the column ordering layout
    mode gives us while making the text readable and compact."""
    lines = [_RUN_OF_SPACES.sub(" ", line).strip() for line in text.split("\n")]
    return _RUN_OF_BLANK_LINES.sub("\n\n", "\n".join(lines).strip())


def _load_pdf(path: Path) -> str:
    try:
        import pypdf  # lazy
    except ImportError as exc:
        raise RuntimeError("pypdf is required for PDF CV uploads") from exc
    reader = pypdf.PdfReader(str(path))
    parts = [_normalize_layout_whitespace(_extract_page_text(page)) for page in reader.pages]
    return "\n".join(parts)


def _load_docx(path: Path) -> str:
    try:
        import docx  # python-docx, lazy
    except ImportError as exc:
        raise RuntimeError("python-docx is required for DOCX CV uploads") from exc
    document = docx.Document(str(path))
    return "\n".join(p.text for p in document.paragraphs)


def extract_cv_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(path).strip()
    if suffix == ".docx":
        return _load_docx(path).strip()
    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="replace").strip()
    raise ValueError(f"Unsupported CV file type: {suffix}. Supported: {SUPPORTED}")


def cv_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
