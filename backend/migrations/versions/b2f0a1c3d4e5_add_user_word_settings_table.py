"""add user word settings table

Revision ID: b2f0a1c3d4e5
Revises: 79b4f715ed6d
Create Date: 2026-09-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2f0a1c3d4e5'
down_revision: Union[str, Sequence[str], None] = '79b4f715ed6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('user_word_settings',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('current_book', sa.String(length=20), server_default='kaoyan', nullable=False),
    sa.Column('daily_new_goal', sa.Integer(), server_default='20', nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', name='uq_user_word_settings_user_id')
    )
    op.create_index(op.f('ix_user_word_settings_user_id'), 'user_word_settings', ['user_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_user_word_settings_user_id'), table_name='user_word_settings')
    op.drop_table('user_word_settings')
