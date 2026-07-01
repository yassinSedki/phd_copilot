"""Deep-dive: filter a list of candidate strings down to real paper titles."""

SYSTEM = "You filter candidate publication titles. JSON only."


def build_user(candidates: list[str]) -> str:
    lines = "\n".join(candidates[:10])
    return (
        "Pick up to 3 entries that look like academic publication titles "
        "(not navigation, not generic page text). Return JSON: "
        '{"publications": ["...", "..."]}.\n\n' + lines
    )
