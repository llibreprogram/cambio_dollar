from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("buy_rate", sa.Float(), nullable=False),
        sa.Column("sell_rate", sa.Float(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
    )

    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("usd_amount", sa.Float(), nullable=False),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("fees", sa.Float(), nullable=False),
        sa.Column("dop_amount", sa.Float(), nullable=False),
        sa.Column("profit_dop", sa.Float(), nullable=False),
    )

    op.create_table(
        "strategy_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("generated_at", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("expected_profit", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("suggested_buy_rate", sa.Float(), nullable=True),
        sa.Column("suggested_sell_rate", sa.Float(), nullable=True),
        sa.Column("spread_advantage", sa.Float(), nullable=True),
    )

    op.create_table(
        "feature_store",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("snapshot_timestamp", sa.Text(), nullable=False),
        sa.Column("feature_version", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("metadata", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_feature_store_timestamp",
        "feature_store",
        ["snapshot_timestamp"],
    )

    op.create_table(
        "labels_performance",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("snapshot_timestamp", sa.Text(), nullable=False),
        sa.Column("horizon_minutes", sa.Integer(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("realized_profit", sa.Float(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "idx_labels_snapshot",
        "labels_performance",
        ["snapshot_timestamp"],
    )

    op.create_table(
        "external_macro",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("metric", sa.Text(), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.UniqueConstraint("timestamp", "source", "metric", name="uq_external_macro_ident"),
    )
    op.create_index(
        "idx_external_macro_timestamp",
        "external_macro",
        ["timestamp"],
    )

    op.create_table(
        "model_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("dataset_version", sa.Text(), nullable=True),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.Text(), nullable=False),
        sa.Column("metadata", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_model_evaluations_ident",
        "model_evaluations",
        ["model_name", "model_version", "metric_name"],
    )


def downgrade() -> None:
    op.drop_index("idx_model_evaluations_ident", table_name="model_evaluations")
    op.drop_table("model_evaluations")

    op.drop_index("idx_external_macro_timestamp", table_name="external_macro")
    op.drop_table("external_macro")

    op.drop_index("idx_labels_snapshot", table_name="labels_performance")
    op.drop_table("labels_performance")

    op.drop_index("idx_feature_store_timestamp", table_name="feature_store")
    op.drop_table("feature_store")

    op.drop_table("strategy_recommendations")
    op.drop_table("trades")
    op.drop_table("rate_snapshots")
