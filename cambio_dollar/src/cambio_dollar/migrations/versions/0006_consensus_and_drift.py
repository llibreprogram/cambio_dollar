from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006_consensus_and_drift"
down_revision: str | None = "0005_provider_error_samples"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consensus_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.Text(), nullable=False, unique=True),
        sa.Column("buy_rate", sa.Float(), nullable=False),
        sa.Column("sell_rate", sa.Float(), nullable=False),
        sa.Column("mid_rate", sa.Float(), nullable=False),
        sa.Column("weighted_buy_rate", sa.Float(), nullable=True),
        sa.Column("weighted_sell_rate", sa.Float(), nullable=True),
        sa.Column("weighted_mid_rate", sa.Float(), nullable=True),
        sa.Column("divergence_range", sa.Float(), nullable=False),
        sa.Column("provider_count", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_consensus_snapshots_timestamp",
        "consensus_snapshots",
        ["timestamp"],
    )

    op.create_table(
        "drift_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("metric", sa.Text(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("ewma", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("cusum_pos", sa.Float(), nullable=False),
        sa.Column("cusum_neg", sa.Float(), nullable=False),
        sa.Column("metadata", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_drift_events_timestamp",
        "drift_events",
        ["timestamp"],
    )
    op.create_index(
        "idx_drift_events_direction",
        "drift_events",
        ["direction"],
    )


def downgrade() -> None:
    op.drop_index("idx_drift_events_direction", table_name="drift_events")
    op.drop_index("idx_drift_events_timestamp", table_name="drift_events")
    op.drop_table("drift_events")

    op.drop_index("idx_consensus_snapshots_timestamp", table_name="consensus_snapshots")
    op.drop_table("consensus_snapshots")
