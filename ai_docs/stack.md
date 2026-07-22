# Stack Tecnológica

## Linguagens e Runtime

| Tecnologia | Versão | Propósito |
|------------|--------|-----------|
| **Python** | 3.11+ | Linguagem principal |
| **Asyncio** | stdlib | Programação assíncrona |

## Frameworks Principais

| Framework | Versão | Propósito |
|-----------|--------|-----------|
| **FastAPI** | 0.109.0 | Framework web assíncrono |
| **Uvicorn** | 0.27.0 | Servidor ASGI |
| **Pydantic** | 2.5.3 | Validação de dados e schemas |
| **SQLAlchemy** | 2.0.25 | ORM assíncrono |
| **Alembic** | 1.13.1 | Migrations de banco de dados |

## Bibliotecas Chave

### AI e Geração de Conteúdo
| Biblioteca | Versão | Propósito |
|------------|--------|-----------|
| `google-genai` | ≥1.5.0 | Google Gemini API (primário do pipeline RSS) |
| `openai` | ≥1.10.0 | OpenAI GPT/DALL-E (fallback) |
| `anthropic` | ≥0.18.0 | Claude API (weekly report + airdrop generator) |
| `sentence-transformers` | 2.2.2 | Embeddings para deduplicação |
| `scikit-learn` | 1.3.2 | Algoritmos de similaridade |
| `torch` | 2.0.1 | PyTorch (dependência) |

### HTTP e Networking
| Biblioteca | Versão | Propósito |
|------------|--------|-----------|
| `httpx` | ≥0.28.1 | Cliente HTTP assíncrono |
| `aiohttp` | 3.9.1 | HTTP alternativo |
| `feedparser` | 6.0.11 | Parser de feeds RSS |
| `ddgs` | ≥7.0.0 | Busca DuckDuckGo (airdrop web research) |
| `beautifulsoup4` | ≥4.12.0 | Parser HTML (extração de fontes do airdrop) |

### Segurança e Autenticação
| Biblioteca | Versão | Propósito |
|------------|--------|-----------|
| `python-jose[cryptography]` | 3.3.0 | JWT tokens |
| `passlib[bcrypt]` | 1.7.4 | Hashing de senhas |
| `python-multipart` | 0.0.6 | Upload de arquivos |

### Imagens e Media
| Biblioteca | Versão | Propósito |
|------------|--------|-----------|
| `cloudinary` | 1.38.0 | Upload e CDN de imagens |
| `Pillow` | 10.2.0 | Processamento de imagens |

### Utilidades
| Biblioteca | Versão | Propósito |
|------------|--------|-----------|
| `python-slugify` | 8.0.1 | Geração de slugs URL |
| `markdown` | 3.5.1 | Conversão Markdown → HTML |
| `loguru` | 0.7.2 | Logging estruturado |
| `python-dotenv` | 1.0.0 | Variáveis de ambiente |

### Rate Limiting e Cache
| Biblioteca | Versão | Propósito |
|------------|--------|-----------|
| `redis` | 5.0.1 | Cache e rate limiting storage |
| `slowapi` | 0.1.9 | Rate limiting |

### Monitoramento
| Biblioteca | Versão | Propósito |
|------------|--------|-----------|
| `sentry-sdk[fastapi]` | 1.39.2 | Rastreamento de erros |

## Banco de Dados

### PostgreSQL
- **Versão**: 14+
- **Driver**: `asyncpg` 0.29.0 (assíncrono)
- **ORM**: SQLAlchemy 2.0 com suporte async
- **Migrations**: Alembic

### Configuração de Pool
```python
DB_POOL_SIZE = 10          # Conexões base no pool
DB_MAX_OVERFLOW = 20       # Conexões extras permitidas
DB_POOL_TIMEOUT = 30       # Timeout para obter conexão (segundos)
DB_POOL_RECYCLE = 1800     # Reciclar conexões após 30 minutos
```

### Modelos Principais
| Modelo | Propósito |
|--------|-----------|
| `Post` | Artigos publicados |
| `Author` | Autores de artigos |
| `Category` | Categorias de conteúdo |
| `Tag` | Tags de artigos |
| `NewsletterSubscriber` | Assinantes da newsletter |
| `AutomationLog` | Logs de execução do pipeline |

### Redis (Opcional)
- **Propósito**: Cache de embeddings, rate limiting
- **Padrão**: Funciona sem Redis (fallback para memória)
- **Recomendado**: Sim, para produção

## Infraestrutura

### Deploy
| Plataforma | Propósito |
|------------|-----------|
| **Railway** | Deploy principal (produção) |
| **Docker** | Containerização |

### Containerização
```dockerfile
# Base image
FROM python:3.11-slim

# Dependências de sistema
RUN apt-get update && apt-get install -y gcc postgresql-client

# Porta exposta
EXPOSE 8000

# Comando de inicialização
CMD ["./start.sh"]
```

### Scripts de Deploy
| Script | Propósito |
|--------|-----------|
| `start.sh` | Inicialização do servidor (migrations + uvicorn) |
| `migrate.sh` | Migrations com retry logic |
| `init_db.sql` | Inicialização manual do banco |

## Ferramentas de Desenvolvimento

### Testes
| Ferramenta | Versão | Propósito |
|------------|--------|-----------|
| `pytest` | 8.0.0 | Framework de testes |
| `pytest-asyncio` | 0.23.3 | Testes assíncronos |
| `pytest-cov` | 4.1.0 | Cobertura de código |
| `pytest-mock` | 3.12.0 | Mocking |
| `aiosqlite` | 0.19.0 | SQLite async para testes |

### Configuração de Testes
```ini
# pytest.ini
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
```

### Linting e Formatação
- Não há configuração explícita de linters no repositório
- Recomendado: `ruff` ou `black` + `isort`

## Arquitetura Geral

```
app/
├── main.py                    # Entry point FastAPI
├── core/                      # Infraestrutura cross-cutting
│   ├── config.py             # Settings (Pydantic BaseSettings)
│   ├── security.py           # JWT, tokens, auth
│   ├── logging.py            # Loguru setup
│   ├── cache.py              # Redis cache
│   ├── rate_limiter.py       # SlowAPI setup
│   ├── exceptions.py         # Hierarquia de exceções
│   ├── repository.py         # Interfaces de repositório
│   └── unit_of_work.py       # Padrão Unit of Work
├── db/                        # Camada de dados
│   ├── base.py               # Engine e session factory
│   ├── base_class.py         # Base class para models
│   └── models.py             # Modelos SQLAlchemy
├── schemas/                   # Pydantic schemas
├── crud/                      # Operações CRUD
├── api/v1/                    # Endpoints da API
│   ├── api.py                # Router agregador
│   └── endpoints/            # Handlers por recurso
└── services/                  # Lógica de negócio
    ├── ai/                   # Serviços de IA
    ├── automation/           # Pipeline de automação
    ├── sources/              # Coleta de notícias
    └── deduplication/        # Detecção de duplicatas
```

## Decisões Arquiteturais Importantes

### Por que FastAPI?
- **Performance**: Async-first, comparable a Node.js/Go
- **Tipagem**: Integração nativa com Pydantic e type hints
- **Documentação**: OpenAPI/Swagger automático
- **Ecossistema**: Compatível com todo o ecossistema Python de ML/AI

### Por que Google Gemini como Primário?
- **Custo**: Mais econômico que OpenAI para volume de produção
- **Qualidade**: Gemini 2.5 Flash oferece boa qualidade para geração de texto
- **Imagens**: Gemini 3.0 Pro gera imagens sem custo adicional de DALL-E
- **Fallback**: OpenAI mantido como backup para confiabilidade

### Por que PostgreSQL?
- **Robustez**: ACID compliance, confiável para produção
- **Features**: JSONB para deduplication_history, full-text search
- **Async**: Suporte nativo via asyncpg
- **Ecossistema**: Bem suportado por Railway e outros PaaS

### Por que Embeddings para Deduplicação?
- **Precisão**: Detecta similaridade semântica, não apenas textual
- **Escalabilidade**: Cacheável via Redis
- **Alternativas**: TF-IDF e Levenshtein disponíveis para casos específicos

## Variáveis de Ambiente

### Obrigatórias
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/verticecripto

# Segurança (mínimo 32 caracteres cada)
SECRET_KEY=<token-seguro-32-chars>
AUTOMATION_TOKEN=<token-seguro-32-chars>
REVALIDATE_SECRET=<token-seguro-32-chars>

# AI APIs
GEMINI_API_KEY=<sua-chave-gemini>
OPENAI_API_KEY=<sua-chave-openai>

# Cloudinary
CLOUDINARY_CLOUD_NAME=<cloud-name>
CLOUDINARY_API_KEY=<api-key>
CLOUDINARY_API_SECRET=<api-secret>

# Frontend
FRONTEND_URL=https://verticecripto.com.br
```

### Opcionais
```bash
# Redis (recomendado para produção)
REDIS_URL=redis://localhost:6379/0

# Monitoramento
SENTRY_DSN=<dsn-do-sentry>

# Configurações de automação
DAILY_POST_LIMIT=10
POSTS_PER_EXECUTION=1
DEDUPLICATION_THRESHOLD=0.80
DEDUPLICATION_ENGINE=embedding

# Debug
DEBUG=false
```

### Validações de Segurança
O sistema valida automaticamente:
- Tokens com mínimo de 32 caracteres
- Valores não podem ser defaults inseguros ("secret", "changeme", etc.)
- Em produção (`DEBUG=false`), falha se tokens inseguros

## Requisitos de Sistema

### Desenvolvimento
- Python 3.11+
- PostgreSQL 14+
- 4GB RAM (para sentence-transformers)
- Redis opcional

### Produção (Railway)
- PostgreSQL addon
- Redis addon (recomendado)
- 512MB+ RAM
- Variáveis de ambiente configuradas
