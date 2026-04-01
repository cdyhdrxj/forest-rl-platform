"""add scientific suite tables

Revision ID: 5d6ba9f7b8c1
Revises: cf0a9b55e2d1
Create Date: 2026-04-01 18:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5d6ba9f7b8c1"
down_revision: Union[str, Sequence[str], None] = "cf0a9b55e2d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "experiment_suites",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("route_key", sa.String(length=100), nullable=False),
        sa.Column("mode", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("manifest_uri", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("finished_at", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "experiment_suite_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("suite_id", sa.BigInteger(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("scenario_family", sa.String(length=100), nullable=False),
        sa.Column("dataset_split", sa.String(length=50), nullable=False),
        sa.Column("method_code", sa.String(length=100), nullable=False),
        sa.Column("replicate_index", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("train_seed", sa.BigInteger(), nullable=True),
        sa.Column("eval_seed", sa.BigInteger(), nullable=True),
        sa.Column("group_key", sa.String(length=150), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["suite_id"], ["experiment_suites.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("suite_id", "run_id", name="uix_suite_run"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("experiment_suite_runs")
    op.drop_table("experiment_suites")
