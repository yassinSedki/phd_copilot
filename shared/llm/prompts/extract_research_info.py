"""Deep-dive: pull research topics/methods/projects from a lab page."""

SYSTEM = "Structured research-info extractor. JSON only."


def build_user(professor_name: str, page_text: str) -> str:
    return (
        f"PROFESSOR: {professor_name}\n\nLAB PAGE TEXT:\n{page_text}\n\n"
        "Extract JSON: topics (array of short strings), methods (array), "
        "recent_projects (array). Output JSON only."
    )
