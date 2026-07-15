"""Backfill NULL contacts.publications to [] and enforce NOT NULL —
ContactRead.publications is a non-nullable list, and a NULL row 500s every
GET involving that contact (found via live send-mail verification testing;
same landmine already fixed on Outreach.chat_history /
ReferenceRequest.chat_history).

Revision ID: 7a4f9b2c8e1d
Revises: 5e8c2a1f7d3b
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a4f9b2c8e1d"
down_revision: Union[str, None] = "5e8c2a1f7d3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE contacts SET publications = '[]' WHERE publications IS NULL")
    op.alter_column("contacts", "publications", existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    op.alter_column("contacts", "publications", existing_type=sa.JSON(), nullable=True)
