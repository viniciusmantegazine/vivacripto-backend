# Padrões de Design

## Padrões Arquiteturais

### Arquitetura em Camadas (Layered Architecture)

O projeto implementa uma arquitetura em 4 camadas bem definidas:

```
┌─────────────────────────────────────────────────────────┐
│                  Presentation Layer                      │
│                 (api/v1/endpoints/)                      │
│         HTTP routing, validação, formatação              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   Service Layer                          │
│                    (services/)                           │
│      Lógica de negócio, orquestração, integrações       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 Data Access Layer                        │
│                     (crud/)                              │
│          Abstração de acesso a dados                     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   Database Layer                         │
│                    (db/models)                           │
│              Modelos ORM, migrations                     │
└─────────────────────────────────────────────────────────┘
```

**Arquivos-chave por camada:**
- **Presentation**: `app/api/v1/endpoints/posts.py`, `automation.py`, `newsletter.py`
- **Service**: `app/services/automation/news_pipeline.py`, `app/services/ai/content_generator.py`
- **Data Access**: `app/crud/crud_post.py`
- **Database**: `app/db/models.py`

### Pipeline Pattern

O sistema de automação implementa um pipeline sequencial com estágios bem definidos:

```python
# app/services/automation/news_pipeline.py
class NewsPipeline:
    async def run(self):
        # Estágio 1: Coleta
        assignments = await self._collect_news()

        # Estágio 2: Processamento (para cada notícia)
        for assignment in assignments:
            # 2a: Geração de conteúdo
            article = await self._generate_content(assignment)

            # 2b: Geração de imagem
            image_url = await self._generate_image(article)

            # 2c: Validação
            is_valid = await self._validate(article)

            # 2d: Deduplicação
            action = await self._check_duplicate(article)

            # 2e: Publicação
            await self._publish(article, action)

        # Estágio 3: Revalidação do frontend
        await self._revalidate_frontend()
```

### Repository Pattern

Interface abstrata para operações de dados com implementações concretas:

```python
# app/core/repository.py
class BaseRepository(ABC, Generic[T, CreateSchema, UpdateSchema]):
    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> Optional[T]: ...

    @abstractmethod
    async def get_all(self, skip: int, limit: int) -> tuple[List[T], int]: ...

    @abstractmethod
    async def create(self, entity_in: CreateSchema) -> T: ...

    @abstractmethod
    async def update(self, entity_id: UUID, entity_in: UpdateSchema) -> Optional[T]: ...

    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool: ...

# Interface estendida com cache
class CacheableRepository(BaseRepository):
    @abstractmethod
    async def get_by_id_cached(self, entity_id: UUID, ttl: int) -> Optional[T]: ...

    @abstractmethod
    async def invalidate_cache(self, entity_id: UUID) -> None: ...
```

### Unit of Work Pattern

Gerenciamento de transações atômicas:

```python
# app/core/unit_of_work.py
class UnitOfWork:
    def __init__(self, auto_commit: bool = True):
        self.auto_commit = auto_commit

    async def __aenter__(self):
        self.session = await get_async_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.session.rollback()
        elif self.auto_commit:
            await self.session.commit()
        await self.session.close()
```

**Uso:**
```python
async with UnitOfWork() as uow:
    post = Post(**data)
    uow.session.add(post)
    # Commit automático no __aexit__ se não houver exceção
```

### Strategy Pattern

Múltiplas implementações de similaridade intercambiáveis:

```python
# app/services/deduplication/similarity_engine.py
class SimilarityEngine(ABC):
    @abstractmethod
    def calculate_similarity(self, text1: str, text2: str) -> float: ...

    @abstractmethod
    def get_engine_type(self) -> str: ...

class LevenshteinEngine(SimilarityEngine):
    def get_engine_type(self) -> str:
        return "levenshtein"

class TFIDFEngine(SimilarityEngine):
    def get_engine_type(self) -> str:
        return "tfidf"

class EmbeddingEngine(SimilarityEngine):
    def get_engine_type(self) -> str:
        return "embedding"

class HybridEngine(SimilarityEngine):
    def get_engine_type(self) -> str:
        return "hybrid"
```

### Factory Pattern

Criação de engines baseada em configuração:

```python
# app/services/deduplication/similarity_engine.py
class SimilarityFactory:
    @staticmethod
    def create(engine_type: str) -> SimilarityEngine:
        engines = {
            "levenshtein": LevenshteinEngine,
            "tfidf": TFIDFEngine,
            "embedding": EmbeddingEngine,
            "hybrid": HybridEngine,
        }
        return engines.get(engine_type, EmbeddingEngine)()
```

### Adapter Pattern

Adaptação de diferentes provedores de IA para interface comum:

```python
# app/services/ai/content_generator.py
class ContentGenerator:
    async def generate_article(self, source_news: NewsAssignment) -> Optional[Article]:
        # Tenta Gemini (primário)
        result = await self._call_gemini(prompt)

        if result is None:
            # Fallback para OpenAI
            result = await self._call_openai(prompt)

        return result
```

## Padrões de Código

### Dependency Injection (FastAPI)

Injeção de dependências via `Depends()`:

```python
# app/api/v1/endpoints/posts.py
@router.get("", response_model=PostList)
async def list_posts(
    request: Request,
    db: AsyncSession = Depends(get_db),        # Sessão do banco
    page: int = Query(1, ge=1),                # Parâmetros validados
    page_size: int = Query(10, ge=1, le=100),
):
    # db já está injetado e gerenciado
    posts, total = await crud_post.get_posts(db, skip=skip, limit=page_size)
```

### Singleton Pattern

Instâncias globais para serviços stateless:

```python
# app/core/config.py
settings = Settings()  # Singleton de configuração

# app/crud/crud_post.py
crud_post = CRUDPost()  # Singleton de CRUD

# app/core/cache.py
cache_manager = CacheManager()  # Singleton de cache
```

### Context Manager Pattern

Gerenciamento de recursos com `async with`:

```python
# app/db/base.py
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

# Uso
async with get_db() as db:
    result = await db.execute(query)
```

### Decorator Pattern

Rate limiting e autenticação via decorators:

```python
# app/api/v1/endpoints/posts.py
@router.get("")
@limiter.limit(RATE_LIMITS["public_read"])  # Rate limiting
async def list_posts(request: Request, ...):
    pass

@router.post("")
async def create_post(
    post_in: PostCreate,
    _: bool = Depends(verify_automation_token),  # Auth via dependency
):
    pass
```

## Organização de Código

### Estrutura de Pastas

```
app/
├── main.py                    # Entry point, middleware setup
├── core/                      # Cross-cutting concerns
│   ├── config.py             # Configurações centralizadas
│   ├── security.py           # Autenticação e tokens
│   ├── exceptions.py         # Hierarquia de exceções
│   ├── logging.py            # Logging estruturado
│   ├── cache.py              # Cache Redis
│   ├── rate_limiter.py       # Rate limiting
│   ├── repository.py         # Interfaces base
│   ├── unit_of_work.py       # Transações
│   └── metrics.py            # Métricas de performance
├── db/
│   ├── base.py               # Engine e session
│   ├── base_class.py         # Base model
│   └── models.py             # Modelos SQLAlchemy
├── schemas/
│   ├── post.py               # Schemas de Post
│   └── newsletter.py         # Schemas de Newsletter
├── crud/
│   └── crud_post.py          # CRUD de Post
├── api/
│   └── v1/
│       ├── api.py            # Router principal
│       └── endpoints/
│           ├── posts.py      # Endpoints de posts
│           ├── newsletter.py # Endpoints de newsletter
│           ├── automation.py # Endpoints de automação
│           └── health.py     # Health checks
└── services/
    ├── ai/
    │   ├── content_generator.py      # Geração de texto
    │   ├── image_generator.py        # Geração de imagens
    │   ├── category_classifier.py    # Classificação automática
    │   ├── smart_prompt_generator.py # Otimização de prompts
    │   ├── news_context_analyzer.py  # Análise de contexto
    │   └── visual_elements_bank.py   # Assets visuais
    ├── automation/
    │   ├── news_pipeline.py          # Orquestrador principal
    │   ├── article_publisher.py      # Publicação
    │   └── quality_validator.py      # Validação
    ├── sources/
    │   ├── news_aggregator.py        # Agregador
    │   ├── rss_collector.py          # RSS feeds
    │   └── api_collector.py          # APIs externas
    └── deduplication/
        ├── duplicate_detector.py     # Detector principal
        ├── similarity_engine.py      # Engines de similaridade
        └── repository.py             # Repositório de dedup
```

### Responsabilidades por Módulo

| Módulo | Responsabilidade |
|--------|------------------|
| `core/` | Infraestrutura compartilhada (config, auth, cache, logging) |
| `db/` | Persistência (models, sessions, migrations) |
| `schemas/` | Contratos de API (validação in/out) |
| `crud/` | Operações de banco (create, read, update, delete) |
| `api/` | Handlers HTTP (routing, request/response) |
| `services/` | Lógica de negócio (orquestração, integrações) |

## Convenções de Nomenclatura

### Classes
| Tipo | Convenção | Exemplo |
|------|-----------|---------|
| Model | Singular, PascalCase | `Post`, `Author`, `Category` |
| Schema | Operação como sufixo | `PostCreate`, `PostRead`, `PostUpdate` |
| Service | Verbo + Substantivo | `ContentGenerator`, `QualityValidator` |
| Repository | Sufixo Repository | `PostRepository`, `CacheableRepository` |
| Exception | Sufixo Error | `NotFoundError`, `ValidationError` |

### Funções
| Tipo | Convenção | Exemplo |
|------|-----------|---------|
| CRUD | verbo + entidade | `create_post()`, `get_posts()` |
| Async | mesmo padrão | `async def get_posts()` |
| Privada | underscore prefix | `_validate_content()`, `_call_gemini()` |
| Handler | HTTP verb + resource | `list_posts()`, `create_post()` |

### Variáveis
| Tipo | Convenção | Exemplo |
|------|-----------|---------|
| Constantes | UPPER_SNAKE_CASE | `MAX_POSTS_PER_DAY`, `RATE_LIMITS` |
| Variáveis | snake_case | `post_data`, `total_count` |
| Parâmetros | snake_case | `page_size`, `skip` |

### Arquivos
| Tipo | Convenção | Exemplo |
|------|-----------|---------|
| Módulos | snake_case | `content_generator.py`, `news_pipeline.py` |
| Testes | prefixo test_ | `test_crud_post.py`, `test_api_posts.py` |

## Padrões de Teste

### Organização de Testes

```
tests/
├── conftest.py              # Fixtures compartilhadas
├── unit/                    # Testes unitários
│   ├── test_crud_post.py
│   ├── test_news_pipeline.py
│   ├── test_quality_validator.py
│   └── test_article_publisher.py
└── integration/             # Testes de integração
    ├── test_api_posts.py
    └── test_api_health.py
```

### Fixtures (conftest.py)

```python
@pytest.fixture(scope="session")
def event_loop():
    """Event loop compartilhado para testes async."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def db_session(async_db_engine):
    """Sessão de banco isolada por teste."""
    async with AsyncSession(async_db_engine) as session:
        yield session

@pytest_asyncio.fixture
async def test_post(db_session, test_category, test_author):
    """Post de teste com dependências."""
    post = Post(title="Test", category_id=test_category.id, ...)
    db_session.add(post)
    await db_session.commit()
    return post
```

### Padrão Arrange-Act-Assert

```python
class TestCRUDPost:
    @pytest.mark.asyncio
    async def test_create_post(self, db_session, test_category):
        # Arrange
        post_data = PostCreate(title="Test", ...)

        # Act
        result = await crud_post.create_post(db_session, post_data)

        # Assert
        assert result.id is not None
        assert result.title == "Test"
```

### Mocking de Serviços Externos

```python
@pytest.fixture
def mock_openai():
    with patch("openai.AsyncOpenAI") as mock:
        client = AsyncMock()
        client.chat.completions.create.return_value = MockResponse(...)
        mock.return_value = client
        yield client

@pytest.fixture
def mock_cloudinary():
    with patch("cloudinary.uploader.upload") as mock:
        mock.return_value = {"secure_url": "https://example.com/image.jpg"}
        yield mock
```

## Padrões de Tratamento de Erros

### Hierarquia de Exceções

```python
# app/core/exceptions.py

# Exceções HTTP (retornam status codes)
class AppException(HTTPException):
    """Base para exceções HTTP."""

class NotFoundError(AppException):
    """404 - Recurso não encontrado."""
    def __init__(self, resource: str, identifier: Any):
        super().__init__(status_code=404, detail=f"{resource} {identifier} not found")

class ValidationError(AppException):
    """422 - Dados inválidos."""

class UnauthorizedError(AppException):
    """401 - Não autenticado."""

class ForbiddenError(AppException):
    """403 - Não autorizado."""

# Exceções de domínio (lógica de negócio)
class DomainException(Exception):
    """Base para exceções de domínio."""
    def __init__(self, message: str, **context):
        super().__init__(message)
        self.context = context

class ContentGenerationError(DomainException):
    """Falha na geração de conteúdo."""

class DeduplicationError(DomainException):
    """Falha na deduplicação."""

class DailyLimitReachedError(DomainException):
    """Limite diário de posts atingido."""
```

### Global Exception Handlers

```python
# app/main.py

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

### Error Recovery com Fallbacks

```python
# app/services/ai/content_generator.py
async def generate_article(self, source: NewsAssignment) -> Optional[Article]:
    try:
        # Tenta serviço primário
        return await self._call_gemini(source)
    except Exception as e:
        logger.warning(f"Gemini failed: {e}, trying OpenAI...")
        try:
            # Fallback
            return await self._call_openai(source)
        except Exception as e2:
            logger.error(f"All providers failed: {e2}")
            return None
```

## Boas Práticas Específicas

### Async/Await

- **Sempre** usar `async def` para operações I/O
- **Nunca** bloquear o event loop com operações síncronas
- Usar `asyncio.gather()` para paralelismo quando apropriado

```python
# BOM
async def process_news(items: List[NewsItem]):
    tasks = [process_single(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)

# EVITAR
def sync_operation():
    time.sleep(5)  # Bloqueia o event loop!
```

### Type Hints

Sempre incluir type hints em funções públicas:

```python
async def get_posts(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    status: Optional[str] = None,
) -> tuple[List[Post], int]:
    ...
```

### Logging Estruturado

Usar extras para contexto:

```python
logger.info(
    "Article published",
    extra={
        "post_id": str(post.id),
        "title": post.title[:50],
        "action": action.value,
    }
)
```

### Validação com Pydantic

Validar na borda (API), confiar internamente:

```python
# Schema valida entrada
class PostCreate(BaseModel):
    title: str = Field(..., min_length=10, max_length=200)
    content: str = Field(..., min_length=100)

# Endpoint recebe dados já validados
@router.post("")
async def create_post(post_in: PostCreate):  # Pydantic já validou
    ...
```
