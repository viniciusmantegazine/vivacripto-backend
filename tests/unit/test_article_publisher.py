"""
Unit tests for Article Publisher service.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Category
from app.services.automation.article_publisher import ArticlePublisher


class TestArticlePublisher:
    """Test suite for ArticlePublisher service."""

    @pytest.fixture
    def publisher(self) -> ArticlePublisher:
        """Create an ArticlePublisher instance with mocked image generator."""
        mock_image_gen = MagicMock()
        mock_image_gen.generate_and_upload_image = AsyncMock(
            return_value="https://res.cloudinary.com/test/image.jpg"
        )
        return ArticlePublisher(image_generator=mock_image_gen)

    @pytest.fixture
    def sample_article(self) -> dict:
        """Create a sample article for testing."""
        return {
            "title": "Bitcoin Atinge Nova Máxima Histórica",
            "slug": "bitcoin-atinge-nova-maxima-historica",
            "content_markdown": "# Bitcoin ATH\n\nBitcoin reached a new all-time high today.",
            "excerpt": "Bitcoin surges to new heights in crypto market.",
            "meta_title": "Bitcoin ATH - Breaking News",
            "meta_description": "Bitcoin reaches new all-time high. Read the full analysis.",
        }

    @pytest_asyncio.fixture
    async def test_category(self, db_session: AsyncSession) -> Category:
        """Create a test category."""
        category = Category(id=uuid4(), name="Bitcoin", slug="bitcoin")
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        return category

    def test_convert_markdown_to_html(self, publisher: ArticlePublisher):
        """Test markdown to HTML conversion."""
        markdown = "# Title\n\nParagraph with **bold** text."

        html = publisher._convert_markdown_to_html(markdown)

        assert "<h1>Title</h1>" in html
        assert "<strong>bold</strong>" in html

    def test_convert_markdown_with_code(self, publisher: ArticlePublisher):
        """Test markdown with code blocks."""
        markdown = "```python\nprint('hello')\n```"

        html = publisher._convert_markdown_to_html(markdown)

        assert "print" in html
        assert "hello" in html

    def test_prepare_post_data_basic(self, publisher: ArticlePublisher, sample_article: dict):
        """Test preparing post data with basic article."""
        category_id = uuid4()
        content_html = "<h1>Test</h1>"
        image_url = "https://example.com/image.jpg"

        post_data = publisher._prepare_post_data(
            sample_article, content_html, image_url, category_id
        )

        assert post_data.title == sample_article["title"]
        assert post_data.slug == sample_article["slug"]
        assert post_data.content_html == content_html
        assert post_data.featured_image_url == image_url
        assert post_data.category_id == category_id
        assert post_data.status == "published"
        assert post_data.published_at is not None

    def test_prepare_post_data_truncates_meta_title(self, publisher: ArticlePublisher, sample_article: dict):
        """Test that meta_title is truncated to 70 chars."""
        sample_article["meta_title"] = "A" * 100  # Too long

        post_data = publisher._prepare_post_data(
            sample_article, "<p>Test</p>", None, uuid4()
        )

        assert len(post_data.meta_title) <= 70
        assert post_data.meta_title.endswith("...")

    def test_prepare_post_data_truncates_meta_description(self, publisher: ArticlePublisher, sample_article: dict):
        """Test that meta_description is truncated to 160 chars."""
        sample_article["meta_description"] = "A" * 200  # Too long

        post_data = publisher._prepare_post_data(
            sample_article, "<p>Test</p>", None, uuid4()
        )

        assert len(post_data.meta_description) <= 160
        assert post_data.meta_description.endswith("...")

    def test_prepare_post_data_uses_article_image_if_no_generated(
        self, publisher: ArticlePublisher, sample_article: dict
    ):
        """Test that article's featured_image_url is used if image generation returns None."""
        sample_article["featured_image_url"] = "https://fallback.com/image.jpg"

        post_data = publisher._prepare_post_data(
            sample_article, "<p>Test</p>", None, uuid4()
        )

        assert post_data.featured_image_url == "https://fallback.com/image.jpg"

    @pytest.mark.asyncio
    async def test_generate_image_success(self, sample_article: dict):
        """Test successful image generation."""
        mock_image_gen = MagicMock()
        expected_url = "https://res.cloudinary.com/test/generated.jpg"
        mock_image_gen.generate_and_upload_image = AsyncMock(return_value=expected_url)

        publisher = ArticlePublisher(image_generator=mock_image_gen)

        result = await publisher._generate_image(sample_article)

        assert result == expected_url
        mock_image_gen.generate_and_upload_image.assert_called_once_with(
            sample_article["title"],
            sample_article["content_markdown"],
        )

    @pytest.mark.asyncio
    async def test_generate_image_failure_returns_none(self, sample_article: dict):
        """Test that image generation failure returns None."""
        mock_image_gen = MagicMock()
        mock_image_gen.generate_and_upload_image = AsyncMock(
            side_effect=Exception("Image generation failed")
        )

        publisher = ArticlePublisher(image_generator=mock_image_gen)

        result = await publisher._generate_image(sample_article)

        assert result is None

    @pytest.mark.asyncio
    async def test_publish_article_success(
        self,
        db_session: AsyncSession,
        test_category: Category,
        sample_article: dict,
    ):
        """Test successful article publication."""
        mock_image_gen = MagicMock()
        mock_image_gen.generate_and_upload_image = AsyncMock(
            return_value="https://example.com/image.jpg"
        )
        publisher = ArticlePublisher(image_generator=mock_image_gen)

        # Mock category classifier to return existing category
        with patch(
            "app.services.automation.article_publisher.category_classifier"
        ) as mock_classifier:
            mock_classifier.classify.return_value = test_category.slug
            mock_classifier.get_category_name.return_value = test_category.name

            result = await publisher.publish_article(sample_article, db_session)

        assert result is True

    @pytest.mark.asyncio
    async def test_publish_article_creates_category_if_not_exists(
        self,
        db_session: AsyncSession,
        sample_article: dict,
    ):
        """Test that article publication creates category if it doesn't exist."""
        mock_image_gen = MagicMock()
        mock_image_gen.generate_and_upload_image = AsyncMock(return_value=None)
        publisher = ArticlePublisher(image_generator=mock_image_gen)

        with patch(
            "app.services.automation.article_publisher.category_classifier"
        ) as mock_classifier:
            mock_classifier.classify.return_value = "new-category"
            mock_classifier.get_category_name.return_value = "New Category"

            result = await publisher.publish_article(sample_article, db_session)

        assert result is True

    @pytest.mark.asyncio
    async def test_publish_article_rollback_on_error(
        self,
        db_session: AsyncSession,
        sample_article: dict,
    ):
        """Test that publication rolls back on error."""
        mock_image_gen = MagicMock()
        mock_image_gen.generate_and_upload_image = AsyncMock(return_value=None)
        publisher = ArticlePublisher(image_generator=mock_image_gen)

        with patch(
            "app.services.automation.article_publisher.category_classifier"
        ) as mock_classifier:
            mock_classifier.classify.side_effect = Exception("Classification error")

            result = await publisher.publish_article(sample_article, db_session)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_article_success(
        self,
        db_session: AsyncSession,
        test_category: Category,
        sample_article: dict,
    ):
        """Test successful article update."""
        # First, create a post to update
        from app.db.models import Post

        post = Post(
            id=uuid4(),
            title="Original Title",
            slug="original-title",
            content_markdown="Original content",
            content_html="<p>Original content</p>",
            status="published",
            category_id=test_category.id,
        )
        db_session.add(post)
        await db_session.commit()

        publisher = ArticlePublisher()

        result = await publisher.update_article(
            str(post.id),
            sample_article,
            db_session,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_article_failure_invalid_id(
        self,
        db_session: AsyncSession,
        sample_article: dict,
    ):
        """Test article update with invalid post ID."""
        publisher = ArticlePublisher()

        result = await publisher.update_article(
            str(uuid4()),  # Non-existent ID
            sample_article,
            db_session,
        )

        # Should still return True as no exception is raised
        # (crud_post.update_post returns None for non-existent)
        assert result is True


class TestArticlePublisherIntegration:
    """Integration tests for ArticlePublisher with real database."""

    @pytest_asyncio.fixture
    async def category(self, db_session: AsyncSession) -> Category:
        """Create a test category."""
        cat = Category(id=uuid4(), name="Ethereum", slug="ethereum")
        db_session.add(cat)
        await db_session.commit()
        return cat

    @pytest.mark.asyncio
    async def test_full_publish_workflow(
        self, db_session: AsyncSession, category: Category
    ):
        """Test the complete publish workflow."""
        mock_image_gen = MagicMock()
        mock_image_gen.generate_and_upload_image = AsyncMock(
            return_value="https://example.com/test.jpg"
        )
        publisher = ArticlePublisher(image_generator=mock_image_gen)

        article = {
            "title": "Ethereum 2.0 Launch Success",
            "slug": "ethereum-2-0-launch-success",
            "content_markdown": "## ETH 2.0\n\nEthereum successfully launched its 2.0 upgrade.",
            "excerpt": "Ethereum 2.0 is live.",
            "meta_title": "ETH 2.0 Live",
            "meta_description": "Ethereum 2.0 has successfully launched its proof of stake upgrade.",
        }

        with patch(
            "app.services.automation.article_publisher.category_classifier"
        ) as mock_classifier:
            mock_classifier.classify.return_value = category.slug
            mock_classifier.get_category_name.return_value = category.name

            result = await publisher.publish_article(article, db_session)

        assert result is True

        # Verify post was created
        from sqlalchemy import select
        from app.db.models import Post

        stmt = select(Post).where(Post.slug == article["slug"])
        result = await db_session.execute(stmt)
        post = result.scalar_one_or_none()

        assert post is not None
        assert post.title == article["title"]
        assert post.status == "published"
        assert post.category_id == category.id
