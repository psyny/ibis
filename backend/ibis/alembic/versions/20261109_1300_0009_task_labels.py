"""household task categories and locations (lists managers edit)

Every household gets the default lists in its language. Tasks keep the category they had (the fixed
list from 0008); "garden" becomes a location.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-09 13:00:00

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from domain.task_labels import KIND_CATEGORY, KIND_LOCATION, default_labels


# revision identifiers, used by Alembic.
revision: str = '0009'
down_revision: Union[str, None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TASK_TABLES = ('tasks', 'recurring_tasks')


def upgrade() -> None:
    op.create_table(
        'task_labels',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('household_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('key', sa.String(length=30), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['household_id'], ['households.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_task_labels_household_id', 'task_labels', ['household_id'])
    for table in TASK_TABLES:
        for column in ('category_id', 'location_id'):
            op.add_column(table, sa.Column(column, sa.Uuid(), nullable=True))
            op.create_foreign_key(
                f'fk_{table}_{column}', table, 'task_labels', [column], ['id'], ondelete='SET NULL'
            )

    conn = op.get_bind()
    labels = sa.table(
        'task_labels',
        sa.column('id', sa.Uuid()),
        sa.column('household_id', sa.Uuid()),
        sa.column('kind', sa.String()),
        sa.column('name', sa.String()),
        sa.column('key', sa.String()),
        sa.column('position', sa.Integer()),
    )
    for household_id, language in conn.execute(sa.text('SELECT id, language FROM households')).all():
        ids = {}
        for position, (kind, key, name) in enumerate(default_labels(language)):
            label_id = uuid.uuid4()
            ids[(kind, key)] = label_id
            conn.execute(labels.insert().values(
                id=label_id, household_id=household_id, kind=kind, key=key, name=name, position=position
            ))
        for table in TASK_TABLES:
            rows = conn.execute(
                sa.text(f'SELECT id, category FROM {table} WHERE household_id = :h AND category IS NOT NULL'),
                {'h': household_id},
            ).all()
            for row_id, category in rows:
                if category == 'garden':
                    column, target = 'location_id', ids.get((KIND_LOCATION, 'garden'))
                else:
                    column, target = 'category_id', ids.get((KIND_CATEGORY, category))
                if target is not None:
                    conn.execute(sa.text(f'UPDATE {table} SET {column} = :v WHERE id = :id'), {'v': target, 'id': row_id})

    for table in TASK_TABLES:
        op.drop_column(table, 'category')


def downgrade() -> None:
    for table in TASK_TABLES:
        op.add_column(table, sa.Column('category', sa.String(length=20), nullable=True))
        op.execute(
            f"UPDATE {table} SET category = (SELECT key FROM task_labels WHERE task_labels.id = {table}.category_id)"
        )
        for column in ('location_id', 'category_id'):
            op.drop_constraint(f'fk_{table}_{column}', table, type_='foreignkey')
            op.drop_column(table, column)
    op.drop_index('ix_task_labels_household_id', table_name='task_labels')
    op.drop_table('task_labels')
