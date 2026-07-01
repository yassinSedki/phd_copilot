"""Extract listings from arbitrary HTML/text (driven by the scraper agent)."""

SYSTEM = (
    "You extract academic job listings from raw HTML or text. Return a "
    "JSON array. Each element has keys: title, institution, country, "
    "city, research_field, offer_type, funding_info, deadline_text, "
    "contact_email, application_url, description, source_key (a stable "
    "short id you invent from the URL or position). Use null for "
    "unknown. Output JSON array only."
)


def build_user(html_or_text: str, source_url: str) -> str:
    return f"SOURCE_URL: {source_url}\n\nCONTENT:\n{html_or_text[:12000]}"
