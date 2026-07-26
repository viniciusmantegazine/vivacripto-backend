"""
Unit tests for NewsPipeline.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.automation.news_pipeline import NewsPipeline


@pytest.fixture
def mock_aggregator():
    """Mock NewsAggregator."""
    with patch("app.services.automation.news_pipeline.NewsAggregator") as mock:
        aggregator = MagicMock()
        aggregator.collect_news = AsyncMock(return_value=[
            {
                "source": "CoinDesk",
                "source_language": "en",
                "title": "Bitcoin Reaches $100,000",
                "url": "https://coindesk.com/test",
                "description": "Bitcoin hits historic milestone.",
                "published_at": datetime.now(timezone.utc),
                "collected_at": datetime.now(timezone.utc),
            }
        ])
        mock.return_value = aggregator
        yield aggregator


@pytest.fixture
def mock_content_generator():
    """Mock ContentGenerator."""
    with patch("app.services.automation.news_pipeline.ContentGenerator") as mock:
        generator = MagicMock()
        generator.generate_article = AsyncMock(return_value={
            "title": "Bitcoin atinge US$ 100 mil pela primeira vez",
            "slug": "bitcoin-atinge-100-mil",
            "content_markdown": "# Bitcoin\n\nConteúdo do artigo aqui.",
            "content_html": "<h1>Bitcoin</h1><p>Conteúdo do artigo aqui.</p>",
            "excerpt": "Bitcoin atinge marco histórico.",
            "meta_title": "Bitcoin US$100k - VerticeCripto",
            "meta_description": "Bitcoin ultrapassa US$100 mil.",
        })
        mock.return_value = generator
        yield generator


@pytest.fixture
def mock_image_generator():
    """Mock ImageGenerator."""
    with patch("app.services.automation.news_pipeline.ImageGenerator") as mock:
        generator = MagicMock()
        generator.generate_and_upload_image = AsyncMock(
            return_value="https://res.cloudinary.com/test/image.jpg"
        )
        mock.return_value = generator
        yield generator


@pytest.fixture
def mock_quality_validator():
    """Mock QualityValidator."""
    with patch("app.services.automation.news_pipeline.QualityValidator") as mock:
        validator = MagicMock()
        validator.validate_article = MagicMock(return_value=(True, []))
        mock.return_value = validator
        yield validator


@pytest.fixture
def mock_article_publisher():
    """Mock ArticlePublisher."""
    with patch("app.services.automation.news_pipeline.ArticlePublisher") as mock:
        publisher = MagicMock()
        publisher.publish_article = AsyncMock(return_value="post-uuid-123")
        mock.return_value = publisher
        yield publisher


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


@pytest.fixture
def mock_crud_post():
    """Mock crud_post."""
    with patch("app.services.automation.news_pipeline.crud_post") as mock:
        mock.get_recent_posts = AsyncMock(return_value=[])
        # O pré-filtro anti-reprocessamento do pipeline awaita este método.
        # Sem AsyncMock explícito, o atributo vira MagicMock comum e o await
        # estoura com "object MagicMock can't be used in 'await' expression".
        mock.get_existing_source_urls = AsyncMock(return_value=set())
        yield mock


class TestNewsPipeline:
    """Test cases for NewsPipeline."""

    def test_pipeline_initialization(self):
        """Test that pipeline initializes correctly."""
        with patch.multiple(
            "app.services.automation.news_pipeline",
            NewsAggregator=MagicMock(),
            ContentGenerator=MagicMock(),
            ImageGenerator=MagicMock(),
            QualityValidator=MagicMock(),
            ArticlePublisher=MagicMock(),
        ):
            pipeline = NewsPipeline()
            assert pipeline.aggregator is not None
            assert pipeline.content_generator is not None
            assert pipeline.image_generator is not None
            assert pipeline.validator is not None
            assert pipeline.publisher is not None

    def test_pipeline_config_from_settings(self):
        """Test that pipeline uses settings for configuration."""
        assert NewsPipeline.MAX_POSTS_PER_DAY > 0
        assert NewsPipeline.POSTS_PER_EXECUTION > 0

    @pytest.mark.asyncio
    async def test_pipeline_respects_daily_limit(
        self,
        db_session,
        mock_aggregator,
        mock_content_generator,
        mock_image_generator,
        mock_quality_validator,
        mock_article_publisher,
    ):
        """Test that pipeline respects daily post limit."""
        # Mock that daily limit is already reached
        with patch("app.services.automation.news_pipeline.crud_post") as mock_crud:
            mock_crud.get_recent_posts = AsyncMock(
                return_value=[MagicMock() for _ in range(NewsPipeline.MAX_POSTS_PER_DAY)]
            )

            pipeline = NewsPipeline()
            report = await pipeline.run(db_session)

            assert report["status"] == "skipped"
            assert "Limite diário" in report["message"]

    @pytest.mark.asyncio
    async def test_pipeline_handles_no_news(
        self,
        db_session,
        mock_content_generator,
        mock_image_generator,
        mock_quality_validator,
        mock_article_publisher,
        mock_crud_post,
    ):
        """Test pipeline handles case when no news is collected."""
        with patch("app.services.automation.news_pipeline.NewsAggregator") as mock:
            aggregator = MagicMock()
            aggregator.collect_news = AsyncMock(return_value=[])
            mock.return_value = aggregator

            pipeline = NewsPipeline()
            report = await pipeline.run(db_session)

            assert report["status"] == "completed"
            # A chave do relatório é "collected" — "news_collected" existe só
            # dentro de metrics, não na raiz do report.
            assert report["collected"] == 0

    @pytest.mark.asyncio
    async def test_pipeline_handles_content_generation_failure(
        self,
        db_session,
        mock_aggregator,
        mock_image_generator,
        mock_quality_validator,
        mock_article_publisher,
        mock_crud_post,
    ):
        """Test pipeline handles content generation failure gracefully."""
        with patch("app.services.automation.news_pipeline.ContentGenerator") as mock:
            generator = MagicMock()
            generator.generate_article = AsyncMock(return_value=None)
            mock.return_value = generator

            pipeline = NewsPipeline()
            report = await pipeline.run(db_session)

            # Should complete but with 0 published
            assert report["status"] in ["completed", "partial"]

    @pytest.mark.asyncio
    async def test_pipeline_handles_validation_failure(
        self,
        db_session,
        mock_aggregator,
        mock_content_generator,
        mock_image_generator,
        mock_article_publisher,
        mock_crud_post,
    ):
        """Test pipeline handles validation failure gracefully."""
        with patch("app.services.automation.news_pipeline.QualityValidator") as mock:
            validator = MagicMock()
            validator.validate_article = MagicMock(
                return_value=(False, ["Content too short"])
            )
            mock.return_value = validator

            pipeline = NewsPipeline()
            report = await pipeline.run(db_session)

            # Should complete but with 0 published due to validation failure
            assert report["status"] in ["completed", "partial"]
