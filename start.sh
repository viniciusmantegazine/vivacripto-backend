#!/bin/bash
set -e

echo "🚀 Iniciando VivaCripto Backend..."

# Executar migrações em subprocesso separado
echo "📦 Executando migrações..."
bash /app/migrate.sh || echo "⚠️  Migrações falharam, mas continuando (tabelas podem já existir)"

# Iniciar aplicação
echo "🎯 Iniciando servidor FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
