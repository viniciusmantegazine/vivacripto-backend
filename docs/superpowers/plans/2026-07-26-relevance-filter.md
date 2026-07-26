# Filtro de Relevância — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Impedir que notícia de outra editoria (hoje: IA) entre na fila de geração e seja publicada como artigo de cripto.

**Architecture:** Classe nova `RelevanceFilter` com duas listas de regex — `OFF_BEAT_PATTERNS` (pauta de outra editoria) e `CRYPTO_SIGNAL_PATTERNS` (veto). Descarta apenas quando a primeira casa **e** a segunda não. Plugada no `NewsAggregator` entre a coleta e a deduplicação. Falha abre.

**Tech Stack:** Python 3.9, `re` da stdlib, pytest. Sem dependência nova. Sem rede nos testes.

**Spec:** `docs/superpowers/specs/2026-07-26-relevance-filter-design.md`

---

## Vocabulário já validado

As duas listas abaixo **não são sugestão** — foram medidas contra a fila real de
110 itens dos 5 feeds em 2026-07-26. Resultado: 7 descartes (6,4%), todos
corretos, zero falso positivo. Use exatamente estas listas na Task 1.

Duas armadilhas estão embutidas e devem ser preservadas:

1. **`hack` está fora do veto de propósito.** Estava dentro na primeira versão e
   deixou passar "Nvidia, Meta, and Microsoft Tell Washington: Don't Kill
   Open-Source AI", cujo resumo diz "survive a hack". Uma palavra que qualquer
   setor usa anulou dois sinais corretos. Mesma proibição vale para `protocol`,
   `exchange`, `treasury`, `node`, `bridge`, `ledger`, `circle`, `ada`.
2. **`gemini` está no veto, não na lista de IA.** Gemini é exchange de cripto
   (Winklevoss) além de modelo do Google. Colocá-la na `OFF_BEAT` descartaria
   notícia de exchange. A ambiguidade foi resolvida para o lado permissivo.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `app/services/sources/relevance_filter.py` (criar) | Decide se uma notícia é do tema. Vocabulário e regra, nada mais. |
| `app/services/sources/news_aggregator.py` (modificar) | Chama o filtro entre coleta e dedup; loga cada descarte. |
| `tests/unit/test_relevance_filter.py` (criar) | Fixture com itens reais; descarte, fronteira editorial, fail-open. |
| `tests/unit/test_news_aggregator_relevance.py` (criar) | Integração: item fora de tema não chega ao dedup. |
| `ai_docs/gotchas.md` (modificar) | Registra as duas armadilhas de vocabulário. |

---

### Task 1: RelevanceFilter e os descartes

**Files:**
- Create: `app/services/sources/relevance_filter.py`
- Test: `tests/unit/test_relevance_filter.py`

- [ ] **Step 1: Escrever a fixture e os testes de descarte**

Criar `tests/unit/test_relevance_filter.py`:

```python
"""
Testes do RelevanceFilter.

A fixture usa titulo e resumo REAIS, capturados dos feeds em 2026-07-26.
Texto sintetico nao serve aqui: o filtro decide por vocabulario, e foi
exatamente o resumo (nao o titulo) que causou as duas falhas da primeira
versao do vocabulario.
"""
import pytest

from app.services.sources.relevance_filter import RelevanceFilter


@pytest.fixture
def filtro() -> RelevanceFilter:
    return RelevanceFilter()


# Itens reais de IA pura, sem nenhum angulo de cripto. Todos do Decrypt,
# que e tanto publicacao de IA quanto de cripto.
FORA_DE_TEMA = [
    (
        "Mira Murati’s Inkling AI Model Review: Best Open-Source Model in the West",
        "After two years of silence from Thinking Machines Lab, Murati's debut "
        "model is out and on OpenRouter. The MCP score is genuinely impressive. "
        "The price-to-performance math is more complicated.",
    ),
    (
        "What Is an AI Kill Switch and Why Do US Lawmakers Want One?",
        "The AI Kill Switch Act would let Homeland Security order frontier AI "
        "throttled or shut down, with fines up to $20 million a day for defying it.",
    ),
    (
        "Claude Opus 5 Outscores Fable 5 on Most Benchmarks—At Half the Price",
        "Anthropic's new everyday model undercuts its own frontier product on "
        "cost and beats it almost everywhere that counts.",
    ),
    (
        "Black Forest Labs Unveils FLUX 3 AI: Ditches Stills for Video—And Robot Hands",
        "FLUX 3 is the German AI lab’s first video model, and the same system is "
        "already teaching robots to work an Audi assembly line.",
    ),
    (
        "Alibaba's New Qwen Image 3 AI Wants to Be Useful, Not Just Pretty",
        "Qwen Image 3.0 generates dense newspapers and infographic grids in one "
        "shot and renders text down to 10 pixels. The catch: no benchmarks, no "
        "open weights.",
    ),
    # Este passou na primeira versao do vocabulario porque 'hack', no RESUMO,
    # estava no veto de cripto e anulou 'Nvidia' + 'Open-Source AI'.
    (
        "Nvidia, Meta, and Microsoft Tell Washington: Don't Kill Open-Source AI",
        "Twenty-five companies signed a letter defending open-weight models days "
        "after a Chinese AI helped Hugging Face survive a hack triggered by "
        "OpenAI's own systems.",
    ),
    # Este passou porque a OFF_BEAT nao tinha nome proprio de laboratorio:
    # "Chinese AI" e "Chinese model GLM 5.2" nao casavam com padrao nenhum.
    (
        "Hugging Face CEO Thanks Chinese AI for Saving the Day After OpenAI Hack",
        "When American commercial AI refused to help investigate the breach, "
        "Hugging Face ran Chinese model GLM 5.2 locally. Its CEO now says "
        "there's an important lesson in this.",
    ),
]


@pytest.mark.parametrize("titulo,resumo", FORA_DE_TEMA)
def test_descarta_noticia_de_outra_editoria(filtro, titulo, resumo):
    termo = filtro.check({"title": titulo, "description": resumo})

    assert termo is not None, f"deveria descartar: {titulo}"


@pytest.mark.parametrize("titulo,resumo", FORA_DE_TEMA)
def test_termo_devolvido_aparece_no_texto(filtro, titulo, resumo):
    """
    O valor devolvido vai para o log de descarte. Se nao for um trecho real do
    texto, a linha de log nao explica nada e a calibracao fica cega.
    """
    termo = filtro.check({"title": titulo, "description": resumo})

    assert termo.lower() in f"{titulo} {resumo}".lower()
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `python3 -m pytest tests/unit/test_relevance_filter.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.sources.relevance_filter'`

- [ ] **Step 3: Implementar o filtro**

Criar `app/services/sources/relevance_filter.py`:

```python
"""
Filtro de relevância na coleta de notícias.

O pipeline não tinha filtro de tema: qualquer item coletado virava candidato a
artigo, e `category_classifier` defaulta para 'altcoins' quando nada casa. Como
quase toda notícia tem source_count=1, a fila é efetivamente ordenada por
recência — um item de IA publicado minutos antes do run ia ao topo.

Direção do teste: descarta quando há sinal de OUTRA editoria E não há sinal de
cripto. O inverso (allowlist de cripto) foi medido e falha: perdeu Shiba Inu,
Odos Protocol, HTX e Bitchat, porque vocabulário exaustivo de cripto não existe
de forma estável — nasce nome novo toda semana.
"""
import re
from typing import Dict, Optional

from loguru import logger


class RelevanceFilter:
    """Decide se uma notícia coletada pertence à editoria do site."""

    # Pauta de outra editoria. Hoje só IA, que é o agrupamento medido: o
    # Decrypt é tanto publicação de IA quanto de cripto. Só cresce com
    # evidência de feed real, nunca por suposição.
    OFF_BEAT_PATTERNS = (
        # Laboratórios e modelos, por NOME PRÓPRIO. Nome próprio é o que
        # resolve o caso "Chinese AI ... Chinese model GLM 5.2", que não casava
        # com jargão nenhum. Note que NÃO existe um `\bai\b` solto aqui:
        # matéria de cripto cita IA o tempo todo ("Is the AI-to-crypto rotation
        # underway?"), e um padrão largo faria tudo depender do veto.
        r"\bopenai\b", r"\banthropic\b", r"\bhugging ?face\b", r"\bmistral\b",
        r"\bdeepseek\b", r"\bqwen\b", r"\bllama\b", r"\bchatgpt\b", r"\bgpt-?\d",
        r"\bclaude\b", r"\bglm\b", r"\bthinking machines\b",
        r"\bblack forest labs\b", r"\bmidjourney\b", r"\bopenrouter\b",
        # Hardware e infraestrutura
        r"\bnvidia\b", r"\bgpus?\b", r"\bdata ?centers?\b",
        # Jargão de IA
        r"\bai (model|lab|labs|startup|safety|agent|agents|kill switch)\b",
        r"\bllms?\b", r"\blarge language model", r"\bchatbot",
        r"\b(image|video|frontier|open-weight) models?\b",
        r"\bopen-?source ai\b", r"\bbenchmarks?\b",
        # Outras editorias
        r"\brobots?\b", r"\bself-driving\b", r"\bquantum comput",
    )

    # Veto. Precisa ser ESPECÍFICA: moeda nomeada, ticker, exchange nomeada,
    # empresa de cripto, jargão próprio.
    #
    # PROIBIDO acrescentar palavra genérica de negócios aqui. Na primeira
    # medição o veto tinha `hack`, e isso deixou passar "Nvidia, Meta, and
    # Microsoft Tell Washington: Don't Kill Open-Source AI" — o resumo dizia
    # "survive a hack", e uma palavra que qualquer setor usa anulou dois sinais
    # corretos. Mesma proibição para: protocol, exchange, treasury, node,
    # bridge, ledger, circle, ada.
    #
    # `gemini` fica AQUI e não na OFF_BEAT: é exchange de cripto (Winklevoss)
    # além de modelo do Google. A ambiguidade foi resolvida para o lado
    # permissivo, que é o barato.
    CRYPTO_SIGNAL_PATTERNS = (
        # Guarda-chuva
        r"\bcrypto", r"\bblockchain\b", r"\bweb3\b", r"\bdefi\b", r"\bnfts?\b",
        r"\bdaos?\b", r"\bstablecoins?\b", r"\baltcoins?\b", r"\bmemecoins?\b",
        r"\bdigital assets?\b", r"\bon-?chain\b", r"\btokens?\b", r"\btokeni[sz]",
        # Moedas e tickers
        r"\bbitcoins?\b", r"\bbtc\b", r"\bethereum\b", r"\beth\b", r"\bsolana\b",
        r"\bxrp\b", r"\bripple\b", r"\bcardano\b", r"\bdogecoins?\b", r"\bshiba\b",
        r"\blitecoin\b", r"\bpolkadot\b", r"\bchainlink\b", r"\btether\b",
        r"\busdt\b", r"\busdc\b", r"\bbnb\b",
        # Exchanges e empresas
        r"\bbinance\b", r"\bcoinbase\b", r"\bkraken\b", r"\bbybit\b", r"\bhtx\b",
        r"\bokx\b", r"\bgemini\b", r"\bmicrostrategy\b", r"\bgrayscale\b",
        r"\bgalaxy\b", r"\bpantera\b", r"\bmetamask\b", r"\bopensea\b",
        r"\buniswap\b",
        # Jargão próprio
        r"\bhodl\b", r"\bsatoshi\b", r"\bhalving\b", r"\bhashrate\b",
        r"\bairdrops?\b", r"\bstaking\b", r"\bvalidators?\b", r"\brollups?\b",
        r"\bl2s?\b", r"\bdexe?s?\b", r"\btvl\b", r"\bmining\b", r"\bminers?\b",
        r"\bsmart contracts?\b", r"\betfs?\b", r"\bwallets?\b", r"\bcustody\b",
    )

    def __init__(self):
        self._off_beat = self._compile(self.OFF_BEAT_PATTERNS, "OFF_BEAT_PATTERNS")
        self._crypto = self._compile(
            self.CRYPTO_SIGNAL_PATTERNS, "CRYPTO_SIGNAL_PATTERNS"
        )

    @staticmethod
    def _compile(patterns, nome: str):
        """
        Compila o vocabulário. Padrão inválido desativa o filtro em vez de
        derrubar a construção do NewsAggregator — e com ele o pipeline inteiro.
        """
        try:
            return re.compile("|".join(patterns), re.IGNORECASE)
        except re.error as e:
            logger.error(
                f"Vocabulário {nome} inválido ({e}); "
                f"filtro de relevância DESATIVADO, tudo passa"
            )
            return None

    def check(self, news: Dict) -> Optional[str]:
        """
        Devolve o termo de outra editoria que motivou o descarte, ou None se a
        notícia for relevante.

        Uma primitiva só, devolvendo decisão e motivo juntos: o chamador testa
        `is None` e usa o valor na linha de log. Evita ter is_relevant() e
        reason() que podem divergir.
        """
        try:
            if self._off_beat is None or self._crypto is None:
                return None

            texto = f"{news.get('title', '')} {news.get('description', '')}"

            fora = self._off_beat.search(texto)
            if not fora:
                return None
            if self._crypto.search(texto):
                return None
            return fora.group(0)

        except Exception as e:
            # Falha ABRE. Mesma assimetria do threshold de deduplicação:
            # descartar notícia real é o erro caro, porque o leitor nunca a vê
            # e ninguém percebe. Artigo fora de tema é visível e removível.
            logger.warning(f"Erro no filtro de relevância ({e}); deixando passar")
            return None
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `python3 -m pytest tests/unit/test_relevance_filter.py -q`
Expected: PASS, 14 passed (7 itens × 2 testes)

- [ ] **Step 5: Commit**

```bash
git add app/services/sources/relevance_filter.py tests/unit/test_relevance_filter.py
git commit -m "feat(sources): filtro de relevancia descarta noticia de outra editoria"
```

---

### Task 2: Fronteira editorial

O critério decidido é o **sujeito da notícia**: empresa de cripto tratando de IA
é pauta do site. Estes testes travam essa decisão. Se alguém apertar o
vocabulário depois, é aqui que reclama.

**Files:**
- Modify: `tests/unit/test_relevance_filter.py`

- [ ] **Step 1: Acrescentar os testes de fronteira**

Acrescentar ao fim de `tests/unit/test_relevance_filter.py`:

```python
# Itens reais que DEVEM passar. Metade fala de IA, mas o sujeito é cripto.
# A decisao editorial e: criterio e o sujeito da noticia.
DENTRO_DO_TEMA = [
    # Worldcoin/World Network: projeto de cripto do Sam Altman
    (
        "Sam Altman-backed World Network secures $52.5 million in fresh funding "
        "to fight online AI deepfakes",
        "",
    ),
    # Casa 'AI agents' na OFF_BEAT — passa pelo veto ('Pantera', 'token sale')
    (
        "World Foundation Raises $52.5M to Scale Sam Altman’s ‘Proof of Human’ ID",
        "Pantera Capital led the one-year locked token sale, joined by Bain "
        "Capital Crypto, as World scales its ID network for AI agents.",
    ),
    (
        "Bitcoin OG selling eases as dormant BTC movement hits 4-year low: Galaxy",
        "Dormant BTC activity fell to its lowest level since Q3 2022, suggesting "
        "long-term holders have slowed distribution after heavy profit-taking.",
    ),
    (
        "Bitcoin treasury companies sell up, repay debt, pivot to AI as share "
        "prices collapse",
        "",
    ),
    (
        "Crypto Biz: Is the AI-to-crypto rotation underway?",
        "Bitcoin ETF inflows, cooling AI momentum and potential regulatory "
        "progress under the CLARITY Act are fueling speculation that capital is "
        "rotating back into crypto.",
    ),
    (
        "Franklin Templeton Says Agentic AI Is Crypto's 'Killer Use Case'",
        "The asset manager argues that AI software capable of paying for things "
        "autonomously will need blockchain rails to work—and that most investors "
        "aren't positioned for it.",
    ),
    # Os tres abaixo sao itens que a allowlist original PERDEU. Ficam como
    # regressao: se alguem trocar o denylist por allowlist, eles caem de novo.
    ("Shiba Inu surges 36% as South Korean traders fuel mystery rally", ""),
    (
        "Odos Protocol to shut down, gives users until July 30 to withdraw assets",
        "Odos Protocol will shut down on July 30, giving users one week to "
        "withdraw assets. The team did not provide a reason for the decision.",
    ),
    (
        "EU authorities include HTX exchange in Russian sanctions",
        "The exchange, already sanctioned by the UK, is now on a list of 18 "
        "entities “providing crypto-assets services or payment services“ in "
        "defiance of the EU’s measures against Russia.",
    ),
]


@pytest.mark.parametrize("titulo,resumo", DENTRO_DO_TEMA)
def test_nao_descarta_noticia_do_tema(filtro, titulo, resumo):
    """
    Trava a decisao editorial: empresa de cripto tratando de IA e pauta.
    Falha aqui significa que o vocabulario ficou estrito demais e esta
    comendo noticia legitima.
    """
    termo = filtro.check({"title": titulo, "description": resumo})

    assert termo is None, f"nao deveria descartar (casou {termo!r}): {titulo}"


def test_noticia_sem_campo_nenhum_passa(filtro):
    """Dict vazio nao pode virar descarte silencioso."""
    assert filtro.check({}) is None
```

- [ ] **Step 2: Rodar**

Run: `python3 -m pytest tests/unit/test_relevance_filter.py -q`
Expected: PASS, 24 passed.

Se algum item de `DENTRO_DO_TEMA` falhar, **não relaxe o teste**. O vocabulário
é que está errado: tire o padrão responsável da `OFF_BEAT_PATTERNS`, ou
acrescente o sinal de cripto correspondente à `CRYPTO_SIGNAL_PATTERNS` — desde
que não seja palavra genérica de negócios.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_relevance_filter.py
git commit -m "test(sources): trava a fronteira editorial do filtro de relevancia"
```

---

### Task 3: Falha abre

**Files:**
- Modify: `tests/unit/test_relevance_filter.py`

- [ ] **Step 1: Escrever os testes de fail-open**

Acrescentar ao fim de `tests/unit/test_relevance_filter.py`:

```python
# --- falha abre ----------------------------------------------------------

def test_erro_interno_deixa_passar(filtro):
    """
    Assimetria: descartar noticia real e o erro caro, porque o leitor nunca a
    ve e ninguem percebe. Artigo fora de tema e visivel e removivel.
    """
    class ExplodeAoBuscar:
        def search(self, _texto):
            raise RuntimeError("regex engine morreu")

    filtro._off_beat = ExplodeAoBuscar()

    assert filtro.check({"title": "Nvidia lanca GPU nova", "description": ""}) is None


def test_vocabulario_invalido_desativa_o_filtro(monkeypatch):
    """
    Padrao quebrado nao pode derrubar a construcao do NewsAggregator, que
    levaria o pipeline inteiro junto.
    """
    monkeypatch.setattr(
        RelevanceFilter, "OFF_BEAT_PATTERNS", (r"[nao-fecha",), raising=True
    )

    filtro_quebrado = RelevanceFilter()

    assert filtro_quebrado._off_beat is None
    assert filtro_quebrado.check({"title": "Nvidia lanca GPU nova"}) is None
```

- [ ] **Step 2: Rodar**

Run: `python3 -m pytest tests/unit/test_relevance_filter.py -q`
Expected: PASS, 26 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_relevance_filter.py
git commit -m "test(sources): filtro de relevancia falha abrindo"
```

---

### Task 4: Ligar no NewsAggregator

**Files:**
- Modify: `app/services/sources/news_aggregator.py:48-51` (construtor) e `:100-113` (fluxo)
- Test: `tests/unit/test_news_aggregator_relevance.py`

- [ ] **Step 1: Escrever o teste de integração**

Criar `tests/unit/test_news_aggregator_relevance.py`:

```python
"""
Integracao do filtro de relevancia no NewsAggregator.

O que importa aqui e a POSICAO: o filtro roda entre a coleta e a
deduplicacao. Antes do dedup porque ele e O(n^2), e porque o agregador e o
funil unico de RSS + API.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.sources.news_aggregator import NewsAggregator


def _noticia(titulo, descricao="", fonte="Decrypt"):
    return {
        "source": fonte,
        "title": titulo,
        "description": descricao,
        "url": f"https://exemplo/{abs(hash(titulo))}",
        "published_at": None,
    }


@pytest.fixture
def aggregator():
    agg = NewsAggregator()
    agg.rss_collector = MagicMock()
    agg.rss_collector.collect_all = AsyncMock(return_value=[])
    agg.api_collector = MagicMock()
    agg.api_collector.collect_all = AsyncMock(return_value=[])
    return agg


@pytest.mark.asyncio
async def test_item_fora_de_tema_nao_chega_ao_dedup(aggregator):
    ia = _noticia(
        "Alibaba's New Qwen Image 3 AI Wants to Be Useful, Not Just Pretty",
        "Qwen Image 3.0 generates dense newspapers and infographic grids.",
    )
    cripto = _noticia("Bitcoin atinge nova maxima", "BTC sobe forte hoje.")
    aggregator.rss_collector.collect_all = AsyncMock(return_value=[ia, cripto])

    vistos = {}

    def _espia(lista):
        vistos["titulos"] = [n["title"] for n in lista]
        return lista

    aggregator._deduplicate_source_news = _espia

    resultado = await aggregator.collect_news(hours_back=24)

    assert vistos["titulos"] == ["Bitcoin atinge nova maxima"]
    assert len(resultado) == 1


@pytest.mark.asyncio
async def test_fila_toda_no_tema_passa_intacta(aggregator):
    noticias = [
        _noticia("Bitcoin atinge nova maxima", "BTC sobe."),
        _noticia("Ethereum conclui atualizacao", "ETH melhora."),
    ]
    aggregator.rss_collector.collect_all = AsyncMock(return_value=noticias)
    aggregator._deduplicate_source_news = lambda lista: lista

    resultado = await aggregator.collect_news(hours_back=24)

    assert len(resultado) == 2


@pytest.mark.asyncio
async def test_cada_descarte_e_logado(aggregator):
    """
    Este projeto ja calibrou dois thresholds fora da faixa do dado real
    (SOURCE_DEDUP_THRESHOLD a 0,65 e DEDUPLICATION_THRESHOLD a 0,80) e nos dois
    casos o sintoma foi SILENCIO. Gate mal calibrado comendo noticia e o mesmo
    modo de falha, com consequencia pior — entao cada descarte deixa rastro.
    """
    from loguru import logger

    linhas = []
    sink_id = logger.add(lambda m: linhas.append(m), level="WARNING")
    try:
        aggregator.rss_collector.collect_all = AsyncMock(
            return_value=[_noticia("Nvidia unveils new GPU for AI labs", "")]
        )
        aggregator._deduplicate_source_news = lambda lista: lista

        await aggregator.collect_news(hours_back=24)
    finally:
        logger.remove(sink_id)

    texto = "".join(linhas)
    assert "Nvidia" in texto
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `python3 -m pytest tests/unit/test_news_aggregator_relevance.py -q`
Expected: FAIL — `test_item_fora_de_tema_nao_chega_ao_dedup` recebe os dois títulos, porque ainda não há filtro.

- [ ] **Step 3: Importar e instanciar o filtro**

Em `app/services/sources/news_aggregator.py`, no bloco de imports (após a linha
`from .api_collector import APICollector`):

```python
from .relevance_filter import RelevanceFilter
```

E no `__init__`, após `self.api_collector = APICollector()`:

```python
        self.relevance_filter = RelevanceFilter()
```

- [ ] **Step 4: Chamar o filtro entre a coleta e o dedup**

Em `app/services/sources/news_aggregator.py`, substituir estas duas linhas:

```python
        total_before = len(all_news)
        logger.info(f"Coleta finalizada: {total_before} notícias no total")
```

por:

```python
        # Filtro de relevância ANTES da deduplicação: o dedup é O(n²), e este é
        # o funil único por onde passam RSS e API.
        coletadas = len(all_news)
        all_news = self._filter_off_topic(all_news)

        total_before = len(all_news)
        logger.info(
            f"Coleta finalizada: {coletadas} notícia(s) coletada(s), "
            f"{total_before} no tema"
        )
```

- [ ] **Step 5: Implementar `_filter_off_topic`**

Em `app/services/sources/news_aggregator.py`, acrescentar este método logo após
`collect_news` (antes de `_deduplicate_source_news`):

```python
    def _filter_off_topic(self, news_list: List[Dict]) -> List[Dict]:
        """
        Remove notícias de outra editoria antes da deduplicação.

        Loga CADA descarte em WARNING, com o termo que o causou. Não é excesso:
        este projeto já calibrou dois thresholds fora da faixa onde o dado real
        cai — SOURCE_DEDUP_THRESHOLD a 0,65 e DEDUPLICATION_THRESHOLD a 0,80 —
        e nos dois casos o sintoma foi silêncio. Gate mal calibrado comendo
        notícia legítima é o mesmo modo de falha, com consequência pior. A ~6%
        de descarte são cerca de 7 linhas por run.
        """
        mantidas = []
        for news in news_list:
            termo = self.relevance_filter.check(news)
            if termo is None:
                mantidas.append(news)
                continue
            logger.warning(
                f"Fora de tema (casou '{termo}', sem sinal de cripto): "
                f"[{news.get('source', '')}] {news.get('title', '')[:80]}"
            )

        descartadas = len(news_list) - len(mantidas)
        if descartadas:
            logger.warning(
                f"Filtro de relevância: {descartadas}/{len(news_list)} "
                f"notícia(s) descartada(s) por serem de outra editoria"
            )
        return mantidas
```

- [ ] **Step 6: Rodar os testes de integração**

Run: `python3 -m pytest tests/unit/test_news_aggregator_relevance.py -q`
Expected: PASS, 3 passed.

- [ ] **Step 7: Rodar a suíte inteira**

Run: `python3 -m pytest tests/ -q`
Expected: PASS. O baseline antes desta task é 444 passed; agora devem ser 473
(444 + 26 da Task 1-3 + 3 desta). Se algum teste **pré-existente** quebrar, é
sinal de que o filtro está comendo notícia usada como fixture em outro teste —
investigue, não relaxe.

- [ ] **Step 8: Commit**

```bash
git add app/services/sources/news_aggregator.py tests/unit/test_news_aggregator_relevance.py
git commit -m "feat(sources): NewsAggregator filtra fora de tema antes do dedup"
```

---

### Task 5: Recalibrar contra o feed vivo

O vocabulário foi medido em 2026-07-26 contra 110 itens: 7 descartes (6,4%),
todos corretos. Esta task **reconfirma** contra o feed do dia da implementação,
que terá outras notícias. É obrigatória: é a única etapa que pega vocabulário
errado de um jeito que o snapshot de hoje não mostrou.

**Files:** nenhum arquivo de produção, a menos que a conferência acuse erro.

- [ ] **Step 1: Rodar o filtro contra o feed vivo**

```bash
python3 - <<'PY'
import asyncio, sys
sys.path.insert(0, '.')
from app.services.sources.rss_collector import RSSCollector
from app.services.sources.relevance_filter import RelevanceFilter

async def main():
    itens = await RSSCollector().collect_all(hours_back=72)
    filtro = RelevanceFilter()
    descartes = [(n, filtro.check(n)) for n in itens]
    fora = [(n, t) for n, t in descartes if t is not None]
    print(f"fila: {len(itens)} | descartados: {len(fora)} ({100*len(fora)/max(len(itens),1):.1f}%)\n")
    print("=== CONFERIR NA MAO, UM POR UM ===")
    for n, termo in fora:
        print(f"  [{n.get('source')}] casou {termo!r}")
        print(f"      {n.get('title','')[:100]}")

asyncio.run(main())
PY
```

- [ ] **Step 2: Conferir cada descarte na mão**

Ler a lista inteira. Para cada item, responder: *isto é notícia de cripto?*

- Se **todos** os descartes forem de outra editoria: vocabulário validado, siga
  para o Step 4.
- Se algum for notícia legítima de cripto: vá para o Step 3.

A taxa esperada fica entre 3% e 10%. Acima de 15% quase certamente indica
padrão largo demais na `OFF_BEAT_PATTERNS` — confira qual termo se repete na
coluna `casou`.

- [ ] **Step 3: Corrigir o vocabulário (só se o Step 2 acusou erro)**

Duas correções possíveis, nesta ordem de preferência:

1. Se o termo que casou na `OFF_BEAT_PATTERNS` for largo demais (ex.: casou
   `benchmarks` numa matéria sobre índice de bitcoin), **restrinja ou remova o
   padrão**.
2. Se o item for cripto mas não tiver nenhum sinal na `CRYPTO_SIGNAL_PATTERNS`
   (ex.: token novo sem nome na lista), **acrescente o sinal específico** —
   nome da moeda, nome da exchange. Nunca palavra genérica de negócios.

Acrescente o item corrigido à fixture da Task 1 ou 2, conforme o caso, e volte
ao Step 1. Repita até a conferência sair limpa.

- [ ] **Step 4: Registrar o resultado**

Rodar de novo a suíte para garantir que qualquer ajuste de vocabulário não
quebrou os testes travados:

Run: `python3 -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 5: Commit (só se houve ajuste no Step 3)**

```bash
git add app/services/sources/relevance_filter.py tests/unit/test_relevance_filter.py
git commit -m "fix(sources): ajusta vocabulario do filtro apos calibracao no feed vivo"
```

Se o Step 2 saiu limpo sem ajuste, não há o que commitar — siga para a Task 6.

---

### Task 6: Documentar as armadilhas

**Files:**
- Modify: `ai_docs/gotchas.md`

- [ ] **Step 1: Acrescentar a seção**

Acrescentar ao fim de `ai_docs/gotchas.md`:

```markdown
## Filtro de relevância: duas armadilhas de vocabulário

`app/services/sources/relevance_filter.py` descarta notícia quando há sinal de
outra editoria (`OFF_BEAT_PATTERNS`) e **não** há sinal de cripto
(`CRYPTO_SIGNAL_PATTERNS`). Duas regras não são óbvias e já custaram uma rodada
de medição cada.

**1. Nunca ponha palavra genérica de negócios no veto.**

A primeira versão tinha `hack` na `CRYPTO_SIGNAL_PATTERNS`. Resultado:

```
título: Nvidia, Meta, and Microsoft Tell Washington: Don't Kill Open-Source AI
resumo: ...days after a Chinese AI helped Hugging Face survive a hack...
```

casou `Nvidia` e `Open-Source AI` na OFF_BEAT, e mesmo assim passou — uma
palavra que qualquer setor usa anulou dois sinais corretos. Também proibidos:
`protocol`, `exchange`, `treasury`, `node`, `bridge`, `ledger`, `circle`, `ada`.

**2. Não use `\bai\b` solto na lista de outra editoria.**

Matéria de cripto cita IA o tempo todo ("Is the AI-to-crypto rotation
underway?", "Franklin Templeton Says Agentic AI Is Crypto's Killer Use Case").
Um padrão largo aí faz todo o resultado depender do veto. A forma correta de
cobrir contexto de IA é **nome próprio** de laboratório ou modelo — foi o que
resolveu "Chinese AI ... Chinese model GLM 5.2", que não casava com jargão
nenhum.

**Fronteira editorial:** o critério é o **sujeito** da notícia. Empresa de
cripto tratando de IA é pauta (Galaxy construindo data center, tesouraria em
bitcoin pivotando para IA, Worldcoin). Os testes em
`tests/unit/test_relevance_filter.py::test_nao_descarta_noticia_do_tema` travam
essa decisão.

**Ao mexer no vocabulário:** rode a calibração contra o feed vivo (Task 5 do
plano `docs/superpowers/plans/2026-07-26-relevance-filter.md`) e confira cada
descarte na mão. Lista de palavras não se escreve por suposição.
```

- [ ] **Step 2: Commit**

```bash
git add ai_docs/gotchas.md
git commit -m "docs: registra as armadilhas de vocabulario do filtro de relevancia"
```

---

## Encerramento

Após a Task 6, usar **superpowers:finishing-a-development-branch** na branch
`feat/relevance-filter`.

## O que este plano deliberadamente NÃO faz

- **Classificador LLM de relevância.** `RelevanceFilter.check` é a costura onde
  ele entraria. A decisão depende de medir em produção se o denylist basta.
- **Fontes primárias (SEC, EDGAR, Ethereum Foundation).** Derrubado pela medição
  registrada na spec. EDGAR continua sendo o candidato real se o tema voltar.
- **Filtrar por idioma ou por fonte.** Nenhuma evidência de que seja necessário.
