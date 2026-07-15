"""Derives an application's docs_checklist from the listing's required_docs.

`kind` on each item drives which action button the frontend renders
(Phase 09): document | manual | reference | portal.
"""

from __future__ import annotations

import re

from shared.models import Listing

_KEYWORD_RULES: list[tuple[str, str, str, str]] = [
    # (keyword regex, kind, id_prefix, doc_type-or-label)
    # "Motivation/motivational letter" is the standard EU-listing phrasing
    # for the same document the app calls "cover letter" — without this,
    # any listing using that wording got a plain non-generatable checkbox
    # instead of a document item with a Generate button.
    (r"cover\s*letter|motivation(al)?\s*letter|letter of motivation", "document", "cover_letter", "cover_letter"),
    (r"statement of purpose|\bsop\b", "document", "sop", "sop"),
    (r"research proposal|\bproposal\b", "document", "research_proposal", "research_proposal"),
    (r"reference|recommendation", "reference", "ref_letter", ""),
]


def _classify_doc(doc: str) -> tuple[str, str, str]:
    """Returns (kind, id, doc_type-or-''). Falls back to a manual item."""

    lowered = doc.lower()
    for pattern, kind, id_prefix, doc_type in _KEYWORD_RULES:
        if re.search(pattern, lowered):
            return kind, id_prefix, doc_type
    slug = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_") or "item"
    return "manual", slug, ""


def derive_checklist(listing: Listing) -> list[dict]:
    items: list[dict] = []
    seen_ids: dict[str, int] = {}
    raw_docs = listing.required_docs or []

    for doc in raw_docs:
        if not isinstance(doc, str) or not doc.strip():
            continue
        # A single required_docs entry can mash together multiple documents
        # (e.g. "CV, cover letter, 2 reference letters") — split defensively.
        for part in re.split(r"[,;\n]", doc):
            part = part.strip()
            if not part:
                continue
            kind, id_prefix, doc_type = _classify_doc(part)
            seen_ids[id_prefix] = seen_ids.get(id_prefix, 0) + 1
            suffix = f"_{seen_ids[id_prefix]}" if seen_ids[id_prefix] > 1 else ""
            item_id = f"{id_prefix}{suffix}"

            if kind == "document":
                items.append({"id": item_id, "kind": "document", "label": part, "doc_type": doc_type, "ready": False})
            elif kind == "reference":
                items.append(
                    {
                        "id": item_id,
                        "kind": "reference",
                        "label": part,
                        "referee_id": None,
                        "reference_request_id": None,
                        "ready": False,
                    }
                )
            else:
                items.append({"id": item_id, "kind": "manual", "label": part, "ready": False})

    if not items:
        # Nothing extracted from the listing page — happens when the source
        # never states its required documents, or scraping/enrichment failed.
        # An application with a genuinely empty checklist has no "Generate"
        # button (only document-kind rows show one) and nothing to check
        # off, so it looks broken. Every PhD/postdoc application needs at
        # least a CV and cover letter — give the user something actionable
        # instead of a dead end.
        items.append({"id": "cv", "kind": "manual", "label": "CV / résumé", "ready": False})
        items.append(
            {"id": "cover_letter", "kind": "document", "label": "Cover letter", "doc_type": "cover_letter", "ready": False}
        )

    if not any(i["kind"] == "portal" for i in items) and listing.application_url:
        items.append(
            {"id": "portal", "kind": "portal", "label": "Submit via portal", "url": listing.application_url, "ready": False}
        )

    return items


def regenerate_preserving_ready(listing: Listing, current: list[dict] | None) -> list[dict]:
    """Rebuild the checklist from the listing, but keep `ready=true` for any
    item whose `id` matches an existing one (Phase 09 DoD: regenerate must
    not lose progress on unchanged items)."""

    current_by_id = {item.get("id"): item for item in (current or []) if isinstance(item, dict)}
    fresh = derive_checklist(listing)
    for item in fresh:
        prior = current_by_id.get(item["id"])
        if prior and prior.get("ready"):
            item["ready"] = True
    return fresh
