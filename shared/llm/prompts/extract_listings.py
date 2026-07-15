"""Extract listings from arbitrary HTML/text (driven by the scraper agent)."""

SYSTEM = (
    "You extract academic job listings from raw HTML or text. Return a "
    'JSON OBJECT of the shape {"listings": [...]} — not a bare array; some '
    "providers' JSON mode only guarantees a top-level object. Each element "
    "of the listings array has keys: title, institution, country, "
    "city, research_field, offer_type, funding_info, deadline_text, "
    "contact_email, application_url, description, source_key (a stable "
    "short id you invent from the URL or position). Use null for "
    'unknown. If there are no listings, return {"listings": []}. '
    "The content may arrive as pre-segmented blocks separated by "
    "'=== LISTING ==='. In that case return EXACTLY ONE listing per block, "
    "in the same order as the blocks. A leading 'LINK: <url>' line is that "
    "listing's own page: use it as application_url. The title is usually "
    "the first text line of the block — never leave title null when the "
    "block has any text. Output JSON only."
)


def build_user(html_or_text: str, source_url: str) -> str:
    return f"SOURCE_URL: {source_url}\n\nCONTENT:\n{html_or_text[:12000]}"
