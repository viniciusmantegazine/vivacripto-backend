#!/bin/bash
set -e

echo "🚀 Iniciando VivaCripto Backend..."
echo "🎯 Iniciando servidor FastAPI..."

exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
