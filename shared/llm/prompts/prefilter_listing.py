"""Cheap pre-filter: drop listings that clearly violate hard constraints
before they reach parse+score. "Keep when uncertain" is intentional —
precision > recall here would waste real signal (Phase 04 brief).

Batched only: the old one-listing-per-call prompt was removed when the
prefilter moved to 20-records-per-call batches (AGENT.md §3.4)."""

import json
from typing import Any

SYSTEM_BATCH = (
    "You prefilter a BATCH of PhD/postdoc listings against a user's hard "
    "constraints and short profile. For each record return a decision. "
    'Return JSON: {"decisions": [{"id": int, "keep": bool, "reason": string}]} '
    "with exactly one decision per input id.\n"
    "Rules — this stage is recall-biased; the expensive scorer downstream is "
    "the strict judge:\n"
    "- Reject ONLY when a hard constraint is clearly violated by the record.\n"
    "- When information is missing or ambiguous, keep.\n"
    "- A record with only a vague title and no snippet (e.g. 'PhD Position "
    "(m/f/d)') MUST be kept unless the title itself proves ineligibility — "
    "a false discard is invisible and unrecoverable; a false keep costs one "
    "page fetch.\n"
    "Output JSON only."
)


def build_batch_user(constraints: dict[str, Any], profile_digest: str, records: list[dict[str, Any]]) -> str:
    return (
        "HARD CONSTRAINTS:\n"
        + json.dumps(constraints, default=str)
        + "\n\nUSER PROFILE (digest):\n"
        + (profile_digest or "(none)")[:1200]
        + "\n\nLISTINGS:\n"
        + json.dumps(records, default=str)[:14000]
    )
