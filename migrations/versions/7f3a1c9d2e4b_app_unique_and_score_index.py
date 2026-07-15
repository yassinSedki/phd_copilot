"""Unique (user_id, listing_id) on applications + composite score index.

- applications: enforce one tracked application per listing per user at the
  DB level (the service check-then-insert alone is racy).
- scores: composite index matching the hottest query — latest_score filters
  on (user_id, listing_id) ordered by scored_at DESC.

Revision ID: 7f3a1c9d2e4b
Revises: 2161300d6e7c
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7f3a1c9d2e4b"
down_revision: Union[str, None] = "2161300d6e7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_applications_user_listing", "applications", ["user_id", "listing_id"]
    )
    op.create_index(
        "ix_scores_user_listing_scored_at",
        "scores",
        ["user_id", "listing_id", "scored_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_scores_user_listing_scored_at", table_name="scores")
    op.drop_constraint("uq_applications_user_listing", "applications", type_="unique")
