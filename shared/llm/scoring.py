"""Deterministic fit-score math.

The LLM fills a fixed rubric; this module, not the model, owns the total
(AGENT.md §3.7): clamp each dimension to its maximum, sum, then apply the
hard-fail caps. Pure function — no I/O, no LLM — so it is unit-tested
directly (tests/test_scoring.py).
"""

from __future__ import annotations

from typing import Any

from shared.llm.prompts.score_listing import RUBRIC_MAX

FUNDING_CAP = 40.0
DEGREE_CAP = 30.0


def compute_fit_score(
    rubric_raw: dict[str, Any],
    flags: dict[str, Any],
    constraints_text: str,
) -> tuple[float, dict[str, float], list[str]]:
    """Returns (total, clamped rubric, red flags added by the hard caps).

    Missing or non-numeric dimensions count as 0. Caps fire only on an
    explicit False flag — "unknown" (None / absent) never penalises.
    """

    rubric: dict[str, float] = {}
    for key, cap in RUBRIC_MAX.items():
        try:
            value = float(rubric_raw.get(key, 0))
        except (TypeError, ValueError):
            value = 0.0
        rubric[key] = max(0.0, min(float(cap), value))
    total = sum(rubric.values())

    red_flags: list[str] = []
    constraints = constraints_text.lower()
    requires_funding = "fund" in constraints or "scholarship" in constraints
    if requires_funding and flags.get("funding_confirmed") is False:
        total = min(total, FUNDING_CAP)
        red_flags.append("User requires funding; listing appears unfunded")
    if flags.get("degree_match") is False:
        total = min(total, DEGREE_CAP)
        red_flags.append("Degree/career-stage requirement may not be met")

    return total, rubric, red_flags
