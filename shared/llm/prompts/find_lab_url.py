"""Deep-dive: guess a professor's lab URL from name + institution."""

SYSTEM = "You answer factual research-group lookup questions. JSON only."


def build_user(professor_name: str, institution: str | None) -> str:
    return (
        f"Professor: {professor_name}\n"
        f"Institution: {institution or 'unknown'}\n\n"
        "Return JSON with a single key `lab_url` (their personal or group "
        "page). Use null if you don't know."
    )
