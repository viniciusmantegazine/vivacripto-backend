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
    # Index for filtering posts by status (very common filter)
    op.create_index(
        'ix_posts_status',
        'posts',
        ['status'],
        unique=False
    )

    # Index for ordering posts by published_at (common for listing)
    op.create_index(
        'ix_posts_published_at_desc',
        'posts',
        [sa.text('published_at DESC NULLS LAST')],
        unique=False
    )

    # Index for filtering posts by created_at (daily limit checks)
    op.create_index(
        'ix_posts_created_at_desc',
        'posts',
        [sa.text('created_at DESC')],
        unique=False
    )

    # Composite index for common query pattern: status + published_at
    op.create_index(
        'ix_posts_status_published_at',
        'posts',
        ['status', sa.text('published_at DESC NULLS LAST')],
        unique=False
    )

    # Index for category_id foreign key (improves JOIN performance)
    op.create_index(
        'ix_posts_category_id',
        'posts',
        ['category_id'],
        unique=False
    )

    # Index for author_id foreign key (improves JOIN performance)
    op.create_index(
        'ix_posts_author_id',
        'posts',
        ['author_id'],
        unique=False
    )

    # Index for automation_logs run_id (for querying logs by run)
    op.create_index(
        'ix_automation_logs_run_id',
        'automation_logs',
        ['run_id'],
        unique=False
    )

    # Index for automation_logs created_at (for time-based queries)
    op.create_index(
        'ix_automation_logs_created_at',
        'automation_logs',
        [sa.text('created_at DESC')],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_automation_logs_created_at', table_name='automation_logs')
    op.drop_index('ix_automation_logs_run_id', table_name='automation_logs')
    op.drop_index('ix_posts_author_id', table_name='posts')
    op.drop_index('ix_posts_category_id', table_name='posts')
    op.drop_index('ix_posts_status_published_at', table_name='posts')
    op.drop_index('ix_posts_created_at_desc', table_name='posts')
    op.drop_index('ix_posts_published_at_desc', table_name='posts')
    op.drop_index('ix_posts_status', table_name='posts')
