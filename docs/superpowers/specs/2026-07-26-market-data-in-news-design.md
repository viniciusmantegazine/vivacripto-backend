# Dados de mercado na geração de notícias — Design

**Data:** 2026-07-26
**Escopo:** `market_data_collector.py`, `news_pipeline.py`, `content_generator.py` e testes
**Tipo:** melhoria de qualidade editorial

## Problema

O `SYSTEM_PROMPT` do `ContentGenerator` proíbe o modelo de citar número que não esteja na fonte (linhas 355-358):

```
1. **DADOS INVENTADOS:**
   - NUNCA invente preços, porcentagens, datas, valores ou estatísticas que NÃO
     estejam EXPLICITAMENTE na fonte fornecida.
   - Se a fonte disser "Bitcoin subiu", NÃO escreva "Bitcoin subiu 5,3%" ou
     "atingiu US$ 70.000".
   - Quando não houver dados específicos, use termos como "registrou alta",
     "apresentou valorização", "sofreu queda".
```

A regra está certa — é o que impede alucinação de preço. Mas ela existe porque **o modelo não tem dado**, então o resultado prático é linguagem vaga: "registrou alta" em vez de "subiu 0,8%, a US$ 64.640".

O `MarketDataCollector` já resolve isso e **já roda em produção**: alimenta o relatório semanal com preço, market cap, volume, variação 24h/7d/30d e distância do ATH, da CoinGecko em tempo real. O pipeline de notícias simplesmente não o consome.

## A medição que define o desenho

`collect_all()` não é uma chamada HTTP. São três, mais **cinco buscas no DuckDuckGo** (`_search_macro_context`: taxa do Fed, CPI, S&P 500, DXY, fluxo de ETF). Medido:

| Parte | Tempo | Tamanho | Relevância para uma notícia |
|---|---|---|---|
| Preços + global + Fear & Greed | **1,1s** | 1.713 chars | alta |
| Macro (5 buscas web) | **5,9s** | 2.533 chars | baixa |

O macro consome **84% do tempo** e é material de análise macro semanal. Num artigo sobre invasão de exchange, taxa do Fed é ruído que ocupa contexto e convida o modelo a enfiar o assunto onde não cabe.

Por isso este trabalho **não é "chamar `collect_all()` no pipeline"** — é extrair o subconjunto barato e relevante.

## Decisões

| Questão | Decisão | Razão |
|---|---|---|
| Qual subconjunto | Novo `collect_snapshot()` — só as 3 chamadas HTTP | 1,1s contra 7,0s; o macro não serve a notícia |
| Nome do método | `collect_snapshot`, não `collect_prices` | Ele traz preço, market cap global e Fear & Greed — "prices" subestimaria e confundiria o próximo leitor |
| `collect_all()` | **Comportamento intacto** | O relatório semanal quer o macro; é o consumidor legítimo dele |
| Duplicação entre os dois | Helper privado `_collect_sections(include_macro)` | Os dois métodos diferem em duas dimensões (macro ou não, texto de fallback ou `None`); um flag só não cobre as duas, e copiar a montagem convidaria divergência |

| Como chega ao gerador | `source_news["market_data"]`, preenchido pelo pipeline | Mesmo padrão do `full_text` na 1ª rodada: sem mudar assinatura, e o `ContentGenerator` segue sem tocar rede |
| Frequência do fetch | Uma vez por run, antes do loop | Preço não muda em segundos, e o run tenta até 3 artigos |
| Seção no prompt | `<dados_de_mercado>`, condicional, **imediatamente após `<dados_da_fonte>`** | É material de fonte, então fica junto do resto do material de fonte e antes das instruções de tarefa. Sem dado, a seção não entra — nada de placeholder vazio |
| Relevância | Por instrução ("use apenas se pertinente"), não por categoria | Condicionar por categoria depende do classificador acertar; errar nega dado a quem precisava |
| Falha de rede | Seção não entra, geração segue | Dado de mercado é enriquecimento, não requisito |

### Estrutura no collector

```python
async def _collect_sections(self, include_macro: bool) -> list[str]:
    """Coleta as seções disponíveis. Falha parcial devolve o que deu."""

async def collect_all(self) -> str:
    """Com macro; em falha total devolve a NOTA de dado indisponível.
    Consumidor: relatório semanal. Comportamento preservado."""

async def collect_snapshot(self) -> Optional[str]:
    """Sem macro; em falha total devolve None.
    Consumidor: pipeline de notícias."""
```

### O ponto que mais importa: o guardrail precisa abençoar a seção

Se os dados entrarem numa seção nova sem tocar no `SYSTEM_PROMPT`, o modelo pode tratá-los como "não sendo a fonte fornecida" e **ignorar os números** — pagaríamos 1,1s e 1.713 chars de contexto por nada, sem sinal nenhum de que não funcionou.

O item 1 do guardrail passa a citar a seção explicitamente como fonte válida, preservando a proibição para todo o resto:

```
1. **DADOS INVENTADOS:**
   - NUNCA invente preços, porcentagens, datas, valores ou estatísticas que NÃO
     estejam EXPLICITAMENTE na fonte fornecida OU na seção <dados_de_mercado>.
   - A seção <dados_de_mercado>, quando presente, contém dados VERIFICADOS de
     mercado em tempo real. Pode e deve citá-los quando forem pertinentes ao
     fato noticiado, sempre indicando que são dados de mercado do momento.
   - Se a fonte disser "Bitcoin subiu" e não houver <dados_de_mercado>, NÃO
     escreva "Bitcoin subiu 5,3%" ou "atingiu US$ 70.000".
   - Sem dados específicos, use termos como "registrou alta", "apresentou
     valorização", "sofreu queda".
```

### Por que não usar o fallback de texto do `collect_all()`

Quando tudo falha, `collect_all()` devolve *"NOTA: Não foi possível coletar dados de mercado em tempo real. Use seu conhecimento mais recente e indique explicitamente que os dados podem estar defasados."* Isso é escrito para o relatório semanal, onde a ausência de dado merece nota ao leitor. Num artigo de notícia esse texto viraria instrução para o modelo especular com conhecimento de treino — o oposto do que o guardrail quer. `collect_snapshot()` devolve `None` em falha total, e a seção simplesmente não entra.

## Arquitetura

```
news_pipeline.run()
  ├── coleta notícias, pré-filtro de URL
  ├── market_data = await market_data_collector.collect_snapshot()   ← 1x por run
  └── loop por notícia:
        ├── full_text  = await article_extractor.extract(url)
        ├── source_news["market_data"] = market_data
        └── content_generator.generate_article(source_news, ...)
              └── _build_article_prompt injeta <dados_de_mercado> se houver
```

| Arquivo | Mudança |
|---|---|
| `market_data_collector.py` | novo `collect_snapshot()` — as 3 chamadas HTTP, sem o macro |
| `news_pipeline.py` | fetch uma vez por run, antes do loop; injeta em `source_news` |
| `content_generator.py` | `<dados_de_mercado>` condicional no prompt; item 1 do guardrail atualizado |

## Fluxo de erro

| Falha | Comportamento |
|---|---|
| CoinGecko fora do ar | `collect_snapshot()` devolve `None`; seção não entra; geração segue |
| Falha parcial (preço ok, F&G fora) | Devolve o que conseguiu — mesma política do `collect_all()` |
| Fetch estoura o timeout | Capturado; `None`; run continua |
| `market_data` ausente em `source_news` | Prompt sem a seção; comportamento idêntico ao de hoje |

Nenhum caminho de falha impede a publicação. Dado de mercado enriquece o artigo; não é requisito dele.

## Estratégia de teste

1. **`collect_snapshot` não dispara o macro** — mock dos `_fetch_*` e asserção de que `_search_macro_context` **não** foi chamado. É o teste que protege os 5,9s.
2. **`collect_snapshot` devolve `None` quando tudo falha** — e não o texto de fallback do `collect_all()`.
3. **Falha parcial devolve o que coletou** — preço ok e Fear & Greed fora resulta em seção com preço.
4. **`collect_all` continua trazendo o macro** — guarda contra alguém "otimizar" o relatório semanal por engano ao mexer no collector.
5. **Pipeline busca uma vez por run**, não uma por artigo — contagem de invocações com 3 notícias na fila.
6. **Pipeline injeta em `source_news["market_data"]`** — o gerador recebe o dado.
7. **Seção entra no prompt quando há dado** e **não entra quando é `None`** — dois testes.
8. **O guardrail cita `<dados_de_mercado>`** — sem isso o modelo ignora os números, e a falha seria silenciosa.
9. **Falha do collector não impede geração** — pipeline com `collect_snapshot` levantando exceção ainda publica.

Baseline atual: `376 passed, 0 failed, 0 errors`.

## Fora de escopo (deliberado)

- **Macro context na notícia.** 5,9s e conteúdo de análise semanal. Se um dia fizer sentido para artigos de categoria `regulacao`, é decisão própria com medição própria.
- **Fontes primárias (SEC, Ethereum Foundation).** Sub-projeto seguinte, via `APICollector`.
- **Fontes brasileiras.** Precisa antes de uma resposta editorial: o pipeline existe para trazer notícia estrangeira ao leitor brasileiro com contexto local, e uma fonte que já publicou em português já fez isso. Some-se o dedup multilíngue (TF-IDF não casa PT com EN, então a mesma notícia sairia duas vezes). Nenhum dos dois é bloqueio técnico intransponível, mas a justificativa vem antes do trabalho.
- **Filtro de artigos-panorama.** Medido: 1 em 95. Com o `source_count` corrigido, um digest de fonte única disputa só por recência contra ~78 outras notícias. Não se paga.
- **Cache entre runs.** O cron roda várias vezes ao dia e preço muda; cachear entre runs entregaria dado velho. Uma vez por run é o ponto certo.

## Risco

Baixo. O collector já é código provado em produção, a mudança nele é aditiva (`collect_all` intocado), e todo caminho de falha degrada para o comportamento atual em vez de quebrar.

O risco real não é de exceção, é de **inércia silenciosa**: o modelo receber os dados e não usá-los, porque o guardrail original o instrui a desconfiar de número fora da fonte. Por isso a atualização do item 1 é parte central deste trabalho e não detalhe, e por isso existe um teste dedicado a ela. Um teste automatizado não prova que o modelo *usou* o número — isso só aparece na leitura dos artigos publicados. Fica como o que observar depois do deploy.
