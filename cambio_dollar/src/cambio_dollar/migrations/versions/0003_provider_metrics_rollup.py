from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_provider_metrics_rollup"
down_revision: str | None = "0002_provider_fetch_metrics"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("window_start", sa.Text(), nullable=False),
        sa.Column("window_end", sa.Text(), nullable=False),
        sa.Column("captures", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("expected_captures", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("coverage_ratio", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("success_ratio", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("mean_latency_ms", sa.Float(), nullable=True),
        sa.Column("latency_p50_ms", sa.Float(), nullable=True),
        sa.Column("latency_p95_ms", sa.Float(), nullable=True),
        sa.Column("mean_error", sa.Float(), nullable=True),
        sa.Column("std_error", sa.Float(), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("provider", "window_start", "window_end", name="uq_provider_window"),
    )
    op.create_index(
        "idx_provider_metrics_provider",
        "provider_metrics",
        ["provider"],
    )
    op.create_index(
        "idx_provider_metrics_window_end",
        "provider_metrics",
        ["window_end"],
    )


def downgrade() -> None:
    op.drop_index("idx_provider_metrics_window_end", table_name="provider_metrics")
    op.drop_index("idx_provider_metrics_provider", table_name="provider_metrics")
    op.drop_table("provider_metrics")
