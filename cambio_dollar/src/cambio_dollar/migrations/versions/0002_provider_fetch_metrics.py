from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_provider_fetch_metrics"
down_revision: str | None = "0001_initial_schema"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_fetch_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("retries", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_provider_fetch_metrics_timestamp",
        "provider_fetch_metrics",
        ["timestamp"],
    )
    op.create_index(
        "idx_provider_fetch_metrics_provider",
        "provider_fetch_metrics",
        ["provider"],
    )


def downgrade() -> None:
    op.drop_index("idx_provider_fetch_metrics_provider", table_name="provider_fetch_metrics")
    op.drop_index("idx_provider_fetch_metrics_timestamp", table_name="provider_fetch_metrics")
    op.drop_table("provider_fetch_metrics")
