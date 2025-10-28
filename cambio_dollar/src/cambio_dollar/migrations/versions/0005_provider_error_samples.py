from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005_provider_error_samples"
down_revision: str | None = "0004_anomaly_events"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_error_samples",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("delta_vs_weighted", sa.Float(), nullable=True),
        sa.Column("delta_vs_consensus", sa.Float(), nullable=True),
        sa.Column("provider_mid", sa.Float(), nullable=True),
        sa.Column("weighted_mid", sa.Float(), nullable=True),
        sa.Column("consensus_mid", sa.Float(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_provider_error_samples_provider",
        "provider_error_samples",
        ["provider"],
    )
    op.create_index(
        "idx_provider_error_samples_timestamp",
        "provider_error_samples",
        ["timestamp"],
    )


def downgrade() -> None:
    op.drop_index("idx_provider_error_samples_timestamp", table_name="provider_error_samples")
    op.drop_index("idx_provider_error_samples_provider", table_name="provider_error_samples")
    op.drop_table("provider_error_samples")
