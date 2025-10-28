from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007_drift_severity"
down_revision: str | None = "0006_consensus_and_drift"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("drift_events", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "severity",
                sa.Text(),
                nullable=False,
                server_default="LOW",
            )
        )


    op.execute(
        sa.text(
            """
            UPDATE drift_events
            SET severity = 'LOW'
            WHERE severity IS NULL
            """
        )
    )


    with op.batch_alter_table("drift_events", schema=None) as batch_op:
        batch_op.alter_column("severity", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("drift_events", schema=None) as batch_op:
        batch_op.drop_column("severity")
