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
