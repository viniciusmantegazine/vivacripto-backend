# Regras de Negócio

## Regras Críticas

### 1. Limites Diários de Publicações

**Descrição**: O sistema limita publicações por dia para manter qualidade, controlar custo de API e evitar sobrecarga. Existem **dois limites independentes**, escopados por origem:

| Limite | Constante | Default | Escopo |
|---|---|---|---|
| Pipeline RSS | `NewsPipeline.MAX_POSTS_PER_DAY` | 10 | Todos os posts criados via `/automation/trigger` |
| Airdrop manual | `AIRDROP_DAILY_LIMIT` | 5 | Apenas posts com `category.slug == "airdrop"` |

Os limites **não se sobrepõem**: o limite de airdrop conta apenas posts na categoria airdrop do dia, então o pipeline RSS publicar 10 posts em outras categorias não consome o orçamento de airdrop, e vice-versa.

**Justificativa**:
- Manter curadoria de qualidade
- Controlar custos de API (Gemini/OpenAI/Claude)
- Evitar sobrecarga do portal e do leitor

**Implementação**:
- Arquivo: `app/services/automation/news_pipeline.py` (linhas 250-273) — pipeline RSS
- Arquivo: `app/api/v1/endpoints/automation.py` — trigger HTTP do pipeline
- Arquivo: `app/api/v1/endpoints/airdrops.py` — endpoint manual de airdrop (`_count_airdrop_posts_since`)

**Configuração**:
```python
# app/services/automation/news_pipeline.py
DAILY_POST_LIMIT = 10        # Pipeline RSS, todas as categorias
POSTS_PER_EXECUTION = 1      # Posts por execução do pipeline

# app/api/v1/endpoints/airdrops.py
AIRDROP_DAILY_LIMIT = 5      # Apenas categoria 'airdrop'
```

**Validações**:
- Conta posts com `published_at` no dia atual (UTC)
- Pipeline RSS conta TODOS os posts; airdrop endpoint conta apenas posts da categoria `airdrop`
- Retorna 429 quando excedido (airdrop) ou `DailyLimitReachedError` (pipeline)

**Exceções**:
- Atualizações de posts existentes NÃO contam no limite
- Preview de airdrop (`publish=false`) NÃO conta no limite (não persiste)
- Apenas novos posts (`CREATE_NEW`) são contabilizados

---

### 2. Threshold de Deduplicação

**Descrição**: Artigos com similaridade acima de 80% com posts existentes são considerados duplicatas.

**Justificativa**:
- Evitar conteúdo repetitivo
- Permitir atualizações de notícias em desenvolvimento
- Manter diversidade editorial

**Implementação**:
- Arquivo: `app/services/deduplication/duplicate_detector.py`
- Arquivo: `app/core/config.py` (linha 158)

**Configuração**:
```python
DEDUPLICATION_THRESHOLD = 0.80  # 80%
DEDUPLICATION_ENGINE = "embedding"
```

**Validações**:
- Compara título + excerpt + conteúdo
- Usa embeddings semânticos (sentence-transformers)
- Cache de embeddings em Redis para performance

**Ações por Similaridade**:
| Similaridade | Ação |
|--------------|------|
| < 80% | `CREATE_NEW` - Publica como novo |
| ≥ 80% | `UPDATE_EXISTING` - Atualiza existente |

---

### 3. Guardrails NFA (Not Financial Advice)

**Descrição**: O sistema implementa proteções para evitar que o conteúdo gerado contenha aconselhamento financeiro direto.

**Justificativa**:
- Compliance regulatório
- Proteção legal do portal
- Responsabilidade editorial

**Implementação**:
- Arquivo: `app/services/ai/content_generator.py` (linhas 108-141, 388-478)

**Frases Proibidas** (detectadas em sanitização):
```python
FORBIDDEN_PHRASES = [
    "investidores devem considerar",
    "recomendamos",
    "momento ideal para investir",
    "oportunidade de compra",
    "é hora de vender",
    "garantia de retorno",
    "lucro garantido",
]
```

**Regras de Geração**:
1. **Nunca** inventar números, datas ou estatísticas não presentes na fonte
2. **Sempre** atribuir dados específicos à fonte original
3. **Nunca** fazer previsões como fatos
4. **Sempre** usar linguagem como "analistas sugerem", "especialistas apontam"

**Comportamento**:
- Frases proibidas geram **warning** no log
- Conteúdo **NÃO é bloqueado** automaticamente
- Revisão manual recomendada para flags de NFA

---

### 4. Validação de Qualidade de Conteúdo

**Descrição**: Todo artigo gerado passa por validação de estrutura e tamanho antes da publicação.

**Justificativa**:
- Garantir consistência editorial
- Otimização para SEO
- Experiência de leitura adequada

**Implementação**:
- Arquivo: `app/services/automation/quality_validator.py`

**Regras de Validação**:
| Campo | Mínimo | Máximo | Obrigatório |
|-------|--------|--------|-------------|
| Título | 30 chars | 100 chars | Sim |
| Excerpt | 80 chars | 200 chars | Sim |
| Conteúdo | 250 palavras | 500 palavras | Sim |
| Meta Description | 120 chars | 180 chars | Sim |
| Slug | - | - | Sim |
| Categoria | - | - | Sim |

**Consequências**:
- Artigos que falham validação são **rejeitados**
- Erro logado com detalhes
- Pipeline continua com próxima notícia

---

### 5. Autenticação de Endpoints Administrativos

**Descrição**: Endpoints de escrita e automação requerem token Bearer válido.

**Justificativa**:
- Proteger contra acesso não autorizado
- Permitir apenas automação controlada
- Auditoria de operações

**Implementação**:
- Arquivo: `app/core/security.py`

**Tokens Utilizados**:
| Token | Propósito | Endpoints |
|-------|-----------|-----------|
| `AUTOMATION_TOKEN` | Pipeline e CRUD de posts | `/posts` (POST/PUT/DELETE), `/automation/*` |
| `REVALIDATE_SECRET` | Webhook ISR do frontend | `/api/revalidate` |

**Validações de Segurança**:
- Mínimo 32 caracteres
- Comparação timing-attack safe (`secrets.compare_digest`)
- Valores default inseguros bloqueados em produção

---

## Validações e Restrições

### Validação de Emails (Newsletter)

**Regras**:
- Formato de email válido (via `email-validator`)
- Email único por assinatura
- Reativação automática se já existente mas inativo

### Validação de Slugs

**Regras**:
- Gerado automaticamente a partir do título
- Caracteres ASCII lowercase + hífens
- Único por post

### Sanitização de Busca

**Regras**:
- Escape de wildcards SQL (`%`, `_`, `\`)
- Remoção de caracteres de controle
- Limite de 200 caracteres
- Trim de espaços

**Implementação**: `app/crud/crud_post.py` (linhas 17-47)

---

## Políticas e Workflows

### Workflow de Publicação

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Coleta    │───▶│   Geração   │───▶│  Validação  │
│   (RSS)     │    │    (IA)     │    │ (Qualidade) │
└─────────────┘    └─────────────┘    └──────┬──────┘
                                             │
                         ┌───────────────────┴───────────────────┐
                         │                                       │
                         ▼                                       ▼
                   ┌──────────┐                           ┌──────────┐
                   │  Válido  │                           │ Inválido │
                   └────┬─────┘                           └────┬─────┘
                        │                                      │
                        ▼                                      ▼
                 ┌─────────────┐                         ┌──────────┐
                 │ Deduplicação│                         │   Skip   │
                 └──────┬──────┘                         │  (log)   │
                        │                                └──────────┘
          ┌─────────────┴─────────────┐
          │                           │
          ▼                           ▼
    ┌───────────┐              ┌─────────────┐
    │ < 80% sim │              │ ≥ 80% sim   │
    │CREATE_NEW │              │UPDATE_EXIST │
    └─────┬─────┘              └──────┬──────┘
          │                           │
          ▼                           ▼
    ┌───────────┐              ┌─────────────┐
    │ Verifica  │              │  Atualiza   │
    │  Limite   │              │   Post      │
    └─────┬─────┘              └──────┬──────┘
          │                           │
          ▼                           │
    ┌───────────┐                     │
    │  Publica  │◀────────────────────┘
    │   Post    │
    └─────┬─────┘
          │
          ▼
    ┌───────────┐
    │Revalidate │
    │ Frontend  │
    └───────────┘
```

### Política de Categorização

**Categorias Disponíveis**:
| ID | Nome | Descrição |
|----|------|-----------|
| 1 | Bitcoin | Notícias sobre BTC |
| 2 | Ethereum | Notícias sobre ETH e ecossistema |
| 3 | Altcoins | Outras criptomoedas |
| 4 | DeFi | Finanças descentralizadas |
| 5 | Regulação | Regulamentação e compliance |
| 6 | Airdrop | Airdrops e distribuições |

**Classificação**:
- Automática via `CategoryClassifier`
- Baseada em keywords e contexto
- Fallback para categoria mais relevante

### Política de Status de Posts

**Estados**:
| Status | Descrição |
|--------|-----------|
| `draft` | Rascunho, não visível |
| `published` | Publicado e visível |
| `archived` | Arquivado, não visível |

---

## Cálculos e Algoritmos

### Cálculo de Similaridade (Embeddings)

```python
# Pseudo-código do algoritmo
def calculate_similarity(text1: str, text2: str) -> float:
    # 1. Gera embedding para cada texto
    embedding1 = sentence_transformer.encode(text1)
    embedding2 = sentence_transformer.encode(text2)

    # 2. Calcula similaridade de cosseno
    similarity = cosine_similarity(embedding1, embedding2)

    return similarity  # 0.0 a 1.0
```

**Modelo Utilizado**: `sentence-transformers/all-MiniLM-L6-v2`

### Cálculo de Word Count

```python
def count_words(text: str) -> int:
    # Remove markdown/HTML
    clean_text = strip_markdown(text)
    # Conta palavras
    words = clean_text.split()
    return len(words)
```

### Reset de Limite Diário

- **Horário**: Meia-noite UTC
- **Cálculo**: `datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)`
- **Timezone**: UTC (sem timezone local)

---

## Compliance e Regulamentações

### Requisitos NFA (Not Financial Advice)

| Requisito | Implementação |
|-----------|---------------|
| Não recomendar investimentos | Guardrails no prompt de geração |
| Não garantir retornos | Detecção de frases proibidas |
| Atribuir previsões | Regras de citação de fonte |
| Disclaimer implícito | Tom jornalístico neutro |

### Proteção de Dados

| Dado | Tratamento |
|------|------------|
| Emails (newsletter) | Armazenados com opt-in explícito |
| Logs | Sem dados pessoais identificáveis |
| Tokens | Comparação timing-safe |

---

## Regras de Domínio

### Invariantes

1. **Todo post publicado deve ter categoria**
2. **Todo post deve ter slug único**
3. **Limite diário não pode ser excedido para novos posts**
4. **Tokens de autenticação devem ter mínimo 32 caracteres**
5. **Posts duplicados (≥80% similaridade) não são criados como novos**

### Relacionamentos

```
Post ──────────▶ Category (N:1)
Post ──────────▶ Author (N:1)
Post ◀─────────▶ Tag (N:M via post_tags)
```

### Regras de Cascade

- `Post` deletado → `post_tags` deletados
- `Category` deletada → Posts órfãos (não permitido)
- `Author` deletado → Posts mantêm referência null
