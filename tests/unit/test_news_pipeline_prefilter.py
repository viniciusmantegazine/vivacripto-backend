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
