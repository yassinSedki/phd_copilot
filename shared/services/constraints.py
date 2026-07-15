from typing import Literal, TypedDict


class ProfileConstraints(TypedDict, total=False):
    funding_required: Literal["yes", "no", "preferred"]
    countries: list[str]
    start_date_window: Literal["0-3m", "3-6m", "6-12m", "flexible"]
    application_type: Literal["phd", "postdoc", "both"]
    hard_constraints_text: str
