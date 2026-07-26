"""
Tipos de coluna portáteis entre Postgres (produção) e SQLite (testes).

Motivação: `models.py` usava `sqlalchemy.dialects.postgresql.UUID` e `JSONB`
direto. São tipos Postgres-only: o SQLite não os compila e qualquer teste com
a fixture `db_session` morria com

    sqlalchemy.exc.CompileError: Compiler can't render element of type UUID

o que deixava 47 testes inertes (ver ai_docs/gotchas.md §6). Com estes
TypeDecorators, produção continua usando os tipos nativos do Postgres e os
testes ganham um equivalente que o SQLite entende.

IMPORTANTE: as migrations Alembic continuam declarando `postgresql.UUID` /
`JSONB` diretamente — elas só rodam contra Postgres, então não precisam (nem
devem) ser portáteis.
"""
import uuid
from typing import Optional

from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import CHAR, JSON, TypeDecorator


class GUID(TypeDecorator):
    """
    UUID nativo no Postgres, CHAR(36) nos demais dialetos.

    Equivale a `UUID(as_uuid=True)`: valores entram como `uuid.UUID` ou str e
    SEMPRE saem como `uuid.UUID`, em qualquer backend — o código da aplicação
    não precisa saber onde está rodando.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    @staticmethod
    def _coerce(value) -> Optional[uuid.UUID]:
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))

    def process_bind_param(self, value, dialect):
        coerced = self._coerce(value)
        if coerced is None:
            return None
        # O driver do Postgres aceita o objeto UUID; no CHAR(36) gravamos a
        # forma canônica com hífens para que a comparação por igualdade e a
        # ordenação sejam estáveis.
        if dialect.name == "postgresql":
            return coerced
        return str(coerced)

    def process_result_value(self, value, dialect):
        return self._coerce(value)


class PortableJSONB(TypeDecorator):
    """JSONB no Postgres, JSON no resto (o SQLite guarda como TEXT)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())
