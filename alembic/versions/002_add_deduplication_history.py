"""add deduplication_history to posts

Revision ID: 002_dedup_history
Revises: 001_initial_migration
Create Date: 2026-01-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '002_dedup_history'
down_revision = '001_initial_migration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add deduplication_history column to posts table"""
    op.add_column(
        'posts',
        sa.Column('deduplication_history', JSONB, nullable=True, server_default='[]')
    )


def downgrade() -> None:
    """Remove deduplication_history column from posts table"""
    op.drop_column('posts', 'deduplication_history')
