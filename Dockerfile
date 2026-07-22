FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application (inclui start.sh e migrate.sh)
COPY . .

# Scripts executáveis
RUN chmod +x start.sh migrate.sh

# Criar usuário não-root e garantir que logs/ seja gravável por ele
RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p logs \
    && chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["./start.sh"]
