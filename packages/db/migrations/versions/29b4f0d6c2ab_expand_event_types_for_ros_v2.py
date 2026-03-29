"""expand event types for ros v2

Revision ID: 29b4f0d6c2ab
Revises: 6a7002181093
Create Date: 2026-03-29 00:00:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "29b4f0d6c2ab"
down_revision: Union[str, Sequence[str], None] = "6a7002181093"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_OLD_EVENTTYPE_VALUES = (
    "collision",
    "goal_reached",
    "timeout",
    "deadlock",
    "fire_started",
    "fire_detected",
    "fire_missed",
    "violator_started",
    "violator_detected",
    "violator_intercepted",
    "patrol_zone_visited",
)

_NEW_EVENTTYPE_VALUES = (
    "collision_passable",
    "collision_impassable",
    "flip",
    "intruder_appeared",
    "intruder_detected",
    "intruder_caught",
)


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        for value in _NEW_EVENTTYPE_VALUES:
            op.execute(f"ALTER TYPE eventtype ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE eventtype RENAME TO eventtype_old")
    op.execute(
        "CREATE TYPE eventtype AS ENUM ({})".format(
            ", ".join(f"'{value}'" for value in _OLD_EVENTTYPE_VALUES)
        )
    )
    op.execute(
        """
        ALTER TABLE episode_events
        ALTER COLUMN event_type TYPE eventtype
        USING (
            CASE event_type::text
                WHEN 'collision_passable' THEN 'collision'
                WHEN 'collision_impassable' THEN 'collision'
                WHEN 'flip' THEN 'deadlock'
                WHEN 'intruder_appeared' THEN 'violator_started'
                WHEN 'intruder_detected' THEN 'violator_detected'
                WHEN 'intruder_caught' THEN 'violator_intercepted'
                ELSE event_type::text
            END
        )::eventtype
        """
    )
    op.execute("DROP TYPE eventtype_old")
