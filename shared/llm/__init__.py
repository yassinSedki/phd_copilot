"""Public API for the LLM module.

External code imports from here, not from `client.py` (which no longer
exists). The old `build_llm_client(provider, *, scoring_model)` is gone;
use `get_llm(settings.llm, role)` instead — the factory derives model,
temperature, and json_mode from the role automatically.
"""

from shared.llm.base import LLMClient, Message
from shared.llm.errors import LLMError, LLMErrorCode
from shared.llm.factory import FREE_TEXT_ROLES, get_llm
from shared.llm.types import (
    DraftedLetter,
    EmailBody,
    ExtractedListing,
    ExtractedProfile,
    OutreachDraft,
    ParsedListing,
    RefinedLetter,
    ResearchSummary,
    ScoreResult,
)

__all__ = [
    "LLMClient",
    "Message",
    "LLMError",
    "LLMErrorCode",
    "get_llm",
    "FREE_TEXT_ROLES",
    "ParsedListing",
    "ScoreResult",
    "DraftedLetter",
    "RefinedLetter",
    "EmailBody",
    "OutreachDraft",
    "ResearchSummary",
    "ExtractedListing",
    "ExtractedProfile",
]
