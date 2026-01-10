#!/bin/bash
set -e

echo "🚀 Iniciando VivaCripto Backend..."

# Executar migrações do banco de dados
echo "📦 Executando migrações do banco de dados..."
if [ -n "$DATABASE_PUBLIC_URL" ]; then
    echo "📡 Usando DATABASE_PUBLIC_URL..."
    export DATABASE_URL="$DATABASE_PUBLIC_URL"
fi

alembic upgrade head || echo "⚠️ Aviso: Falha ao executar migrações (continuando...)"

echo "🎯 Iniciando servidor FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
