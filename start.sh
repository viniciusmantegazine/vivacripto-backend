#!/bin/bash
set -e

echo "🚀 Iniciando VerticeCripto Backend..."

# Migrações: usam DATABASE_PUBLIC_URL se disponível (Railway às vezes só expõe
# a URL pública durante o build/deploy). A URL é passada inline SÓ para o
# alembic — o processo web (uvicorn) continua usando a DATABASE_URL interna.
echo "📦 Executando migrações do banco de dados..."
if [ -n "$DATABASE_PUBLIC_URL" ]; then
    echo "📡 Usando DATABASE_PUBLIC_URL para migrações..."
    DATABASE_URL="$DATABASE_PUBLIC_URL" alembic upgrade head
else
    alembic upgrade head
fi

echo "🎯 Iniciando servidor FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
