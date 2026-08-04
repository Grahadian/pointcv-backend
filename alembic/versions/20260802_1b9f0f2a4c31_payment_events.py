"""add payment events

Revision ID: 1b9f0f2a4c31
Revises: 1004823f51b2
Create Date: 2026-08-02 02:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "1b9f0f2a4c31"
down_revision: Union[str, None] = "1004823f51b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("notification_id", sa.String(length=255), nullable=True),
        sa.Column("order_id", sa.String(length=36), nullable=True),
        sa.Column("transaction_id", sa.String(length=255), nullable=True),
        sa.Column("transaction_status", sa.String(length=50), nullable=True),
        sa.Column("payment_type", sa.String(length=100), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payment_events_notification_id",
        "payment_events",
        ["notification_id"],
        unique=True,
    )
    op.create_index(
        "ix_payment_events_order_id",
        "payment_events",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        "ix_payment_events_processed",
        "payment_events",
        ["processed"],
        unique=False,
    )
    op.create_index(
        "ix_payment_events_transaction_id",
        "payment_events",
        ["transaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_payment_events_transaction_status",
        "payment_events",
        ["transaction_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_payment_events_transaction_status", table_name="payment_events")
    op.drop_index("ix_payment_events_transaction_id", table_name="payment_events")
    op.drop_index("ix_payment_events_processed", table_name="payment_events")
    op.drop_index("ix_payment_events_order_id", table_name="payment_events")
    op.drop_index("ix_payment_events_notification_id", table_name="payment_events")
    op.drop_table("payment_events")
