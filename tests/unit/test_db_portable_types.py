"""
Testes dos tipos de coluna portáteis (app/db/types.py).

Regressão: models.py usava `sqlalchemy.dialects.postgresql.UUID` e `JSONB`,
que o SQLite não compila. Qualquer teste com a fixture `db_session` morria
com `CompileError: Compiler can't render element of type UUID`, mantendo 47
testes inertes — o gotcha §6 de ai_docs/gotchas.md.

O contrato é: mesma semântica nos dois backends (entra e sai uuid.UUID),
tipo nativo no Postgres, equivalente portátil no SQLite.
"""
import uuid

import pytest
from sqlalchemy import Column, MetaData, Table, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.types import GUID, PortableJSONB


def test_guid_usa_uuid_nativo_no_postgres():
    assert "UUID" in str(GUID().compile(dialect=postgresql.dialect()))


def test_guid_usa_char36_no_sqlite():
    assert "CHAR(36)" in str(GUID().compile(dialect=sqlite.dialect()))


def test_jsonb_nativo_no_postgres_json_no_sqlite():
    assert "JSONB" in str(PortableJSONB().compile(dialect=postgresql.dialect()))
    assert "JSON" in str(PortableJSONB().compile(dialect=sqlite.dialect()))


@pytest.mark.asyncio
async def test_round_trip_no_sqlite_preserva_tipos():
    """Escrever e ler de volta em SQLite devolve uuid.UUID e o JSON intacto."""
    metadata = MetaData()
    tabela = Table(
        "amostra",
        metadata,
        Column("id", GUID(), primary_key=True),
        Column("payload", PortableJSONB()),
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    identificador = uuid.uuid4()
    payload = {"fontes": ["CoinDesk", "Decrypt"], "contagem": 2}

    try:
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
            await conn.execute(tabela.insert().values(id=identificador, payload=payload))
            linha = (await conn.execute(select(tabela))).one()
    finally:
        await engine.dispose()

    assert linha.id == identificador
    assert isinstance(linha.id, uuid.UUID)
    assert linha.payload == payload


@pytest.mark.asyncio
async def test_aceita_uuid_em_string():
    """IDs vindos de path params da API chegam como str — devem funcionar."""
    metadata = MetaData()
    tabela = Table("amostra", metadata, Column("id", GUID(), primary_key=True))

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    identificador = uuid.uuid4()

    try:
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
            await conn.execute(tabela.insert().values(id=str(identificador)))
            achado = (
                await conn.execute(select(tabela).where(tabela.c.id == str(identificador)))
            ).one()
    finally:
        await engine.dispose()

    assert achado.id == identificador
