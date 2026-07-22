# Airdrop Post Generator — Design

**Data:** 2026-05-21
**Autor:** Vinicius Mantega (com assistência do Claude)
**Status:** Aprovado, aguardando plano de implementação

## Contexto e Objetivo

Hoje a categoria "Airdrop" (id 6) do VerticeCripto não é populada — todas as notícias vêm do pipeline RSS, que raramente cobre airdrops específicos. O objetivo é criar um **endpoint manual** que recebe os dados básicos de um projeto cripto com expectativa de airdrop e gera/publica um artigo educacional sobre ele, embutindo o link de referência do operador do portal.

**Premissas de produto:**

- Conteúdo precisa ter **tom neutro**, sem indução a investimento (compliance NFA).
- **Disclosure obrigatório** de que o link é de referência.
- Geração deve usar **pesquisa web** para enriquecer contexto, evitando alucinação.
- Endpoint é **manual** (operado pelo dono do portal), não roda no cron de automação diária.

## Não-objetivos

- Pesquisar e disparar airdrops automaticamente (sem trigger manual).
- Gerenciar lista persistente de "airdrops cadastrados" — cada chamada é stateless.
- Calcular ou exibir valores monetários esperados do airdrop.
- Lidar com cadastros/autenticação do usuário final no projeto do airdrop — o portal só direciona.

## Visão Geral da Solução

Novo serviço dedicado `app/services/airdrop/`, novo router `app/api/v1/endpoints/airdrops.py`, novo schema `app/schemas/airdrop.py` e novo módulo de prompt `app/services/ai/prompts/airdrop_prompts.py`. Reusa `QualityValidator` (com parâmetros de palavras configuráveis), `ArticlePublisher`, `ImageGenerator`, autenticação e rate limiting existentes.

```
app/
├── api/v1/endpoints/
│   └── airdrops.py                          # NOVO - router HTTP
├── services/airdrop/                         # NOVO módulo
│   ├── __init__.py
│   ├── web_researcher.py                    # DDG search + fetch + extração
│   └── airdrop_post_generator.py            # Orquestra: pesquisa → Claude → artigo
├── services/ai/prompts/
│   └── airdrop_prompts.py                   # NOVO - system prompt + template
└── schemas/
    └── airdrop.py                           # NOVO - request/response
```

### Modelo de IA

- **Primário:** Claude Sonnet 4.6 (`claude-sonnet-4-6`)
- **Fallback:** Gemini Flash via `ContentGenerator` existente
- **Temperatura:** 0.5 (mais conservador que weekly_report 0.7)
- **Max tokens:** 3000

## Contrato da API

### Request

```http
POST /api/v1/airdrops/generate-post
Authorization: Bearer {AUTOMATION_TOKEN}
Content-Type: application/json

{
  "project_name": "LayerZero",
  "official_url": "https://layerzero.network",
  "referral_url": "https://app.layerzero.foundation/ref/abc123",
  "publish": false
}
```

### Schemas

```python
# app/schemas/airdrop.py

class AirdropPostRequest(BaseModel):
    project_name: str = Field(..., min_length=2, max_length=100)
    official_url: HttpUrl
    referral_url: HttpUrl
    publish: bool = False  # default false (preview)

class AirdropPostResponse(BaseModel):
    success: bool
    post_id: Optional[str] = None        # só preenchido se publish=true
    title: str
    slug: str
    excerpt: str
    image_url: Optional[str] = None
    word_count: int = 0
    sources_used: List[str] = []         # URLs efetivamente consultadas
    preview_content: Optional[str] = None  # só em preview
    errors: List[str] = []
```

### Códigos de resposta

| Status | Significado |
|---|---|
| 200 | Sucesso (preview ou publicado) |
| 401 | Token ausente/inválido |
| 422 | Body inválido ou conteúdo falhou validação de qualidade |
| 429 | Rate limit (5/min) ou limite diário de posts atingido (`publish=true`) |
| 502 | Pesquisa web falhou completamente (sem fontes confiáveis) |
| 500 | Erro interno |

### Rate limit e contabilização

- Rate limit: **5/min** (categoria `automation`, mesmo de `trigger` e `weekly-report`)
- `publish=true` conta no `DAILY_POST_LIMIT` (10/dia)
- `publish=false` não conta

## Componentes

### `web_researcher.py`

**Responsabilidade:** Coletar contexto público sobre o projeto a partir de buscas web e da página oficial.

**Interface pública:**

```python
class WebResearcher:
    async def gather_context(
        self,
        project_name: str,
        official_url: str,
    ) -> ResearchResult:
        """
        Retorna ResearchResult com:
          - sources_text: str  (contexto consolidado pra prompt)
          - sources_used: List[str]  (URLs efetivamente usadas)
        Raises ResearchFailedError se não há fonte primária disponível.
        """
```

**Estratégia:**

1. Faz 3 queries paralelas no DuckDuckGo (`ddgs`):
   - `f"{project_name} airdrop"`
   - `f"{project_name} como participar"`
   - `f"{project_name} token tokenomics"`
   - `results_per_query = 4` → até 12 URLs candidatas
2. Deduplica URLs por domínio (mesmo domínio → mantém só a top)
3. Aplica blocklist (descarta sociais/vídeo/chat)
4. Aplica boost de whitelist priorizada
5. **Sempre** inclui `official_url` como FONTE 1, independente de aparecer no DDG
6. Pega top 5 URLs (4 ranqueadas + oficial)
7. Fetch paralelo via `httpx.AsyncClient` (timeout 10s/URL, filtra `Content-Type: text/html`)
8. Extrai texto limpo via `BeautifulSoup` (remove `<script>`, `<style>`, `<nav>`, `<footer>`)
9. Trunca cada fonte a **3000 chars**
10. Monta bloco consolidado:

```
=== FONTES PESQUISADAS PARA "<project_name>" ===

[FONTE 1 - OFICIAL] https://layerzero.network
<conteúdo extraído>

[FONTE 2] https://coinmarketcap.com/...
<conteúdo extraído>

=== FIM DAS FONTES ===
```

**Listas:**

```python
BLOCKED_DOMAINS = {
    "reddit.com", "twitter.com", "x.com",
    "youtube.com", "tiktok.com",
    "telegram.org", "discord.com",
}

PREFERRED_DOMAINS = {
    "coinmarketcap.com", "coingecko.com", "cryptorank.io",
    "coindesk.com", "cointelegraph.com", "decrypt.co",
    "theblock.co", "cryptoslate.com", "messari.io",
    "airdrops.io", "coinlist.co",
}
```

**Tratamento de falhas:**

- DDG sem resultados nas 3 queries → segue só com `official_url`
- Fetch da `official_url` falha → levanta `ResearchFailedError` (502 no endpoint)
- Fetch de URL secundária falha → loga warning, ignora, continua

**Dependência nova:** `beautifulsoup4` em `requirements.txt`.

### `airdrop_post_generator.py`

**Responsabilidade:** Orquestrar pesquisa → geração com Claude (fallback Gemini) → validação → retornar dict de artigo.

**Interface pública:**

```python
class AirdropPostGenerator:
    async def generate(
        self,
        project_name: str,
        official_url: str,
        referral_url: str,
    ) -> Optional[Dict]:
        """
        Retorna dict no mesmo shape do weekly_report_generator:
          - title, slug, excerpt
          - content_markdown
          - meta_title, meta_description
          - image_url (depois do ImageGenerator)
          - word_count
          - sources_used
        Retorna None se geração falhou em ambos os modelos.
        """
```

**Fluxo interno:**

1. Chama `WebResearcher.gather_context()`
2. Monta prompt injetando `project_name`, `official_url`, `referral_url`, `sources_text`, `current_date`
3. Chama Claude Sonnet 4.6 com `response_format=json`
4. Se Claude falha → fallback Gemini via `ContentGenerator` (mesmo prompt adaptado)
5. Parse JSON → valida com `_post_validate()` (ver validações abaixo)
6. Se validação extra falhar (link de referência/oficial ausente), regenera **1x** com instrução de correção; se falhar de novo, retorna `None`
7. Gera imagem via `ImageGenerator` (não bloqueia se falhar)
8. Retorna dict completo

**Validações pós-geração (além de QualityValidator):**

1. `referral_url` está presente no markdown — regenera 1x se ausente
2. `official_url` está presente no bloco disclosure — regenera 1x se ausente
3. Frases proibidas NFA — warning no log (não bloqueia, padrão atual)
4. String-chave `"não constitui recomendação"` presente no disclosure

### `airdrop_prompts.py`

System prompt detalhado com:

- **Papel:** redator do VerticeCripto, conteúdo educacional sobre cripto
- **Tom:** neutro, jornalístico, sem indução a investimento
- **Regras de fato:** usar apenas o que está nas fontes, atribuir afirmações, não inventar números/datas
- **Estrutura obrigatória (500-750 palavras):**
  1. Introdução (1 parágrafo neutro)
  2. `## Sobre o projeto <nome>`
  3. `## O programa de airdrop`
  4. `## Como participar` — com link inline de referência
  5. `## Informações importantes` — disclosure obrigatório com link oficial + texto NFA
- **Formato de saída:** JSON com `title`, `slug`, `excerpt`, `content_markdown`, `meta_title`, `meta_description`

**Texto fixo do disclosure (final do artigo):**

> "O link de cadastro neste artigo é um link de referência. Você também pode acessar o projeto diretamente pelo site oficial: [{official_url}]({official_url}). Este conteúdo é meramente informativo e não constitui recomendação de investimento. Airdrops podem ter requisitos, restrições geográficas e datas que mudam — sempre verifique as condições atualizadas no site oficial antes de participar."

### `airdrops.py` (endpoint)

**Responsabilidade:** HTTP layer — auth, rate limit, validação Pydantic, orquestração preview/publish.

**Fluxo:**

1. Auth (`verify_automation_token`) + rate limit `automation`
2. Valida `AirdropPostRequest`
3. Chama `AirdropPostGenerator.generate()`
4. Se retornou `None` → 422 com lista de erros
5. Valida com `QualityValidator(min_words=500, max_words=750)` — overrides
6. Se `publish=false` → monta `AirdropPostResponse` com `preview_content` preenchido, retorna
7. Se `publish=true`:
   - Verifica `DAILY_POST_LIMIT` (mesma lógica do pipeline)
   - Atribui `category_id` da categoria "Airdrop" (id 6)
   - Chama `ArticlePublisher.publish_article()`
   - Dispara webhook de revalidação ISR (não-bloqueante)
   - Retorna `AirdropPostResponse` com `post_id`

## Mudanças em código existente

### `QualityValidator` — parametrização

Aceitar `min_words` / `max_words` opcionais no `__init__` ou no método `validate_article`. Default mantém comportamento atual (250-500). Para airdrops chamamos com `(500, 750)`.

### `requirements.txt`

Adicionar `beautifulsoup4>=4.12.0`.

### `app/api/v1/api.py`

Registrar router `airdrops` em `/api/v1/airdrops`.

## Fluxo de Dados

```
POST /api/v1/airdrops/generate-post
  ↓ Auth + Rate Limit
  ↓ Pydantic validate
  ↓ AirdropPostGenerator.generate()
    ↓ WebResearcher.gather_context()
      ↓ DDG search (3 queries paralelas)
      ↓ Dedup + blocklist + whitelist boost
      ↓ Fetch top 5 URLs (paralelo)
      ↓ Extrai texto + trunca a 3000 chars
      ↓ Monta bloco consolidado
    ↓ Prompt injection (Claude Sonnet 4.6)
    ↓ Fallback Gemini se falha
    ↓ Parse JSON + validações extras
    ↓ Regenera 1x se link referência/oficial ausente
    ↓ ImageGenerator (não-bloqueante)
  ↓ QualityValidator(500, 750)
  ↓ publish ?
    sim → ArticlePublisher + revalidate ISR → response com post_id
    não → response com preview_content
```

## Tratamento de Falhas

| Etapa | Falha | Comportamento |
|---|---|---|
| DDG | 0 resultados | Segue só com `official_url`, loga warning |
| Fetch URL secundária | timeout/404 | Loga warning, ignora aquela URL, continua |
| Fetch `official_url` | timeout/404 | Levanta `ResearchFailedError` → 502 |
| Claude | exceção/timeout | Fallback automático pro Gemini |
| Gemini (fallback) | exceção | Retorna `None` → 422 |
| Validações extras (regenera 1x) | falha após retry | Retorna `None` → 422 |
| QualityValidator | inválido | 422 com lista de erros |
| ImageGenerator | falha | Publica sem imagem (padrão atual) |
| ArticlePublisher | falha DB | 500, detalhes só em DEBUG |
| Revalidação ISR | falha | Warning no log, não bloqueia (padrão atual) |

## Testes

### Unitários

`tests/unit/test_airdrop_web_researcher.py`
- `test_dedup_urls_same_domain`
- `test_always_includes_official_url`
- `test_blocks_blocked_domains`
- `test_prefers_whitelisted_domains`
- `test_truncates_source_to_3000_chars`
- `test_returns_only_official_when_ddg_empty`
- `test_raises_when_no_sources_at_all`
- `test_skips_failed_fetch_continues_others`

`tests/unit/test_airdrop_post_generator.py`
- `test_generate_with_full_sources_returns_article`
- `test_includes_referral_url_in_markdown`
- `test_includes_official_url_in_disclosure`
- `test_falls_back_to_gemini_when_claude_fails`
- `test_regenerates_once_when_referral_url_missing`
- `test_returns_none_when_both_models_fail`

`tests/unit/test_quality_validator_airdrop.py`
- `test_accepts_custom_word_range_500_750`
- `test_rejects_below_min_words`
- `test_rejects_above_max_words`

### Integração

`tests/integration/test_api_airdrops.py`
- `test_generate_post_requires_auth`
- `test_generate_post_preview_returns_markdown_not_persisted`
- `test_generate_post_publish_creates_post_with_category_airdrop`
- `test_invalid_url_returns_422`
- `test_rate_limit_5_per_min`
- `test_research_failure_returns_502`

### Mocking

- DDG: mock `DDGS().text()` com fixture
- httpx: mock `AsyncClient.get` com HTML fixture
- Claude: mock `AsyncAnthropic.messages.create` com JSON fixture
- Gemini fallback: mock no formato do `ContentGenerator`
- ImageGenerator: mock retornando URL falsa
- DB: SQLite em memória (padrão `conftest.py`)

### Fixtures novas em `conftest.py`

- `mock_ddg_results`
- `airdrop_html_fixture`
- `airdrop_category` (garante categoria id 6 existe)

### Cobertura alvo

- `web_researcher.py`: 90%+
- `airdrop_post_generator.py`: 80%+
- Endpoint: 100% dos caminhos HTTP (200 preview, 200 publish, 401, 422, 429, 502)

## Compliance e Guardrails NFA

| Requisito | Implementação |
|---|---|
| Não recomendar investimento | Regras explícitas no system prompt |
| Não criar expectativa de valor | Lista de frases proibidas no prompt + warning pós-geração |
| Atribuir afirmações | Regra de "use apenas o que está nas fontes" + instrução de citar fonte |
| Disclosure de link de referência | Bloco fixo obrigatório com validação string-chave |
| Link oficial alternativo | Sempre presente no bloco disclosure (validado) |
| Disclaimer NFA | Texto fixo "não constitui recomendação de investimento" no disclosure |

## Decisões deixadas de fora (escopo futuro)

- **Lista de airdrops cadastrados:** não persiste estado entre chamadas; se quiser dashboard de airdrops já gerados, é trabalho separado.
- **Tracking de cliques no link de referência:** fora de escopo — pode ser feito depois via UTM no link ou serviço próprio.
- **Atualização periódica do artigo:** cada chamada gera um post novo; não há lógica de "regenerar artigo antigo".
- **Multi-idioma:** só pt-br, igual ao resto do portal.
