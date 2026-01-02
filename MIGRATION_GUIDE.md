# Guia de Migrações do Banco de Dados

## Executar Migrações no Railway

### Opção 1: Via Railway CLI

```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Login
railway login

# Conectar ao projeto
railway link

# Executar migrações
railway run bash migrate.sh
```

### Opção 2: Via Dashboard do Railway

1. Acesse o dashboard do Railway
2. Vá para o serviço do backend
3. Clique em "Settings" → "Deploy"
4. Em "Custom Start Command", adicione temporariamente:
   ```
   bash migrate.sh && bash start.sh
   ```
5. Após o deploy com sucesso, remova o comando de migração e deixe apenas:
   ```
   bash start.sh
   ```

### Opção 3: Criar Migração Manualmente

Se as tabelas não existirem, você pode criá-las manualmente executando o SQL:

```bash
railway run psql $DATABASE_URL < init_db.sql
```

## Criar Nova Migração

Quando você modificar os modelos em `app/db/models.py`:

```bash
# Gerar migração automaticamente
alembic revision --autogenerate -m "Descrição da mudança"

# Aplicar migração
alembic upgrade head
```

## Reverter Migração

```bash
# Reverter última migração
alembic downgrade -1

# Reverter para versão específica
alembic downgrade <revision_id>
```
