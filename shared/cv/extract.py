"""CV text extraction. Follows the ingest guide §2 ("Load") pattern:
a small pure function with optional dependencies imported INSIDE the
branch that needs them — so `pypdf` and `python-docx` are not loaded
unless the user actually uploads a PDF or DOCX.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


SUPPORTED = (".pdf", ".docx", ".txt", ".md")


def _load_pdf(path: Path) -> str:
    try:
        import pypdf  # lazy
    except ImportError as exc:
        raise RuntimeError("pypdf is required for PDF CV uploads") from exc
    reader = pypdf.PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
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
