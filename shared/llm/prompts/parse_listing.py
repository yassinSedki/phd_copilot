"""Parse a raw scraped listing into structured fields."""

SYSTEM = (
    "You extract structured fields from a raw academic-job posting. "
    "Return a SINGLE JSON object with keys: title, institution, country, "
    "city, research_field, offer_type (PhD/Postdoc/etc), funding_info, "
    "deadline (YYYY-MM-DD or null), contact_email, application_url, "
    "required_docs (array of strings), description. Use null when unknown. "
    "Output JSON only, no prose."
)


def build_user(raw: str) -> str:
    return raw[:8000]
