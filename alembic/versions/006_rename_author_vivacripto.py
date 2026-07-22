"""Rename default author VivaCripto -> VerticeCripto (rebrand)

Revision ID: 006
Revises: 005
Create Date: 2026-07-21

Renomeia o autor padrão já existente em produção. Os posts publicados estão
assinados por 'VivaCripto'; após o rebrand o byline deve mostrar 'VerticeCripto'.
Idempotente: só atualiza a linha antiga se ela existir.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE authors SET name = 'VerticeCripto' WHERE name = 'VivaCripto'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE authors SET name = 'VivaCripto' WHERE name = 'VerticeCripto'"
    )
