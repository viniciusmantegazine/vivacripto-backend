#!/bin/bash
set -e

echo "📦 Executando migrações do banco de dados..."

# Usar DATABASE_PUBLIC_URL se disponível
if [ -n "$DATABASE_PUBLIC_URL" ]; then
    echo "📡 Usando DATABASE_PUBLIC_URL..."
    export DATABASE_URL="$DATABASE_PUBLIC_URL"
fi

# Função para executar migrações com retry
run_migrations() {
    local max_attempts=10
    local attempt=1
    local wait_time=3

    while [ $attempt -le $max_attempts ]; do
        echo "Tentativa $attempt de $max_attempts..."
        
        if alembic upgrade head 2>&1; then
            echo "✅ Migrações executadas com sucesso!"
            return 0
        else
            if [ $attempt -eq $max_attempts ]; then
                echo "❌ Falha ao executar migrações após $max_attempts tentativas."
                return 1
            fi
            
            echo "❌ Falha. Aguardando ${wait_time}s..."
            sleep $wait_time
            attempt=$((attempt + 1))
            wait_time=$((wait_time + 2))
        fi
    done
}

# Falha explícita se as migrações não completarem após todas as tentativas.
run_migrations || exit 1
