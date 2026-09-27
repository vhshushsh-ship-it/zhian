"""add writing topics table

Revision ID: e7f8a9b0c1d2
Revises: c4d5e6f7a8b9
Create Date: 2026-09-27 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, Sequence[str], None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('writing_topics',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('category', sa.String(length=20), nullable=False),
    sa.Column('topic', sa.String(length=200), nullable=False),
    sa.Column('difficulty', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_writing_topics_category'), 'writing_topics', ['category'], unique=False)
    op.create_index(op.f('ix_writing_topics_created_at'), 'writing_topics', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_writing_topics_created_at'), table_name='writing_topics')
    op.drop_index(op.f('ix_writing_topics_category'), table_name='writing_topics')
    op.drop_table('writing_topics')
