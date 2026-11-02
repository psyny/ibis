"""households.language: interface language per household

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-02 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('households', schema=None) as batch_op:
        batch_op.add_column(sa.Column('language', sa.String(length=10), nullable=False, server_default='en'))


def downgrade() -> None:
    with op.batch_alter_table('households', schema=None) as batch_op:
        batch_op.drop_column('language')
