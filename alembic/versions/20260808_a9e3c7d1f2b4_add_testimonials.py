"""add testimonials

Revision ID: a9e3c7d1f2b4
Revises: b8f2c0a4e1d9
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a9e3c7d1f2b4"
down_revision: Union[str, None] = "b8f2c0a4e1d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "testimonials",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "user_id", sa.String(length=128), nullable=False
        ),
        sa.Column("order_id", sa.String(length=36), nullable=True),
        sa.Column("user_name", sa.String(length=255), nullable=False),
        sa.Column("user_role", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("avatar_url", sa.String(length=1024), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "order_id", name="uq_testimonials_user_order"),
    )
    op.create_index("idx_testimonials_user_id", "testimonials", ["user_id"])
    op.create_index("idx_testimonials_order_id", "testimonials", ["order_id"])
    op.create_index("idx_testimonials_status", "testimonials", ["status"])


def downgrade() -> None:
    op.drop_index("idx_testimonials_status", table_name="testimonials")
    op.drop_index("idx_testimonials_order_id", table_name="testimonials")
    op.drop_index("idx_testimonials_user_id", table_name="testimonials")
    op.drop_table("testimonials")
