"""Application state machine. Section 10 of the architecture doc.

SAVED -> IN_PROGRESS -> DOCS_READY -> APPLIED -> INTERVIEW -> OFFER
   |          |              |           |            |
   v          v              v           v            v
REJECTED   REJECTED      REJECTED    REJECTED     REJECTED

WITHDRAWN is reachable from SAVED..INTERVIEW. There is no EXPIRED status —
overdue deadlines are surfaced as urgency in the UI, not a status.
"""

from typing import Any, Iterable

SAVED = "SAVED"
IN_PROGRESS = "IN_PROGRESS"
DOCS_READY = "DOCS_READY"
APPLIED = "APPLIED"
INTERVIEW = "INTERVIEW"
OFFER = "OFFER"
REJECTED = "REJECTED"
WITHDRAWN = "WITHDRAWN"

ALL_STATUSES = {
    SAVED,
    IN_PROGRESS,
    DOCS_READY,
    APPLIED,
    INTERVIEW,
    OFFER,
    REJECTED,
    WITHDRAWN,
}

_TRANSITIONS: dict[str, set[str]] = {
    SAVED: {IN_PROGRESS, REJECTED, WITHDRAWN},
    IN_PROGRESS: {DOCS_READY, SAVED, REJECTED, WITHDRAWN},
    DOCS_READY: {APPLIED, IN_PROGRESS, WITHDRAWN},
    APPLIED: {INTERVIEW, REJECTED, WITHDRAWN},
    INTERVIEW: {OFFER, REJECTED, WITHDRAWN},
    OFFER: {REJECTED},
    REJECTED: set(),
    WITHDRAWN: set(),
}

KANBAN_COLUMNS = [
    SAVED,
    IN_PROGRESS,
    DOCS_READY,
    APPLIED,
    INTERVIEW,
    OFFER,
    REJECTED,
    WITHDRAWN,
]


class IllegalTransition(ValueError):
    pass


class GuardFailed(ValueError):
    pass


def is_legal(src: str, dst: str) -> bool:
    return dst in _TRANSITIONS.get(src, set())


def allowed_transitions(src: str) -> list[str]:
    """Legal next statuses from `src`, for the tracker's inline dropdown."""

    return sorted(_TRANSITIONS.get(src, set()))


def check_transition(src: str, dst: str, *, docs_checklist: Iterable[dict[str, Any]] | None = None) -> None:
    if dst not in ALL_STATUSES:
        raise IllegalTransition(f"unknown status: {dst}")
    if src == dst:
        return
    if not is_legal(src, dst):
        raise IllegalTransition(f"cannot transition from {src} to {dst}")
    if dst == DOCS_READY:
        items = list(docs_checklist or [])
        if not items:
            raise GuardFailed("docs_checklist must exist before moving to DOCS_READY")
        if not all(item.get("ready") for item in items):
            raise GuardFailed("all docs_checklist items must be ready=true before DOCS_READY")
