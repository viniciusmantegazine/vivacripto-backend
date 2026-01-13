"""Add performance indexes for common queries

Revision ID: 003
Revises: 002
Create Date: 2025-01-12

This migration adds indexes to improve query performance for:
- Filtering posts by status
- Ordering posts by published_at
- Filtering posts by created_at (daily limit checks)
- Filtering newsletter subscribers by email
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use IF NOT EXISTS para evitar erro se índice já existir
    op.execute('CREATE INDEX IF NOT EXISTS ix_posts_status ON posts (status)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_posts_published_at_desc ON posts (published_at DESC NULLS LAST)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_posts_created_at_desc ON posts (created_at DESC)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_posts_status_published_at ON posts (status, published_at DESC NULLS LAST)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_posts_category_id ON posts (category_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_posts_author_id ON posts (author_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_automation_logs_run_id ON automation_logs (run_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_automation_logs_created_at ON automation_logs (created_at DESC)')


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_automation_logs_created_at')
    op.execute('DROP INDEX IF EXISTS ix_automation_logs_run_id')
    op.execute('DROP INDEX IF EXISTS ix_posts_author_id')
    op.execute('DROP INDEX IF EXISTS ix_posts_category_id')
    op.execute('DROP INDEX IF EXISTS ix_posts_status_published_at')
    op.execute('DROP INDEX IF EXISTS ix_posts_created_at_desc')
    op.execute('DROP INDEX IF EXISTS ix_posts_published_at_desc')
    op.execute('DROP INDEX IF EXISTS ix_posts_status')
