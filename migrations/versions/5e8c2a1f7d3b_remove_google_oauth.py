"""Remove Google sign-in and Gmail-send support: auth is email/password
only now. Drops the OAuth identity columns and Gmail token storage from
users, along with the now-unused unique constraint on (oauth_provider,
oauth_subject).

Revision ID: 5e8c2a1f7d3b
Revises: 3d7e5f9a2c1b
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5e8c2a1f7d3b"
down_revision: Union[str, None] = "3d7e5f9a2c1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_users_oauth_identity", "users", type_="unique")
    op.drop_column("users", "google_token_expires_at")
    op.drop_column("users", "google_refresh_token")
    op.drop_column("users", "google_access_token")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "oauth_subject")
    op.drop_column("users", "oauth_provider")


def downgrade() -> None:
    op.add_column("users", sa.Column("oauth_provider", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("oauth_subject", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=1024), nullable=True))
    op.add_column("users", sa.Column("google_access_token", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("google_refresh_token", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("google_token_expires_at", sa.DateTime(), nullable=True))
    op.create_unique_constraint("uq_users_oauth_identity", "users", ["oauth_provider", "oauth_subject"])
