"""Shared CV upload flow — validate, store, extract text, persist to Profile.

Used by both POST /api/profile/cv and POST /api/onboarding/cv, which
previously copy-pasted this block. File writes and text extraction are
blocking I/O, so they run in a worker thread rather than on the event loop.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from shared.cv.extract import SUPPORTED, cv_sha256, extract_cv_text
from shared.repositories import users as users_repo
from shared.storage import get_storage


async def store_and_extract_cv(file: UploadFile, user_id: int, db: Session) -> tuple[str, str, str]:
    """Returns (filename, extracted_text, sha256). Raises HTTPException on
    unsupported type, empty file, missing profile, or extraction failure."""

    filename = file.filename or "cv.bin"
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type {suffix!r}. Supported: {', '.join(SUPPORTED)}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty file")

    profile = users_repo.get_profile(db, user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile not found")

    sha = cv_sha256(content)
    key = f"cvs/user_{user_id}/{sha[:16]}{suffix}"

    def _extract_and_store() -> tuple[str, str]:
        # Extraction needs a real file path; use a temp file so the durable
        # copy can live in any storage backend (local disk or blob bucket).
        # Only a CV that parsed successfully gets stored.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / f"cv{suffix}"
            tmp_path.write_bytes(content)
            text = extract_cv_text(tmp_path)
        return text, get_storage().save(key, content)

    try:
        text, stored_at = await asyncio.to_thread(_extract_and_store)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    profile.cv_filename = filename
    profile.cv_path = stored_at
    profile.cv_text = text
    profile.cv_sha256 = sha
    db.commit()
    return filename, text, sha
