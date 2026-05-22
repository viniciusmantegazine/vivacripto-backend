# Funcionalidades

## Funcionalidades Principais

### 1. Pipeline de Automação de Notícias

**Descrição**: Sistema completo que coleta notícias de fontes RSS, gera artigos em português usando IA, cria imagens únicas, valida qualidade, detecta duplicatas e publica automaticamente.

**Casos de Uso**:
- Publicação automática de conteúdo sobre criptomoedas
- Manutenção de portal de notícias atualizado 24/7
- Geração de conteúdo SEO-otimizado em português

**Componentes Envolvidos**:
- `app/services/automation/news_pipeline.py` - Orquestrador principal
- `app/services/sources/news_aggregator.py` - Agregador de notícias
- `app/services/ai/content_generator.py` - Geração de texto
- `app/services/ai/image_generator.py` - Geração de imagens
- `app/services/automation/quality_validator.py` - Validação
- `app/services/deduplication/duplicate_detector.py` - Deduplicação
- `app/services/automation/article_publisher.py` - Publicação

**Dependências**:
- Google Gemini API (primário) / OpenAI API (fallback)
- Cloudinary para armazenamento de imagens
- PostgreSQL para persistência
- Redis para cache de embeddings (opcional)

**Fluxo de Execução**:
```
1. Coleta (NewsAggregator)
   ├── RSS feeds de 5 fontes
   └── Retorna lista de NewsAssignment

2. Para cada notícia:
   ├── Geração de conteúdo (ContentGenerator)
   │   ├── Analisa contexto da notícia
   │   ├── Gera título, excerpt, conteúdo, meta tags
   │   └── Fallback Gemini → OpenAI
   │
   ├── Geração de imagem (ImageGenerator)
   │   ├── Cria prompt contextual
   │   ├── Gera imagem via Gemini/DALL-E
   │   └── Upload para Cloudinary
   │
   ├── Validação (QualityValidator)
   │   ├── Word count (250-500 palavras)
   │   ├── Tamanho de título (30-100 chars)
   │   ├── Excerpt (80-200 chars)
   │   └── Meta description (120-180 chars)
   │
   ├── Deduplicação (DuplicateDetector)
   │   ├── Calcula similaridade com posts existentes
   │   ├── Threshold: 0.80
   │   └── Decide: CREATE_NEW ou UPDATE_EXISTING
   │
   └── Publicação (ArticlePublisher)
       ├── Classifica categoria automaticamente
       ├── Converte Markdown → HTML
       └── Persiste no banco

3. Revalidação do Frontend
   └── Webhook para ISR do Next.js
```

---

### 2. Geração de Conteúdo com IA

**Descrição**: Transforma notícias de fontes em inglês em artigos completos em português brasileiro, mantendo tom jornalístico e evitando aconselhamento financeiro.

**Casos de Uso**:
- Tradução e adaptação de notícias internacionais
- Geração de conteúdo SEO-friendly
- Criação de artigos com tom adequado por categoria

**Componentes Envolvidos**:
- `app/services/ai/content_generator.py` (655 linhas)
- `app/services/ai/smart_prompt_generator.py` (393 linhas)
- `app/services/ai/news_context_analyzer.py` (974 linhas)
- `app/services/ai/category_classifier.py` (120 linhas)

**Características**:
| Aspecto | Detalhe |
|---------|---------|
| **Modelo Primário** | Google Gemini 2.5 Flash |
| **Modelo Fallback** | OpenAI GPT-4o-mini |
| **Idioma Output** | Português Brasileiro |
| **Word Count** | 250-500 palavras |
| **Tom** | Jornalístico, varia por categoria |

**Tons por Categoria**:
| Categoria | Tom |
|-----------|-----|
| `bitcoin` | Factual e analítico |
| `ethereum` | Técnico e educacional |
| `altcoins` | Informativo e cauteloso |
| `defi` | Educacional e técnico |
| `regulacao` | Formal e analítico |
| `airdrop` | Instrucional e direto |

**Guardrails (NFA)**:
- Proibido: "investidores devem considerar", "recomendamos", "momento ideal para investir"
- Obrigatório: Citar fonte de dados específicos
- Proibido: Inventar números, datas ou estatísticas
- Obrigatório: Previsões devem ser atribuídas a analistas

---

### 3. Geração de Imagens com IA

**Descrição**: Cria imagens únicas e contextuais para cada artigo, usando elementos visuais do universo cripto.

**Casos de Uso**:
- Ilustração automática de artigos
- Imagens otimizadas para redes sociais (1200x630)
- Evitar uso de imagens genéricas ou stock photos

**Componentes Envolvidos**:
- `app/services/ai/image_generator.py` (557 linhas)
- `app/services/ai/visual_elements_bank.py` (1157 linhas)
- `app/services/ai/smart_prompt_generator.py`

**Características**:
| Aspecto | Detalhe |
|---------|---------|
| **Modelo Primário** | Google Gemini 3.0 Pro Image Preview |
| **Modelo Fallback** | OpenAI DALL-E 3 |
| **Dimensões** | 1200x630 pixels |
| **Formato** | PNG (com conversão RGBA → RGB) |
| **Storage** | Cloudinary CDN |

**Elementos Visuais**:
- Elementos de criptomoedas (moedas, gráficos, redes)
- Composições editoriais profissionais
- Backgrounds contextuais por tipo de notícia
- Palavras bloqueadas para segurança

---

### 4. Detecção de Duplicatas

**Descrição**: Identifica artigos similares já publicados para evitar conteúdo repetitivo e decidir entre criar novo ou atualizar existente.

**Casos de Uso**:
- Evitar publicação de notícias repetidas
- Atualizar artigos existentes com novas informações
- Manter qualidade editorial do portal

**Componentes Envolvidos**:
- `app/services/deduplication/duplicate_detector.py`
- `app/services/deduplication/similarity_engine.py`
- `app/services/deduplication/repository.py`

**Algoritmos Disponíveis**:
| Engine | Descrição | Uso Recomendado |
|--------|-----------|-----------------|
| `embedding` | Similaridade semântica via sentence-transformers | **Produção** (padrão) |
| `tfidf` | TF-IDF vectorization | Testes, baixo custo |
| `levenshtein` | Distância de edição | Títulos exatos |
| `hybrid` | Combinação ponderada | Desenvolvimento |

**Configuração**:
```python
DEDUPLICATION_THRESHOLD = 0.80  # 80% similaridade = duplicata
DEDUPLICATION_ENGINE = "embedding"
```

**Ações Possíveis**:
| Ação | Condição | Resultado |
|------|----------|-----------|
| `CREATE_NEW` | Similaridade < 0.80 | Publica como novo artigo |
| `UPDATE_EXISTING` | Similaridade ≥ 0.80 | Atualiza artigo existente |

---

### 5. Validação de Qualidade

**Descrição**: Verifica se o conteúdo gerado atende aos padrões de qualidade antes da publicação.

**Casos de Uso**:
- Garantir consistência editorial
- Evitar publicação de conteúdo malformado
- Validar requisitos de SEO

**Componentes Envolvidos**:
- `app/services/automation/quality_validator.py`

**Validações**:
| Campo | Regra |
|-------|-------|
| Título | 30-100 caracteres |
| Excerpt | 80-200 caracteres |
| Conteúdo | 250-500 palavras |
| Meta Description | 120-180 caracteres |
| Slug | Presente e válido |
| Categoria | Presente |

---

### 6. Geração de Posts sobre Airdrops

**Descrição**: Endpoint manual que recebe nome de um projeto cripto + link oficial + link de referência do operador, pesquisa o projeto na web e gera um artigo educacional de 500-750 palavras com guardrails NFA, ou publica direto na categoria Airdrop.

**Casos de Uso**:
- Cobertura editorial de airdrops conhecidos
- Monetização via link de referência com disclosure obrigatória
- Manter categoria "Airdrop" populada (RSS quase não cobre)

**Componentes Envolvidos**:
- `app/api/v1/endpoints/airdrops.py` - Endpoint HTTP (preview + publish)
- `app/services/airdrop/airdrop_post_generator.py` - Orquestrador IA
- `app/services/airdrop/web_researcher.py` - Pesquisa DDG + fetch HTML
- `app/services/ai/prompts/airdrop_prompts.py` - System prompt + builder
- `app/schemas/airdrop.py` - Request/response schemas

**Características**:
| Aspecto | Detalhe |
|---------|---------|
| **Modelo Primário** | Claude Sonnet 4.6 (com prompt caching) |
| **Modelo Fallback** | Gemini Flash (via ContentGenerator) |
| **Word Count** | 500-750 palavras |
| **Pesquisa Web** | DuckDuckGo (`ddgs`) + fetch httpx + BeautifulSoup |
| **Top URLs** | 5 (4 do DDG + 1 oficial) |
| **Categoria** | Sempre `airdrop` (forçada via `force_category_slug`) |
| **Limite diário** | 5 publicações/dia (separado do pipeline RSS) |

**Fluxo de Execução**:
```
1. Auth + rate limit + validação Pydantic
   │
2. WebResearcher.gather_context()
   ├── 3 queries DDG paralelas
   ├── Blocklist (social/vídeo) + whitelist boost (CoinDesk, etc.)
   ├── Fetch paralelo top 5 URLs (oficial sempre incluída)
   ├── Extração de texto via BeautifulSoup (trunca a 3000 chars)
   └── Monta bloco "=== FONTES PESQUISADAS ===" pro prompt
   │
3. AirdropPostGenerator.generate()
   ├── Claude Sonnet 4.6 com prompt caching no system prompt
   ├── Fallback Gemini se Claude falhar
   ├── Validação extra: referral_url na seção "## Como participar",
   │   official_url no markdown, disclosure NFA presente
   ├── Regenera 1x com hint de correção se validação falhar
   └── Imagem só gerada se publish=true (economia)
   │
4. QualityValidator(min_words=500, max_words=750)
   │
5. Se publish=false → retorna preview markdown
   Se publish=true →
   ├── Verifica AIRDROP_DAILY_LIMIT (5/dia, escopo: categoria airdrop)
   ├── _resolve_unique_slug (retry com sufixo -2, -3, ...)
   ├── ArticlePublisher com force_category_slug="airdrop"
   └── _revalidate_frontend fire-and-forget
```

**Guardrails NFA Específicos**:
- Disclosure fixo no bloco final (texto exato no system prompt)
- Validação que link de referência está dentro de `## Como participar`
- Validação que link oficial aparece no disclosure
- Validação que frase "não constitui recomendação" aparece (Unicode-normalized)
- `project_name` sanitizado contra prompt injection (strip control chars, cap 200)

---

### 7. Gestão de Posts (CRUD)

**Descrição**: API completa para criar, ler, atualizar e deletar artigos.

**Casos de Uso**:
- Consumo pelo frontend Next.js
- Administração de conteúdo
- Busca e listagem de artigos

**Componentes Envolvidos**:
- `app/api/v1/endpoints/posts.py`
- `app/crud/crud_post.py`
- `app/schemas/post.py`

**Operações**:
| Operação | Endpoint | Auth |
|----------|----------|------|
| Listar | `GET /posts` | Público |
| Buscar | `GET /posts/search?q=` | Público |
| Obter por ID | `GET /posts/{id}` | Público |
| Obter por Slug | `GET /posts/slug/{slug}` | Público |
| Criar | `POST /posts` | Token |
| Atualizar | `PUT /posts/{id}` | Token |
| Deletar | `DELETE /posts/{id}` | Token |

---

### 8. Newsletter

**Descrição**: Sistema de inscrição para newsletter com validação de email e proteção contra duplicatas.

**Casos de Uso**:
- Captura de leads
- Comunicação com leitores
- Base para futuro envio automático

**Componentes Envolvidos**:
- `app/api/v1/endpoints/newsletter.py`
- `app/db/models.py` (NewsletterSubscriber)
- `app/schemas/newsletter.py`

**Funcionalidades**:
- Validação de email
- Prevenção de duplicatas
- Reativação de inscrições canceladas
- Rate limiting contra spam

---

## Funcionalidades Secundárias

### Health Checks

**Descrição**: Endpoints para monitoramento de saúde da aplicação.

**Endpoints**:
- `GET /health` - Status básico
- `GET /api/v1/health` - Status da API
- `GET /api/v1/health/database` - Conectividade do banco

### Rate Limiting

**Descrição**: Proteção contra abuso com limites por endpoint.

**Limites**:
| Endpoint | Limite |
|----------|--------|
| Leitura pública | 100/min |
| Busca | 30/min |
| Escrita autenticada | 20/min |
| Automação | 5/min |
| Newsletter | 10/min |

### Logging Estruturado

**Descrição**: Logs com contexto de request para debugging e auditoria.

**Features**:
- Request ID tracking
- Formato JSON em produção
- Rotação de arquivos de erro
- Integração com Sentry

### Métricas de Performance

**Descrição**: Coleta de métricas durante execução do pipeline.

**Métricas Coletadas**:
- Tempo de geração de conteúdo
- Tempo de geração de imagem
- Taxa de deduplicação
- Taxa de validação
- Contagem de publicações/atualizações

---

## Funcionalidades em Roadmap

### 1. Suporte a Mais Fontes de Notícias

**Status**: Planejado
**Descrição**: Adicionar novas fontes RSS e APIs de notícias (CryptoPanic, etc.)

### 2. Melhorias de IA

**Status**: Planejado
**Descrição**:
- Evolução dos prompts de geração
- Novos modelos conforme disponíveis
- Otimização de qualidade de imagens

### 3. Newsletter Automática

**Status**: Planejado
**Descrição**: Envio automático de newsletters com resumo de notícias do dia/semana

---

## Funcionalidades Deprecated

*Nenhuma funcionalidade deprecated no momento.*
