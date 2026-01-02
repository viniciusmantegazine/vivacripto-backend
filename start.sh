#!/bin/bash
set -e

echo "🚀 Iniciando VivaCripto Backend..."

# Salvar DATABASE_URL original
ORIGINAL_DATABASE_URL="$DATABASE_URL"

# Usar DATABASE_PUBLIC_URL para migrações se disponível
if [ -n "$DATABASE_PUBLIC_URL" ]; then
    echo "📡 Usando DATABASE_PUBLIC_URL para migrações..."
    export DATABASE_URL="$DATABASE_PUBLIC_URL"
fi

# Função para executar migrações com retry
run_migrations() {
    local max_attempts=10
    local attempt=1
    local wait_time=3

    echo "📦 Executando migrações do banco de dados..."

    while [ $attempt -le $max_attempts ]; do
        echo "Tentativa $attempt de $max_attempts..."
        
        if alembic upgrade head 2>&1; then
            echo "✅ Migrações executadas com sucesso!"
            return 0
        else
            if [ $attempt -eq $max_attempts ]; then
                echo "❌ Falha ao executar migrações após $max_attempts tentativas."
                echo "⚠️  Iniciando aplicação mesmo assim (as tabelas podem já existir)..."
                return 1
            fi
            
            echo "❌ Falha ao executar migrações. Aguardando ${wait_time}s antes de tentar novamente..."
            sleep $wait_time
            attempt=$((attempt + 1))
            wait_time=$((wait_time + 2))  # Incremento linear
        fi
    done
}

# Executar migrações
run_migrations || true

# Restaurar DATABASE_URL original para a aplicação (deve ter +asyncpg)
echo "🔄 Restaurando DATABASE_URL original para aplicação..."
export DATABASE_URL="$ORIGINAL_DATABASE_URL"

# Iniciar aplicação
echo "🎯 Iniciando servidor FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
