from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_anomaly_events"
down_revision: str | None = "0003_provider_metrics_rollup"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "anomaly_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("metric", sa.Text(), nullable=False),
        sa.Column("detector", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index(
        "idx_anomaly_events_timestamp",
        "anomaly_events",
        ["timestamp"],
    )
    op.create_index(
        "idx_anomaly_events_provider",
        "anomaly_events",
        ["provider"],
    )


def downgrade() -> None:
    op.drop_index("idx_anomaly_events_provider", table_name="anomaly_events")
    op.drop_index("idx_anomaly_events_timestamp", table_name="anomaly_events")
    op.drop_table("anomaly_events")
