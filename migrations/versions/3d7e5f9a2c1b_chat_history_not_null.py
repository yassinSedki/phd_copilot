"""Backfill NULL chat_history to [] and enforce NOT NULL on outreach +
reference_requests — both API read schemas declare chat_history as a
non-nullable list, and a row with NULL (e.g. every Outreach created by the
deep-dive task, which never set it) 500s the list/get endpoint.

Revision ID: 3d7e5f9a2c1b
Revises: 6b2d4f8a1c7e
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3d7e5f9a2c1b"
down_revision: Union[str, None] = "6b2d4f8a1c7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE outreach SET chat_history = '[]' WHERE chat_history IS NULL")
    op.execute("UPDATE reference_requests SET chat_history = '[]' WHERE chat_history IS NULL")
    op.alter_column("outreach", "chat_history", existing_type=sa.JSON(), nullable=False)
    op.alter_column("reference_requests", "chat_history", existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    op.alter_column("reference_requests", "chat_history", existing_type=sa.JSON(), nullable=True)
    op.alter_column("outreach", "chat_history", existing_type=sa.JSON(), nullable=True)
