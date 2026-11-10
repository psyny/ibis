"""WhatsApp groups, outgoing message queue, task notify channels and private tasks

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-10 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0010'
down_revision: Union[str, None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TASK_FLAGS = (
    'notify_expiring_whatsapp',
    'notify_expiring_email',
    'notify_expiring_groups',
    'notify_expired_whatsapp',
    'notify_expired_email',
    'notify_expired_groups',
    'is_private',
)


def upgrade() -> None:
    for table in ('tasks', 'recurring_tasks'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            for flag in TASK_FLAGS:
                batch_op.add_column(sa.Column(flag, sa.Boolean(), server_default=sa.false(), nullable=False))

    op.create_table(
        'whatsapp_groups',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('household_id', sa.Uuid(), nullable=False),
        sa.Column('jid', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['household_id'], ['households.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('household_id', 'jid', name='uq_whatsapp_groups_household_jid'),
    )
    op.create_index('ix_whatsapp_groups_household_id', 'whatsapp_groups', ['household_id'])

    op.create_table(
        'outgoing_messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('household_id', sa.Uuid(), nullable=False),
        sa.Column('channel', sa.String(length=10), nullable=False),
        sa.Column('recipient', sa.String(length=255), nullable=False),
        sa.Column('recipient_label', sa.String(length=200), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['household_id'], ['households.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_outgoing_messages_household_id', 'outgoing_messages', ['household_id'])
    op.create_index('ix_outgoing_messages_status', 'outgoing_messages', ['status'])


def downgrade() -> None:
    op.drop_index('ix_outgoing_messages_status', table_name='outgoing_messages')
    op.drop_index('ix_outgoing_messages_household_id', table_name='outgoing_messages')
    op.drop_table('outgoing_messages')
    op.drop_index('ix_whatsapp_groups_household_id', table_name='whatsapp_groups')
    op.drop_table('whatsapp_groups')
    for table in ('tasks', 'recurring_tasks'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            for flag in reversed(TASK_FLAGS):
                batch_op.drop_column(flag)
