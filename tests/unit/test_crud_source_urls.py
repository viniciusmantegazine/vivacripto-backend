"""
Testes de get_existing_source_urls. Usa AsyncSession mockada — a fixture
db_session real quebra com UUID/SQLite (ai_docs/gotchas.md §6).
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.crud.crud_post import get_existing_source_urls


@pytest.mark.asyncio
async def test_lista_vazia_nao_consulta_banco():
    db = MagicMock()
    db.execute = AsyncMock()

    result = await get_existing_source_urls(db, [], datetime(2026, 1, 1))

    assert result == set()
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_retorna_apenas_urls_existentes():
    db = MagicMock()
    query_result = MagicMock()
    query_result.all.return_value = [
        ("https://a.com/1",),
        ("https://b.com/2",),
    ]
    db.execute = AsyncMock(return_value=query_result)

    result = await get_existing_source_urls(
        db,
        ["https://a.com/1", "https://b.com/2", "https://c.com/3"],
        datetime(2026, 1, 1),
    )

    assert result == {"https://a.com/1", "https://b.com/2"}
