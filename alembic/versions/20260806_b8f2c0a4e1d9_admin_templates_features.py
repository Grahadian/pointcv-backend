"""add packages.features and cv_templates.category

Revision ID: b8f2c0a4e1d9
Revises: bf018d38dc93
Create Date: 2026-08-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8f2c0a4e1d9"
down_revision: Union[str, None] = "bf018d38dc93"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("packages", sa.Column("features", sa.JSON(), nullable=True))
    op.add_column("cv_templates", sa.Column("category", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("cv_templates", "category")
    op.drop_column("packages", "features")