# Dados de mercado na geração de notícias — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar ao gerador de notícias acesso a dados de mercado verificados (preço, market cap, Fear & Greed) para que os artigos citem números reais em vez de contornar com "registrou alta" — sem pagar os 5,9s de contexto macro que só o relatório semanal precisa.

**Architecture:** `MarketDataCollector` ganha `collect_snapshot()` (as 3 chamadas HTTP, sem o macro) extraído de um helper compartilhado com `collect_all()`, cujo comportamento fica preservado. O pipeline busca uma vez por run e injeta em `source_news["market_data"]`, seguindo o mesmo padrão do `full_text`. O prompt ganha uma seção `<dados_de_mercado>` condicional, e o item 1 do guardrail passa a abençoar essa seção como fonte válida — sem isso o modelo ignora os números.

**Tech Stack:** Python 3.11+, `httpx`, pytest (mocks — nenhum teste toca CoinGecko).

---

## Contexto essencial para o executor

- **Rodar testes:** `python3 -m pytest tests/unit/... -q` (não existe venv; use `python3`).
- **Baseline (2026-07-26):** `376 passed, 0 failed, 0 errors`.
- **Comentários de código em português** (convenção do projeto).
- **Por que não chamar `collect_all()`:** medido, `collect_all()` leva 7,0s — dos quais **5,9s são cinco buscas no DuckDuckGo** (`_search_macro_context`: taxa do Fed, CPI, S&P 500, DXY, fluxo de ETF). Isso é material de análise macro semanal; num artigo sobre invasão de exchange é ruído que ocupa contexto. A parte útil (preços + global + Fear & Greed) leva 1,1s e tem 1.713 chars.
- **`collect_all()` NÃO pode mudar de comportamento.** O relatório semanal é seu consumidor legítimo e quer o macro. Existe teste dedicado a proteger isso (Task 1).
- **O risco central não é exceção, é inércia silenciosa.** O `SYSTEM_PROMPT` instrui o modelo a nunca citar número fora da fonte. Se os dados entrarem numa seção nova sem atualizar esse guardrail, o modelo pode ignorá-los — e não haveria sinal nenhum de falha, só artigos continuando vagos. Por isso a Task 2 tem teste dedicado ao texto do guardrail.
- **O que os testes NÃO provam:** que o modelo usou os números. Provam que o dado chegou ao prompt. O uso efetivo só aparece lendo artigo publicado — está na Task 4, Step 4, como observação pós-deploy.
- **Ordem das tasks:** o collector primeiro (isolado, sem dependências), depois o prompt, depois o pipeline que liga os dois. Cada uma deixa a suíte verde.

---

### Task 1: `collect_snapshot()` no collector

**Files:**
- Modify: `app/services/ai/market_data_collector.py:27-60` (refatorar `collect_all`, adicionar `_collect_sections` e `collect_snapshot`)
- Test: `tests/unit/test_market_data_snapshot.py` (novo)

Hoje `collect_all` monta as seções inline. Extrair `_collect_sections(include_macro)` permite os dois consumidores sem duplicar a montagem — e duplicar convidaria divergência, que é como o relatório semanal acabaria perdendo o macro sem ninguém notar.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/unit/test_market_data_snapshot.py`:

```python
"""
Testes do collect_snapshot — o subconjunto de dados de mercado que serve ao
pipeline de notícias.

collect_all() leva 7,0s, dos quais 5,9s são cinco buscas no DuckDuckGo para
contexto macro (Fed, CPI, S&P, DXY, ETF). Isso é material de análise semanal;
para um artigo de notícia é ruído caro. collect_snapshot faz só as 3 chamadas
HTTP (1,1s).

O teste que mais importa aqui é o primeiro: ele é o que impede alguém de
"simplificar" collect_snapshot chamando collect_all e trazer os 5,9s de volta.
"""
from unittest.mock import AsyncMock

import pytest

from app.services.ai.market_data_collector import MarketDataCollector


@pytest.fixture
def collector() -> MarketDataCollector:
    return MarketDataCollector()


def _mock_fetches(monkeypatch, collector, precos="PREÇOS: BTC US$ 64.640",
                  glob="GLOBAL: cap US$ 2.1T", fng="FEAR & GREED: 54 (neutro)",
                  macro="MACRO: Fed manteve juros"):
    """Substitui os quatro coletores. Devolve o registro de quem foi chamado."""
    chamados = []

    async def _precos(client):
        chamados.append("precos")
        return precos

    async def _glob(client):
        chamados.append("global")
        return glob

    async def _fng(client):
        chamados.append("fng")
        return fng

    async def _macro():
        chamados.append("macro")
        return macro

    monkeypatch.setattr(collector, "_fetch_crypto_prices", _precos)
    monkeypatch.setattr(collector, "_fetch_global_crypto", _glob)
    monkeypatch.setattr(collector, "_fetch_fear_greed", _fng)
    monkeypatch.setattr(collector, "_search_macro_context", _macro)
    return chamados


@pytest.mark.asyncio
async def test_snapshot_nao_dispara_a_busca_macro(monkeypatch, collector):
    """
    Guarda dos 5,9s. Se alguém reescrever collect_snapshot como um alias de
    collect_all, este teste acusa.
    """
    chamados = _mock_fetches(monkeypatch, collector)

    await collector.collect_snapshot()

    assert "macro" not in chamados, f"macro foi chamado: {chamados}"
    assert set(chamados) == {"precos", "global", "fng"}


@pytest.mark.asyncio
async def test_snapshot_traz_as_tres_secoes(monkeypatch, collector):
    _mock_fetches(monkeypatch, collector)

    resultado = await collector.collect_snapshot()

    assert "PREÇOS" in resultado
    assert "GLOBAL" in resultado
    assert "FEAR & GREED" in resultado
    assert "MACRO" not in resultado


@pytest.mark.asyncio
async def test_snapshot_tem_cabecalho_com_timestamp(monkeypatch, collector):
    """O artigo precisa saber que o dado é do momento, não histórico."""
    _mock_fetches(monkeypatch, collector)

    resultado = await collector.collect_snapshot()

    assert "DADOS DE MERCADO COLETADOS EM" in resultado
    assert "UTC" in resultado


@pytest.mark.asyncio
async def test_snapshot_devolve_none_quando_tudo_falha(monkeypatch, collector):
    """
    NÃO devolve o texto de fallback do collect_all ("NOTA: não foi possível...
    use seu conhecimento mais recente"). Aquele texto é escrito para o
    relatório semanal; num artigo de notícia viraria licença para o modelo
    especular com conhecimento de treino, que é o oposto do guardrail.
    """
    _mock_fetches(monkeypatch, collector, precos=None, glob=None, fng=None)

    assert await collector.collect_snapshot() is None


@pytest.mark.asyncio
async def test_snapshot_com_falha_parcial_devolve_o_que_coletou(monkeypatch, collector):
    """Preço ok e Fear & Greed fora do ar ainda é dado útil."""
    _mock_fetches(monkeypatch, collector, glob=None, fng=None)

    resultado = await collector.collect_snapshot()

    assert resultado is not None
    assert "PREÇOS" in resultado
    assert "FEAR & GREED" not in resultado


@pytest.mark.asyncio
async def test_collect_all_continua_trazendo_o_macro(monkeypatch, collector):
    """
    Guarda do relatório semanal: ele é o consumidor legítimo do macro, e o
    refactor não pode tirá-lo por engano.
    """
    chamados = _mock_fetches(monkeypatch, collector)

    resultado = await collector.collect_all()

    assert "macro" in chamados
    assert "MACRO" in resultado


@pytest.mark.asyncio
async def test_collect_all_mantem_o_texto_de_fallback(monkeypatch, collector):
    """O contrato do relatório semanal em falha total não muda: string, não None."""
    _mock_fetches(monkeypatch, collector, precos=None, glob=None, fng=None, macro=None)

    resultado = await collector.collect_all()

    assert isinstance(resultado, str)
    assert "Não foi possível coletar" in resultado
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `python3 -m pytest tests/unit/test_market_data_snapshot.py -q`
Expected: FAIL nos 5 testes de `collect_snapshot` com `AttributeError: 'MarketDataCollector' object has no attribute 'collect_snapshot'`. Os 2 de `collect_all` já passam — existem como guarda de não-regressão.

- [ ] **Step 3: Implementar**

Substituir o `collect_all` atual (linhas 27-60 de `app/services/ai/market_data_collector.py`) por:

```python
    async def _collect_sections(self, include_macro: bool) -> list:
        """
        Coleta as seções de dados disponíveis.

        Falha parcial devolve o que deu — dado incompleto ainda é dado útil.
        `include_macro` controla as 5 buscas web de contexto macro, que custam
        ~5,9s dos ~7,0s totais e só interessam ao relatório semanal.
        """
        sections = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            crypto = await self._fetch_crypto_prices(client)
            if crypto:
                sections.append(crypto)

            global_data = await self._fetch_global_crypto(client)
            if global_data:
                sections.append(global_data)

            fng = await self._fetch_fear_greed(client)
            if fng:
                sections.append(fng)

        if include_macro:
            macro = await self._search_macro_context()
            if macro:
                sections.append(macro)

        return sections

    def _formatar(self, sections: list) -> str:
        """Cabeçalho com timestamp + seções. O timestamp diz ao modelo que o
        dado é do momento, não histórico."""
        timestamp = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
        header = f"=== DADOS DE MERCADO COLETADOS EM {timestamp} ==="
        return header + "\n\n" + "\n\n".join(sections)

    async def collect_all(self) -> str:
        """
        Dados de mercado COM contexto macro, para o relatório semanal.

        Em falha total devolve uma NOTA em texto (não None): no relatório
        semanal a ausência de dado merece nota ao leitor. Contrato preservado
        do comportamento anterior.
        """
        sections = await self._collect_sections(include_macro=True)

        if not sections:
            return (
                "NOTA: Não foi possível coletar dados de mercado em tempo real. "
                "Use seu conhecimento mais recente e indique explicitamente que "
                "os dados podem estar defasados."
            )

        return self._formatar(sections)

    async def collect_snapshot(self) -> Optional[str]:
        """
        Dados de mercado SEM contexto macro, para o pipeline de notícias.

        Devolve None em falha total — e não o texto de fallback do collect_all,
        que instruiria o modelo a especular com conhecimento de treino. Aqui a
        ausência de dado significa apenas que a seção não entra no prompt.
        """
        sections = await self._collect_sections(include_macro=False)
        if not sections:
            logger.warning("[MarketData] Nenhum dado coletado para o snapshot")
            return None
        return self._formatar(sections)
```

- [ ] **Step 4: Rodar para confirmar que passam**

Run: `python3 -m pytest tests/unit/test_market_data_snapshot.py -q`
Expected: PASS (7 testes)

- [ ] **Step 5: Confirmar que o relatório semanal não regrediu**

Run: `python3 -m pytest tests/unit/test_weekly_report_generator.py tests/unit/test_weekly_report_prompts.py -q`
Expected: PASS (14 testes). O `_generate_content` do relatório chama `collect_all()`, cujo contrato foi preservado.

- [ ] **Step 6: Commit**

```bash
git add app/services/ai/market_data_collector.py tests/unit/test_market_data_snapshot.py
git commit -m "feat(sources): collect_snapshot sem contexto macro (1.1s vs 7.0s)"
```

---

### Task 2: seção `<dados_de_mercado>` no prompt e guardrail atualizado

**Files:**
- Modify: `app/services/ai/content_generator.py` — `SYSTEM_PROMPT` (item 1 do guardrail), `_ARTICLE_PROMPT_TEMPLATE`, `_build_article_prompt`
- Test: `tests/unit/test_content_generator_market_data.py` (novo)

O `market_data` chega como argumento novo de `_build_article_prompt`. O pipeline só passa a preencher na Task 3 — nesta task o caminho existe e é testado, mas ainda não é exercitado em produção.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/unit/test_content_generator_market_data.py`:

```python
"""
Testes da injeção de dados de mercado no prompt.

O SYSTEM_PROMPT proíbe o modelo de citar número fora da fonte — regra que
existe para impedir alucinação de preço, e que continua valendo. O efeito
colateral é linguagem vaga ("registrou alta") por falta de dado.

Com <dados_de_mercado> o modelo passa a ter número verificado. Mas o guardrail
precisa dizer explicitamente que a seção é fonte válida: sem isso o modelo
trata os dados como "não sendo a fonte fornecida" e os ignora — e a falha seria
silenciosa, só visível na leitura de artigos publicados.
"""
import pytest

from app.services.ai.content_generator import ContentGenerator

SNAPSHOT = (
    "=== DADOS DE MERCADO COLETADOS EM 26/07/2026 17:51 UTC ===\n\n"
    "PREÇOS CRIPTO (fonte: CoinGecko, tempo real):\n"
    "  Bitcoin (BTC):\n    Preço: US$ 64,640.00\n    Variação: 24h +0.80%"
)


@pytest.fixture
def generator() -> ContentGenerator:
    return ContentGenerator()


def test_secao_entra_no_prompt_quando_ha_dado(generator: ContentGenerator):
    prompt = generator._build_article_prompt(
        "Bitcoin sobe", "corpo da noticia", "CoinDesk", "bitcoin",
        "Bitcoin", None, market_data=SNAPSHOT,
    )

    assert "<dados_de_mercado>" in prompt
    assert "</dados_de_mercado>" in prompt
    assert "US$ 64,640.00" in prompt


def test_secao_nao_entra_quando_nao_ha_dado(generator: ContentGenerator):
    """Sem dado, nada de seção vazia ou placeholder confundindo o modelo."""
    prompt = generator._build_article_prompt(
        "Bitcoin sobe", "corpo da noticia", "CoinDesk", "bitcoin",
        "Bitcoin", None, market_data=None,
    )

    assert "<dados_de_mercado>" not in prompt


def test_market_data_e_opcional(generator: ContentGenerator):
    """Chamada sem o argumento continua válida — o default é None."""
    prompt = generator._build_article_prompt(
        "Bitcoin sobe", "corpo", "CoinDesk", "bitcoin", "Bitcoin", None,
    )

    assert "<dados_de_mercado>" not in prompt
    assert "<dados_da_fonte>" in prompt


def test_secao_vem_logo_apos_dados_da_fonte(generator: ContentGenerator):
    """
    Posição importa: é material de fonte, então fica junto do resto do
    material de fonte e ANTES das instruções de tarefa.
    """
    prompt = generator._build_article_prompt(
        "t", "d", "s", "bitcoin", "Bitcoin", None, market_data=SNAPSHOT,
    )

    fim_fonte = prompt.index("</dados_da_fonte>")
    ini_mercado = prompt.index("<dados_de_mercado>")
    ini_tarefa = prompt.index("<tarefa>")

    assert fim_fonte < ini_mercado < ini_tarefa


def test_secao_instrui_uso_condicional(generator: ContentGenerator):
    """
    O dado entra em todo artigo, mas preço é irrelevante para uma notícia de
    regulação. A instrução evita que o modelo enfie número onde não cabe.
    """
    prompt = generator._build_article_prompt(
        "t", "d", "s", "bitcoin", "Bitcoin", None, market_data=SNAPSHOT,
    )

    ini = prompt.index("<dados_de_mercado>")
    fim = prompt.index("</dados_de_mercado>")
    bloco = prompt[ini:fim].lower()

    assert "pertinente" in bloco or "relevante" in bloco


def test_guardrail_abencoa_a_secao_de_dados_de_mercado():
    """
    O teste que protege contra a falha silenciosa: sem esta menção, o modelo
    recebe os dados e não os usa, e nada no sistema acusa.
    """
    guardrail = ContentGenerator.SYSTEM_PROMPT

    assert "<dados_de_mercado>" in guardrail, (
        "o guardrail de dados inventados precisa citar a seção como fonte "
        "válida, senão o modelo ignora os números"
    )


def test_guardrail_mantem_a_proibicao_de_inventar():
    """Abençoar a seção não pode virar licença geral para inventar número."""
    guardrail = ContentGenerator.SYSTEM_PROMPT

    assert "NUNCA invente preços" in guardrail
    assert "registrou alta" in guardrail
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `python3 -m pytest tests/unit/test_content_generator_market_data.py -q`
Expected: FAIL nos 7 testes. Os 5 primeiros com `TypeError: _build_article_prompt() got an unexpected keyword argument 'market_data'`; `test_guardrail_abencoa_a_secao_de_dados_de_mercado` com `AssertionError`. `test_guardrail_mantem_a_proibicao_de_inventar` já passa.

- [ ] **Step 3: Implementar — atualizar o item 1 do guardrail**

Em `app/services/ai/content_generator.py`, substituir o item 1 de `<guardrails_de_seguranca>` (as 3 linhas atuais sob `1. **DADOS INVENTADOS:**`) por:

```
1. **DADOS INVENTADOS:**
   - NUNCA invente preços, porcentagens, datas, valores ou estatísticas que NÃO estejam EXPLICITAMENTE na fonte fornecida OU na seção <dados_de_mercado>.
   - A seção <dados_de_mercado>, quando presente, contém dados VERIFICADOS de mercado em tempo real. Pode e DEVE citá-los quando forem pertinentes ao fato noticiado, sempre deixando claro que são dados de mercado do momento.
   - Se a fonte disser "Bitcoin subiu" e não houver <dados_de_mercado>, NÃO escreva "Bitcoin subiu 5,3%" ou "atingiu US$ 70.000".
   - Sem dados específicos, use termos como "registrou alta", "apresentou valorização", "sofreu queda".
```

- [ ] **Step 4: Implementar — o bloco da seção**

Adicionar a constante na classe `ContentGenerator`, logo após `JSON_CONTRACT_BLOCK`:

```python
    # Seção de dados de mercado. Condicional: só entra quando o pipeline
    # conseguiu coletar. O "apenas se pertinente" evita que o modelo enfie
    # preço numa notícia de regulação só porque o número está ali.
    MARKET_DATA_BLOCK = """
<dados_de_mercado>
Dados VERIFICADOS de mercado, coletados em tempo real. São fonte válida para
citar números — use-os apenas se forem pertinentes ao fato noticiado, e deixe
claro que se referem ao momento da publicação.

{market_data}
</dados_de_mercado>
"""
```

- [ ] **Step 5: Implementar — injeção em `_build_article_prompt`**

Trocar a assinatura e o corpo inicial de `_build_article_prompt`:

```python
    def _build_article_prompt(
        self,
        title: str,
        description: str,
        source: str,
        category: str,
        keyword: str,
        correction_hint: Optional[str] = None,
        market_data: Optional[str] = None,
    ) -> str:
        """
        Monta o user prompt da chamada única.

        Reaproveita as seções que já existiam no prompt de conteúdo
        (<dados_da_fonte> até <validacao_obrigatoria>), acrescenta o contrato
        de saída no lugar do <output> antigo — que pedia "APENAS o artigo em
        Markdown", incompatível com JSON — e anexa o bloco de correção em retry.

        `market_data` entra logo após <dados_da_fonte>: é material de fonte, e
        fica antes das instruções de tarefa.
        """
        cat_config = self._get_category_config(category)
        base = self._ARTICLE_PROMPT_TEMPLATE.format(
            title=title,
            description=description,
            category=category,
            tom=cat_config["tom"],
            foco=cat_config["foco"],
            keyword=keyword,
        )

        if market_data:
            marcador = "</dados_da_fonte>"
            base = base.replace(
                marcador,
                marcador + "\n" + self.MARKET_DATA_BLOCK.format(market_data=market_data),
                1,
            )

        prompt = base + self.JSON_CONTRACT_BLOCK.format(keyword=keyword)
```

O resto do método (o bloco de `correction_hint` e o `return prompt`) fica inalterado.

- [ ] **Step 6: Implementar — repassar de `_generate_article_json`**

Em `_generate_article_json`, aceitar e repassar o dado. Trocar a assinatura e a chamada ao construtor:

```python
    async def _generate_article_json(
        self,
        title: str,
        description: str,
        source: str,
        category: str = "default",
        correction_hint: Optional[str] = None,
        market_data: Optional[str] = None,
    ) -> Optional[Dict]:
```

e, dentro dele:

```python
        user_prompt = self._build_article_prompt(
            title, description, source, category, keyword, correction_hint, market_data
        )
```

- [ ] **Step 7: Implementar — repassar de `generate_article`**

Em `generate_article`, ler de `source_news` e repassar. Trocar a chamada:

```python
            dados = await self._generate_article_json(
                title,
                description,
                source,
                category,
                correction_hint,
                market_data=source_news.get("market_data"),
            )
```

- [ ] **Step 8: Rodar os testes**

Run: `python3 -m pytest tests/unit/test_content_generator_market_data.py tests/unit/test_content_generator_single_call.py tests/unit/test_content_generator_article.py -q`
Expected: PASS (7 + 7 + 10 = 24 testes). Os de `single_call` e `article` não mudaram — `market_data` tem default `None`, então o comportamento sem ele é idêntico.

- [ ] **Step 9: Commit**

```bash
git add app/services/ai/content_generator.py tests/unit/test_content_generator_market_data.py
git commit -m "feat(ai): secao <dados_de_mercado> no prompt e guardrail que a abencoa"
```

---

### Task 3: pipeline busca uma vez por run e injeta

**Files:**
- Modify: `app/services/automation/news_pipeline.py` — fetch antes do loop, injeção dentro dele
- Test: `tests/unit/test_news_pipeline_market_data.py` (novo)

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/unit/test_news_pipeline_market_data.py`:

```python
"""
Testes da injeção de dados de mercado pelo pipeline.

O fetch é UMA vez por run, não por artigo: preço não muda em segundos e o run
tenta até 3 notícias. Buscar por artigo triplicaria 1,1s de rede sem ganho.

Falha do collector não pode impedir publicação — dado de mercado enriquece o
artigo, não é requisito dele.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.deduplication import ActionType

SNAPSHOT = "=== DADOS DE MERCADO ===\n\nPREÇOS: BTC US$ 64,640.00"


def _news(source, title, url):
    return {
        "source": source,
        "source_language": "en",
        "title": title,
        "url": url,
        "description": f"descrição de {title}",
        "published_at": datetime.now(timezone.utc),
        "collected_at": datetime.now(timezone.utc),
        "source_count": 1,
        "covered_by": [source],
    }


ARTICLE = {
    "title": "Bitcoin atinge US$ 100 mil pela primeira vez na história",
    "slug": "bitcoin-atinge-100-mil",
    "content_markdown": "## Bitcoin\n\n" + "palavra de conteúdo " * 120,
    "excerpt": "Bitcoin atinge marco histórico em meio a forte demanda institucional hoje.",
    "meta_title": "Bitcoin US$100k",
    "meta_description": "Bitcoin ultrapassa US$100 mil pela primeira vez na história do mercado.",
    "source_url": "https://coindesk.com/a",
    "source_name": "CoinDesk",
    "category": "bitcoin",
}


@pytest.fixture
def m():
    """Patcha as dependências do pipeline e expõe os mocks."""
    with patch("app.services.automation.news_pipeline.NewsAggregator") as agg_cls, \
         patch("app.services.automation.news_pipeline.ContentGenerator") as gen_cls, \
         patch("app.services.automation.news_pipeline.ImageGenerator"), \
         patch("app.services.automation.news_pipeline.QualityValidator") as val_cls, \
         patch("app.services.automation.news_pipeline.ArticlePublisher") as pub_cls, \
         patch("app.services.automation.news_pipeline.CategoryClassifier") as cat_cls, \
         patch("app.services.automation.news_pipeline.ArticleExtractor") as ext_cls, \
         patch("app.services.automation.news_pipeline.DuplicateDetector") as det_cls, \
         patch("app.services.automation.news_pipeline.PostRepositoryImpl"), \
         patch("app.services.automation.news_pipeline.market_data_collector") as mdc, \
         patch("app.services.automation.news_pipeline.crud_post") as crud, \
         patch("app.services.automation.news_pipeline.engine") as eng:

        mocks = MagicMock()

        mocks.aggregator = MagicMock()
        mocks.aggregator.collect_news = AsyncMock(return_value=[])
        agg_cls.return_value = mocks.aggregator

        mocks.generator = MagicMock()
        mocks.generator.generate_article = AsyncMock(return_value=dict(ARTICLE))
        gen_cls.return_value = mocks.generator

        mocks.validator = MagicMock()
        mocks.validator.validate_article = MagicMock(return_value=(True, []))
        val_cls.return_value = mocks.validator

        mocks.publisher = MagicMock()
        mocks.publisher.publish_article = AsyncMock(return_value=True)
        mocks.publisher.update_article = AsyncMock(return_value=True)
        pub_cls.return_value = mocks.publisher

        mocks.classifier = MagicMock()
        mocks.classifier.classify = MagicMock(return_value="bitcoin")
        cat_cls.return_value = mocks.classifier

        mocks.extractor = MagicMock()
        mocks.extractor.extract = AsyncMock(return_value=None)
        ext_cls.return_value = mocks.extractor

        mocks.detector = MagicMock()
        check = MagicMock()
        check.acao = ActionType.CREATE_NEW
        mocks.detector.check_duplicate = AsyncMock(return_value=check)
        det_cls.return_value = mocks.detector

        mocks.market = mdc
        mdc.collect_snapshot = AsyncMock(return_value=SNAPSHOT)

        mocks.crud = crud
        crud.get_recent_posts = AsyncMock(return_value=[])
        crud.get_existing_source_urls = AsyncMock(return_value=set())

        lock_result = MagicMock()
        lock_result.scalar.return_value = True
        lock_conn = AsyncMock()
        lock_conn.execute = AsyncMock(return_value=lock_result)
        eng.connect = AsyncMock(return_value=lock_conn)

        yield mocks


@pytest.mark.asyncio
async def test_busca_o_snapshot_uma_vez_por_run(m):
    """
    Três notícias na fila, uma única coleta. Buscar por artigo triplicaria
    1,1s de rede para obter o mesmo preço.
    """
    from app.services.automation.news_pipeline import NewsPipeline

    m.aggregator.collect_news.return_value = [
        _news("CoinDesk", "Noticia A", "https://a.com/1"),
        _news("Decrypt", "Noticia B", "https://b.com/2"),
        _news("CryptoSlate", "Noticia C", "https://c.com/3"),
    ]
    m.generator.generate_article.side_effect = [None, None, dict(ARTICLE)]

    await NewsPipeline().run(MagicMock())

    assert m.market.collect_snapshot.await_count == 1


@pytest.mark.asyncio
async def test_injeta_o_snapshot_em_source_news(m):
    """O gerador recebe o dado pelo mesmo caminho do full_text."""
    from app.services.automation.news_pipeline import NewsPipeline

    m.aggregator.collect_news.return_value = [
        _news("CoinDesk", "Noticia A", "https://a.com/1"),
    ]

    await NewsPipeline().run(MagicMock())

    recebido = m.generator.generate_article.await_args_list[0][0][0]
    assert recebido["market_data"] == SNAPSHOT


@pytest.mark.asyncio
async def test_snapshot_none_nao_impede_publicacao(m):
    """CoinGecko fora do ar não pode parar o pipeline."""
    from app.services.automation.news_pipeline import NewsPipeline

    m.aggregator.collect_news.return_value = [
        _news("CoinDesk", "Noticia A", "https://a.com/1"),
    ]
    m.market.collect_snapshot.return_value = None

    report = await NewsPipeline().run(MagicMock())

    assert report["published"] == 1
    recebido = m.generator.generate_article.await_args_list[0][0][0]
    assert recebido.get("market_data") is None


@pytest.mark.asyncio
async def test_excecao_no_collector_nao_impede_publicacao(m):
    """
    Timeout ou erro de rede no collector é capturado. Dado de mercado
    enriquece o artigo; não é requisito dele.
    """
    from app.services.automation.news_pipeline import NewsPipeline

    m.aggregator.collect_news.return_value = [
        _news("CoinDesk", "Noticia A", "https://a.com/1"),
    ]
    m.market.collect_snapshot.side_effect = RuntimeError("timeout na CoinGecko")

    report = await NewsPipeline().run(MagicMock())

    assert report["published"] == 1
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `python3 -m pytest tests/unit/test_news_pipeline_market_data.py -q`
Expected: FAIL nos 4 testes. O primeiro modo é `AttributeError` no `patch` de `market_data_collector`, porque o nome ainda não existe no namespace do `news_pipeline`.

- [ ] **Step 3: Implementar — import**

Em `app/services/automation/news_pipeline.py`, adicionar junto aos imports de services (depois de `from app.services.sources.article_extractor import ArticleExtractor`):

```python
from app.services.ai.market_data_collector import market_data_collector
```

- [ ] **Step 4: Implementar — fetch uma vez por run**

Inserir imediatamente **antes** da linha `processed_count = 0` (que fica após o log de "Meta: ... teto de tentativas"):

```python
            # Dados de mercado: UMA coleta por run, reaproveitada por todas as
            # tentativas. Preço não muda em segundos e o run tenta até 3
            # notícias — buscar por artigo triplicaria 1,1s de rede pelo mesmo
            # número. Usa collect_snapshot e não collect_all: o contexto macro
            # do collect_all custa ~5,9s e é material de análise semanal.
            # Falha aqui não bloqueia: dado de mercado enriquece o artigo.
            market_data = None
            try:
                market_data = await market_data_collector.collect_snapshot()
                if market_data:
                    logger.info(f"Dados de mercado coletados ({len(market_data)} chars)")
                else:
                    logger.warning("Dados de mercado indisponíveis — seguindo sem eles")
            except Exception as e:
                logger.warning(f"Falha ao coletar dados de mercado: {e} (seguindo sem eles)")

            processed_count = 0
```

- [ ] **Step 5: Implementar — injeção no loop**

Dentro do loop, logo **após** o bloco que injeta o `full_text` (o `if full_text: source_news["full_text"] = ...`), inserir:

```python
                    if market_data:
                        source_news["market_data"] = market_data
```

- [ ] **Step 6: Rodar os testes**

Run: `python3 -m pytest tests/unit/test_news_pipeline_market_data.py -q`
Expected: PASS (4 testes)

- [ ] **Step 7: Patchar o collector nas fixtures de pipeline existentes**

As fixtures de `tests/unit/test_news_pipeline.py` e `tests/unit/test_news_pipeline_prefilter.py` não conhecem o `market_data_collector`. Sem patch, esses testes passariam a **bater na CoinGecko de verdade** — teste unitário não pode depender de rede externa, independentemente de ficar lento ou não: torna a suíte instável quando a API cai ou muda de latência.

Em `tests/unit/test_news_pipeline_prefilter.py`, adicionar ao `with` da fixture `m`, junto aos outros patches:

```python
         patch("app.services.automation.news_pipeline.market_data_collector") as mdc, \
```

e, no corpo da fixture, junto aos outros mocks:

```python
        mocks.market = mdc
        mdc.collect_snapshot = AsyncMock(return_value=None)
```

Em `tests/unit/test_news_pipeline.py`, adicionar uma fixture equivalente e usá-la nos testes que chamam `pipeline.run()`:

```python
@pytest.fixture(autouse=True)
def mock_market_data():
    """
    Neutraliza a coleta de dados de mercado.

    `autouse` de propósito: todo teste que roda o pipeline passa pelo fetch, e
    nenhum deles deve tocar a CoinGecko.
    """
    with patch("app.services.automation.news_pipeline.market_data_collector") as mdc:
        mdc.collect_snapshot = AsyncMock(return_value=None)
        yield mdc
```

Run: `python3 -m pytest tests/unit/test_news_pipeline.py tests/unit/test_news_pipeline_prefilter.py -q`
Expected: PASS (6 + 5 = 11 testes), e sem latência de rede.

- [ ] **Step 8: Commit**

```bash
git add app/services/automation/news_pipeline.py \
  tests/unit/test_news_pipeline_market_data.py \
  tests/unit/test_news_pipeline.py \
  tests/unit/test_news_pipeline_prefilter.py
git commit -m "feat(pipeline): coleta snapshot de mercado 1x por run e injeta na geracao"
```

---

### Task 4: Verificação final

**Files:** nenhum (verificação)

- [ ] **Step 1: Suíte completa**

Run: `python3 -m pytest tests/ -q 2>&1 | tail -3`
Expected: `394 passed, 0 failed, 0 errors` — baseline 376 mais 7 (collector) + 7 (prompt) + 4 (pipeline) = 18.

- [ ] **Step 2: Confirmar o ganho de tempo medido**

```bash
T=$(python3 -c "import secrets;print(secrets.token_urlsafe(32))"); \
SECRET_KEY=$T AUTOMATION_TOKEN=$T REVALIDATE_SECRET=$T \
DATABASE_URL="sqlite+aiosqlite:///:memory:" python3 -c "
import asyncio, time
from app.services.ai.market_data_collector import market_data_collector as m

async def main():
    t0 = time.monotonic(); snap = await m.collect_snapshot(); t_snap = time.monotonic() - t0
    t0 = time.monotonic(); full = await m.collect_all();      t_all  = time.monotonic() - t0
    print(f'  collect_snapshot: {t_snap:.1f}s | {len(snap or \"\")} chars')
    print(f'  collect_all:      {t_all:.1f}s | {len(full)} chars')
    print(f'  snapshot tem macro? {\"MACRO\" in (snap or \"\")}')
    print(f'  collect_all tem macro? {\"MACRO\" in full or \"Federal Reserve\" in full}')
asyncio.run(main())
" 2>&1 | grep "^  "
```
Expected: `collect_snapshot` em torno de 1s, `collect_all` em torno de 7s, snapshot sem macro e `collect_all` com macro.

- [ ] **Step 3: Confirmar o prompt montado de ponta a ponta**

```bash
T=$(python3 -c "import secrets;print(secrets.token_urlsafe(32))"); \
SECRET_KEY=$T AUTOMATION_TOKEN=$T REVALIDATE_SECRET=$T \
DATABASE_URL="sqlite+aiosqlite:///:memory:" python3 -c "
from app.services.ai.content_generator import ContentGenerator
g = ContentGenerator()
snap = '=== DADOS DE MERCADO ===\n\nPREÇOS: BTC US\$ 64,640.00 | 24h +0.80%'
p = g._build_article_prompt('Bitcoin sobe', 'corpo', 'CoinDesk', 'bitcoin', 'Bitcoin', None, market_data=snap)
print('  secao presente:', '<dados_de_mercado>' in p)
print('  numero presente:', '64,640.00' in p)
print('  ordem correta:', p.index('</dados_da_fonte>') < p.index('<dados_de_mercado>') < p.index('<tarefa>'))
print('  guardrail cita a secao:', '<dados_de_mercado>' in ContentGenerator.SYSTEM_PROMPT)
sem = g._build_article_prompt('t','c','s','bitcoin','Bitcoin', None)
print('  sem dado, sem secao:', '<dados_de_mercado>' not in sem)
" 2>&1 | grep "^  "
```
Expected: as cinco confirmações verdadeiras.

- [ ] **Step 4: Nota de deploy**

Nenhuma migration, nenhuma env var. `ddgs` (usado só pelo macro do `collect_all`) segue como dependência do relatório semanal, inalterada. O deploy é só o código.

**O que observar depois do deploy — e por que teste não cobre:** os testes provam que o dado chega ao prompt, não que o modelo o usa. Isso só aparece lendo artigo publicado: procure por preço e percentual concretos ("subiu 0,8%, a US$ 64.640") em lugar de "registrou alta". Se os artigos continuarem vagos, o guardrail não convenceu e o caminho é reforçar a instrução no `MARKET_DATA_BLOCK`, não injetar mais dado.

O outro sinal a acompanhar é o oposto: número enfiado onde não cabe — preço de Bitcoin numa notícia de regulação. Se aparecer, endurecer o "apenas se pertinente".

---

## Fora do escopo deste plano (deliberadamente adiado)

- **Contexto macro na notícia.** 5,9s e material de análise semanal. Se um dia fizer sentido para artigos de `regulacao`, é decisão própria com medição própria.
- **Fontes primárias (SEC, Ethereum Foundation).** Sub-projeto seguinte, via `APICollector`, que já é o ponto de extensão ligado ao aggregator.
- **Fontes brasileiras.** Precisa antes de resposta editorial: o pipeline existe para trazer notícia estrangeira ao leitor brasileiro com contexto local, e uma fonte que já publicou em português já fez isso. Some-se o dedup multilíngue (TF-IDF não casa PT com EN). A justificativa vem antes do trabalho técnico.
- **Filtro de artigos-panorama.** Medido: 1 em 95. Com o `source_count` corrigido, um digest de fonte única disputa só por recência contra ~78 outras notícias. Não se paga.
- **Cache de snapshot entre runs.** O cron roda várias vezes ao dia e preço muda; cachear entre runs entregaria dado velho. Uma vez por run é o ponto certo.
