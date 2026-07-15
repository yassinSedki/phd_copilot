"""Add chat_history to outreach + reference_requests — both email drafts
can now be revised via chat ("ask the AI to change it"), same pattern as
DocumentVersion.chat_history for cover letters/SOP/research proposal.

Revision ID: 1a8f6d3c9e2b
Revises: 9c4e2a7f1b3d
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a8f6d3c9e2b"
down_revision: Union[str, None] = "9c4e2a7f1b3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("outreach", sa.Column("chat_history", sa.JSON(), nullable=True))
    op.add_column("reference_requests", sa.Column("chat_history", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("reference_requests", "chat_history")
    op.drop_column("outreach", "chat_history")
