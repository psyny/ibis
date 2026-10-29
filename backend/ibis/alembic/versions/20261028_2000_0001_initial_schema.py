"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-10-28 20:00:14.560946

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('households',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('timezone', sa.String(length=64), nullable=False),
    sa.Column('auto_close_days', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_households'))
    )
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('login_name', sa.String(length=100), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('display_name', sa.String(length=100), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_admin', sa.Boolean(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('whatsapp', sa.String(length=50), nullable=True),
    sa.Column('transfer_number', sa.String(length=255), nullable=True),
    sa.Column('transfer_qr', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('login_name', name=op.f('uq_users_login_name'))
    )
    op.create_table('categories',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('color', sa.String(length=20), nullable=True),
    sa.Column('is_archived', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_categories_household_id_households'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_categories'))
    )
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_categories_household_id'), ['household_id'], unique=False)

    op.create_table('household_members',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_household_members_household_id_households'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_household_members_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_household_members')),
    sa.UniqueConstraint('household_id', 'user_id', name='uq_household_members_household_user')
    )
    with op.batch_alter_table('household_members', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_household_members_household_id'), ['household_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_household_members_user_id'), ['user_id'], unique=False)

    op.create_table('household_months',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('month', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('closed_by_user_id', sa.Uuid(), nullable=True),
    sa.Column('auto_close_exempt', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['closed_by_user_id'], ['users.id'], name=op.f('fk_household_months_closed_by_user_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_household_months_household_id_households'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_household_months')),
    sa.UniqueConstraint('household_id', 'year', 'month', name='uq_household_months_household_year_month')
    )
    with op.batch_alter_table('household_months', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_household_months_household_id'), ['household_id'], unique=False)

    op.create_table('cost_presets',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('category_id', sa.Uuid(), nullable=True),
    sa.Column('default_amount', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_cost_presets_category_id_categories'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_cost_presets_household_id_households'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cost_presets'))
    )
    with op.batch_alter_table('cost_presets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_cost_presets_household_id'), ['household_id'], unique=False)

    op.create_table('recurring_costs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('description', sa.String(length=200), nullable=False),
    sa.Column('category_id', sa.Uuid(), nullable=True),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('day_of_month', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_recurring_costs_category_id_categories'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_recurring_costs_household_id_households'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_recurring_costs'))
    )
    with op.batch_alter_table('recurring_costs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_recurring_costs_household_id'), ['household_id'], unique=False)

    op.create_table('costs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('month_id', sa.Uuid(), nullable=False),
    sa.Column('description', sa.String(length=200), nullable=False),
    sa.Column('category_id', sa.Uuid(), nullable=True),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('recurring_cost_id', sa.Uuid(), nullable=True),
    sa.Column('created_by_user_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_costs_category_id_categories'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name=op.f('fk_costs_created_by_user_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_costs_household_id_households'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['month_id'], ['household_months.id'], name=op.f('fk_costs_month_id_household_months'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recurring_cost_id'], ['recurring_costs.id'], name=op.f('fk_costs_recurring_cost_id_recurring_costs'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_costs'))
    )
    with op.batch_alter_table('costs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_costs_household_id'), ['household_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_costs_month_id'), ['month_id'], unique=False)

    op.create_table('recurring_cost_coverers',
    sa.Column('recurring_cost_id', sa.Uuid(), nullable=False),
    sa.Column('member_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['member_id'], ['household_members.id'], name=op.f('fk_recurring_cost_coverers_member_id_household_members'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recurring_cost_id'], ['recurring_costs.id'], name=op.f('fk_recurring_cost_coverers_recurring_cost_id_recurring_costs'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('recurring_cost_id', 'member_id', name=op.f('pk_recurring_cost_coverers'))
    )
    op.create_table('recurring_cost_payers',
    sa.Column('recurring_cost_id', sa.Uuid(), nullable=False),
    sa.Column('member_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['member_id'], ['household_members.id'], name=op.f('fk_recurring_cost_payers_member_id_household_members'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recurring_cost_id'], ['recurring_costs.id'], name=op.f('fk_recurring_cost_payers_recurring_cost_id_recurring_costs'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('recurring_cost_id', 'member_id', name=op.f('pk_recurring_cost_payers'))
    )
    op.create_table('cost_coverers',
    sa.Column('cost_id', sa.Uuid(), nullable=False),
    sa.Column('member_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['cost_id'], ['costs.id'], name=op.f('fk_cost_coverers_cost_id_costs'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['member_id'], ['household_members.id'], name=op.f('fk_cost_coverers_member_id_household_members'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('cost_id', 'member_id', name=op.f('pk_cost_coverers'))
    )
    op.create_table('cost_payers',
    sa.Column('cost_id', sa.Uuid(), nullable=False),
    sa.Column('member_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['cost_id'], ['costs.id'], name=op.f('fk_cost_payers_cost_id_costs'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['member_id'], ['household_members.id'], name=op.f('fk_cost_payers_member_id_household_members'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('cost_id', 'member_id', name=op.f('pk_cost_payers'))
    )


def downgrade() -> None:
    op.drop_table('cost_payers')
    op.drop_table('cost_coverers')
    op.drop_table('recurring_cost_payers')
    op.drop_table('recurring_cost_coverers')
    with op.batch_alter_table('costs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_costs_month_id'))
        batch_op.drop_index(batch_op.f('ix_costs_household_id'))

    op.drop_table('costs')
    with op.batch_alter_table('recurring_costs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_recurring_costs_household_id'))

    op.drop_table('recurring_costs')
    with op.batch_alter_table('cost_presets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cost_presets_household_id'))

    op.drop_table('cost_presets')
    with op.batch_alter_table('household_months', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_household_months_household_id'))

    op.drop_table('household_months')
    with op.batch_alter_table('household_members', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_household_members_user_id'))
        batch_op.drop_index(batch_op.f('ix_household_members_household_id'))

    op.drop_table('household_members')
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_categories_household_id'))

    op.drop_table('categories')
    op.drop_table('users')
    op.drop_table('households')
