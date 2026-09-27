"""add user daily tasks table

Revision ID: f9a0b1c2d3e4
Revises: e7f8a9b0c1d2
Create Date: 2026-09-27 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9a0b1c2d3e4'
down_revision: Union[str, Sequence[str], None] = 'e7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('user_daily_tasks',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('task_type', sa.String(length=20), nullable=False),
    sa.Column('task_title', sa.String(length=200), nullable=False),
    sa.Column('done', sa.Boolean(), server_default=sa.text('0'), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'date', 'task_type', name='uq_user_daily_tasks_user_date_type')
    )
    op.create_index(op.f('ix_user_daily_tasks_user_id'), 'user_daily_tasks', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_daily_tasks_date'), 'user_daily_tasks', ['date'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_user_daily_tasks_date'), table_name='user_daily_tasks')
    op.drop_index(op.f('ix_user_daily_tasks_user_id'), table_name='user_daily_tasks')
    op.drop_table('user_daily_tasks')
