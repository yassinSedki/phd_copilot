"""Add outreach.sent_at — supervisor outreach can now actually be sent
(Gmail API, mirroring reference-request send) instead of copy-only.

Revision ID: 9c4e2a7f1b3d
Revises: 7f3a1c9d2e4b
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c4e2a7f1b3d"
down_revision: Union[str, None] = "7f3a1c9d2e4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("outreach", sa.Column("sent_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("outreach", "sent_at")
