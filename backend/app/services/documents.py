"""Unified document service — cover_letter | sop | research_proposal
(Phase 10). Supersedes the cover-letter-only flow in
`backend/app/services/cover_letters.py` (kept, deprecated, for the
pre-existing `/cover-letter` endpoints — new work should use this).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.models import Application, DocumentVersion, Profile, Score
from shared.repositories import document_versions as doc_repo
from shared.services import state_machine as sm
from shared.llm import LLMClient, get_llm

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "worker" / "pipeline" / "draft" / "templates"

_TEMPLATE_FILES = {
    "cover_letter": "cover_letter.md",
    "sop": "sop.md",
    "research_proposal": "research_proposal.md",
}

DOC_TYPES = tuple(_TEMPLATE_FILES.keys())


class UnknownDocType(Exception):
    pass


def _load_template(doc_type: str) -> str:
    if doc_type not in _TEMPLATE_FILES:
        raise UnknownDocType(doc_type)
    return (TEMPLATE_DIR / _TEMPLATE_FILES[doc_type]).read_text(encoding="utf-8")


def _profile_payload(profile: Optional[Profile]) -> dict:
    if profile is None:
        return {}
    return {
        "full_name": profile.full_name,
        "research_summary": profile.research_summary,
        "interests": profile.interests,
        "skills": profile.skills,
        "languages": profile.languages,
        "publications": profile.publications,
        "cv_text": (profile.cv_text or "")[:8000],
        "cv_filename": profile.cv_filename,
    }


def _listing_payload(application: Application) -> dict:
    listing = application.listing
    return {
        "title": listing.title,
        "institution": listing.institution,
        "country": listing.country,
        "city": listing.city,
        "research_field": listing.research_field,
        "description": listing.description,
        "funding_info": listing.funding_info,
    }


def _latest_red_flags(db: Session, application: Application) -> list[str]:
    score = db.scalar(
        select(Score)
        .where(Score.listing_id == application.listing_id, Score.user_id == application.user_id)
        .order_by(Score.scored_at.desc())
        .limit(1)
    )
    return list(score.red_flags or []) if score else []


def get_current(db: Session, application: Application, doc_type: str) -> Optional[DocumentVersion]:
    return doc_repo.get_latest(db, application.user_id, application.id, doc_type)


def list_versions(db: Session, application: Application, doc_type: str) -> list[DocumentVersion]:
    return doc_repo.list_for_document(db, application.user_id, application.id, doc_type)


def generate(db: Session, application: Application, profile: Optional[Profile], doc_type: str) -> DocumentVersion:
    template = _load_template(doc_type)
    settings = get_settings()
    llm: LLMClient = get_llm(settings.llm, role="drafter")
    red_flags = _latest_red_flags(db, application)

    drafted = llm.draft_document(_profile_payload(profile), _listing_payload(application), template, doc_type, red_flags)

    existing = list_versions(db, application, doc_type)
    next_version = (existing[0].version_number + 1) if existing else 1

    version = doc_repo.create(
        db,
        application.user_id,
        application_id=application.id,
        doc_type=doc_type,
        version_number=next_version,
        body_markdown=drafted.body_markdown,
        created_by="agent",
        author_notes=drafted.author_notes,
        warnings=drafted.warnings,
        chat_history=[
            {"role": "assistant", "content": drafted.author_notes or "Here's your draft.", "at": None},
        ],
    )

    if doc_type == "cover_letter" and application.status == sm.SAVED:
        application.status = sm.IN_PROGRESS
        db.commit()

    return version


def refine(
    db: Session,
    application: Application,
    profile: Optional[Profile],
    doc_type: str,
    user_message: str,
) -> tuple[DocumentVersion, str]:
    current = get_current(db, application, doc_type)
    if current is None:
        current = generate(db, application, profile, doc_type)

    settings = get_settings()
    llm: LLMClient = get_llm(settings.llm, role="refiner")

    history = list(current.chat_history or [])
    refined = llm.refine_document(
        doc_type,
        current.body_markdown,
        [{"role": h.get("role", "user"), "content": h.get("content", "")} for h in history],
        user_message,
        profile=_profile_payload(profile),
        listing=_listing_payload(application),
    )

    history.append({"role": "user", "content": user_message, "at": None})
    history.append({"role": "assistant", "content": refined.assistant_reply, "at": None})

    next_version = current.version_number + 1
    version = doc_repo.create(
        db,
        application.user_id,
        application_id=application.id,
        doc_type=doc_type,
        version_number=next_version,
        body_markdown=refined.body_markdown,
        created_by="agent",
        chat_history=history,
    )
    return version, refined.assistant_reply


def save_edit(db: Session, application: Application, doc_type: str, body_markdown: str) -> DocumentVersion:
    """The user writing their own change directly (as opposed to /chat asking
    the AI). Saved as a new version so it shows up in history/revert like
    every other change."""
    current = get_current(db, application, doc_type)
    next_version = (current.version_number + 1) if current else 1
    return doc_repo.create(
        db,
        application.user_id,
        application_id=application.id,
        doc_type=doc_type,
        version_number=next_version,
        body_markdown=body_markdown,
        created_by="user",
        chat_history=list(current.chat_history or []) if current else [],
    )


class PdfUnavailable(Exception):
    pass


_PDF_TYPOGRAPHIC_REPLACEMENTS = {
    "—": "-",  # em dash
    "–": "-",  # en dash
    "‘": "'",  # left single quote
    "’": "'",  # right single quote
    "“": '"',  # left double quote
    "”": '"',  # right double quote
    "…": "...",  # ellipsis
    "•": "-",  # bullet
}


def _pdf_safe(text: str) -> str:
    """The core Helvetica font (no extra font files to bundle/embed) only
    supports Latin-1 — but LLM-drafted documents routinely use em dashes,
    curly quotes, and ellipses, which crashed PDF generation outright before
    this was added. Normalize the common typographic punctuation to ASCII,
    then drop anything still outside Latin-1 (e.g. CJK/Arabic/emoji) rather
    than let a single stray character fail the whole export."""
    for ch, repl in _PDF_TYPOGRAPHIC_REPLACEMENTS.items():
        text = text.replace(ch, repl)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def render_pdf(version: DocumentVersion, profile: Optional[Profile]) -> bytes:
    """Lazy-imports fpdf2 (Phase 10, `poetry install --extras pdf`) — same
    pattern as the cohere/anthropic/playwright providers: the app runs fine
    without it, this one call just fails clearly until installed. fpdf2 is
    pure Python (no system GTK/Pango/Cairo libraries needed, unlike the
    WeasyPrint version this replaced), so it works out of the box on any
    platform pip does, including plain Windows dev machines."""

    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise PdfUnavailable(
            "PDF export requires the 'pdf' extra: poetry install --extras pdf"
        ) from exc

    full_name = (profile.full_name if profile else None) or ""

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    # fpdf2's multi_cell doesn't reliably leave the x-cursor back at the
    # left margin for the next call (depends on the exact line-wrap it took)
    # — a stray x offset can make the next call compute almost no available
    # width and raise "Not enough horizontal space to render a single
    # character" on completely ordinary text. Reset x before every call.
    def _line(text: str, height: float) -> None:
        pdf.set_x(20)
        pdf.multi_cell(0, height, _pdf_safe(text))

    if full_name:
        pdf.set_font("Helvetica", "B", 13)
        _line(full_name, 8)
        pdf.ln(2)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)

    # The editor already treats body_markdown as plain prose (rendered
    # verbatim with white-space: pre-wrap in the UI, never through a
    # markdown-to-HTML pass) — mirror that here rather than half-rendering
    # markdown fpdf can't interpret. A leading "#" line becomes a bold
    # heading; stray "**"/"*" emphasis markers are stripped so they don't
    # show up as literal asterisks in the PDF.
    pdf.set_font("Helvetica", size=11)
    for raw_line in version.body_markdown.splitlines():
        line = raw_line.strip()
        if not line:
            pdf.ln(3)
            continue
        if line.startswith("#"):
            text = line.lstrip("#").strip().replace("**", "")
            pdf.set_font("Helvetica", "B", 12)
            _line(text, 7)
            pdf.set_font("Helvetica", size=11)
            pdf.ln(1)
            continue
        text = line.replace("**", "").replace("*", "")
        _line(text, 6.5)

    return bytes(pdf.output())


class VersionNotFound(Exception):
    pass


def revert(db: Session, application: Application, doc_type: str, version_number: int) -> DocumentVersion:
    versions = list_versions(db, application, doc_type)
    target = next((v for v in versions if v.version_number == version_number), None)
    if target is None:
        raise VersionNotFound(f"version {version_number} not found for {doc_type}")

    next_version = versions[0].version_number + 1
    return doc_repo.create(
        db,
        application.user_id,
        application_id=application.id,
        doc_type=doc_type,
        version_number=next_version,
        body_markdown=target.body_markdown,
        created_by="user",
        chat_history=target.chat_history,
        author_notes=target.author_notes,
        warnings=target.warnings,
    )
