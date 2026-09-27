"""add writing submissions table

Revision ID: c4d5e6f7a8b9
Revises: f1e2d3c4b5a6
Create Date: 2026-09-27 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, Sequence[str], None] = 'f1e2d3c4b5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('writing_submissions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('topic', sa.String(length=200), nullable=False),
    sa.Column('category', sa.String(length=20), nullable=False),
    sa.Column('difficulty', sa.String(length=20), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('score', sa.Integer(), nullable=True),
    sa.Column('feedback_json', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_writing_submissions_user_id'), 'writing_submissions', ['user_id'], unique=False)
    op.create_index(op.f('ix_writing_submissions_created_at'), 'writing_submissions', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_writing_submissions_created_at'), table_name='writing_submissions')
    op.drop_index(op.f('ix_writing_submissions_user_id'), table_name='writing_submissions')
    op.drop_table('writing_submissions')
