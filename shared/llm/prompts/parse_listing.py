"""Parse a raw scraped listing into structured fields."""

SYSTEM = (
    "You extract structured fields from a raw academic-job posting. "
    "Return a SINGLE JSON object with keys: title, institution, country, "
    "city, research_field, offer_type (PhD/Postdoc/etc), funding_info, "
    "deadline (YYYY-MM-DD or null), contact_email, application_url, "
    "required_docs (array of strings), description. Use null when unknown. "
    "required_docs = ONLY the documents/materials the applicant must SUBMIT "
    "with the application (e.g. \"CV\", \"Cover letter\", \"Transcripts\", "
    "\"2 reference letters\", \"Research proposal\", \"Degree certificate\", "
    "\"Writing sample\", \"Publication list\"). One document per array element, "
    "short canonical names. Do NOT put eligibility criteria, qualifications, "
    "skills, grades, or language-level requirements in required_docs — those "
    "belong in description. Empty array if the posting names no documents. "
    "Output JSON only, no prose."
)


def build_user(raw: str) -> str:
    # 16k chars ≈ 4k tokens: one listing's text, enough to keep the
    # required-docs / deadline sections that often sit at the end of a page
    # (the on-demand /research endpoint feeds full detail pages through here).
    return raw[:16000]
