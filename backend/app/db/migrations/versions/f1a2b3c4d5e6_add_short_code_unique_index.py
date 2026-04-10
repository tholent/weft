"""add partial unique index on short_code for active topics

Revision ID: f1a2b3c4d5e6
Revises: e5ac2fcea29b
Create Date: 2026-04-10

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e5ac2fcea29b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add partial unique index on topic.short_code where status = 'active'."""
    op.execute(
        "CREATE UNIQUE INDEX ix_topic_short_code_active "
        "ON topic(short_code) WHERE status = 'active'"
    )


def downgrade() -> None:
    """Drop the partial unique index."""
    op.execute("DROP INDEX IF EXISTS ix_topic_short_code_active")
