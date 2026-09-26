"""add reading articles and history

Revision ID: a1b2c3d4e5f6
Revises: c9d81f2a4b7e
Create Date: 2026-09-17 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c9d81f2a4b7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('reading_articles',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('difficulty', sa.String(length=20), nullable=False),
    sa.Column('topic', sa.String(length=50), nullable=False),
    sa.Column('word_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('long_sentences', sa.Text(), nullable=False),
    sa.Column('quiz', sa.Text(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reading_articles_difficulty'), 'reading_articles', ['difficulty'], unique=False)
    op.create_index(op.f('ix_reading_articles_topic'), 'reading_articles', ['topic'], unique=False)
    op.create_index(op.f('ix_reading_articles_created_at'), 'reading_articles', ['created_at'], unique=False)

    op.create_table('reading_history',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('article_id', sa.Integer(), nullable=False),
    sa.Column('read_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('quiz_score', sa.Float(), nullable=True),
    sa.Column('words_collected', sa.Integer(), server_default='0', nullable=False),
    sa.ForeignKeyConstraint(['article_id'], ['reading_articles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'article_id', name='uq_reading_history_user_article')
    )
    op.create_index(op.f('ix_reading_history_user_id'), 'reading_history', ['user_id'], unique=False)
    op.create_index(op.f('ix_reading_history_article_id'), 'reading_history', ['article_id'], unique=False)

    op.add_column('user_word_progress', sa.Column('source_article_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_user_word_progress_source_article_id', 'user_word_progress', 'reading_articles', ['source_article_id'], ['id'])
    op.create_index(op.f('ix_user_word_progress_source_article_id'), 'user_word_progress', ['source_article_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_user_word_progress_source_article_id'), table_name='user_word_progress')
    op.drop_constraint('fk_user_word_progress_source_article_id', 'user_word_progress', type_='foreignkey')
    op.drop_column('user_word_progress', 'source_article_id')
    op.drop_index(op.f('ix_reading_history_article_id'), table_name='reading_history')
    op.drop_index(op.f('ix_reading_history_user_id'), table_name='reading_history')
    op.drop_table('reading_history')
    op.drop_index(op.f('ix_reading_articles_created_at'), table_name='reading_articles')
    op.drop_index(op.f('ix_reading_articles_topic'), table_name='reading_articles')
    op.drop_index(op.f('ix_reading_articles_difficulty'), table_name='reading_articles')
    op.drop_table('reading_articles')
