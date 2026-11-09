"""task categories (optional, fixed list); month-close payment tasks are "bills"

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-09 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('category', sa.String(length=20), nullable=True))
    op.add_column('recurring_tasks', sa.Column('category', sa.String(length=20), nullable=True))
    op.execute("UPDATE tasks SET category = 'bills' WHERE kind = 'month_payment'")


def downgrade() -> None:
    op.drop_column('recurring_tasks', 'category')
    op.drop_column('tasks', 'category')
