"""rename creator to owner, add direct transfer flag

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE member SET role = 'owner' WHERE role = 'creator'")
    op.add_column("creator_transfer", sa.Column("direct", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.execute("UPDATE member SET role = 'creator' WHERE role = 'owner'")
    op.drop_column("creator_transfer", "direct")
