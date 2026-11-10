"""households: month-close payment task settings (on/off, due and warning days, notify options)

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-11 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0011'
down_revision: Union[str, None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOTIFY_FLAGS = (
    'payment_task_notify_expiring',
    'payment_task_notify_expired',
    'payment_task_notify_expiring_whatsapp',
    'payment_task_notify_expiring_email',
    'payment_task_notify_expiring_groups',
    'payment_task_notify_expired_whatsapp',
    'payment_task_notify_expired_email',
    'payment_task_notify_expired_groups',
)


def upgrade() -> None:
    with op.batch_alter_table('households', schema=None) as batch_op:
        batch_op.add_column(sa.Column('payment_task_enabled', sa.Boolean(), server_default=sa.true(), nullable=False))
        batch_op.add_column(sa.Column('payment_task_due_days', sa.Integer(), server_default='3', nullable=False))
        batch_op.add_column(sa.Column('payment_task_warn_days', sa.Integer(), server_default='3', nullable=False))
        for flag in NOTIFY_FLAGS:
            batch_op.add_column(sa.Column(flag, sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('households', schema=None) as batch_op:
        for flag in reversed(NOTIFY_FLAGS):
            batch_op.drop_column(flag)
        batch_op.drop_column('payment_task_warn_days')
        batch_op.drop_column('payment_task_due_days')
        batch_op.drop_column('payment_task_enabled')
