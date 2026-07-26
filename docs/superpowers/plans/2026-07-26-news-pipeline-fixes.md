# Correção de Fontes RSS + Achados da Revisão do Pipeline de Notícias — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir as fontes RSS quebradas (The Block 403, falta de User-Agent), eliminar os bugs encontrados na revisão do pipeline (fonte vazia no dedup, excerpt contaminado por heading, fallback de título em inglês), reduzir custo de LLM (pré-filtro por URL, loop até a meta) e melhorar a qualidade editorial (ranking por contagem de fontes, extração do texto completo da notícia original).

**Architecture:** As mudanças seguem a arquitetura em camadas existente: coleta em `app/services/sources/`, orquestração em `app/services/automation/news_pipeline.py`, geração em `app/services/ai/content_generator.py`, persistência via `app/crud/crud_post.py` + migration Alembic. Um novo serviço `ArticleExtractor` (trafilatura) busca o texto completo da matéria original apenas para as notícias selecionadas para processamento.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async, Alembic, httpx, feedparser, trafilatura (novo), pytest + pytest-asyncio.

---

## Contexto essencial para o executor

- **Rodar testes:** `python3 -m pytest tests/unit/... -q` (não existe venv no repo; `python` puro não existe, use `python3`).
- **Baseline de testes (2026-07-26):** os 4 testes de `tests/unit/test_news_pipeline.py` que usam a fixture `db_session` **já erram** antes deste plano (gotcha UUID/SQLite documentada em `ai_docs/gotchas.md` §6). Não é regressão sua. Todos os testes novos deste plano usam mocks (`MagicMock`/`AsyncMock`) em vez de `db_session`.
- **Datetimes:** o banco usa `TIMESTAMP WITHOUT TIME ZONE` → operações de banco usam `datetime.utcnow()` naive. Coleta RSS usa UTC-aware. Não misturar (ver `ai_docs/gotchas.md`).
- **Comentários de código em português** (convenção do projeto).
- **Verificado hoje via curl:** `https://www.theblock.co/rss.xml` → 403 (mesmo com UA de browser; remover). `https://bitcoinmagazine.com/feed` → 200 (substituto). Demais feeds atuais → 200.

---

### Task 1: RSSCollector — User-Agent, tratamento de HTTP status, troca The Block → Bitcoin Magazine, `collected_at` UTC

**Files:**
- Modify: `app/services/sources/rss_collector.py`
- Test: `tests/unit/test_rss_collector_fetch.py` (novo)
- Test: `tests/unit/test_rss_collector_date_filter.py` (adicionar 1 teste)

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/unit/test_rss_collector_fetch.py`:

```python
"""
Testes do _fetch_feed do RSSCollector: tratamento de HTTP status.

Regressão: The Block retornava 403 e caía no `except Exception` genérico,
sumindo silenciosamente da coleta. 4xx não deve ter retry (bloqueio/feed
removido); 5xx deve ser retentado.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.sources.rss_collector import RSSCollector


def _resp_with_status(status: int):
    """Response mock cujo raise_for_status levanta HTTPStatusError."""
    resp = MagicMock()
    resp.status_code = status
    err = httpx.HTTPStatusError(
        f"HTTP {status}", request=MagicMock(), response=resp
    )
    resp.raise_for_status = MagicMock(side_effect=err)
    return resp


def _client_ctx(response):
    """Context manager async fake para httpx.AsyncClient."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, client


@pytest.mark.asyncio
async def test_4xx_nao_tem_retry_e_retorna_none():
    collector = RSSCollector()
    ctx, client = _client_ctx(_resp_with_status(403))

    with patch(
        "app.services.sources.rss_collector.httpx.AsyncClient",
        return_value=ctx,
    ):
        result = await collector._fetch_feed("https://exemplo.com/rss")

    assert result is None
    assert client.get.await_count == 1  # sem retry para 4xx


@pytest.mark.asyncio
async def test_5xx_tem_retry():
    collector = RSSCollector()
    ctx, client = _client_ctx(_resp_with_status(500))

    with patch(
        "app.services.sources.rss_collector.httpx.AsyncClient",
        return_value=ctx,
    ):
        result = await collector._fetch_feed("https://exemplo.com/rss")

    assert result is None
    assert client.get.await_count == 2  # max_retries = 2


def test_the_block_removido_bitcoin_magazine_presente():
    """The Block responde 403 permanente (bloqueio anti-bot); substituído."""
    names = [f["name"] for f in RSSCollector.RSS_FEEDS]
    assert "The Block" not in names
    assert "Bitcoin Magazine" in names
```

Adicionar ao final de `tests/unit/test_rss_collector_date_filter.py`:

```python
@pytest.mark.asyncio
async def test_collected_at_utc_aware(monkeypatch):
    """collected_at deve ser UTC-aware (era datetime.now() local/naive)."""
    collector = RSSCollector()

    recent_struct = (datetime.now(timezone.utc) - timedelta(hours=1)).timetuple()
    feed = _feed([_entry("Noticia recente", published_struct=recent_struct)])

    async def fake_fetch(url):
        return feed

    monkeypatch.setattr(collector, "_fetch_feed", fake_fetch)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    items = await collector._collect_from_feed(
        {"name": "Test", "url": "x", "language": "en"}, cutoff
    )

    assert items[0]["collected_at"].tzinfo is not None
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

Run: `python3 -m pytest tests/unit/test_rss_collector_fetch.py tests/unit/test_rss_collector_date_filter.py -q`
Expected: FAIL — `test_4xx_nao_tem_retry_e_retorna_none` e `test_5xx_tem_retry` falham (o `except Exception` genérico engole o 4xx sem log claro e o comportamento de retry difere), `test_the_block_removido...` falha (The Block ainda na lista), `test_collected_at_utc_aware` falha (`tzinfo is None`).

- [ ] **Step 3: Implementar em `app/services/sources/rss_collector.py`**

3a. Substituir a entrada do The Block na lista `RSS_FEEDS` (linhas 37-41):

```python
        {
            "name": "Bitcoin Magazine",
            "url": "https://bitcoinmagazine.com/feed",
            "language": "en"
        },
```

3b. Adicionar constante de headers na classe (logo após `RSS_FEEDS`):

```python
    # Alguns feeds (CoinDesk, Bitcoin Magazine) retornam 403 para User-Agents
    # de bibliotecas HTTP. Usamos UA de browser real + Accept de RSS.
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        ),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
```

3c. Em `_fetch_feed`, passar headers no client e tratar `HTTPStatusError` antes do `except Exception`:

```python
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    limits=httpx.Limits(max_connections=5),
                    headers=self.HEADERS,
                ) as client:
```

Novo bloco except (inserir ANTES do `except Exception`, depois do `except httpx.TimeoutException`):

```python
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status >= 500 and attempt < max_retries - 1:
                    logger.warning(
                        f"HTTP {status} ao buscar {url} "
                        f"(tentativa {attempt + 1}/{max_retries})"
                    )
                    continue
                # 4xx não adianta repetir: feed removido ou bloqueio anti-bot.
                logger.error(
                    f"Feed {url} respondeu HTTP {status} — "
                    f"verificar se o feed mudou de URL ou bloqueia bots"
                )
                return None
```

3d. Trocar `collected_at` (linha 119):

```python
                        "collected_at": datetime.now(timezone.utc),
```

- [ ] **Step 4: Rodar os testes para confirmar que passam**

Run: `python3 -m pytest tests/unit/test_rss_collector_fetch.py tests/unit/test_rss_collector_date_filter.py -q`
Expected: PASS (todos)

- [ ] **Step 5: Verificação manual dos feeds reais**

```bash
python3 -c "
import asyncio
from app.services.sources.rss_collector import RSSCollector
items = asyncio.run(RSSCollector().collect_all(hours_back=24))
by_source = {}
for i in items:
    by_source[i['source']] = by_source.get(i['source'], 0) + 1
print(by_source)
"
```
Expected: dicionário com contagens > 0 para CoinDesk, Cointelegraph, CryptoSlate, Decrypt e Bitcoin Magazine (sem The Block). Se alguma fonte vier 0, verificar log de erro impresso.

- [ ] **Step 6: Commit**

```bash
git add app/services/sources/rss_collector.py tests/unit/test_rss_collector_fetch.py tests/unit/test_rss_collector_date_filter.py
git commit -m "fix(rss): UA de browser, tratamento de HTTP status, troca The Block (403) por Bitcoin Magazine, collected_at UTC"
```

---

### Task 2: RSSCollector — strip de HTML em título e descrição

**Files:**
- Modify: `app/services/sources/rss_collector.py`
- Test: `tests/unit/test_rss_collector_strip_html.py` (novo)

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/unit/test_rss_collector_strip_html.py`:

```python
"""
Testes do _strip_html: `entry.summary` de vários feeds vem com HTML,
que contaminava o prompt do LLM, o TF-IDF de dedup e o critério de
"descrição mais completa" (tags inflam o tamanho).
"""
from app.services.sources.rss_collector import _strip_html


def test_remove_tags():
    assert _strip_html("<p>Bitcoin <b>sobe</b> hoje</p>") == "Bitcoin sobe hoje"


def test_unescape_entidades():
    assert _strip_html("Fear &amp; Greed em alta") == "Fear & Greed em alta"


def test_colapsa_espacos_e_quebras():
    assert _strip_html("Bitcoin\n\n  sobe   hoje") == "Bitcoin sobe hoje"


def test_vazio_e_none():
    assert _strip_html("") == ""
    assert _strip_html(None) == ""
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `python3 -m pytest tests/unit/test_rss_collector_strip_html.py -q`
Expected: FAIL com `ImportError: cannot import name '_strip_html'`

- [ ] **Step 3: Implementar**

Em `app/services/sources/rss_collector.py`, adicionar aos imports do topo:

```python
import html as html_lib
import re
```

Adicionar função module-level (antes da classe `RSSCollector`):

```python
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text) -> str:
    """
    Remove tags HTML e entidades de texto vindo de feeds RSS.
    Vários feeds mandam `summary` com HTML embutido, que contaminaria o
    prompt do LLM e a comparação de similaridade do dedup de fontes.
    """
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()
```

Em `_collect_from_feed`, aplicar no dict de item (substituir as duas linhas):

```python
                        "title": _strip_html(entry.get("title", "")),
                        "description": _strip_html(entry.get("summary", "")),
```

(remover os `.strip()` antigos — `_strip_html` já faz)

- [ ] **Step 4: Rodar os testes**

Run: `python3 -m pytest tests/unit/test_rss_collector_strip_html.py tests/unit/test_rss_collector_date_filter.py -q`
Expected: PASS (o teste de date filter continua passando — summaries de teste não têm HTML)

- [ ] **Step 5: Commit**

```bash
git add app/services/sources/rss_collector.py tests/unit/test_rss_collector_strip_html.py
git commit -m "fix(rss): remove HTML de titulo/descricao das entradas de feed"
```

---

### Task 3: NewsAggregator — ranking por contagem de fontes + fix do `.index()`

**Files:**
- Modify: `app/services/sources/news_aggregator.py`
- Test: `tests/unit/test_news_aggregator_ranking.py` (novo)

Contexto: hoje o pipeline processa as notícias **na ordem dos feeds** (CoinDesk domina) — não existe seleção de "melhor notícia". A deduplicação de fontes descarta duplicatas, jogando fora o melhor sinal de relevância disponível: quantas fontes cobriram o mesmo tema. Esta task transforma o descarte em contagem (`source_count`) e ordena o resultado por (nº de fontes desc, recência desc).

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/unit/test_news_aggregator_ranking.py`:

```python
"""
Testes do ranking do NewsAggregator: a deduplicação de fontes deve CONTAR
quantas fontes cobriram cada tema (source_count) e ordenar por relevância
(mais fontes primeiro; empate -> mais recente).
"""
from datetime import datetime, timedelta, timezone

from app.services.sources.news_aggregator import NewsAggregator


class _StubResult:
    def __init__(self, score):
        self.score = score


class _StubEngine:
    """Considera duplicatas textos cujo primeiro token (marcador) coincide."""

    def calculate(self, a, b):
        return _StubResult(1.0 if a.split()[0] == b.split()[0] else 0.0)


def _news(source, title, description, hours_ago):
    return {
        "source": source,
        "title": title,
        "description": description,
        "published_at": datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        "url": f"https://{source.lower().replace(' ', '')}.com/x",
    }


def _aggregator_with_stub(monkeypatch):
    agg = NewsAggregator()
    monkeypatch.setattr(agg, "_get_similarity_engine", lambda: _StubEngine())
    return agg


def test_conta_fontes_e_mantem_descricao_mais_completa(monkeypatch):
    agg = _aggregator_with_stub(monkeypatch)
    items = [
        _news("CoinDesk", "TEMA1 bitcoin etf aprovado", "curta", 5),
        _news("Decrypt", "TEMA1 bitcoin etf liberado",
              "descrição bem mais longa e completa sobre o assunto", 4),
        _news("CryptoSlate", "TEMA2 ethereum upgrade", "outra coisa", 1),
    ]

    result = agg._deduplicate_source_news(items)

    assert len(result) == 2
    tema1 = next(n for n in result if n["title"].startswith("TEMA1"))
    assert tema1["source_count"] == 2
    assert set(tema1["covered_by"]) == {"CoinDesk", "Decrypt"}
    # Mantém a versão com descrição mais completa, sem perder a contagem
    assert tema1["description"].startswith("descrição bem mais longa")


def test_ordena_por_cobertura_depois_recencia(monkeypatch):
    agg = _aggregator_with_stub(monkeypatch)
    items = [
        _news("CryptoSlate", "TEMA2 ethereum upgrade", "single source", 1),  # mais recente
        _news("CoinDesk", "TEMA1 bitcoin etf", "desc a", 5),
        _news("Decrypt", "TEMA1 bitcoin etf tambem", "desc b", 4),
    ]

    result = agg._deduplicate_source_news(items)

    # TEMA1 tem 2 fontes -> vem primeiro, mesmo TEMA2 sendo mais recente
    assert result[0]["title"].startswith("TEMA1")
    assert result[0]["source_count"] == 2
    assert result[1]["source_count"] == 1


def test_sem_engine_retorna_tudo_com_count_1(monkeypatch):
    agg = NewsAggregator()
    monkeypatch.setattr(agg, "_get_similarity_engine", lambda: None)
    items = [
        _news("CoinDesk", "TEMA1 bitcoin", "a", 1),
        _news("Decrypt", "TEMA1 bitcoin igual", "b", 2),
    ]

    result = agg._deduplicate_source_news(items)

    assert len(result) == 2
    assert all(n["source_count"] == 1 for n in result)
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `python3 -m pytest tests/unit/test_news_aggregator_ranking.py -q`
Expected: FAIL com `KeyError: 'source_count'`

- [ ] **Step 3: Implementar**

Em `app/services/sources/news_aggregator.py`:

3a. Adicionar import no topo:

```python
from datetime import datetime, timezone
```

3b. Substituir `_deduplicate_source_news` inteiro por:

```python
    def _deduplicate_source_news(self, news_list: List[Dict]) -> List[Dict]:
        """
        Remove notícias duplicadas de diferentes fontes sobre o mesmo tema.

        Mantém a notícia com descrição mais completa e CONTA quantas fontes
        cobriram cada tema (source_count) — esse é o sinal de relevância
        usado para ordenar o resultado: notícia coberta por mais fontes é
        mais importante e vai para o topo da fila de processamento.
        Empate é resolvido por recência (published_at).

        Args:
            news_list: Lista de notícias coletadas

        Returns:
            Lista de notícias únicas, ordenada por relevância
        """
        for news in news_list:
            news["source_count"] = 1
            news["covered_by"] = [news.get("source", "")]

        if len(news_list) <= 1:
            return news_list

        engine = self._get_similarity_engine()
        if engine is None:
            logger.warning("Engine de similaridade não disponível, retornando todas as notícias")
            return news_list

        logger.info(f"Iniciando deduplicação de {len(news_list)} notícias...")
        unique_news = []
        duplicates_found = 0

        for i, news_i in enumerate(news_list):
            text_i = self._get_comparison_text(news_i)
            is_duplicate = False

            # Comparar com notícias já marcadas como únicas
            for j, news_j in enumerate(unique_news):
                text_j = self._get_comparison_text(news_j)

                try:
                    similarity = engine.calculate(text_i, text_j).score
                except Exception as e:
                    logger.warning(f"Erro ao calcular similaridade: {e}")
                    continue

                if similarity >= self.SOURCE_DEDUP_THRESHOLD:
                    duplicates_found += 1
                    logger.debug(
                        f"Duplicata #{duplicates_found}: {similarity:.0%} - "
                        f"[{news_i.get('source')}] vs [{news_j.get('source')}]"
                    )

                    # Mantém a descrição mais completa, acumulando contagem
                    # de fontes e lista de cobertura de ambas as versões.
                    desc_i = len(news_i.get('description', ''))
                    desc_j = len(news_j.get('description', ''))
                    keeper = news_i if desc_i > desc_j else news_j
                    keeper["source_count"] = news_j["source_count"] + 1
                    keeper["covered_by"] = news_j["covered_by"] + [news_i.get("source", "")]
                    unique_news[j] = keeper

                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_news.append(news_i)

            # Log de progresso a cada 10 notícias
            if (i + 1) % 10 == 0:
                logger.debug(f"Deduplicação: {i + 1}/{len(news_list)} processadas")

        # Ordena por relevância: mais fontes primeiro; empate -> mais recente.
        # published_at das fontes RSS é sempre UTC-aware; fallback aware para
        # itens sem data não quebrar a comparação.
        fallback_date = datetime.min.replace(tzinfo=timezone.utc)
        unique_news.sort(
            key=lambda n: (n["source_count"], n.get("published_at") or fallback_date),
            reverse=True,
        )

        logger.info(f"Deduplicação concluída: {duplicates_found} duplicatas encontradas")
        if unique_news:
            top = unique_news[0]
            logger.info(
                f"Top da fila: [{top['source_count']} fonte(s)] {top.get('title', '')[:60]}"
            )
        return unique_news
```

- [ ] **Step 4: Rodar os testes**

Run: `python3 -m pytest tests/unit/test_news_aggregator_ranking.py -q`
Expected: PASS (3 testes)

- [ ] **Step 5: Commit**

```bash
git add app/services/sources/news_aggregator.py tests/unit/test_news_aggregator_ranking.py
git commit -m "feat(aggregator): ranking por contagem de fontes na deduplicacao (melhor noticia primeiro)"
```

---

### Task 4: Persistir `source_url` no Post (migration + model + schema + publisher)

**Files:**
- Create: `alembic/versions/007_add_post_source_url.py`
- Modify: `app/db/models.py` (classe `Post`, após `canonical_url`)
- Modify: `app/schemas/post.py` (classe `PostCreate`)
- Modify: `app/services/automation/article_publisher.py` (`_prepare_post_data`)
- Test: `tests/unit/test_article_publisher_source_url.py` (novo)

Contexto: hoje a URL da notícia original não é persistida (`canonical_url=None` fixo). Sem ela não dá para pré-filtrar notícias já processadas (Task 8). `create_post` faz `Post(**post_in.model_dump(exclude={'tag_ids'}))`, então basta campo no schema `PostCreate` + coluna no model. O campo entra em `PostCreate` (não em `PostBase`) para NÃO expor a URL da fonte na API pública de leitura.

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/unit/test_article_publisher_source_url.py`:

```python
"""
Teste: _prepare_post_data deve propagar source_url do artigo para o
PostCreate — é o que permite o pré-filtro anti-reprocessamento do pipeline.
"""
from unittest.mock import MagicMock
from uuid import uuid4

from app.services.automation.article_publisher import ArticlePublisher


def test_prepare_post_data_persiste_source_url():
    publisher = ArticlePublisher(MagicMock())
    article = {
        "title": "Bitcoin atinge novo recorde histórico de preço em dólar",
        "slug": "bitcoin-recorde-historico",
        "content_markdown": "## Bitcoin\n\n" + "palavra de conteúdo " * 60,
        "excerpt": "Bitcoin atinge novo recorde em meio a forte demanda.",
        "meta_title": "Bitcoin bate recorde",
        "meta_description": "Bitcoin ultrapassa máxima histórica.",
        "source_url": "https://coindesk.com/noticia-original",
    }

    post_data = publisher._prepare_post_data(
        article, "<p>html</p>", None, uuid4()
    )

    assert post_data.source_url == "https://coindesk.com/noticia-original"
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `python3 -m pytest tests/unit/test_article_publisher_source_url.py -q`
Expected: FAIL — `PostCreate` não tem campo `source_url` (AttributeError ou ValidationError)

- [ ] **Step 3: Implementar**

3a. Criar `alembic/versions/007_add_post_source_url.py`:

```python
"""Add source_url to posts (pré-filtro de notícias já processadas)

Revision ID: 007
Revises: 006
Create Date: 2026-07-26

O pipeline gastava chamadas de LLM regenerando notícias já processadas em
runs anteriores (coleta olha 24h para trás; cron roda várias vezes ao dia).
Persistir a URL da notícia original permite pular essas notícias ANTES da
geração de conteúdo.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('posts', sa.Column('source_url', sa.Text(), nullable=True))
    op.create_index('ix_posts_source_url', 'posts', ['source_url'])


def downgrade() -> None:
    op.drop_index('ix_posts_source_url', table_name='posts')
    op.drop_column('posts', 'source_url')
```

3b. Em `app/db/models.py`, classe `Post`, logo após `canonical_url = Column(String(255))`:

```python
    # URL da notícia original nas fontes (pré-filtro anti-reprocessamento
    # do pipeline — ver crud_post.get_existing_source_urls)
    source_url = Column(Text, nullable=True, index=True)
```

3c. Em `app/schemas/post.py`, classe `PostCreate`, adicionar campo:

```python
class PostCreate(PostBase):
    """Post creation schema"""
    category_id: Optional[UUID] = None
    author_id: Optional[UUID] = None
    tag_ids: List[UUID] = Field(default_factory=list)
    status: PostStatus = "draft"
    published_at: Optional[datetime] = None
    # URL da notícia original (não exposta em PostBase/PostRead de propósito)
    source_url: Optional[str] = None
```

3d. Em `app/services/automation/article_publisher.py`, `_prepare_post_data`, no `return PostCreate(...)`, adicionar após `canonical_url=None,`:

```python
            source_url=article.get("source_url"),
```

- [ ] **Step 4: Rodar os testes**

Run: `python3 -m pytest tests/unit/test_article_publisher_source_url.py tests/unit/test_article_publisher.py -q`
Expected: PASS no teste novo; testes existentes do publisher no mesmo estado da baseline

- [ ] **Step 5: Validar a migration localmente (se houver banco local configurado)**

Run: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
Expected: sem erros. Se não houver Postgres local, pular — `start.sh` roda `alembic upgrade head` no deploy.

- [ ] **Step 6: Commit**

```bash
git add alembic/versions/007_add_post_source_url.py app/db/models.py app/schemas/post.py app/services/automation/article_publisher.py tests/unit/test_article_publisher_source_url.py
git commit -m "feat(db): persiste source_url do post (base do pre-filtro anti-reprocessamento)"
```

---

### Task 5: CRUD — `get_existing_source_urls`

**Files:**
- Modify: `app/crud/crud_post.py`
- Test: `tests/unit/test_crud_source_urls.py` (novo)

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/unit/test_crud_source_urls.py`:

```python
"""
Testes de get_existing_source_urls. Usa AsyncSession mockada — a fixture
db_session real quebra com UUID/SQLite (ai_docs/gotchas.md §6).
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.crud.crud_post import get_existing_source_urls


@pytest.mark.asyncio
async def test_lista_vazia_nao_consulta_banco():
    db = MagicMock()
    db.execute = AsyncMock()

    result = await get_existing_source_urls(db, [], datetime(2026, 1, 1))

    assert result == set()
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_retorna_apenas_urls_existentes():
    db = MagicMock()
    query_result = MagicMock()
    query_result.all.return_value = [
        ("https://a.com/1",),
        ("https://b.com/2",),
    ]
    db.execute = AsyncMock(return_value=query_result)

    result = await get_existing_source_urls(
        db,
        ["https://a.com/1", "https://b.com/2", "https://c.com/3"],
        datetime(2026, 1, 1),
    )

    assert result == {"https://a.com/1", "https://b.com/2"}
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `python3 -m pytest tests/unit/test_crud_source_urls.py -q`
Expected: FAIL com `ImportError: cannot import name 'get_existing_source_urls'`

- [ ] **Step 3: Implementar em `app/crud/crud_post.py`**

3a. Ajustar import de typing no topo do arquivo para incluir `Set` (manter os já existentes):

```python
from typing import List, Optional, Set
```

3b. Adicionar função module-level (após `get_recent_posts`):

```python
async def get_existing_source_urls(
    db: AsyncSession, urls: List[str], since: datetime
) -> Set[str]:
    """
    Retorna o subconjunto de `urls` que já foi usado como fonte de algum
    post criado desde `since`.

    Usado pelo pipeline para pular notícias já processadas ANTES de gastar
    chamadas de LLM (a coleta olha 24h para trás e o cron roda várias vezes
    ao dia — sem esse filtro, a mesma notícia é regenerada em cada run).
    """
    if not urls:
        return set()

    result = await db.execute(
        select(Post.source_url).where(
            Post.source_url.in_(urls),
            Post.created_at >= since,
        )
    )
    return {row[0] for row in result.all()}
```

3c. Adicionar wrapper na classe `CRUDPost` (após `get_recent_posts`):

```python
    async def get_existing_source_urls(
        self, db: AsyncSession, urls: List[str], since: datetime
    ) -> Set[str]:
        return await get_existing_source_urls(db, urls, since)
```

- [ ] **Step 4: Rodar os testes**

Run: `python3 -m pytest tests/unit/test_crud_source_urls.py tests/unit/test_crud_post.py -q`
Expected: teste novo PASS; `test_crud_post.py` no mesmo estado da baseline

- [ ] **Step 5: Commit**

```bash
git add app/crud/crud_post.py tests/unit/test_crud_source_urls.py
git commit -m "feat(crud): get_existing_source_urls para pre-filtro do pipeline"
```

---

### Task 6: ArticleExtractor — texto completo da notícia original (trafilatura)

**Files:**
- Create: `app/services/sources/article_extractor.py`
- Modify: `requirements.txt`
- Test: `tests/unit/test_article_extractor.py` (novo)

Contexto: o gerador de conteúdo recebe só o `summary` do RSS (1-2 frases em vários feeds) e precisa produzir 700+ palavras sem inventar dados — contradição que força enchimento/alucinação. Este serviço busca o HTML da matéria original e extrai o texto com trafilatura. Falha em qualquer etapa ⇒ retorna `None` e o pipeline segue só com o resumo (nunca bloqueia).

- [ ] **Step 1: Adicionar dependência e instalar**

Em `requirements.txt`, após a linha `beautifulsoup4>=4.12.0`:

```
trafilatura>=1.8.0  # Extração de texto de páginas de notícias (ArticleExtractor)
```

Run: `python3 -m pip install "trafilatura>=1.8.0"`
Expected: instalação sem erro. Verificar: `python3 -c "import trafilatura; print(trafilatura.__version__)"`

- [ ] **Step 2: Escrever os testes que falham**

Criar `tests/unit/test_article_extractor.py`:

```python
"""
Testes do ArticleExtractor: extração do texto completo da notícia original.
Toda falha deve resultar em None (o pipeline segue com o resumo do RSS).
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("trafilatura")

from app.services.sources.article_extractor import (
    MAX_TEXT_CHARS,
    ArticleExtractor,
)


def _with_fetch(monkeypatch, ext, html):
    async def fake_fetch(url):
        return html
    monkeypatch.setattr(ext, "_fetch", fake_fetch)


@pytest.mark.asyncio
async def test_url_vazia_retorna_none():
    ext = ArticleExtractor()
    assert await ext.extract("") is None


@pytest.mark.asyncio
async def test_fetch_falhou_retorna_none(monkeypatch):
    ext = ArticleExtractor()
    _with_fetch(monkeypatch, ext, None)
    assert await ext.extract("https://exemplo.com/noticia") is None


@pytest.mark.asyncio
async def test_extracao_curta_descartada(monkeypatch):
    """Texto < 200 chars = extração falhou (paywall, página de erro)."""
    ext = ArticleExtractor()
    _with_fetch(monkeypatch, ext, "<html><body>x</body></html>")
    monkeypatch.setattr(
        "app.services.sources.article_extractor.trafilatura.extract",
        lambda *a, **k: "texto curto demais",
    )
    assert await ext.extract("https://exemplo.com/noticia") is None


@pytest.mark.asyncio
async def test_texto_valido_e_truncamento(monkeypatch):
    ext = ArticleExtractor()
    _with_fetch(monkeypatch, ext, "<html><body>ok</body></html>")
    texto_longo = "palavra " * 3000  # ~24k chars
    monkeypatch.setattr(
        "app.services.sources.article_extractor.trafilatura.extract",
        lambda *a, **k: texto_longo,
    )

    result = await ext.extract("https://exemplo.com/noticia")

    assert result is not None
    assert len(result) == MAX_TEXT_CHARS
    assert result.startswith("palavra")
```

- [ ] **Step 3: Rodar para confirmar que falham**

Run: `python3 -m pytest tests/unit/test_article_extractor.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.services.sources.article_extractor'`

- [ ] **Step 4: Criar `app/services/sources/article_extractor.py`**

```python
"""
Article Extractor Service
Busca o HTML da notícia original e extrai o texto completo com trafilatura.

Motivação: o `summary` de RSS costuma ter 1-2 frases — insuficiente para o
ContentGenerator produzir 700+ palavras sem alucinar. Com o texto completo,
a geração fica ancorada em fatos reais da matéria original.

Qualquer falha (rede, paywall, extração vazia) retorna None e o pipeline
segue apenas com o resumo do RSS — este serviço nunca bloqueia o fluxo.
"""
import asyncio
from typing import Optional

import httpx
from loguru import logger

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    logger.warning(
        "trafilatura não instalado — geração usará apenas o resumo do RSS"
    )

# Extração abaixo disso = falhou (página de erro, paywall, consent wall)
MIN_TEXT_CHARS = 200
# Teto para limitar o tamanho do prompt de geração
MAX_TEXT_CHARS = 8000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
}


class ArticleExtractor:
    """Extrai o texto completo de uma página de notícia."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    async def extract(self, url: str) -> Optional[str]:
        """
        Busca a página e extrai o texto principal.

        Args:
            url: URL da notícia original

        Returns:
            Texto extraído (até MAX_TEXT_CHARS) ou None em qualquer falha
        """
        if not url or not TRAFILATURA_AVAILABLE:
            return None

        html = await self._fetch(url)
        if not html:
            return None

        # trafilatura.extract é síncrono e CPU-bound: fora do event loop
        text = await asyncio.to_thread(
            trafilatura.extract,
            html,
            include_comments=False,
            include_tables=False,
        )

        if not text:
            logger.warning(f"Extração de texto vazia para {url}")
            return None

        text = text.strip()
        if len(text) < MIN_TEXT_CHARS:
            logger.warning(
                f"Extração muito curta ({len(text)} chars) para {url} — descartada"
            )
            return None

        return text[:MAX_TEXT_CHARS]

    async def _fetch(self, url: str) -> Optional[str]:
        """Busca o HTML da página. Falha => None (nunca levanta exceção)."""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=HEADERS,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.warning(
                f"Falha ao buscar página da notícia {url}: {type(e).__name__}: {e}"
            )
            return None
```

- [ ] **Step 5: Rodar os testes**

Run: `python3 -m pytest tests/unit/test_article_extractor.py -q`
Expected: PASS (5 testes)

- [ ] **Step 6: Verificação manual com URL real**

```bash
python3 -c "
import asyncio
from app.services.sources.article_extractor import ArticleExtractor
t = asyncio.run(ArticleExtractor().extract('https://cointelegraph.com/news'))
print('chars:', len(t or ''))
print((t or 'FALHOU')[:300])
"
```
Expected: alguns milhares de chars de texto legível (ou, se essa URL específica falhar, testar com uma URL de matéria real recém-coletada pelo RSSCollector).

- [ ] **Step 7: Commit**

```bash
git add app/services/sources/article_extractor.py requirements.txt tests/unit/test_article_extractor.py
git commit -m "feat(sources): ArticleExtractor busca texto completo da noticia original (trafilatura)"
```

---

### Task 7: ContentGenerator — usa texto completo, excerpt sem heading, descarta artigo sem título SEO

**Files:**
- Modify: `app/services/ai/content_generator.py`
- Test: `tests/unit/test_content_generator_article.py` (novo)
- Test: `tests/unit/test_content_generator_excerpt.py` (novo)

Três correções da revisão:
1. `generate_article` deve preferir `full_text` (do ArticleExtractor) sobre `description` (resumo RSS).
2. `_generate_excerpt` vaza o texto do primeiro H2 no excerpt (só remove os caracteres `##`, não a linha).
3. Se `_generate_seo_title` falhar, `"title": seo_title or title` publica o post com o **título original em inglês** — deve descartar o artigo.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/unit/test_content_generator_article.py`:

```python
"""
Testes do generate_article: preferência por full_text e descarte de artigo
quando o título SEO não pôde ser gerado (o fallback seria o título original
em INGLÊS do feed — inaceitável em portal PT-BR).
"""
import pytest

from app.services.ai.content_generator import ContentGenerator

VALID_CONTENT = (
    "## Bitcoin em alta\n\nO Bitcoin subiu nesta semana. "
    + "Contexto adicional do mercado de criptomoedas no Brasil. " * 40
)


def _news(**extra):
    news = {
        "title": "Bitcoin Hits New All-Time High",
        "description": "resumo curto do RSS",
        "source": "CoinDesk",
        "url": "https://coindesk.com/noticia",
    }
    news.update(extra)
    return news


@pytest.mark.asyncio
async def test_prefere_full_text_sobre_description(monkeypatch):
    gen = ContentGenerator()
    captured = {}

    async def fake_content(title, description, source, category="default",
                           correction_hint=None):
        captured["description"] = description
        return VALID_CONTENT

    async def fake_title(content, keyword="criptomoeda"):
        return "Bitcoin Sobe Forte Após Aprovação de ETF nos EUA"

    async def fake_meta(content, title="", keyword="criptomoeda"):
        return "Meta description de teste com tamanho adequado para SEO e CTR."

    monkeypatch.setattr(gen, "_generate_content", fake_content)
    monkeypatch.setattr(gen, "_generate_seo_title", fake_title)
    monkeypatch.setattr(gen, "_generate_meta_description", fake_meta)

    article = await gen.generate_article(
        _news(full_text="texto completo extraído da matéria original")
    )

    assert article is not None
    assert captured["description"] == "texto completo extraído da matéria original"


@pytest.mark.asyncio
async def test_sem_full_text_usa_description(monkeypatch):
    gen = ContentGenerator()
    captured = {}

    async def fake_content(title, description, source, category="default",
                           correction_hint=None):
        captured["description"] = description
        return VALID_CONTENT

    async def fake_title(content, keyword="criptomoeda"):
        return "Bitcoin Sobe Forte Após Aprovação de ETF nos EUA"

    async def fake_meta(content, title="", keyword="criptomoeda"):
        return "Meta description de teste com tamanho adequado para SEO e CTR."

    monkeypatch.setattr(gen, "_generate_content", fake_content)
    monkeypatch.setattr(gen, "_generate_seo_title", fake_title)
    monkeypatch.setattr(gen, "_generate_meta_description", fake_meta)

    article = await gen.generate_article(_news())

    assert article is not None
    assert captured["description"] == "resumo curto do RSS"


@pytest.mark.asyncio
async def test_descarta_artigo_sem_titulo_seo(monkeypatch):
    """Sem título SEO, o fallback seria o título em inglês — descartar."""
    gen = ContentGenerator()

    async def fake_content(*args, **kwargs):
        return VALID_CONTENT

    async def fake_title(*args, **kwargs):
        return None

    monkeypatch.setattr(gen, "_generate_content", fake_content)
    monkeypatch.setattr(gen, "_generate_seo_title", fake_title)

    assert await gen.generate_article(_news()) is None
```

Criar `tests/unit/test_content_generator_excerpt.py`:

```python
"""
Testes do _generate_excerpt: o texto do primeiro H2 vazava no excerpt
(o código antigo só removia os caracteres '##', não a linha de heading).
"""
import pytest

from app.services.ai.content_generator import ContentGenerator


@pytest.mark.asyncio
async def test_excerpt_ignora_linha_de_heading():
    gen = ContentGenerator()
    content = (
        "## Manchete Interna do Artigo\n\n"
        "O Bitcoin subiu nesta terça-feira. Investidores acompanham o movimento. "
        "Uma terceira frase que não deve entrar."
    )

    excerpt = await gen._generate_excerpt(content)

    assert "Manchete" not in excerpt
    assert excerpt.startswith("O Bitcoin subiu")


@pytest.mark.asyncio
async def test_excerpt_remove_negrito_e_limita_150():
    gen = ContentGenerator()
    content = "## Titulo\n\n**Bitcoin** " + ("palavra " * 40) + ". Segunda frase."

    excerpt = await gen._generate_excerpt(content)

    assert "**" not in excerpt
    assert len(excerpt) <= 150
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `python3 -m pytest tests/unit/test_content_generator_article.py tests/unit/test_content_generator_excerpt.py -q`
Expected: FAIL — `test_prefere_full_text...` (usa description), `test_descarta_artigo_sem_titulo_seo` (retorna artigo com título em inglês), `test_excerpt_ignora_linha_de_heading` ("Manchete" presente)

- [ ] **Step 3: Implementar em `app/services/ai/content_generator.py`**

3a. Em `generate_article`, substituir a linha `description = source_news.get("description", "")` por:

```python
            # Preferir o texto completo extraído da matéria original
            # (ArticleExtractor); o resumo do RSS é o fallback — com 1-2
            # frases o LLM não tem material para 700+ palavras sem alucinar.
            description = source_news.get("full_text") or source_news.get("description", "")
```

3b. Em `generate_article`, logo após `seo_title = await self._generate_seo_title(content, keyword)`, adicionar:

```python
            if not seo_title:
                # Sem título SEO não publicamos: o fallback seria o título
                # original em INGLÊS do feed — inaceitável num portal PT-BR.
                logger.error("Falha ao gerar título SEO — artigo descartado")
                return None
```

3c. Ainda em `generate_article`, simplificar os usos agora que `seo_title` é garantido:

```python
            # Gerar slug
            slug = slugify(seo_title)

            article = {
                "title": seo_title,
```

(trocar `slugify(seo_title or title)` e `"title": seo_title or title,`; `"meta_title": seo_title,` já está correto)

3d. Substituir `_generate_excerpt` inteiro por:

```python
    async def _generate_excerpt(self, content: str) -> Optional[str]:
        """
        Gera excerpt a partir do primeiro parágrafo de TEXTO do artigo.
        Linhas de heading são ignoradas — sem isso o texto do primeiro H2
        vazava colado na primeira frase do excerpt.
        """
        paragraphs = [
            line.strip()
            for line in content.split('\n')
            if line.strip() and not line.strip().startswith('#')
        ]
        text = ' '.join(paragraphs).replace('**', '').replace('*', '')

        sentences = text.split('. ')[:2]
        excerpt = '. '.join(sentences)

        # Limitar a 150 caracteres
        if len(excerpt) > 150:
            excerpt = excerpt[:147] + "..."

        return excerpt
```

- [ ] **Step 4: Rodar os testes**

Run: `python3 -m pytest tests/unit/test_content_generator_article.py tests/unit/test_content_generator_excerpt.py tests/unit/test_content_generator_sanitize.py -q`
Expected: PASS (incluindo os testes de sanitize existentes, que não são afetados)

- [ ] **Step 5: Commit**

```bash
git add app/services/ai/content_generator.py tests/unit/test_content_generator_article.py tests/unit/test_content_generator_excerpt.py
git commit -m "fix(ai): gera a partir do texto completo, excerpt sem heading, descarta artigo sem titulo SEO"
```

---

### Task 8: NewsPipeline — fix `fonte`, pré-filtro por URL, loop até a meta, integração do extractor

**Files:**
- Modify: `app/services/automation/news_pipeline.py`
- Test: `tests/unit/test_news_pipeline_prefilter.py` (novo)

Quatro mudanças no orquestrador:
1. **Bug:** `fonte=source_news.get("source_name", "")` — a chave no dict coletado é `"source"`; hoje `fonte` chega sempre vazia no dedup (e o post atualizado ganha `"[Atualização - ]"` sem nome).
2. **Pré-filtro por URL:** antes de gerar, remover da fila notícias cuja URL já virou post nos últimos 7 dias (usa `get_existing_source_urls` da Task 5). Nota de comportamento intencional: re-runs da MESMA notícia deixam de disparar `UPDATE_EXISTING` — cobertura nova do mesmo tema por OUTRA fonte (URL diferente) continua atualizando via dedup.
3. **Loop até a meta:** hoje o slice `news_items[:posts_to_process]` é fixo — se a notícia 1 falha, a 4 nunca é tentada. Passar a iterar a fila (já ordenada por relevância pela Task 3) até atingir a meta, com teto de tentativas (`target * 3`) para limitar custo de LLM.
4. **Extractor:** buscar texto completo (Task 6) apenas para as notícias efetivamente tentadas.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/unit/test_news_pipeline_prefilter.py`:

```python
"""
Testes do NewsPipeline: pré-filtro de URL, loop até a meta, fix do campo
fonte e integração do ArticleExtractor.

Usa mocks em vez de db_session (gotcha UUID/SQLite — ai_docs/gotchas.md §6).
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.deduplication import ActionType


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
    "excerpt": "Bitcoin atinge marco histórico em meio a forte demanda.",
    "meta_title": "Bitcoin US$100k",
    "meta_description": "Bitcoin ultrapassa US$100 mil pela primeira vez.",
    "source_url": "https://coindesk.com/a",
    "source_name": "CoinDesk",
    "category": "bitcoin",
}


@pytest.fixture
def m():
    """Patcha todas as dependências do pipeline e expõe os mocks."""
    with patch("app.services.automation.news_pipeline.NewsAggregator") as agg_cls, \
         patch("app.services.automation.news_pipeline.ContentGenerator") as gen_cls, \
         patch("app.services.automation.news_pipeline.ImageGenerator") as img_cls, \
         patch("app.services.automation.news_pipeline.QualityValidator") as val_cls, \
         patch("app.services.automation.news_pipeline.ArticlePublisher") as pub_cls, \
         patch("app.services.automation.news_pipeline.CategoryClassifier") as cat_cls, \
         patch("app.services.automation.news_pipeline.ArticleExtractor") as ext_cls, \
         patch("app.services.automation.news_pipeline.DuplicateDetector") as det_cls, \
         patch("app.services.automation.news_pipeline.PostRepositoryImpl"), \
         patch("app.services.automation.news_pipeline.crud_post") as crud, \
         patch("app.services.automation.news_pipeline.engine") as eng:

        mocks = MagicMock()

        mocks.aggregator = MagicMock()
        mocks.aggregator.collect_news = AsyncMock(return_value=[])
        agg_cls.return_value = mocks.aggregator

        mocks.generator = MagicMock()
        mocks.generator.generate_article = AsyncMock(return_value=dict(ARTICLE))
        gen_cls.return_value = mocks.generator

        img_cls.return_value = MagicMock()

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
async def test_prefiltro_pula_urls_ja_processadas(m):
    from app.services.automation.news_pipeline import NewsPipeline

    m.aggregator.collect_news.return_value = [
        _news("CoinDesk", "Noticia A", "https://a.com/1"),
        _news("Decrypt", "Noticia B", "https://b.com/2"),
    ]
    m.crud.get_existing_source_urls.return_value = {"https://a.com/1"}

    report = await NewsPipeline().run(MagicMock())

    assert report["skipped_already_processed"] == 1
    # A primeira notícia tentada deve ser a B (a A foi filtrada)
    called_news = m.generator.generate_article.await_args_list[0][0][0]
    assert called_news["url"] == "https://b.com/2"


@pytest.mark.asyncio
async def test_todas_filtradas_encerra_sem_gerar(m):
    from app.services.automation.news_pipeline import NewsPipeline

    m.aggregator.collect_news.return_value = [
        _news("CoinDesk", "Noticia A", "https://a.com/1"),
    ]
    m.crud.get_existing_source_urls.return_value = {"https://a.com/1"}

    report = await NewsPipeline().run(MagicMock())

    assert report["status"] == "completed"
    m.generator.generate_article.assert_not_awaited()


@pytest.mark.asyncio
async def test_falha_de_geracao_nao_consome_meta(m):
    """Se a notícia 1 falha, a notícia 2 deve ser tentada no mesmo run."""
    from app.services.automation.news_pipeline import NewsPipeline

    m.aggregator.collect_news.return_value = [
        _news("CoinDesk", "Noticia A", "https://a.com/1"),
        _news("Decrypt", "Noticia B", "https://b.com/2"),
    ]
    m.generator.generate_article.side_effect = [None, dict(ARTICLE)]

    report = await NewsPipeline().run(MagicMock())

    assert report["failed"] == 1
    assert report["published"] == 1


@pytest.mark.asyncio
async def test_fonte_vem_da_chave_source(m):
    """Regressão: fonte lia 'source_name' (inexistente) e chegava vazia."""
    from app.services.automation.news_pipeline import NewsPipeline

    m.aggregator.collect_news.return_value = [
        _news("CoinDesk", "Noticia A", "https://a.com/1"),
    ]

    await NewsPipeline().run(MagicMock())

    assignment = m.detector.check_duplicate.await_args[0][0]
    assert assignment.fonte == "CoinDesk"


@pytest.mark.asyncio
async def test_texto_completo_vai_para_o_gerador(m):
    from app.services.automation.news_pipeline import NewsPipeline

    m.aggregator.collect_news.return_value = [
        _news("CoinDesk", "Noticia A", "https://a.com/1"),
    ]
    m.extractor.extract.return_value = "texto completo da matéria original " * 20

    await NewsPipeline().run(MagicMock())

    called_news = m.generator.generate_article.await_args_list[0][0][0]
    assert called_news["full_text"].startswith("texto completo")
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `python3 -m pytest tests/unit/test_news_pipeline_prefilter.py -q`
Expected: FAIL — `ArticleExtractor` não existe no namespace do pipeline (AttributeError no patch); após ver isso, os demais falhariam por `skipped_already_processed` ausente, fonte vazia etc.

- [ ] **Step 3: Implementar em `app/services/automation/news_pipeline.py`**

3a. Imports — trocar a linha `from datetime import datetime, timezone` por:

```python
from datetime import datetime, timedelta, timezone
```

e adicionar junto aos imports de services:

```python
from app.services.sources.article_extractor import ArticleExtractor
```

3b. No `__init__`, adicionar:

```python
        self.article_extractor = ArticleExtractor()
```

3c. Logo APÓS o bloco de coleta (depois de `report["collected"] = len(news_items)` e do `except` correspondente) e ANTES do check `if not news_items:`, inserir o pré-filtro:

```python
            # Pré-filtro: descarta notícias cuja URL já virou post nos
            # últimos 7 dias. A coleta olha 24h para trás e o cron roda
            # várias vezes ao dia — sem isso, a mesma notícia era regerada
            # (4 chamadas de LLM) em cada run só para o dedup descartá-la.
            if news_items:
                urls = [n["url"] for n in news_items if n.get("url")]
                # naive p/ TIMESTAMP WITHOUT TIME ZONE (ver ai_docs/gotchas.md)
                since = datetime.utcnow() - timedelta(days=7)
                seen_urls = await crud_post.get_existing_source_urls(db, urls, since)
                if seen_urls:
                    news_items = [
                        n for n in news_items if n.get("url") not in seen_urls
                    ]
                    report["skipped_already_processed"] = len(seen_urls)
                    logger.info(
                        f"Pré-filtro de URL: {len(seen_urls)} notícia(s) já "
                        f"processada(s) removidas da fila"
                    )
```

O check existente `if not news_items:` passa a cobrir também o caso "todas filtradas" — ajustar a mensagem:

```python
            if not news_items:
                report["status"] = "completed"
                report["message"] = "Nenhuma notícia nova para processar"
```

3d. Substituir o bloco do slice + loop (de `remaining_slots = ...` até a linha `for i, source_news in enumerate(news_items[:posts_to_process], 1):` inclusive) por:

```python
            remaining_slots = await self._get_remaining_daily_slots(db)
            target = min(self.POSTS_PER_EXECUTION, remaining_slots)
            # Falhas e duplicatas não consomem a meta: tentamos as próximas
            # da fila (ordenada por relevância) até atingir o alvo, com teto
            # de tentativas para limitar custo de LLM em runs problemáticos.
            max_attempts = min(len(news_items), target * 3)
            logger.info(
                f"Meta: {target} post(s) | fila: {len(news_items)} | "
                f"teto de tentativas: {max_attempts}"
            )

            processed_count = 0
            attempts = 0

            for source_news in news_items:
                if processed_count >= target or attempts >= max_attempts:
                    break
                attempts += 1
                try:
                    logger.info(
                        f"\n--- Tentativa {attempts}/{max_attempts} "
                        f"(meta {processed_count}/{target}) ---"
                    )
                    logger.info(f"Título: {source_news.get('title', '')[:80]}...")
```

(o corpo interno do `try` continua o mesmo, com as mudanças 3e-3g abaixo; atenção à indentação — o `for` perde o `enumerate` e a variável `i`)

3e. Dentro do loop, logo após o log do título e ANTES da pré-classificação de categoria, inserir a extração de texto completo:

```python
                    # Texto completo da matéria original: o resumo de RSS tem
                    # 1-2 frases — insuficiente para 700+ palavras sem
                    # alucinação. Falha => segue só com o resumo.
                    full_text = await self.article_extractor.extract(
                        source_news.get("url", "")
                    )
                    if full_text:
                        source_news["full_text"] = full_text
                        logger.info(f"Texto completo extraído ({len(full_text)} chars)")
```

3f. Na pré-classificação, aproveitar o texto completo como conteúdo:

```python
                    category = self.category_classifier.classify(
                        title, description, source_news.get("full_text", "")
                    )
```

3g. Corrigir o bug da fonte no `NewsAssignment`:

```python
                        fonte=source_news.get("source", ""),
```

- [ ] **Step 4: Rodar os testes**

Run: `python3 -m pytest tests/unit/test_news_pipeline_prefilter.py -q`
Expected: PASS (5 testes)

- [ ] **Step 5: Conferir que a suite não regrediu vs baseline**

Run: `python3 -m pytest tests/unit/ -q 2>&1 | tail -5`
Expected: mesmos 4 ERRORs pré-existentes de `test_news_pipeline.py` (fixture `db_session`), zero FAILs novos.

- [ ] **Step 6: Commit**

```bash
git add app/services/automation/news_pipeline.py tests/unit/test_news_pipeline_prefilter.py
git commit -m "feat(pipeline): pre-filtro por URL, loop ate a meta, texto completo na geracao e fix da fonte no dedup"
```

---

### Task 9: Verificação final

**Files:** nenhum (verificação)

- [ ] **Step 1: Suite completa**

Run: `python3 -m pytest tests/ -q 2>&1 | tail -10`
Expected: todos os testes novos passando; únicos ERRORs são os pré-existentes por `db_session`/SQLite (baseline: 4 em `test_news_pipeline.py`; conferir que não aumentou).

- [ ] **Step 2: Smoke do fluxo de coleta + ranking real (com rede)**

```bash
python3 -c "
import asyncio
from app.services.sources.news_aggregator import NewsAggregator
items = asyncio.run(NewsAggregator().collect_news(hours_back=24))
print(f'{len(items)} notícias únicas')
for n in items[:8]:
    print(f\"  [{n['source_count']} fonte(s)] {n['source']}: {n['title'][:70]}\")
"
```
Expected: lista ordenada com notícias multi-fonte no topo (`source_count` >= 2 nas primeiras posições quando houver tema coberto por várias fontes). Sem The Block; com Bitcoin Magazine.

- [ ] **Step 3: Smoke do extractor com URL real da coleta**

Pegar uma `url` do output do Step 2 e rodar:

```bash
python3 -c "
import asyncio
from app.services.sources.article_extractor import ArticleExtractor
t = asyncio.run(ArticleExtractor().extract('<URL_DO_STEP_2>'))
print('chars:', len(t or 0) if t else 'FALHOU')
print((t or '')[:400])
"
```
Expected: texto legível da matéria (>200 chars). Se uma fonte específica bloquear, testar com URL de outra fonte — o fallback para o resumo é comportamento aceito.

- [ ] **Step 4: Lembrete de deploy**

A migration 007 roda automaticamente no deploy (`start.sh` → `alembic upgrade head`). Nenhuma env var nova. `requirements.txt` ganhou `trafilatura` — o build do Railway instala sozinho.

---

## Fora do escopo deste plano (deliberadamente adiado)

- **Consolidar as 4 chamadas de LLM em 1** (conteúdo + título + meta em um JSON estruturado) — refactor maior do ContentGenerator; fazer depois que este plano estabilizar.
- **Novas fontes** (CoinGecko para preços ao vivo, feeds de fontes primárias SEC/Ethereum Foundation, fontes brasileiras) — discutido e aprovado em conceito, mas depende de decisões próprias (dedup multilíngue) e merece plano separado.
- **`temperature` nas chamadas Gemini de título/meta** e **word-boundary na remoção de nomes de veículos** — melhorias menores agrupáveis no refactor acima.
