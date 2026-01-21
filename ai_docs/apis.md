# Especificação de APIs

## Visão Geral da API

**Base URL**: `/api/v1`
**Versão**: 1.0.0
**Formato**: JSON
**Autenticação**: Bearer Token (endpoints protegidos)

**Documentação Interativa**:
- Swagger UI: `GET /api/v1/docs`
- ReDoc: `GET /api/v1/redoc`
- OpenAPI Schema: `GET /api/v1/openapi.json`

---

## Autenticação e Autorização

### Bearer Token

Endpoints protegidos requerem header `Authorization`:

```
Authorization: Bearer <AUTOMATION_TOKEN>
```

**Endpoints que requerem autenticação**:
- `POST /posts` - Criar post
- `PUT /posts/{id}` - Atualizar post
- `DELETE /posts/{id}` - Deletar post
- `POST /automation/trigger` - Executar pipeline
- `POST /automation/test-generation` - Testar geração

### Tokens Disponíveis

| Token | Variável | Propósito |
|-------|----------|-----------|
| Automação | `AUTOMATION_TOKEN` | CRUD de posts e pipeline |
| Revalidação | `REVALIDATE_SECRET` | Webhook ISR do frontend |

---

## Endpoints

### Posts

#### Listar Posts

```http
GET /api/v1/posts
```

**Autenticação**: Não requerida
**Rate Limit**: 100/min

**Query Parameters**:
| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `page` | int | 1 | Página atual (≥1) |
| `page_size` | int | 10 | Itens por página (1-100) |
| `status` | string | - | Filtrar por status |
| `category_id` | uuid | - | Filtrar por categoria |

**Resposta de Sucesso** (200):
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Bitcoin atinge nova máxima histórica",
      "slug": "bitcoin-atinge-nova-maxima-historica",
      "excerpt": "A principal criptomoeda do mercado...",
      "content": "# Bitcoin atinge nova máxima...",
      "content_html": "<h1>Bitcoin atinge nova máxima...</h1>",
      "image_url": "https://res.cloudinary.com/xxx/image.jpg",
      "meta_title": "Bitcoin atinge nova máxima histórica | VivaCripto",
      "meta_description": "A principal criptomoeda do mercado atingiu...",
      "status": "published",
      "published_at": "2024-01-15T10:30:00Z",
      "created_at": "2024-01-15T10:25:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "category": {
        "id": "uuid",
        "name": "Bitcoin",
        "slug": "bitcoin"
      },
      "author": {
        "id": "uuid",
        "name": "VivaCripto AI",
        "bio": "..."
      },
      "tags": [
        {"id": "uuid", "name": "Bitcoin", "slug": "bitcoin"}
      ]
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 10,
  "total_pages": 15
}
```

---

#### Buscar Posts

```http
GET /api/v1/posts/search
```

**Autenticação**: Não requerida
**Rate Limit**: 30/min

**Query Parameters**:
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `q` | string | Sim | Termo de busca (max 200 chars) |
| `page` | int | Não | Página atual |
| `page_size` | int | Não | Itens por página |

**Resposta de Sucesso** (200):
```json
{
  "items": [...],
  "total": 5,
  "page": 1,
  "page_size": 10,
  "total_pages": 1,
  "query": "bitcoin"
}
```

---

#### Obter Post por ID

```http
GET /api/v1/posts/{post_id}
```

**Autenticação**: Não requerida
**Rate Limit**: 100/min

**Path Parameters**:
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `post_id` | uuid | ID único do post |

**Resposta de Sucesso** (200):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Bitcoin atinge nova máxima histórica",
  "slug": "bitcoin-atinge-nova-maxima-historica",
  ...
}
```

**Códigos de Erro**:
- `404`: Post não encontrado

---

#### Obter Post por Slug

```http
GET /api/v1/posts/slug/{slug}
```

**Autenticação**: Não requerida
**Rate Limit**: 100/min

**Path Parameters**:
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `slug` | string | Slug URL do post |

**Resposta de Sucesso** (200): Mesmo schema de Post

**Códigos de Erro**:
- `404`: Post não encontrado

---

#### Criar Post

```http
POST /api/v1/posts
```

**Autenticação**: Requerida (`AUTOMATION_TOKEN`)
**Rate Limit**: 20/min

**Request Body**:
```json
{
  "title": "Título do artigo",
  "slug": "titulo-do-artigo",
  "excerpt": "Resumo curto do artigo...",
  "content": "# Conteúdo em Markdown...",
  "content_html": "<h1>Conteúdo em HTML...</h1>",
  "image_url": "https://example.com/image.jpg",
  "meta_title": "Título SEO",
  "meta_description": "Descrição para SEO",
  "status": "published",
  "category_id": "uuid",
  "author_id": "uuid",
  "tag_ids": ["uuid1", "uuid2"]
}
```

**Campos Obrigatórios**:
- `title`
- `content`

**Resposta de Sucesso** (201):
```json
{
  "id": "new-uuid",
  "title": "Título do artigo",
  ...
}
```

**Códigos de Erro**:
- `401`: Token inválido ou ausente
- `422`: Dados inválidos

---

#### Atualizar Post

```http
PUT /api/v1/posts/{post_id}
```

**Autenticação**: Requerida (`AUTOMATION_TOKEN`)
**Rate Limit**: 20/min

**Request Body**: Mesmo schema de criação (campos opcionais)

**Resposta de Sucesso** (200): Post atualizado

**Códigos de Erro**:
- `401`: Token inválido
- `404`: Post não encontrado
- `422`: Dados inválidos

---

#### Deletar Post

```http
DELETE /api/v1/posts/{post_id}
```

**Autenticação**: Requerida (`AUTOMATION_TOKEN`)
**Rate Limit**: 20/min

**Resposta de Sucesso** (204): No content

**Códigos de Erro**:
- `401`: Token inválido
- `404`: Post não encontrado

---

### Newsletter

#### Inscrever Email

```http
POST /api/v1/newsletter/subscribe
```

**Autenticação**: Não requerida
**Rate Limit**: 10/min

**Request Body**:
```json
{
  "email": "usuario@exemplo.com"
}
```

**Resposta de Sucesso** (201):
```json
{
  "message": "Inscrição realizada com sucesso",
  "email": "usuario@exemplo.com"
}
```

**Códigos de Erro**:
- `400`: Email já inscrito
- `422`: Email inválido

---

### Automação

#### Executar Pipeline

```http
POST /api/v1/automation/trigger
```

**Autenticação**: Requerida (`AUTOMATION_TOKEN`)
**Rate Limit**: 5/min

**Request Body**: Nenhum

**Resposta de Sucesso** (200):
```json
{
  "status": "completed",
  "published": 1,
  "updated": 0,
  "skipped": 2,
  "errors": 0,
  "message": "Pipeline executado com sucesso"
}
```

**Códigos de Erro**:
- `401`: Token inválido
- `429`: Limite diário atingido

---

#### Status de Automação

```http
GET /api/v1/automation/status
```

**Autenticação**: Não requerida

**Resposta de Sucesso** (200):
```json
{
  "daily_limit": 10,
  "published_today": 3,
  "remaining": 7,
  "last_execution": "2024-01-15T10:30:00Z"
}
```

---

#### Testar Geração

```http
POST /api/v1/automation/test-generation
```

**Autenticação**: Requerida (`AUTOMATION_TOKEN`)
**Rate Limit**: 5/min

**Descrição**: Testa a geração de conteúdo sem coletar notícias ou publicar.

**Request Body**:
```json
{
  "title": "Título da notícia de teste",
  "url": "https://example.com/news",
  "excerpt": "Resumo da notícia..."
}
```

**Resposta de Sucesso** (200):
```json
{
  "generated_title": "Título gerado",
  "generated_excerpt": "Excerpt gerado...",
  "generated_content": "# Conteúdo gerado...",
  "word_count": 350,
  "validation": {
    "is_valid": true,
    "errors": []
  }
}
```

---

### Health Checks

#### Health Check Básico

```http
GET /health
```

**Resposta de Sucesso** (200):
```json
{
  "status": "healthy"
}
```

---

#### Health Check da API

```http
GET /api/v1/health
```

**Resposta de Sucesso** (200):
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

#### Health Check do Banco

```http
GET /api/v1/health/database
```

**Resposta de Sucesso** (200):
```json
{
  "status": "healthy",
  "database": "connected"
}
```

**Códigos de Erro**:
- `503`: Banco indisponível

---

## Rate Limiting

### Limites por Endpoint

| Endpoint | Limite |
|----------|--------|
| Leitura pública (`GET /posts/*`) | 100/min |
| Busca (`GET /posts/search`) | 30/min |
| Escrita (`POST/PUT/DELETE /posts`) | 20/min |
| Automação (`POST /automation/*`) | 5/min |
| Newsletter | 10/min |
| Health checks | 1000/min |

### Headers de Resposta

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
Retry-After: 60
```

### Resposta de Rate Limit Excedido (429)

```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```

---

## Versionamento

A API usa versionamento via URL path:

- **Versão atual**: `/api/v1/`
- **Formato**: `/api/v{major}/`

Mudanças breaking incrementam a versão major.

---

## Webhooks

### Revalidação ISR

**Endpoint chamado**: `{FRONTEND_URL}/api/revalidate`
**Método**: POST
**Trigger**: Após publicação ou atualização de post

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

**Comportamento em Falha**:
- Log de warning
- Não bloqueia a operação principal

---

## Schemas Pydantic

### PostCreate

```python
class PostCreate(BaseModel):
    title: str = Field(..., min_length=10, max_length=200)
    slug: Optional[str] = None  # Gerado automaticamente se não fornecido
    excerpt: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=100)
    content_html: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    meta_title: Optional[str] = Field(None, max_length=100)
    meta_description: Optional[str] = Field(None, max_length=200)
    status: str = "draft"
    category_id: Optional[UUID] = None
    author_id: Optional[UUID] = None
    tag_ids: List[UUID] = []
```

### PostRead

```python
class PostRead(BaseModel):
    id: UUID
    title: str
    slug: str
    excerpt: Optional[str]
    content: str
    content_html: Optional[str]
    image_url: Optional[str]
    meta_title: Optional[str]
    meta_description: Optional[str]
    status: str
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryRead]
    author: Optional[AuthorRead]
    tags: List[TagRead]
```

### PostList

```python
class PostList(BaseModel):
    items: List[PostRead]
    total: int
    page: int
    page_size: int
    total_pages: int
```

---

## Exemplos de Uso

### Listar Posts Publicados

```bash
curl -X GET "https://api.vivacripto.com.br/api/v1/posts?status=published&page_size=5"
```

### Buscar Posts

```bash
curl -X GET "https://api.vivacripto.com.br/api/v1/posts/search?q=bitcoin"
```

### Criar Post (Autenticado)

```bash
curl -X POST "https://api.vivacripto.com.br/api/v1/posts" \
  -H "Authorization: Bearer $AUTOMATION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Novo artigo sobre Bitcoin",
    "content": "# Conteúdo do artigo...",
    "status": "published"
  }'
```

### Executar Pipeline

```bash
curl -X POST "https://api.vivacripto.com.br/api/v1/automation/trigger" \
  -H "Authorization: Bearer $AUTOMATION_TOKEN"
```

### Inscrever Newsletter

```bash
curl -X POST "https://api.vivacripto.com.br/api/v1/newsletter/subscribe" \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@exemplo.com"}'
```

---

## OpenAPI/Swagger

A documentação interativa está disponível em:

- **Swagger UI**: `https://api.vivacripto.com.br/api/v1/docs`
- **ReDoc**: `https://api.vivacripto.com.br/api/v1/redoc`

Para baixar o schema OpenAPI:

```bash
curl "https://api.vivacripto.com.br/api/v1/openapi.json" > openapi.json
```
