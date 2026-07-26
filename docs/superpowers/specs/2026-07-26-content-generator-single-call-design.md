# Consolidar as chamadas de LLM do ContentGenerator em uma — Design

**Data:** 2026-07-26
**Escopo:** `app/services/ai/content_generator.py` e seus testes
**Tipo:** refactor com correção de dois defeitos embutidos

## Problema

`generate_article` (linha 246) faz **três** chamadas de LLM sequenciais e dependentes:

| Ordem | Método | Linha | Entrada | `max_tokens` |
|---|---|---|---|---|
| 1 | `_generate_content` | 329 | título + texto da fonte | 2500 |
| 2 | `_generate_seo_title` | 704 | **primeiros 500 chars** do conteúdo | 60 |
| 3 | `_generate_meta_description` | 803 | primeiros 500 chars + título | 80 |

(`_generate_excerpt`, linha 781, não é chamada de LLM — é fatiamento de string.)

### Defeito 1 — artigo caro descartado por falha de chamada barata

Se a chamada 2 falha, `generate_article` retorna `None` e o artigo **inteiro** é descartado, incluindo a chamada 1 que já custou ~2500 tokens de saída. Esse comportamento foi introduzido deliberadamente (publicar com o título original em inglês é pior num portal PT-BR), e a decisão continua certa — mas o desenho de três chamadas é o que cria o dilema. Numa transação única ele não existe: ou vem tudo, ou não vem nada.

### Defeito 2 — `excerpt` derivado mecanicamente pode reprovar na validação

`_generate_excerpt` corta as duas primeiras frases e limita a 150 chars. O `QualityValidator` exige **80 a 200**. Nada no fatiamento garante o piso. Medido:

| Lead do artigo | Excerpt | Resultado |
|---|---|---|
| curto (`"O Bitcoin subiu. Investidores reagiram."`) | **39 chars** | **reprova** |
| médio | 91 chars | ok |
| longo | 150 chars | ok |

Quando reprova, o artigo é rejeitado e regerado — hoje ao custo de mais três chamadas — por um defeito que não tem relação com a qualidade do conteúdo.

### Sobre o ganho de custo

Uma correção ao que foi dito antes durante o planejamento: o ganho de **50–65%** vale para **contagem de chamadas**, não para custo em tokens. As duas chamadas de SEO são pequenas (`max_tokens` 60 e 80, vendo apenas 500 chars do artigo) contra ~2500 da geração de conteúdo. Em tokens a economia fica na ordem de 10–20%.

Os ganhos que justificam o trabalho, em ordem de peso:

1. **Fim do descarte por falha acessória** (defeito 1) — o mais valioso.
2. **`excerpt` escrito conforme especificação** em vez de fatiado (defeito 2).
3. **Menos round-trips**: 3 → 1 por artigo, 6 → 2 com retry. Latência e superfície de falha parcial.
4. **Alinhamento de SEO**: hoje título e meta são escritos vendo só os primeiros 500 chars do artigo. Na chamada única o modelo escreve tudo conhecendo o texto completo.

## Decisões

| Questão | Decisão | Razão |
|---|---|---|
| Enforcement do JSON | Contrato no prompt + dica nativa por provedor + `json_repair` + validação de chaves | Ver abaixo |
| Provedores | Gemini primário, OpenAI fallback — ambos com o mesmo contrato | Mantém a estrutura atual |
| `excerpt` no JSON | Sim, com fallback mecânico | Corrige o defeito 2 sem criar novo modo de descarte |
| `title` ausente | Descarta o artigo | Preserva a decisão de nunca publicar título em inglês |
| Limites do validador | Explícitos no prompt | Hoje o modelo não os conhece, então erra e a gente descobre na validação |

### Por que não usar `response_schema` nativo

`google-genai 1.46.0` suporta `response_schema`, e seria o enforcement mais forte. Foi descartado porque **o fallback OpenAI precisa do mesmo contrato**, e o mecanismo de saída estruturada do OpenAI é diferente do do Gemini. Depender de enforcement nativo exigiria duas implementações de contrato e dobraria a superfície de falha.

A escolha é: o **prompt** define o contrato — um só, para os dois provedores — e cada provedor recebe sua dica nativa de "responda JSON" como reforço barato (`response_mime_type="application/json"` no Gemini, `response_format={"type": "json_object"}` no OpenAI). O parse e a validação de chaves são um caminho único.

Isso segue o precedente do repo: `ContextualImageAnalyzer` já usa `response_mime_type` sem schema, e `AirdropPostGenerator` já usa `json_repair` para o caso conhecido de aspas e newlines não escapadas dentro de um campo de markdown longo — que é exatamente o nosso `content_markdown`.

## Arquitetura

```
generate_article
  ├── monta o user prompt (conteúdo + SEO + contrato JSON + correction_hint)
  ├── _generate_article_json  ──► Gemini (response_mime_type)
  │                            └► OpenAI (response_format)  [fallback]
  │        └── _parse_article_json (cercas → json.loads → json_repair → chaves)
  ├── _sanitize_content(content_markdown)
  ├── excerpt: do JSON se 80-200 chars, senão _generate_excerpt(content)
  └── monta o dict do artigo
```

### Métodos

| Método | Situação |
|---|---|
| `_generate_article_json(title, description, source, category, correction_hint)` | **novo** — a chamada única, com fallback de provedor |
| `_parse_article_json(text)` | **novo** — remoção de cercas, `json.loads`, `json_repair`, validação de chaves obrigatórias |
| `_generate_content` | **removido** — absorvido |
| `_generate_seo_title` | **removido** |
| `_generate_meta_description` | **removido** |
| `_generate_excerpt` | **mantido** — passa a ser fallback |
| `_sanitize_content` | mantido — passa a rodar sobre o `content_markdown` do JSON |

`SYSTEM_PROMPT` fica como está: trata de persona, guardrails e formato, e nada disso muda. O contrato JSON e os poucos exemplos de título e meta description entram no **user prompt**, aproveitando os few-shots que já existem nos prompts das chamadas 2 e 3.

### O contrato

```json
{
  "content_markdown": "## Manchete...",
  "title": "...",
  "excerpt": "...",
  "meta_description": "..."
}
```

Limites declarados no prompt, derivados do `QualityValidator`:

| Campo | Limite | Origem |
|---|---|---|
| `content_markdown` | 700–1500 palavras, começa com `##`, ≥3 H2 | `MIN/MAX_WORD_COUNT`, `_validate_content_structure` |
| `title` | 30–100 chars, PT-BR | `MIN/MAX_TITLE_LENGTH` |
| `excerpt` | 80–200 chars | `MIN/MAX_EXCERPT_LENGTH` |
| `meta_description` | 120–180 chars | `MIN/MAX_META_LENGTH` |

Campos derivados, fora do JSON: `slug` (via `slugify(title)`), `meta_title` (= `title`; o validador trunca em 70), `source_url` / `source_name` / `category` (vêm do input).

### Obrigatórios versus recuperáveis

A distinção segue o princípio que motiva todo este trabalho — não descartar o caro por causa do barato:

| Campo | Classe | Se vier ausente ou inválido |
|---|---|---|
| `content_markdown` | **obrigatório** | `None` — sem texto não há artigo |
| `title` | **obrigatório** | `None` — publicar com o título em inglês da fonte é pior |
| `excerpt` | recuperável | fallback para `_generate_excerpt(content)` |
| `meta_description` | recuperável sem fallback | segue `None` no campo; o validador reprova e o pipeline faz retry |

`meta_description` é o caso mais fraco: não há fallback de boa qualidade (truncar o excerpt daria uma meta ruim para SEO), então a ausência custa um retry. Fica como resíduo aceito — o modelo entregar exatamente 3 dos 4 campos é improvável, e criar um fallback ruim para SEO seria pior que a raridade do caso.

## Fluxo de erro

| Falha | Comportamento |
|---|---|
| Gemini indisponível ou erro | OpenAI, mesmo contrato |
| Ambos os provedores falham | `None` |
| JSON não parseia nem com `json_repair` | `None` |
| `content_markdown` ou `title` ausente, ou não é string não-vazia | `None` |
| `excerpt` ausente ou fora de 80–200 | fallback para `_generate_excerpt(content)` |
| `meta_description` ausente | mantém `None` no campo; o validador reprova e o pipeline faz retry |

`None` de `generate_article` já é tratado pelo pipeline: conta como falha e tenta a próxima notícia da fila, graças ao loop até a meta introduzido na primeira rodada.

## Estratégia de teste

### Testes que este trabalho quebra

Parte honesta do preço:

| Arquivo | Testes | Destino |
|---|---|---|
| `test_content_generator_article.py` | 3 | **reescrever** — mockam os três métodos removidos |
| `test_content_generator_sanitize.py` | 5 | **2 reescrever** — verificam o `correction_hint` dentro do prompt de `_generate_content`; as outras 3 testam `_sanitize_content` puro e sobrevivem |
| `test_content_generator_excerpt.py` | 2 | sobrevivem — o método continua existindo como fallback |
| `test_content_generator_sanitize_boundary.py` | 13 | sobrevivem — `_sanitize_content` não muda |

### Testes novos

Todos com mock do cliente, sem rede e sem chave de API.

1. **Uma chamada, não três** — contagem de invocações no cliente Gemini. É o teste que prova a consolidação.
2. **Parse com cercas** — `` ```json ... ``` `` é aceito.
3. **`json_repair` salva aspas não escapadas** — `content_markdown` longo com `"` interno cru, que é o modo de falha conhecido.
4. **Campo obrigatório faltando → `None`** — parametrizado sobre `content_markdown` e `title`, os dois obrigatórios. Um teste separado garante que a ausência de `excerpt` ou `meta_description` **não** descarta o artigo, porque são recuperáveis.
5. **Excerpt do LLM é usado quando está na faixa**, e o **fallback mecânico entra quando está fora** — dois testes, cobrindo o defeito 2.
6. **Sanitização é aplicada ao `content_markdown` do JSON** — guarda contra perder o `_sanitize_content` no refactor.
7. **Fallback OpenAI dispara quando o Gemini falha**, com o mesmo contrato.
8. **`correction_hint` aparece no prompt** — substitui os 2 testes reescritos de `test_content_generator_sanitize.py`.
9. **Título ausente descarta o artigo** — preserva a garantia da primeira rodada.

Baseline atual: `353 passed, 0 failed, 0 errors`.

## Fora de escopo (deliberado)

- **`response_schema` nativo do Gemini.** Descartado com razão registrada acima. Se o parse se mostrar frágil em produção, é o próximo passo natural — mas aí valeria para o Gemini apenas, com o caminho de prompt permanecendo para o OpenAI.
- **Corrigir o comentário "4 chamadas de LLM" no `news_pipeline.py`.** São 3. Entra neste trabalho como ajuste de uma linha, já que o número é o assunto aqui.
- **Artigos-panorama poluindo o pipeline.** Digests do tipo "Here's what happened in crypto today" são ímãs de falso positivo no dedup e provavelmente não deveriam virar post. Achado de outra rodada, item próprio.
- **Novas fontes** (SEC, fontes brasileiras, ligar o `MarketDataCollector` ao pipeline de notícias). Sub-projeto seguinte.

## Risco

Médio — é o caminho central de geração de todo o pipeline de notícias, e o único deste conjunto de rodadas que mexe em algo que já funciona. Mitigações: a suíte cobre o fluxo em ambas as direções (sucesso e cada modo de falha); o fallback de excerpt e o fallback de provedor evitam que uma falha parcial descarte trabalho caro; e o pipeline já tem o loop até a meta, então um artigo descartado não consome a cota do run.

O modo de falha que mais merece atenção em produção é o parse: se o modelo passar a devolver JSON malformado com frequência acima do que o `json_repair` conserta, a taxa de descarte sobe silenciosamente. O log de falha de parse precisa ser em nível `error`, para que isso apareça no monitoramento em vez de virar queda inexplicada de volume.
