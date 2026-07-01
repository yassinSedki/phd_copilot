"""Score step: profile + listing -> Score row.

The cheap LLM (`scorer` role) gets the first pass. Borderline results
(LOW < s < THRESHOLD) trigger a re-score with the stronger LLM
(`scorer_strong` role) — the borderline band is exactly where extra
spend buys real signal.

Architecture: phd copilot.md → "CV-driven scoring".
"""

from typing import Optional

from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.models import Listing, Profile, Score
from shared.llm import LLMClient


def _profile_to_payload(profile: Optional[Profile]) -> dict:
    if profile is None:
        return {}
    return {
        "full_name": profile.full_name,
        "research_summary": profile.research_summary,
        "interests": profile.interests,
        "skills": profile.skills,
        "education": profile.education,
        "publications": profile.publications,
        "languages": profile.languages,
        "location_prefs": profile.location_prefs,
        "constraints": profile.constraints,
        # NEW: feed the CV text into the scorer — phd copilot.md "CV-driven scoring"
        "cv_text": (profile.cv_text or "")[:8000] if profile is not None else "",
        "cv_filename": getattr(profile, "cv_filename", None) if profile is not None else None,
    }


def _listing_to_payload(listing: Listing) -> dict:
    return {
        "source_key": listing.source_key,
        "title": listing.title,
        "institution": listing.institution,
        "country": listing.country,
        "city": listing.city,
        "research_field": listing.research_field,
        "offer_type": listing.offer_type,
        "funding_info": listing.funding_info,
        "description": listing.description,
    }


def score_listing(
    db: Session,
    llm: LLMClient,
    *,
    user_id: int,
    profile: Optional[Profile],
    listing: Listing,
    strong_llm: Optional[LLMClient] = None,
) -> Score:
    settings = get_settings()
    profile_payload = _profile_to_payload(profile)
    listing_payload = _listing_to_payload(listing)

    result = llm.score_listing(profile_payload, listing_payload)

    if (
        strong_llm is not None
        and settings.low_score_threshold < result.score < settings.default_score_threshold
    ):
        result = strong_llm.score_listing(profile_payload, listing_payload)

    score_row = Score(
        user_id=user_id,
        listing_id=listing.id,
        score=result.score,
        fit_breakdown=result.fit_breakdown,
        reasons=result.reasons,
        red_flags=result.red_flags,
        model_used=result.model_used,
    )
    db.add(score_row)
    db.flush()
    return score_row
