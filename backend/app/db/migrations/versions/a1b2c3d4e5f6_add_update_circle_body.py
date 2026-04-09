"""add update_circle body variant

Revision ID: a1b2c3d4e5f6
Revises: 3f62b7606a45
Create Date: 2026-04-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "3f62b7606a45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("update_circle", sa.Column("body", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("update_circle", "body")
