"""add user_daily_stats table

Revision ID: c9d81f2a4b7e
Revises: 6ef7175035e6
Create Date: 2026-09-17 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d81f2a4b7e'
down_revision: Union[str, Sequence[str], None] = '6ef7175035e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('user_daily_stats',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('stat_date', sa.Date(), nullable=False),
    sa.Column('words_reviewed', sa.Integer(), server_default='0', nullable=False),
    sa.Column('words_new', sa.Integer(), server_default='0', nullable=False),
    sa.Column('speaking_messages', sa.Integer(), server_default='0', nullable=False),
    sa.Column('reading_minutes', sa.Integer(), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'stat_date', name='uq_user_daily_stats_user_date')
    )
    op.create_index(op.f('ix_user_daily_stats_user_id'), 'user_daily_stats', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_user_daily_stats_user_id'), table_name='user_daily_stats')
    op.drop_table('user_daily_stats')
