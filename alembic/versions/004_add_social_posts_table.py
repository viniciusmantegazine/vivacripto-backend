"""Add social_posts table for tracking social media publications

Revision ID: 004_add_social_posts
Revises: 003_add_performance_indexes
Create Date: 2026-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'social_posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('platform_post_id', sa.String(255), nullable=True),
        sa.Column('platform_url', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.CheckConstraint("platform IN ('twitter', 'instagram', 'linkedin')", name='check_social_platform'),
        sa.CheckConstraint("status IN ('pending', 'success', 'failed')", name='check_social_status'),
    )

    # Index for querying by post_id
    op.create_index('ix_social_posts_post_id', 'social_posts', ['post_id'])

    # Index for querying by platform and status
    op.create_index('ix_social_posts_platform_status', 'social_posts', ['platform', 'status'])


def downgrade() -> None:
    op.drop_index('ix_social_posts_platform_status', table_name='social_posts')
    op.drop_index('ix_social_posts_post_id', table_name='social_posts')
    op.drop_table('social_posts')
