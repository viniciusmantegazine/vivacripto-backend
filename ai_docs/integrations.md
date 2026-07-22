# Integrações

## Repositórios e Serviços Relacionados

### Frontend Next.js (verticecripto-frontend)

**Tipo**: Aplicação web consumidora
**Protocolo**: REST API + Webhook ISR
**Propósito**: Portal de notícias que consome e exibe o conteúdo gerado

**Comunicação**:
| Direção | Tipo | Endpoint |
|---------|------|----------|
| Frontend → Backend | REST | `GET /api/v1/posts/*` |
| Backend → Frontend | Webhook | `POST /api/revalidate` |

**Dados Trocados**:
- **Frontend → Backend**: Requisições de listagem, busca e detalhes de posts
- **Backend → Frontend**: Notificação de revalidação ISR após publicação

**Dependência**: Crítica (frontend é o único consumidor)

**Tratamento de Falhas**:
- Revalidação falha silenciosamente com log de warning
- Frontend continua funcionando com cache stale
- Retry manual possível via novo trigger de automação

**Configuração**:
```bash
FRONTEND_URL=https://verticecripto.com.br
REVALIDATE_SECRET=<secret-compartilhado-32-chars>
```

---

## Dependências Externas

### Google Gemini API

**Tipo**: API REST
**Propósito**: Geração de conteúdo e imagens (serviço primário)
**SDK**: `google-genai >= 1.5.0`

**Modelos Utilizados**:
| Modelo | Propósito |
|--------|-----------|
| `gemini-2.5-flash` | Geração de texto (artigos) |
| `gemini-3-pro-image-preview` | Geração de imagens |

**Configuração**:
```bash
GEMINI_API_KEY=<sua-chave>
```

**Tratamento de Falhas**:
- Fallback automático para OpenAI
- Log de warning quando fallback é usado
- Retry interno antes de fallback

**Arquivos**:
- `app/services/ai/content_generator.py`
- `app/services/ai/image_generator.py`

---

### OpenAI API

**Tipo**: API REST
**Propósito**: Fallback para geração de conteúdo e imagens
**SDK**: `openai >= 1.10.0`

**Modelos Utilizados**:
| Modelo | Propósito |
|--------|-----------|
| `gpt-4o-mini` | Geração de texto (fallback) |
| `dall-e-3` | Geração de imagens (fallback) |

**Configuração**:
```bash
OPENAI_API_KEY=sk-xxx
```

**Tratamento de Falhas**:
- Se OpenAI também falhar, operação retorna `None`
- Pipeline continua com próxima notícia
- Erro logado para investigação

---

### Anthropic Claude API

**Tipo**: API REST
**Propósito**: Geração analítica profunda (relatórios semanais + posts de airdrop)
**SDK**: `anthropic >= 0.18.0`

**Modelos Utilizados**:
| Modelo | Propósito |
|--------|-----------|
| `claude-opus-4-20250514` | Relatórios semanais (`weekly_report_generator`) |
| `claude-sonnet-4-6` | Geração de posts de airdrop (`airdrop_post_generator`) |

**Configuração**:
```bash
ANTHROPIC_API_KEY=sk-ant-xxx
```

**Otimização**:
- `airdrop_post_generator` usa **prompt caching** (`cache_control: ephemeral`) no system prompt — ~50% de desconto em retries dentro de 5 min e em chamadas back-to-back.

**Tratamento de Falhas**:
- Airdrop: fallback automático pra Gemini Flash via `ContentGenerator.gemini_client`
- Weekly report: sem fallback (relatório semanal exige Claude)

**Arquivos**:
- `app/services/ai/weekly_report_generator.py`
- `app/services/airdrop/airdrop_post_generator.py`

---

### DuckDuckGo Search (ddgs)

**Tipo**: Biblioteca Python (sem API key — scraping)
**Propósito**: Pesquisa web pra enriquecer contexto do airdrop generator
**SDK**: `ddgs >= 7.0.0` (fallback legacy: `duckduckgo_search`)

**Operações**:
- 3 queries por geração de airdrop (`{nome} airdrop`, `{nome} como participar`, `{nome} token tokenomics`)
- 4 resultados por query → 12 URLs candidatas
- Filtragem por blocklist (social/vídeo) e whitelist boost (fontes cripto confiáveis)
- Top 5 selecionadas pra fetch (oficial sempre incluída)

**Configuração**: Nenhuma (sem chave de API)

**Tratamento de Falhas**:
- Timeout dedicado de 15s (`DDG_TIMEOUT_SECONDS`)
- Se DDG falhar/timeout, segue com apenas a URL oficial fornecida pelo operador
- Erros por query são swallowed (loga warning, segue com próxima query)

**Limitações**:
- Sem garantia de SLA (scraping não-oficial)
- Rate limits informais do DDG podem retornar resultados vazios em alta volumetria
- Sem cache local — cada request faz busca nova

**Arquivos**:
- `app/services/airdrop/web_researcher.py` (`_search_ddg`, `gather_context`)

---

### Cloudinary

**Tipo**: API REST + CDN
**Propósito**: Armazenamento e distribuição de imagens
**SDK**: `cloudinary 1.38.0`

**Operações**:
- Upload de imagens geradas por IA
- Transformações automáticas (resize, quality)
- CDN para distribuição

**Configuração**:
```bash
CLOUDINARY_CLOUD_NAME=<cloud-name>
CLOUDINARY_API_KEY=<api-key>
CLOUDINARY_API_SECRET=<api-secret>
```

**Transformações Aplicadas**:
```python
transformation = {
    "width": 1200,
    "height": 630,
    "crop": "fill",
    "gravity": "center",
    "quality": "auto:good"
}
```

**Tratamento de Falhas**:
- Retry com formato diferente se upload falhar
- Bypass de validação Pillow se necessário
- Erro logado; post pode ser publicado sem imagem

---

### RSS Feeds (Fontes de Notícias)

**Tipo**: XML/RSS
**Propósito**: Coleta de notícias para processamento
**Parser**: `feedparser 6.0.11`

**Fontes Configuradas**:
| Fonte | URL |
|-------|-----|
| CoinDesk | `https://www.coindesk.com/arc/outboundfeeds/rss/` |
| Cointelegraph | `https://cointelegraph.com/rss` |
| Bitcoin Magazine | `https://bitcoinmagazine.com/.rss/full/` |
| CryptoSlate | `https://cryptoslate.com/feed/` |
| CoinPaper | `https://coinpaper.com/rss/news` |

**Configuração**: Hardcoded em `app/services/sources/rss_collector.py`

**Tratamento de Falhas**:
- Timeout de 10 segundos por feed
- 2 retries automáticos
- Feeds que falham são ignorados; outros continuam
- Mínimo de 1 notícia coletada para pipeline continuar

---

### PostgreSQL

**Tipo**: Banco de dados relacional
**Propósito**: Persistência de todos os dados
**Driver**: `asyncpg 0.29.0`
**ORM**: SQLAlchemy 2.0

**Configuração**:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/verticecripto
```

**Pool de Conexões**:
```python
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 20
DB_POOL_TIMEOUT = 30
DB_POOL_RECYCLE = 1800
```

**Tratamento de Falhas**:
- `pool_pre_ping=True` para detectar conexões mortas
- Retry de conexão no `migrate.sh` (até 10 tentativas)
- Transações com rollback automático em exceções

---

### Redis

**Tipo**: In-memory data store
**Propósito**: Cache de embeddings e rate limiting
**SDK**: `redis 5.0.1`

**Configuração**:
```bash
REDIS_URL=redis://localhost:6379/0
```

**Uso**:
| Feature | Descrição |
|---------|-----------|
| Embeddings Cache | Cache de vetores de similaridade |
| Rate Limiting | Storage para SlowAPI |
| Session Cache | Cache de dados de sessão |

**Tratamento de Falhas**:
- **Opcional**: Funciona sem Redis
- Fallback para memória local
- Log de warning se conexão falhar

---

### Sentry

**Tipo**: Error tracking SaaS
**Propósito**: Monitoramento de erros em produção
**SDK**: `sentry-sdk[fastapi] 1.39.2`

**Configuração**:
```bash
SENTRY_DSN=<dsn-opcional>
```

**Tratamento de Falhas**:
- **Opcional**: Funciona sem Sentry
- Se não configurado, erros só vão para logs locais

---

## Eventos

### Eventos Publicados (Outbound)

| Evento | Destino | Trigger |
|--------|---------|---------|
| ISR Revalidate | Frontend Next.js | Após publicação/atualização de post |

**Payload do Webhook**:
```json
{
  "secret": "REVALIDATE_SECRET"
}
```

**Headers**:
```
Content-Type: application/json
```

### Eventos Consumidos (Inbound)

| Evento | Origem | Handler |
|--------|--------|---------|
| RSS Items | Feeds externos | `RSSCollector.collect()` |
| CRON Trigger | Railway | `POST /automation/trigger` |

---

## Contratos de Integração

### Contrato com Frontend (Posts API)

**Endpoint**: `GET /api/v1/posts`

**Response Schema**:
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "string",
      "slug": "string",
      "excerpt": "string",
      "content": "markdown string",
      "content_html": "html string",
      "image_url": "url string",
      "meta_title": "string",
      "meta_description": "string",
      "published_at": "datetime",
      "category": {
        "id": "uuid",
        "name": "string",
        "slug": "string"
      },
      "tags": [
        {"id": "uuid", "name": "string"}
      ]
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 10,
  "total_pages": 10
}
```

### Contrato com Frontend (ISR Webhook)

**Endpoint**: `POST {FRONTEND_URL}/api/revalidate`

**Request**:
```json
{
  "secret": "REVALIDATE_SECRET"
}
```

**Expected Response**:
```json
{
  "revalidated": true
}
```

**Timeout**: 10 segundos

---

## Resiliência

### Circuit Breakers

O sistema não implementa circuit breakers formais, mas usa padrões de fallback:

```
Gemini API
    │
    ├── Sucesso → Continua
    │
    └── Falha → OpenAI API
                   │
                   ├── Sucesso → Continua
                   │
                   └── Falha → Retorna None
                               (pipeline continua)
```

### Retries

| Componente | Retries | Backoff |
|------------|---------|---------|
| RSS Feeds | 2 | Fixo |
| Migrations | 10 | +2s por tentativa |
| AI APIs | 1 (via fallback) | Imediato |
| Cloudinary | 1 (formato diferente) | Imediato |

### Timeouts

| Componente | Timeout |
|------------|---------|
| RSS Feeds | 10s |
| ISR Webhook | 10s |
| Database Pool | 30s |
| AI APIs | SDK default |

### Fallbacks

| Serviço Primário | Fallback | Último Recurso |
|------------------|----------|----------------|
| Gemini (texto) | OpenAI | `None` (skip) |
| Gemini (imagem) | DALL-E | Sem imagem |
| Redis | Memória | Sem cache |
| Sentry | - | Logs locais |

---

## Diagrama de Integração

```
                                    ┌─────────────┐
                                    │   Railway   │
                                    │   (CRON)    │
                                    └──────┬──────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     VerticeCripto Backend                          │
│                        (FastAPI)                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Services Layer                         │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │  │
│  │  │   Content   │ │   Image     │ │   Deduplication     │ │  │
│  │  │  Generator  │ │  Generator  │ │     Service         │ │  │
│  │  └──────┬──────┘ └──────┬──────┘ └──────────┬──────────┘ │  │
│  │         │               │                    │            │  │
│  └─────────┼───────────────┼────────────────────┼────────────┘  │
│            │               │                    │               │
└────────────┼───────────────┼────────────────────┼───────────────┘
             │               │                    │
     ┌───────┴───────┐       │              ┌─────┴─────┐
     │               │       │              │           │
     ▼               ▼       ▼              ▼           ▼
┌─────────┐    ┌─────────┐ ┌──────────┐ ┌───────┐ ┌──────────┐
│ Gemini  │    │ OpenAI  │ │Cloudinary│ │ Redis │ │PostgreSQL│
│  API    │    │  API    │ │   CDN    │ │(cache)│ │   (DB)   │
└─────────┘    └─────────┘ └──────────┘ └───────┘ └──────────┘
     ▲
     │
┌────┴────────────────────────────────┐
│           RSS Feeds                  │
│  CoinDesk │ Cointelegraph │ etc.    │
└─────────────────────────────────────┘

                    │
                    │ Webhook ISR
                    ▼
            ┌──────────────┐
            │   Frontend   │
            │  (Next.js)   │
            │ verticecripto-  │
            │   frontend   │
            └──────────────┘
```
