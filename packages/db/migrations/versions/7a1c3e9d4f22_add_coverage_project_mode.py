"""add coverage project mode

Revision ID: 7a1c3e9d4f22
Revises: 5d6ba9f7b8c1
Create Date: 2026-04-01 19:20:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7a1c3e9d4f22"
down_revision: Union[str, Sequence[str], None] = "5d6ba9f7b8c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE projectmode ADD VALUE IF NOT EXISTS 'coverage'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE projectmode RENAME TO projectmode_old")
    op.execute("CREATE TYPE projectmode AS ENUM ('trail', 'robot', 'patrol', 'fast_grid', 'reforestation')")
    op.execute(
        """
        ALTER TABLE scenarios
        ALTER COLUMN mode TYPE projectmode
        USING (
            CASE mode::text
                WHEN 'coverage' THEN 'fast_grid'
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
                WHEN 'coverage' THEN 'fast_grid'
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
                WHEN 'coverage' THEN 'fast_grid'
                ELSE mode::text
            END
        )::projectmode
        """
    )
    op.execute("DROP TYPE projectmode_old")

