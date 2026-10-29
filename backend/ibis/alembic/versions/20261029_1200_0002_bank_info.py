"""bank info: type (pix/other) + value, replacing transfer_number

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-29 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('transfer_number', new_column_name='bank_info', existing_type=sa.String(length=255))
        batch_op.add_column(sa.Column('bank_info_type', sa.String(length=20), nullable=False, server_default='pix'))


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('bank_info_type')
        batch_op.alter_column('bank_info', new_column_name='transfer_number', existing_type=sa.String(length=255))
