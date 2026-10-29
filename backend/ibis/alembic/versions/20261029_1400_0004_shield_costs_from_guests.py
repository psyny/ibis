"""households.shield_costs_from_guests: guests only see what involves them

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-29 14:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('households', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('shield_costs_from_guests', sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table('households', schema=None) as batch_op:
        batch_op.drop_column('shield_costs_from_guests')
