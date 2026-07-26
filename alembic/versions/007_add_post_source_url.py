"""Add source_url to posts (pré-filtro de notícias já processadas)

Revision ID: 007
Revises: 006
Create Date: 2026-07-26

O pipeline gastava chamadas de LLM regenerando notícias já processadas em
runs anteriores (coleta olha 24h para trás; cron roda várias vezes ao dia).
Persistir a URL da notícia original permite pular essas notícias ANTES da
geração de conteúdo.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('posts', sa.Column('source_url', sa.Text(), nullable=True))
    op.create_index('ix_posts_source_url', 'posts', ['source_url'])


def downgrade() -> None:
    op.drop_index('ix_posts_source_url', table_name='posts')
    op.drop_column('posts', 'source_url')
