# Serviços Internos

## Visão Geral da Arquitetura de Serviços

O VivaCripto Backend organiza sua lógica de negócio em serviços especializados, cada um com responsabilidade bem definida.

```
app/services/
├── ai/                      # Serviços de Inteligência Artificial
│   ├── content_generator.py     # Geração de artigos
│   ├── image_generator.py       # Geração de imagens
│   ├── category_classifier.py   # Classificação automática
│   ├── smart_prompt_generator.py # Otimização de prompts
│   ├── news_context_analyzer.py  # Análise de contexto
│   └── visual_elements_bank.py   # Banco de elementos visuais
├── automation/              # Pipeline de Automação
│   ├── news_pipeline.py         # Orquestrador principal
│   ├── article_publisher.py     # Publicação de artigos
│   └── quality_validator.py     # Validação de qualidade
├── sources/                 # Coleta de Notícias
│   ├── news_aggregator.py       # Agregador multi-fonte
│   ├── rss_collector.py         # Coletor de RSS
│   └── api_collector.py         # Coletor de APIs
└── deduplication/           # Detecção de Duplicatas
    ├── duplicate_detector.py    # Detector principal
    ├── similarity_engine.py     # Engines de similaridade
    └── repository.py            # Repositório de dados
```

---

## Serviços de IA (app/services/ai/)

### ContentGenerator

**Arquivo**: `content_generator.py` (655 linhas)
**Responsabilidade**: Gerar artigos em português a partir de notícias fonte.

**Funcionalidades**:
- Transformação de notícias em inglês para artigos em português
- Aplicação de tom específico por categoria
- Guardrails NFA (Not Financial Advice)
- Fallback Gemini → OpenAI

**Configuração por Categoria**:
```python
CATEGORY_CONFIG = {
    "bitcoin": {"tom": "Factual e analítico", ...},
    "ethereum": {"tom": "Técnico e educacional", ...},
    "altcoins": {"tom": "Informativo e cauteloso", ...},
    "defi": {"tom": "Educacional e técnico", ...},
    "regulacao": {"tom": "Formal e analítico", ...},
    "airdrop": {"tom": "Instrucional e direto", ...},
}
```

**Métodos Principais**:
```python
class ContentGenerator:
    async def generate_article(
        self,
        source_news: NewsAssignment
    ) -> Optional[GeneratedArticle]:
        """Gera artigo completo a partir de notícia fonte."""

    async def _call_gemini(self, prompt: str) -> Optional[str]:
        """Chama API do Gemini."""

    async def _call_openai(self, prompt: str) -> Optional[str]:
        """Fallback para OpenAI."""

    def _sanitize_content(self, content: str) -> str:
        """Remove/flagga conteúdo problemático (NFA)."""
```

**Output (GeneratedArticle)**:
```python
@dataclass
class GeneratedArticle:
    title: str
    slug: str
    excerpt: str
    content: str  # Markdown
    meta_title: str
    meta_description: str
```

---

### ImageGenerator

**Arquivo**: `image_generator.py` (557 linhas)
**Responsabilidade**: Criar imagens únicas para artigos.

**Funcionalidades**:
- Geração via Gemini 3.0 Pro Image
- Fallback para DALL-E 3
- Upload automático para Cloudinary
- Tratamento de double base64

**Métodos Principais**:
```python
class ImageGenerator:
    async def generate_image(
        self,
        article: GeneratedArticle,
        category: str
    ) -> Optional[str]:
        """Gera imagem e retorna URL do Cloudinary."""

    async def _generate_with_gemini(self, prompt: str) -> Optional[bytes]:
        """Gera imagem via Gemini."""

    async def _generate_with_dalle(self, prompt: str) -> Optional[bytes]:
        """Fallback para DALL-E."""

    async def _upload_to_cloudinary(
        self,
        image_bytes: bytes,
        public_id: str
    ) -> Optional[str]:
        """Upload para Cloudinary com transformações."""
```

**Transformações Cloudinary**:
```python
transformation = {
    "width": 1200,
    "height": 630,
    "crop": "fill",
    "gravity": "center",
    "quality": "auto:good"
}
```

---

### CategoryClassifier

**Arquivo**: `category_classifier.py` (120 linhas)
**Responsabilidade**: Classificar automaticamente artigos em categorias.

**Categorias Disponíveis**:
| ID | Slug | Nome |
|----|------|------|
| 1 | bitcoin | Bitcoin |
| 2 | ethereum | Ethereum |
| 3 | altcoins | Altcoins |
| 4 | defi | DeFi |
| 5 | regulacao | Regulação |
| 6 | airdrop | Airdrop |

**Métodos Principais**:
```python
class CategoryClassifier:
    def classify(
        self,
        title: str,
        content: str
    ) -> str:
        """Retorna slug da categoria mais apropriada."""
```

---

### SmartPromptGenerator

**Arquivo**: `smart_prompt_generator.py` (393 linhas)
**Responsabilidade**: Gerar prompts otimizados para IA.

**Funcionalidades**:
- Contextualização baseada na notícia
- Elementos visuais apropriados
- Palavras bloqueadas para segurança

**Palavras Bloqueadas**:
```python
BLOCKED_WORDS = [
    "nude", "naked", "sexual", "porn",
    "weapon", "gun", "drug", "murder",
    "blood", "gore", "torture"
]
```

---

### NewsContextAnalyzer

**Arquivo**: `news_context_analyzer.py` (974 linhas)
**Responsabilidade**: Analisar contexto de notícias para geração.

**Funcionalidades**:
- Extração de entidades (moedas, exchanges, pessoas)
- Identificação de tom da notícia
- Análise de sentimento

---

### VisualElementsBank

**Arquivo**: `visual_elements_bank.py` (1157 linhas)
**Responsabilidade**: Gerenciar elementos visuais para imagens.

**Funcionalidades**:
- Biblioteca de elementos cripto (moedas, gráficos)
- Composições editoriais
- Backgrounds contextuais

---

## Serviços de Automação (app/services/automation/)

### NewsPipeline

**Arquivo**: `news_pipeline.py`
**Responsabilidade**: Orquestrar todo o pipeline de automação.

**Fluxo de Execução**:
```
1. Verifica limite diário
2. Coleta notícias (NewsAggregator)
3. Para cada notícia:
   a. Gera conteúdo (ContentGenerator)
   b. Gera imagem (ImageGenerator)
   c. Valida qualidade (QualityValidator)
   d. Verifica duplicatas (DuplicateDetector)
   e. Publica (ArticlePublisher)
4. Revalida frontend (webhook ISR)
5. Retorna métricas
```

**Métodos Principais**:
```python
class NewsPipeline:
    async def run(self) -> PipelineResult:
        """Executa pipeline completo."""

    async def _check_daily_limit(self) -> bool:
        """Verifica se limite diário foi atingido."""

    async def _collect_news(self) -> List[NewsAssignment]:
        """Coleta notícias de todas as fontes."""

    async def _process_news(
        self,
        assignment: NewsAssignment
    ) -> Optional[ProcessedArticle]:
        """Processa uma notícia individual."""

    async def _revalidate_frontend(self) -> None:
        """Envia webhook para revalidação ISR."""
```

**Configurações**:
```python
DAILY_POST_LIMIT = 10      # Máximo de posts por dia
POSTS_PER_EXECUTION = 1    # Posts por execução
```

**Resultado**:
```python
@dataclass
class PipelineResult:
    published: int
    updated: int
    skipped: int
    errors: int
    status: str
```

---

### ArticlePublisher

**Arquivo**: `article_publisher.py`
**Responsabilidade**: Persistir artigos no banco de dados.

**Funcionalidades**:
- Criação de novos posts
- Atualização de posts existentes
- Conversão Markdown → HTML
- Associação de categorias e tags

**Métodos Principais**:
```python
class ArticlePublisher:
    async def publish(
        self,
        article: ProcessedArticle,
        action: ActionType
    ) -> Optional[Post]:
        """Publica ou atualiza artigo."""

    async def _create_new(
        self,
        article: ProcessedArticle
    ) -> Post:
        """Cria novo post."""

    async def _update_existing(
        self,
        article: ProcessedArticle,
        existing_id: UUID
    ) -> Post:
        """Atualiza post existente."""
```

---

### QualityValidator

**Arquivo**: `quality_validator.py`
**Responsabilidade**: Validar qualidade do conteúdo gerado.

**Validações**:
| Campo | Regra |
|-------|-------|
| Título | 30-100 caracteres |
| Excerpt | 80-200 caracteres |
| Conteúdo | 250-500 palavras |
| Meta Description | 120-180 caracteres |

**Métodos Principais**:
```python
class QualityValidator:
    def validate(
        self,
        article: GeneratedArticle
    ) -> ValidationResult:
        """Valida artigo contra regras de qualidade."""

    def _validate_title(self, title: str) -> bool:
        """Valida tamanho do título."""

    def _validate_content(self, content: str) -> bool:
        """Valida word count."""

    def _count_words(self, text: str) -> int:
        """Conta palavras em texto."""
```

**Resultado**:
```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
```

---

## Serviços de Coleta (app/services/sources/)

### NewsAggregator

**Arquivo**: `news_aggregator.py`
**Responsabilidade**: Coordenar coleta de múltiplas fontes.

**Métodos Principais**:
```python
class NewsAggregator:
    async def collect(
        self,
        max_items: int = 10
    ) -> List[NewsAssignment]:
        """Coleta notícias de todas as fontes."""

    async def _aggregate_sources(self) -> List[RawNews]:
        """Agrega resultados de RSS e APIs."""
```

---

### RSSCollector

**Arquivo**: `rss_collector.py`
**Responsabilidade**: Coletar notícias de feeds RSS.

**Fontes Configuradas**:
```python
RSS_FEEDS = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Bitcoin Magazine", "https://bitcoinmagazine.com/.rss/full/"),
    ("CryptoSlate", "https://cryptoslate.com/feed/"),
    ("CoinPaper", "https://coinpaper.com/rss/news"),
]
```

**Métodos Principais**:
```python
class RSSCollector:
    async def collect(self) -> List[RawNews]:
        """Coleta de todos os feeds RSS."""

    async def _fetch_feed(
        self,
        name: str,
        url: str
    ) -> List[RawNews]:
        """Busca feed individual com retry."""
```

**Configurações**:
- Timeout: 10 segundos
- Retries: 2
- Graceful degradation: continua se feed falhar

---

### APICollector

**Arquivo**: `api_collector.py`
**Responsabilidade**: Coletar notícias de APIs externas.

**Status**: Estrutura preparada, APIs não ativadas atualmente.

**Potenciais Fontes**:
- CryptoPanic API
- Outras APIs de notícias

---

## Serviços de Deduplicação (app/services/deduplication/)

### DuplicateDetector

**Arquivo**: `duplicate_detector.py`
**Responsabilidade**: Detectar artigos duplicados ou similares.

**Fluxo**:
```
1. Recebe artigo candidato
2. Busca posts existentes
3. Calcula similaridade com cada um
4. Retorna ação baseada no threshold
```

**Métodos Principais**:
```python
class DuplicateDetector:
    async def check_duplicate(
        self,
        assignment: NewsAssignment
    ) -> DuplicateResult:
        """Verifica se notícia é duplicata."""

    def _calculate_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """Calcula similaridade entre textos."""
```

**Ações Possíveis**:
```python
class ActionType(Enum):
    CREATE_NEW = "create_new"
    UPDATE_EXISTING = "update_existing"
```

**Configuração**:
```python
DEDUPLICATION_THRESHOLD = 0.80  # 80%
DEDUPLICATION_ENGINE = "embedding"
```

---

### SimilarityEngine

**Arquivo**: `similarity_engine.py`
**Responsabilidade**: Calcular similaridade entre textos.

**Engines Disponíveis**:

| Engine | Descrição | Performance | Precisão |
|--------|-----------|-------------|----------|
| `embedding` | Sentence Transformers | Lenta | Alta |
| `tfidf` | TF-IDF vectorization | Média | Média |
| `levenshtein` | Distância de edição | Rápida | Baixa |
| `hybrid` | Combinação ponderada | Média | Alta |

**Interface**:
```python
class SimilarityEngine(ABC):
    @abstractmethod
    def calculate_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """Retorna similaridade de 0.0 a 1.0."""

    @abstractmethod
    def get_engine_type(self) -> str:
        """Retorna identificador do engine."""
```

**Factory**:
```python
class SimilarityFactory:
    @staticmethod
    def create(engine_type: str) -> SimilarityEngine:
        """Cria engine baseado no tipo."""
```

---

## Serviços Core (app/core/)

### CacheManager

**Arquivo**: `cache.py`
**Responsabilidade**: Gerenciar cache Redis.

**Métodos**:
```python
class CacheManager:
    async def connect(self) -> bool:
        """Conecta ao Redis."""

    async def get(self, key: str) -> Optional[Any]:
        """Busca valor do cache."""

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600
    ) -> bool:
        """Define valor no cache."""

    async def delete(self, key: str) -> bool:
        """Remove valor do cache."""
```

---

### Security

**Arquivo**: `security.py`
**Responsabilidade**: Autenticação e tokens.

**Métodos**:
```python
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Cria JWT token."""

def verify_automation_token(
    credentials: HTTPAuthorizationCredentials
) -> bool:
    """Verifica token de automação."""

def secure_compare(
    provided: str,
    expected: str
) -> bool:
    """Comparação timing-safe."""
```

---

### Metrics

**Arquivo**: `metrics.py`
**Responsabilidade**: Coletar métricas de execução.

**Métricas Coletadas**:
```python
@dataclass
class PipelineMetrics:
    news_collected: int
    content_generation_time: float
    image_generation_time: float
    deduplication_time: float
    validation_passed: int
    validation_failed: int
    published: int
    updated: int
    errors: int
```

**Uso**:
```python
with metrics.measure("content_generation"):
    article = await generator.generate_article(news)

metrics.record_publish()
metrics.log_summary()
```

---

## Comunicação Entre Serviços

### Diagrama de Dependências

```
┌─────────────────────────────────────────────────────────────┐
│                      NewsPipeline                           │
│                    (Orquestrador)                           │
└───────────┬──────────────┬────────────────┬────────────────┘
            │              │                │
            ▼              ▼                ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ NewsAggregator│  │ContentGenerator│  │QualityValidator│
└───────┬───────┘  └───────┬───────┘  └───────────────┘
        │                  │
        ▼                  ▼
┌───────────────┐  ┌───────────────┐
│ RSSCollector  │  │ ImageGenerator│
│ APICollector  │  │               │
└───────────────┘  └───────────────┘
                          │
            ┌─────────────┼─────────────┐
            │             │             │
            ▼             ▼             ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│DuplicateDetect│ │ArticlePublish │ │CategoryClassif│
└───────┬───────┘ └───────────────┘ └───────────────┘
        │
        ▼
┌───────────────┐
│SimilarityEngin│
└───────────────┘
```

### Fluxo de Dados

```
RawNews (RSS)
    │
    ▼
NewsAssignment
    │
    ▼
GeneratedArticle (texto + imagem)
    │
    ▼
ValidationResult
    │
    ▼
DuplicateResult (ação: CREATE/UPDATE)
    │
    ▼
Post (persistido)
    │
    ▼
PipelineResult (métricas)
```

---

## Observabilidade

### Logging

Todos os serviços usam `loguru` para logging estruturado:

```python
from app.core.logging import logger

logger.info("Processing news", extra={"source": "CoinDesk"})
logger.warning("Fallback triggered", extra={"from": "Gemini", "to": "OpenAI"})
logger.error("Generation failed", extra={"error": str(e)})
```

### Métricas

Métricas coletadas durante execução do pipeline:

- Tempo de cada estágio
- Contagem de sucessos/falhas
- Taxa de deduplicação
- Uso de fallbacks

### Health Checks

Cada serviço pode ser verificado indiretamente via:

```
GET /api/v1/health/database  # Verifica conexão DB
GET /api/v1/automation/status  # Verifica estado do pipeline
```
