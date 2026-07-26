# Gotchas e Conhecimento Tácito

Este documento captura o conhecimento que desenvolvedores experientes acumulam ao longo do tempo - as "armadilhas" não documentadas, comportamentos contra-intuitivos e workarounds que são essenciais para trabalhar efetivamente neste repositório.

## Armadilhas Comuns

### 1. Configuração de Ambiente - Ordem de Chaves de API

**Sintoma**: Pipeline de automação falha silenciosamente ou usa fallback quando não deveria.

**Causa**: As chaves de API precisam ser configuradas na ordem correta de prioridade.

**Solução**: Configure na seguinte ordem de prioridade:
1. `GEMINI_API_KEY` - Primário (mais econômico)
2. `OPENAI_API_KEY` - Fallback (mais caro)
3. `CLOUDINARY_*` - Para upload de imagens

**Contexto**: O sistema usa Gemini como primário e OpenAI como fallback. Se Gemini falhar silenciosamente (chave inválida), todo o custo vai para OpenAI.

**Verificação**:
```bash
# Teste a chave Gemini antes de usar em produção
curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

---

### 2. AI Fallbacks - Comportamento Silencioso

**Sintoma**: Custos de API maiores que esperado; logs mostram muitos fallbacks.

**Causa**: Quando Gemini falha, o sistema automaticamente usa OpenAI sem interromper a execução.

**Solução**:
- Monitore logs para warnings de fallback
- Verifique regularmente os custos de cada API
- Configure alertas para taxa alta de fallbacks

**Arquivos relacionados**:
- `app/services/ai/content_generator.py` (linhas 340-370)
- `app/services/ai/image_generator.py` (linhas 170-206)

**Padrão de log para monitorar**:
```
[ContentGen] Gemini failed, trying OpenAI...
[ImageGen] Gemini image generation failed, falling back to DALL-E
```

---

### 3. Threshold de Deduplicação - Falsos Positivos/Negativos

**Sintoma**: Notícias únicas são rejeitadas como duplicatas, ou duplicatas são publicadas.

**Causa**: Threshold de 0.80 pode ser muito alto ou baixo dependendo do conteúdo.

**Solução**:
| Ambiente | Threshold | Engine | Comportamento |
|----------|-----------|--------|---------------|
| Desenvolvimento | 0.40 | hybrid | Permissivo |
| Staging | 0.60 | hybrid | Moderado |
| **Produção** | **0.80** | **embedding** | Restritivo |

**Configuração**:
```bash
DEDUPLICATION_THRESHOLD=0.80
DEDUPLICATION_ENGINE=embedding
```

**Diagnóstico**:
```python
# No log, procure por:
# "Similarity: 0.XX with post_id: ..."
# Se muitos posts têm similaridade entre 0.75-0.85, ajuste o threshold
```

---

### 4. Redis Opcional - Impacto em Performance

**Sintoma**: Deduplicação muito lenta em produção; mesmos embeddings recalculados repetidamente.

**Causa**: Sem Redis, o cache de embeddings é em memória e perdido entre requests.

**Solução**:
- **Desenvolvimento**: Redis opcional (funciona sem)
- **Produção**: Redis **fortemente recomendado**

**Impacto sem Redis**:
- Cada deduplicação recalcula embeddings (~500ms por post)
- Sem cache de sessão entre execuções
- Rate limiting usa memória (perdido em restart)

**Configuração**:
```bash
# Produção - adicione Redis
REDIS_URL=redis://default:xxx@redis.railway.internal:6379
```

---

### 5. Tokens Inseguros em Produção

**Sintoma**: Aplicação não inicia em produção com erro de validação.

**Causa**: Tokens com valores default ou muito curtos são bloqueados em `DEBUG=false`.

**Solução**: Todos os tokens devem ter mínimo 32 caracteres e não podem ser valores default.

**Valores bloqueados**:
```python
INSECURE_DEFAULTS = [
    "your-secret-key-change-in-production",
    "automation-service-token-change-in-production",
    "revalidation-secret-change-in-production",
    "secret",
    "changeme",
    "password",
    "",
]
```

**Geração de tokens seguros**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

### 6. Testes — UUID PostgreSQL vs SQLite ✅ RESOLVIDO (2026-07-26)

**Sintoma (histórico)**: Qualquer teste que usasse a fixture `db_session` quebrava com:
```
sqlalchemy.exc.CompileError: Compiler can't render element of type UUID
```

**Causa**: `app/db/models.py` importava `UUID`/`JSONB` de `sqlalchemy.dialects.postgresql` (tipos Postgres-only). Os testes rodam SQLite in-memory, que não compila esses tipos. 47 testes morriam antes de executar uma linha.

**Solução aplicada**: `app/db/types.py` define os TypeDecorators portáteis:
- `GUID` — `UUID` nativo no Postgres, `CHAR(36)` no resto. Sempre devolve `uuid.UUID`, aceita `uuid.UUID` ou `str` na entrada.
- `PortableJSONB` — `JSONB` no Postgres, `JSON` no resto.

`models.py` usa esses tipos. **As migrations Alembic seguem declarando `postgresql.UUID`/`JSONB` direto** — rodam só contra Postgres, não precisam (nem devem) ser portáteis.

**Ao escrever testes novos**: `db_session` funciona normalmente, use-a. O padrão de mockar `AsyncSession` (ainda presente em `tests/integration/test_api_airdrops_*.py` e em vários testes deste repo) continua válido para testes de unidade que não querem tocar banco, mas não é mais uma obrigação imposta por este gotcha.

**Lição**: enquanto os 47 testes ficaram cegos, dois bugs se esconderam atrás deles — `httpx 0.28` quebrando a fixture `api_client` (removeu `AsyncClient(app=...)`, exige `ASGITransport`) e 9 chamadas `PostCreate` sem o campo obrigatório `excerpt`. Teste que não roda não é rede de segurança; é passivo.

---

### 7. Testes — Rate Limiter Compartilhado

**Sintoma**: Tests de integração começam a retornar 429 quando rodados em sequência, mesmo isoladamente bem.

**Causa**: `slowapi.Limiter` é singleton por processo. O contador é compartilhado entre tests do mesmo endpoint.

**Solução**: `tests/conftest.py` faz monkey-patch de `slowapi.Limiter.limit` pra um no-op decorator. Isso desativa rate limiting em **todos** os testes.

**Implicação**: Não dá pra testar lógica de rate limit via pytest sem reverter esse patch.

```python
# tests/conftest.py
import slowapi
slowapi.Limiter.limit = _noop_limit
```

---

### 8. Tests — Env Vars Default

**Sintoma**: `Settings()` falha em testes com "SECRET_KEY inválida" ao importar `app.core.config`.

**Causa**: `Settings()` valida `SECRET_KEY` no construtor. Sem `.env`, falta a variável.

**Solução**: `tests/conftest.py` faz `os.environ.setdefault(...)` pras 4 envs obrigatórias **antes** de qualquer import que carregue config. Aplicado em module-level no topo do conftest.

**Implicação**: Testes que queiram validar comportamento de "SECRET_KEY ausente" devem usar `monkeypatch.delenv("SECRET_KEY")`.

---

## Comportamentos Contra-Intuitivos

### 1. Datetime - UTC vs Local

**O que parece**: O código usa `datetime.now()` normalmente.

**O que realmente acontece**: O código mistura `datetime.utcnow()` (naive) e `datetime.now(timezone.utc)` (aware).

**Por quê**: O banco usa `TIMESTAMP WITHOUT TIME ZONE`, incompatível com datetimes aware.

**Implicações**:
- Sempre use `datetime.utcnow()` para operações de banco
- JWT tokens usam `timezone.utc` (correto)
- Limite diário reseta em **meia-noite UTC**, não local

**Arquivos afetados**:
- `app/db/models.py` (linha 12-14) - naive
- `app/services/automation/news_pipeline.py` (linhas 255-273) - naive para banco
- `app/core/security.py` (linhas 25-27) - aware para JWT

---

### 2. Guardrails NFA - Warning, Não Bloqueio

**O que parece**: Conteúdo com frases proibidas de NFA seria bloqueado.

**O que realmente acontece**: Frases proibidas geram **warning no log**, mas conteúdo é **publicado**.

**Por quê**: É preferível publicar e revisar depois do que perder conteúdo válido por falso positivo.

**Implicações**:
- Monitore logs para `[NFA Warning]`
- Considere revisão manual para posts flagados
- Guardrails são *sugestões*, não *bloqueios*

---

### 3. Frontend Revalidation - Falha Silenciosa

**O que parece**: Webhook de revalidação é crítico para o ISR funcionar.

**O que realmente acontece**: Se o webhook falhar, o log registra warning e a execução continua.

**Por quê**: Falha de revalidação não deve impedir publicação de conteúdo.

**Implicações**:
- Posts podem estar publicados no banco mas não visíveis no frontend
- Verifique logs para `[Revalidation failed]`
- Cache do frontend pode estar desatualizado

**Arquivo**: `app/services/automation/news_pipeline.py` (linhas 275-296)

---

### 4. Categorização - Fallback para Default

**O que parece**: Toda notícia deve ter uma categoria específica atribuída.

**O que realmente acontece**: Se a classificação falhar, usa tom `"default"` (genérico).

**Por quê**: Melhor publicar com tom genérico do que não publicar.

**Implicações**:
- Alguns posts podem ter tom inconsistente
- Revise posts sem categoria específica periodicamente

---

## Workarounds e Soluções Temporárias

### 1. Double Base64 Gemini Images

**Problema Original**: Gemini às vezes retorna dados de imagem double-encoded em base64.

**Solução Aplicada**: Detecção automática e decodificação dupla quando necessário.

**Localização**: `app/services/ai/image_generator.py` (linhas 313-330)

**Status**: Permanente (bug do SDK, não do código)

**Cuidados**: Não remover a lógica de detecção mesmo que pareça "hacky".

```python
# O código verifica se os primeiros bytes parecem base64
first_chars = first_bytes.decode('ascii')
if all(c in 'ABCDEF...=' for c in first_chars):
    # É double-encoded, decodifica novamente
    image_bytes = base64.b64decode(image_bytes)
```

---

### 2. Pillow Validation Bypass

**Problema Original**: Nem todos os formatos de imagem do Gemini são validáveis pelo Pillow.

**Solução Aplicada**: Se Pillow falhar, faz upload direto para Cloudinary sem validação.

**Localização**: `app/services/ai/image_generator.py` (linhas 450-454)

**Status**: Permanente (limitação de formatos suportados)

**Cuidados**: Cloudinary pode rejeitar imagens inválidas; monitore erros de upload.

---

## Dependências de Ordem e Sequência

### 1. Middleware Order em FastAPI

**Contexto**: Setup de middlewares em `app/main.py`

**Ordem Necessária**:
1. Rate limiting (primeiro)
2. CORS
3. Request context
4. Exception handlers

**Consequência se Ignorado**: Rate limiting pode não funcionar corretamente.

**Código**:
```python
# app/main.py linha 46-47
# Rate limiting (deve vir antes dos outros middlewares)
setup_rate_limiting(app)
```

---

### 2. Migrations Antes do Start

**Contexto**: O servidor depende do schema do banco estar atualizado.

**Ordem Necessária**:
1. `alembic upgrade head`
2. `uvicorn app.main:app`

**Consequência se Ignorado**: Erros de colunas/tabelas inexistentes.

**Script**: `start.sh` já faz isso automaticamente.

---

### 3. Configuração de Ambiente Antes de Testes

**Contexto**: Testes precisam de variáveis mínimas configuradas.

**Ordem Necessária**:
1. Copiar `.env.example` para `.env`
2. Preencher pelo menos `SECRET_KEY`
3. Executar `pytest`

**Consequência se Ignorado**: Testes falham com erro de validação de config.

---

## Configurações Não-Óbvias

### 1. `DB_POOL_RECYCLE = 1800`

**Configuração**: Conexões são recicladas após 30 minutos

**Por que parece errado**: Por que não manter conexões indefinidamente?

**Por que está certo**: Evita conexões stale após timeouts do PostgreSQL ou reinícios do banco.

---

### 2. `pool_pre_ping = True`

**Configuração**: Testa conexões antes de usar

**Por que parece errado**: Overhead adicional em cada query

**Por que está certo**: Previne erros de "connection already closed" em produção

---

### 3. CORS sem `PATCH`

**Configuração**: Métodos permitidos: GET, POST, PUT, DELETE, OPTIONS

**Por que parece errado**: PATCH é comum para updates parciais

**Por que está certo**: A API usa PUT para todos os updates; PATCH não é usado

---

## Débitos Técnicos Conhecidos

### 1. Mistura de Datetime Patterns

**Descrição**: Código usa tanto `datetime.utcnow()` quanto `datetime.now(timezone.utc)`

**Impacto**: Potencial para bugs de comparação de timezone

**Origem**: Evolução orgânica do código

**Plano**: Padronizar para `datetime.utcnow()` em operações de banco

---

### 2. Sem Linter Configurado

**Descrição**: Não há `ruff`, `black`, ou `isort` configurado

**Impacto**: Inconsistência de formatação entre desenvolvedores

**Origem**: Setup inicial sem CI/CD

**Plano**: Adicionar `ruff` ou `black` com pre-commit hooks

---

### 3. Cobertura de Testes Parcial

**Descrição**: ~1958 linhas de testes para ~8782 linhas de código

**Impacto**: Alguns serviços de IA não têm testes unitários

**Origem**: Serviços de IA são difíceis de testar sem mocks extensivos

**Plano**: Aumentar cobertura com mocks de APIs externas

---

## Dicas de Desenvolvimento

### Ambiente Local

```bash
# 1. Clone e configure
git clone <repo>
cd verticecripto-backend
cp .env.example .env

# 2. Edite .env com chaves de API reais
# Mínimo necessário:
# - DATABASE_URL (pode usar SQLite para testes)
# - SECRET_KEY (32+ chars)
# - GEMINI_API_KEY (para gerar conteúdo)
# - OPENAI_API_KEY (fallback)
# - CLOUDINARY_* (para imagens)

# 3. Instale dependências
pip install -r requirements.txt

# 4. Execute migrations
alembic upgrade head

# 5. Inicie o servidor
uvicorn app.main:app --reload

# 6. Teste a API
curl http://localhost:8000/health
```

### Debugging

```bash
# Ver logs do pipeline
grep -E "(Pipeline|ContentGen|ImageGen|Dedup)" logs/app.log

# Verificar fallbacks de AI
grep "trying OpenAI\|falling back" logs/app.log

# Verificar deduplicação
grep "Similarity:" logs/app.log

# Verificar rate limiting
grep "rate limit" logs/app.log
```

### Performance

**Evitar**:
- Não chamar `/automation/trigger` mais de 5x/minuto (rate limited)
- Não desabilitar cache de embeddings em produção
- Não aumentar `POSTS_PER_EXECUTION` muito (custos de API)

**Otimizar**:
- Use Redis em produção para cache
- Configure `DAILY_POST_LIMIT` baseado em orçamento de API
- Monitore métricas de pipeline para identificar gargalos

### Testes

```bash
# Rodar todos os testes
pytest

# Com coverage
pytest --cov=app

# Apenas testes unitários
pytest tests/unit/

# Apenas testes de integração
pytest tests/integration/

# Teste específico
pytest tests/unit/test_crud_post.py -v

# Com output detalhado
pytest -v --tb=short
```

**Dica**: Testes usam SQLite em memória, não precisa de PostgreSQL local.

---

## O Que Eu Gostaria de Ter Sabido

1. **Configure Gemini primeiro**: É mais barato que OpenAI e deve ser o primário. Teste a chave antes de deploy.

2. **Redis não é opcional em produção**: Funciona sem, mas performance de deduplicação cai drasticamente.

3. **O limite diário é por UTC**: Se você está em BRT (UTC-3), o dia "vira" às 21h horário de Brasília.

4. **Fallbacks são silenciosos**: Se sua conta Gemini estiver com problema, você só descobre quando vê a fatura do OpenAI.

5. **Guardrails de NFA são warnings**: O conteúdo é publicado mesmo com flags; monitore os logs.

6. **O frontend precisa do webhook funcionando**: ISR não atualiza automaticamente; depende do `/api/revalidate`.

7. **Deduplicação com threshold 0.80 é conservadora**: Se muitas notícias únicas estão sendo rejeitadas, experimente 0.75.

8. **Railway tem CRON limitado**: Configure execuções algumas vezes ao dia, não a cada 30 minutos, para evitar custos extras.

9. **Sempre teste com `DEBUG=false` antes de deploy**: Validações de segurança só rodam em produção.

10. **Os comentários no código estão em português**: Toda a lógica de negócio está bem documentada nos próprios arquivos.

---

## Decisão pendente: o que `UPDATE_EXISTING` deveria fazer

Quando o `DuplicateDetector` decide `UPDATE_EXISTING`, o caminho vivo
(`ArticlePublisher.update_article`) **sobrescreve** o corpo do post com o
artigo novo. Não mescla, não guarda histórico.

O código continha uma implementação alternativa, mais rica, em
`DuplicateDetector.process_assignment` — método sem nenhum consumidor, removido
em 2026-07-26. O que ela fazia, registrado aqui porque a decisão de qual
comportamento é o certo continua aberta:

1. **Anexava com marcador de fonte** em vez de sobrescrever:
   `conteudo += f"\n\n[Atualização - {fonte}]\n{novo_conteudo}"`
2. **Guardava histórico** em `historico_atualizacoes`: timestamp, tipo da
   atualização, conteúdo adicionado, fonte e resumo da mudança. O campo NÃO
   existe no modelo do banco — `deduplication/repository.py` tem o comentário
   "Será implementado quando o campo for adicionado ao modelo".
3. **Tinha guarda de idempotência**: só anexava se o conteúdo novo já não
   estivesse presente.

**Nenhuma das duas abordagens é claramente melhor:**

| | Sobrescrever (vivo) | Anexar (intenção original) |
|---|---|---|
| Resultado | um artigo coerente | dois artigos de 700-1500 palavras concatenados |
| Perda | o texto original é destruído | nada se perde |
| Problema | perde a cobertura anterior | redundante, e estoura o limite de 1500 palavras do validador — que não é reexecutado em update |

Uma terceira via seria regerar um artigo mesclado, ao custo de mais uma chamada
de LLM.

**Ao decidir, considere junto:** o threshold do detector está em 0.80 e não
dispara (ver a seção sobre isso), então hoje o caminho de update quase nunca
roda. Corrigir o threshold aumenta a frequência disso e torna a escolha mais
urgente.
