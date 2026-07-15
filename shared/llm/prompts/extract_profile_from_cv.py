"""Extract a structured profile from CV text. Phase 03 onboarding."""

SYSTEM = (
    "You extract a researcher's profile from their CV text. "
    "Return JSON matching this schema:\n"
    "{\n"
    '  "full_name": string,\n'
    '  "email": string (their contact email address, usually near the top or in a header/footer),\n'
    '  "phone": string (their phone number, in whatever format the CV uses),\n'
    '  "research_summary": string (4-6 SPECIFIC sentences a search agent will '
    "score every job listing against — cover their concrete research topics, "
    "methods/tools actually used, notable projects or publications with real "
    "detail, prior roles, and what kind of position they're evidently suited "
    "for next. Write it as flowing prose, not a list. Ground every claim in "
    "the CV text — do not pad with generic phrases like 'passionate about "
    "technology'),\n"
    '  "research_areas": string[] (max 8),\n'
    '  "methods": string[] (max 8, e.g. "PyTorch", "MRI acquisition"),\n'
    '  "programming_languages": string[],\n'
    '  "degree_subject": string,\n'
    '  "graduation_year": number | null,\n'
    '  "career_stage": "undergrad" | "masters" | "phd_student" | "postdoc" | "other",\n'
    '  "languages_spoken": string[],\n'
    '  "publications": [{"title": string, "venue": string, "year": number}] (max 5),\n'
    '  "geographic_hints": string[] (countries mentioned as prior locations or preferences)\n'
    "}\n"
    "The CV text may be truncated mid-document — still extract everything "
    "findable from what's given. Output JSON only. Never guess a field you "
    "cannot find — omit it or use null."
)


def build_user(cv_text: str) -> str:
    # Was 12000 — long CVs (2-3+ dense pages) routinely exceed that, silently
    # losing everything past the cutoff (later education, publications,
    # contact details in a footer). All providers in use here have context
    # windows far larger than the ~6-8k tokens this now costs.
    return f"CV:\n{cv_text[:24000]}"
