"""Add unsubscribed_at column to newsletter_subscribers

Revision ID: 005
Revises: 004
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """O model NewsletterSubscriber tem unsubscribed_at, mas nenhuma migration
    a criava — causava UndefinedColumnError em queries de unsubscribe."""
    op.add_column(
        'newsletter_subscribers',
        sa.Column('unsubscribed_at', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('newsletter_subscribers', 'unsubscribed_at')
