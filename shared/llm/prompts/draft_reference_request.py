import json
from typing import Any

SYSTEM = (
    "You draft a formal, warm reference-letter request email from a PhD applicant "
    "to a professor. Return JSON: {\"subject\": string, \"body\": string}. "
    "Constraints: "
    "1. Subject: 'Reference letter request — <position> at <institution>, deadline <date>'. "
    "2. Body: 4 short paragraphs. First: the ask. Second: the position (2 sentences). "
    "Third: why you're asking THIS referee (based on the personal_note, if given). "
    "Fourth: logistics (submission method) and thanks. "
    "3. No exclamation marks, no emojis, no filler. Under 220 words. "
    "4. Plain-text email — never use markdown (**bold**, *italic*, # headers)."
)


def build_user(
    referee: dict[str, Any],
    student: dict[str, Any],
    position: dict[str, Any],
    deadline: str | None,
    submission_method: str,
    personal_note: str | None,
) -> str:
    return json.dumps(
        {
            "referee": referee,
            "student": student,
            "position": position,
            "deadline": deadline,
            "submission_method": submission_method,
            "personal_note": personal_note or "",
        },
        default=str,
    )
