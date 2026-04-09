"""add reforestation project mode

Revision ID: cf0a9b55e2d1
Revises: 29b4f0d6c2ab
Create Date: 2026-03-29 00:00:01

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "cf0a9b55e2d1"
down_revision: Union[str, Sequence[str], None] = "29b4f0d6c2ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE projectmode ADD VALUE IF NOT EXISTS 'reforestation'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE projectmode RENAME TO projectmode_old")
    op.execute("CREATE TYPE projectmode AS ENUM ('trail', 'robot', 'patrol', 'fast_grid')")
    op.execute(
        """
        ALTER TABLE scenarios
        ALTER COLUMN mode TYPE projectmode
        USING (
            CASE mode::text
                WHEN 'reforestation' THEN 'fast_grid'
                ELSE mode::text
            END
        )::projectmode
        """
    )
    op.execute(
        """
        ALTER TABLE algorithms
        ALTER COLUMN mode TYPE projectmode
        USING (
            CASE mode::text
                WHEN 'reforestation' THEN 'fast_grid'
                ELSE mode::text
            END
        )::projectmode
        """
    )
    op.execute(
        """
        ALTER TABLE runs
        ALTER COLUMN mode TYPE projectmode
        USING (
            CASE mode::text
                WHEN 'reforestation' THEN 'fast_grid'
                ELSE mode::text
            END
        )::projectmode
        """
    )
    op.execute("DROP TYPE projectmode_old")
