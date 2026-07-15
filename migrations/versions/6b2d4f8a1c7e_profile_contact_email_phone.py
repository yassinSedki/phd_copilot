"""Add profiles.contact_email + profiles.phone — CV extraction now pulls
contact details, not just the name, and they need somewhere to land that
isn't the User.email login identity.

Revision ID: 6b2d4f8a1c7e
Revises: 1a8f6d3c9e2b
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6b2d4f8a1c7e"
down_revision: Union[str, None] = "1a8f6d3c9e2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("contact_email", sa.String(length=255), nullable=True))
    op.add_column("profiles", sa.Column("phone", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "phone")
    op.drop_column("profiles", "contact_email")
