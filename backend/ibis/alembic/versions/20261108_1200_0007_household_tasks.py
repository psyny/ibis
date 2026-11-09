"""household tasks and recurring tasks; notifications become notes only

Existing "task" notifications become notes. Pending month-payment ones (not done, not deleted)
also become household tasks, due 3 days after they were sent, and the note links to the task.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-08 12:00:00

"""
import uuid
from datetime import timedelta
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _task_settings() -> list:
    return [
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('warn_days', sa.Integer(), server_default='3', nullable=False),
        sa.Column('notify_expiring', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('notify_expired', sa.Boolean(), server_default=sa.false(), nullable=False),
    ]


def _link_table(name: str, owner_table: str, owner_column: str) -> None:
    op.create_table(
        name,
        sa.Column(owner_column, sa.Uuid(), nullable=False),
        sa.Column('member_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint([owner_column], [f'{owner_table}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['member_id'], ['household_members.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint(owner_column, 'member_id'),
    )


def upgrade() -> None:
    op.create_table(
        'recurring_tasks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('household_id', sa.Uuid(), nullable=False),
        *_task_settings(),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('interval', sa.Integer(), nullable=False),
        sa.Column('unit', sa.String(length=10), nullable=False),
        sa.Column('due_offset_days', sa.Integer(), server_default='0', nullable=False),
        sa.Column('wait_for_previous', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('assign_mode', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('last_occurrence_date', sa.Date(), nullable=True),
        sa.Column('created_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['household_id'], ['households.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_recurring_tasks_household_id', 'recurring_tasks', ['household_id'])
    _link_table('recurring_task_assignees', 'recurring_tasks', 'recurring_task_id')

    op.create_table(
        'tasks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('household_id', sa.Uuid(), nullable=False),
        *_task_settings(),
        sa.Column('kind', sa.String(length=40), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('group_key', sa.String(length=120), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('recurring_task_id', sa.Uuid(), nullable=True),
        sa.Column('occurrence_date', sa.Date(), nullable=True),
        sa.Column('created_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('expiring_notified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expired_notified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['household_id'], ['households.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recurring_task_id'], ['recurring_tasks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['completed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('recurring_task_id', 'occurrence_date', name='uq_tasks_recurring_occurrence'),
    )
    op.create_index('ix_tasks_household_id', 'tasks', ['household_id'])
    op.create_index('ix_tasks_group_key', 'tasks', ['group_key'])
    op.create_index('ix_tasks_recurring_task_id', 'tasks', ['recurring_task_id'])
    _link_table('task_assignees', 'tasks', 'task_id')

    op.add_column('notifications', sa.Column('task_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'fk_notifications_task_id', 'notifications', 'tasks', ['task_id'], ['id'], ondelete='CASCADE'
    )
    op.create_index('ix_notifications_task_id', 'notifications', ['task_id'])

    _move_payment_tasks()
    op.drop_column('notifications', 'completed_at')


def _move_payment_tasks() -> None:
    conn = op.get_bind()
    notifications = sa.table(
        'notifications',
        sa.column('id', sa.Uuid()),
        sa.column('user_id', sa.Uuid()),
        sa.column('household_id', sa.Uuid()),
        sa.column('type', sa.String()),
        sa.column('kind', sa.String()),
        sa.column('title', sa.String()),
        sa.column('data', sa.JSON()),
        sa.column('group_key', sa.String()),
        sa.column('task_id', sa.Uuid()),
        sa.column('viewed_at', sa.DateTime(timezone=True)),
        sa.column('completed_at', sa.DateTime(timezone=True)),
        sa.column('deleted_at', sa.DateTime(timezone=True)),
        sa.column('created_at', sa.DateTime(timezone=True)),
    )
    members = sa.table(
        'household_members', sa.column('id', sa.Uuid()), sa.column('household_id', sa.Uuid()), sa.column('user_id', sa.Uuid())
    )
    tasks = sa.table(
        'tasks',
        sa.column('id', sa.Uuid()),
        sa.column('household_id', sa.Uuid()),
        sa.column('title', sa.String()),
        sa.column('warn_days', sa.Integer()),
        sa.column('notify_expiring', sa.Boolean()),
        sa.column('notify_expired', sa.Boolean()),
        sa.column('kind', sa.String()),
        sa.column('data', sa.JSON()),
        sa.column('group_key', sa.String()),
        sa.column('due_date', sa.Date()),
        sa.column('created_at', sa.DateTime(timezone=True)),
    )
    task_assignees = sa.table('task_assignees', sa.column('task_id', sa.Uuid()), sa.column('member_id', sa.Uuid()))

    pending = conn.execute(
        sa.select(notifications).where(
            notifications.c.type == 'task',
            notifications.c.kind == 'month_payment',
            notifications.c.household_id.is_not(None),
            notifications.c.completed_at.is_(None),
            notifications.c.deleted_at.is_(None),
        )
    ).mappings().all()
    for row in pending:
        member_id = conn.scalar(
            sa.select(members.c.id).where(
                members.c.household_id == row['household_id'], members.c.user_id == row['user_id']
            )
        )
        if member_id is None:
            continue
        task_id = uuid.uuid4()
        conn.execute(
            tasks.insert().values(
                id=task_id,
                household_id=row['household_id'],
                title=row['title'],
                warn_days=3,
                notify_expiring=False,
                notify_expired=False,
                kind='month_payment',
                data=row['data'] or {},
                group_key=row['group_key'],
                due_date=(row['created_at'] + timedelta(days=3)).date(),
                created_at=row['created_at'],
            )
        )
        conn.execute(task_assignees.insert().values(task_id=task_id, member_id=member_id))
        conn.execute(notifications.update().where(notifications.c.id == row['id']).values(task_id=task_id))

    # Every notification is a note now; a completed task counts as read
    conn.execute(
        notifications.update()
        .where(notifications.c.type == 'task')
        .values(type='note', viewed_at=sa.func.coalesce(notifications.c.viewed_at, notifications.c.completed_at))
    )


def downgrade() -> None:
    op.add_column('notifications', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    op.drop_index('ix_notifications_task_id', table_name='notifications')
    op.drop_constraint('fk_notifications_task_id', 'notifications', type_='foreignkey')
    op.drop_column('notifications', 'task_id')
    op.drop_table('task_assignees')
    op.drop_index('ix_tasks_recurring_task_id', table_name='tasks')
    op.drop_index('ix_tasks_group_key', table_name='tasks')
    op.drop_index('ix_tasks_household_id', table_name='tasks')
    op.drop_table('tasks')
    op.drop_table('recurring_task_assignees')
    op.drop_index('ix_recurring_tasks_household_id', table_name='recurring_tasks')
    op.drop_table('recurring_tasks')
