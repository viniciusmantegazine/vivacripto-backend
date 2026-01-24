#!/bin/bash
set -e

echo "🚀 Iniciando VivaCripto Backend..."

# Usar DATABASE_PUBLIC_URL se disponível
if [ -n "$DATABASE_PUBLIC_URL" ]; then
    echo "📡 Usando DATABASE_PUBLIC_URL..."
    export DATABASE_URL="$DATABASE_PUBLIC_URL"
fi

# Reset do banco de dados se RESET_DATABASE=true
if [ "$RESET_DATABASE" = "true" ]; then
    echo "⚠️ RESET_DATABASE=true detectado. Resetando banco de dados..."
    echo "🗑️ Executando downgrade para base..."
    alembic downgrade base || echo "⚠️ Downgrade falhou (banco pode estar vazio)"
    echo "📦 Executando upgrade para head..."
    alembic upgrade head
    echo "🌱 Inserindo dados iniciais..."
    psql "$DATABASE_URL" -f init_db.sql || echo "⚠️ init_db.sql falhou (pode já existir)"
    echo "✅ Reset completo!"
else
    echo "📦 Executando migrações do banco de dados..."
    alembic upgrade head || echo "⚠️ Aviso: Falha ao executar migrações (continuando...)"
fi

echo "🎯 Iniciando servidor FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
