# Filtro de relevância na coleta de notícias

**Data:** 2026-07-26
**Status:** aprovado, pronto para plano de implementação

## Problema

O pipeline não tem filtro de tema. Qualquer item que entra pela coleta vira
candidato a artigo, e `category_classifier.py:88` defaulta para `'altcoins'`
quando nenhuma palavra-chave casa:

```python
# If no matches, default to 'altcoins' (most generic)
logger.info(f"No category match found, defaulting to 'altcoins' for: {title[:50]}...")
```

O Decrypt é tanto publicação de IA quanto de cripto. Do feed real, coletado em
2026-07-26, estes cinco itens não têm nenhum ângulo de cripto:

```
Mira Murati's Inkling AI Model Review: Best Open-Source Model in the West
What Is an AI Kill Switch and Why Do US Lawmakers Want One?
Claude Opus 5 Outscores Fable 5 on Most Benchmarks—At Half the Price
Black Forest Labs Unveils FLUX 3 AI: Ditches Stills for Video—And Robot Hands
Alibaba's New Qwen Image 3 AI Wants to Be Useful, Not Just Pretty
```

Eles entram na fila, são classificados como `altcoins` e podem ser publicados
como artigo de cripto.

O caminho é curto. A ordenação da fila é
`(source_count, published_at)` decrescente e quase todo item tem
`source_count == 1`, então na prática ela é ordenação por recência: um item de
IA publicado minutos antes do run vai ao topo, dentro das 3 tentativas por
execução.

Isto não é risco hipotético. Está no feed hoje.

## Origem: o que a medição descartou

Este trabalho começou como "fontes primárias (SEC, Ethereum Foundation)". A
medição derrubou aquele escopo e apontou para cá.

| Feed | Volume | % com termo de cripto | Itens na janela de 24h |
|---|---|---|---|
| SEC press releases | 0,38/dia | 8% (2 de 25) | 0 |
| Ethereum Foundation blog | 0,14/dia | 66% | 0 |
| CFTC press releases | 0,36/dia | 10% (1 de 10) | 0 |

A SEC produz cerca de um item de cripto a cada 33 dias; o conteúdo real do feed
é roundtable de horário de bolsa, nomeação de COO, FAQ de assessor municipal. O
feed de litígios da SEC, onde estaria o enforcement de cripto, responde HTTP
403. Mesmo quando um item aparecesse, `source_count == 1` o colocaria abaixo de
qualquer notícia coberta por dois veículos.

Registrado aqui porque a conclusão tem prazo de validade: se a SEC voltar a
tratar cripto com a frequência de 2024-2025, os números mudam e a decisão
merece ser refeita. E qualquer retomada daquele escopo depende deste filtro
primeiro — 90% do que aqueles feeds emitem é de outra editoria.

## Decisões

| Questão | Decisão | Razão |
|---|---|---|
| Mecanismo | Denylist por palavra-chave | Medido: 5/5 de precisão, 4,5% da fila. Custo zero, determinístico, testável sem rede |
| Direção do teste | Sinal de outra editoria **e** ausência de sinal de cripto | Allowlist de cripto exige vocabulário exaustivo e nasce token novo toda semana |
| Fronteira editorial | Critério é o **sujeito** da notícia | Empresa de cripto tratando de IA é pauta do site |
| Posição | `NewsAggregator`, antes do dedup | Funil único de RSS + API; reduz o O(n²) do dedup |
| Falha | Abre (deixa passar) | Descartar notícia real é o erro caro |

### Por que denylist e não allowlist

A primeira medição usou allowlist — "tem termo de cripto, passa" — e errou em
itens que são inequivocamente cripto: Shiba Inu, Odos Protocol, HTX, Bitchat.
Vocabulário exaustivo de cripto não existe de forma estável; nomes novos
aparecem toda semana. Denylist inverte o ônus: só é descartado o que casa com
uma pauta *conhecida* de outra editoria.

### Por que não classificador LLM

Pegaria os casos ambíguos, mas adiciona custo por run, latência e um modo de
falha novo. Como o gate precisa abrir quando o classificador falha, o pior caso
dele é exatamente o comportamento de hoje. O denylist já resolve o agrupamento
medido a custo zero, e deixa a costura pronta caso a medição em produção mostre
que não basta.

### Por que não reaproveitar o category_classifier

`classify()` já tem assinatura `Optional[str]`, e seria tentador fazê-lo
devolver `None` para item fora de tema. Mas as palavras-chave dele respondem
outra pergunta — *qual categoria de cripto* — e não *se é cripto*. Notícia sobre
invasão a uma exchange é cripto sem casar com nenhuma categoria. Além disso
`article_publisher._get_or_create_category` depende de sempre receber um slug;
mudar o contrato quebraria a publicação.

## Componente

Arquivo novo `app/services/sources/relevance_filter.py`, responsabilidade única.

```python
class RelevanceFilter:
    def check(self, news: Dict) -> Optional[str]:
        """
        Devolve o termo de outra editoria que motivou o descarte,
        ou None se a notícia for relevante.
        """
```

Uma primitiva devolve decisão e motivo juntos: o chamador testa
`if filtro.check(n) is None` e usa o valor devolvido na linha de log. Evita ter
`is_relevant()` e `reason()` que podem divergir.

Texto examinado: `title + " " + description`, o mesmo par que
`NewsAggregator._get_comparison_text` usa.

### Vocabulário

Duas listas com papéis assimétricos.

**`OFF_BEAT`** — focada no agrupamento medido: modelo de IA, laboratório de IA,
benchmark, GPU, chip, **e nomes próprios** (Nvidia, OpenAI, Hugging Face,
Anthropic, Mistral, DeepSeek, Qwen, GLM). Só cresce com evidência de feed real.

**`CRYPTO_SIGNALS`** — o veto. Precisa ser **específica**: moeda nomeada, ticker,
exchange nomeada, empresa de cripto, jargão próprio.

Na medição, dois itens de outra editoria escaparam. As causas são **diferentes**
e cada uma disciplina uma das listas.

*Veto por palavra genérica* — este item casou `Nvidia` e `Open-Source AI` na
`OFF_BEAT`, e mesmo assim passou:

```
título: Nvidia, Meta, and Microsoft Tell Washington: Don't Kill Open-Source AI
resumo: ...days after a Chinese AI helped Hugging Face survive a hack...
```

O único termo de cripto que casou foi `hack`, vindo do resumo. Uma palavra que
qualquer setor usa anulou dois sinais corretos. Proibidas na `CRYPTO_SIGNALS`:
`hack`, `protocol`, `exchange`, `treasury`, `node`, `bridge` e equivalentes.

*Lacuna na lista de outra editoria* — este não casou **nada** na `OFF_BEAT`:

```
título: Hugging Face CEO Thanks Chinese AI for Saving the Day After OpenAI Hack
resumo: ...Hugging Face ran Chinese model GLM 5.2 locally...
```

"Chinese AI", "Chinese model", "GLM 5.2" não casam com padrão nenhum. A correção
é acrescentar **nomes próprios** de laboratórios e modelos, não um `\bAI\b` solto
— matéria de cripto cita IA o tempo todo ("Is the AI-to-crypto rotation
underway?"), e um padrão largo aí faria o gate depender do veto para tudo.

## Fluxo

`NewsAggregator.collect_news`, depois de estender `all_news` com RSS e API e
antes de `_deduplicate_source_news`:

1. Para cada notícia, chamar `check()`.
2. Item com termo devolvido sai da lista.
3. Cada descarte gera uma linha de log em WARNING com título e termo.
4. A lista filtrada segue para a deduplicação.

## Observabilidade

Log em WARNING de **cada** título descartado, com o termo que causou.

Não é excesso de log. Este projeto já calibrou dois thresholds fora da faixa
onde o dado real cai — `SOURCE_DEDUP_THRESHOLD` a 0,65 e o
`DEDUPLICATION_THRESHOLD` a 0,80 — e nos dois casos o sintoma foi silêncio: o
corte nunca disparava e nada no log dizia isso. Um gate mal calibrado comendo
notícia legítima é o mesmo modo de falha, com consequência pior.

O protótipo descartou 5 de 110 itens (4,5%); com as duas correções de
vocabulário acima, o esperado é 7 de 110 (6,4%) — cerca de 5 a 7 linhas por
run. Volume baixo o bastante para ser lido, e desregulagem aparece no primeiro
log em vez de virar queda inexplicada de volume.

## Tratamento de erro

Exceção dentro de `check()` é capturada e a notícia **passa**. Mesma assimetria
do threshold de deduplicação: falso positivo descarta notícia distinta e o
leitor nunca a vê, enquanto falso negativo produz um artigo fora de tema que é
visível e removível.

## Testes

Sem rede. Fixture com os títulos reais capturados do feed em 2026-07-26.

**Descarte** — os cinco itens de IA acima têm que cair, mais os dois que
escaparam da medição, cada um travando a correção de uma lista:

```
Nvidia, Meta, and Microsoft Tell Washington: Don't Kill Open-Source AI
   (com o resumo, que contém "hack" — trava a remoção de palavra genérica do veto)
Hugging Face CEO Thanks Chinese AI for Saving the Day After OpenAI Hack
   (com o resumo, que contém "GLM 5.2" — trava a inclusão de nomes próprios na OFF_BEAT)
```

Os dois precisam do resumo junto do título na fixture: é no resumo que está o
termo que causou cada falha.

**Fronteira editorial** — estes têm que passar, e é o teste que trava a decisão
de que o critério é o sujeito da notícia:

```
Sam Altman-backed World Network secures $52.5 million in fresh funding   (Worldcoin)
World Foundation Raises $52.5M to Scale Sam Altman's 'Proof of Human' ID (Worldcoin)
The brutal $346M math behind Galaxy's race to build CoreWeave's Texas AI mega-center
Bitcoin treasury companies sell up, repay debt, pivot to AI as share prices collapse
Crypto Biz: Is the AI-to-crypto rotation underway?
Franklin Templeton Says Agentic AI Is Crypto's 'Killer Use Case'
```

Se alguém apertar o vocabulário depois, é este teste que reclama.

**Falso negativo conhecido** — os itens que a allowlist original perdeu (Shiba
Inu, Odos Protocol, HTX, Bitchat) têm que passar pelo filtro novo.

**Fail-open** — vocabulário que levanta exceção deixa a notícia passar.

**Integração** — `NewsAggregator.collect_news` remove item fora de tema antes de
chamar a deduplicação.

## Etapa obrigatória de calibração

Antes de commitar o vocabulário, rodar o filtro contra o feed vivo e **conferir
na mão todo item descartado**. Lista de palavras não vai ser escrita por
suposição. Se a conferência mostrar descarte de notícia legítima, a palavra
responsável sai da `OFF_BEAT` ou o sinal correspondente entra na
`CRYPTO_SIGNALS` — e a rodada se repete até o descarte estar limpo.

Essa verificação usa rede e roda uma vez, na implementação. Os testes
automatizados nunca tocam a rede: usam a fixture.

## Fora de escopo

- Classificador LLM de relevância. A costura fica pronta; a decisão depende de
  medição em produção.
- Fontes primárias (SEC, EDGAR, Ethereum Foundation). Derrubado pela medição
  acima; EDGAR continua sendo o candidato real caso o tema volte.
- Threshold do `DuplicateDetector`. Depende de dado de produção.
