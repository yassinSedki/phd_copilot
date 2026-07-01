"""Application state machine. Section 10 of the architecture doc.

NEW -> REVIEWING -> SHORTLISTED -> DRAFTING -> READY -> APPLIED
            |                                              |
            v                                    INTERVIEW / REJECTED
        DISCARDED                                   |
                                                OFFER / REJECTED

WITHDRAWN and EXPIRED are reachable from most states.
"""

from typing import Any, Iterable

NEW = "NEW"
REVIEWING = "REVIEWING"
SHORTLISTED = "SHORTLISTED"
DISCARDED = "DISCARDED"
DRAFTING = "DRAFTING"
READY = "READY"
APPLIED = "APPLIED"
INTERVIEW = "INTERVIEW"
OFFER = "OFFER"
REJECTED = "REJECTED"
WITHDRAWN = "WITHDRAWN"
EXPIRED = "EXPIRED"

ALL_STATUSES = {
    NEW,
    REVIEWING,
    SHORTLISTED,
    DISCARDED,
    DRAFTING,
    READY,
    APPLIED,
    INTERVIEW,
    OFFER,
    REJECTED,
    WITHDRAWN,
    EXPIRED,
}

_TRANSITIONS: dict[str, set[str]] = {
    NEW: {REVIEWING, DISCARDED, WITHDRAWN, EXPIRED},
    REVIEWING: {SHORTLISTED, DISCARDED, WITHDRAWN, EXPIRED},
    SHORTLISTED: {DRAFTING, DISCARDED, WITHDRAWN, EXPIRED, REVIEWING},
    DRAFTING: {READY, SHORTLISTED, WITHDRAWN, EXPIRED},
    READY: {APPLIED, DRAFTING, WITHDRAWN, EXPIRED},
    APPLIED: {INTERVIEW, REJECTED, WITHDRAWN},
    INTERVIEW: {OFFER, REJECTED, WITHDRAWN},
    OFFER: {REJECTED, WITHDRAWN},
    REJECTED: set(),
    DISCARDED: {REVIEWING},
    WITHDRAWN: set(),
    EXPIRED: set(),
}

KANBAN_COLUMNS = [
    REVIEWING,
    SHORTLISTED,
    DRAFTING,
    READY,
    APPLIED,
    INTERVIEW,
    OFFER,
    REJECTED,
]


class IllegalTransition(ValueError):
    pass


class GuardFailed(ValueError):
    pass


def is_legal(src: str, dst: str) -> bool:
    return dst in _TRANSITIONS.get(src, set())


def check_transition(src: str, dst: str, *, docs_checklist: Iterable[dict[str, Any]] | None = None) -> None:
    if dst not in ALL_STATUSES:
        raise IllegalTransition(f"unknown status: {dst}")
    if src == dst:
        return
    if not is_legal(src, dst):
        raise IllegalTransition(f"cannot transition from {src} to {dst}")
    if dst == READY:
        items = list(docs_checklist or [])
        if not items:
            raise GuardFailed("docs_checklist must exist before moving to READY")
        if not all(item.get("ready") for item in items):
            raise GuardFailed("all docs_checklist items must be ready=true before READY")
