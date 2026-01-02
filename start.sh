#!/bin/bash
set -e

echo "🚀 Iniciando VivaCripto Backend..."

# Função para executar migrações com retry
run_migrations() {
    local max_attempts=5
    local attempt=1
    local wait_time=5

    echo "📦 Executando migrações do banco de dados..."

    while [ $attempt -le $max_attempts ]; do
        echo "Tentativa $attempt de $max_attempts..."
        
        if alembic upgrade head; then
            echo "✅ Migrações executadas com sucesso!"
            return 0
        else
            echo "❌ Falha ao executar migrações. Aguardando ${wait_time}s antes de tentar novamente..."
            sleep $wait_time
            attempt=$((attempt + 1))
            wait_time=$((wait_time * 2))  # Exponential backoff
        fi
    done

    echo "❌ Falha ao executar migrações após $max_attempts tentativas."
    echo "⚠️  Iniciando aplicação mesmo assim (as tabelas podem já existir)..."
    return 1
}

# Executar migrações
run_migrations || true

# Iniciar aplicação
echo "🎯 Iniciando servidor FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
