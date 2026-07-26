"""
Unit tests for Post CRUD operations.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_post import crud_post
from app.db.models import Category, Post
from app.schemas.post import PostCreate, PostUpdate


class TestCRUDPost:
    """Test suite for Post CRUD operations."""

    @pytest_asyncio.fixture
    async def category(self, db_session: AsyncSession) -> Category:
        """Create a test category."""
        category = Category(id=uuid4(), name="Test Category", slug="test-category")
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        return category

    @pytest.mark.asyncio
    async def test_create_post(self, db_session: AsyncSession, category: Category):
        """Test creating a new post."""
        post_data = PostCreate(
            title="Test Post",
            slug="test-post",
            content_markdown="# Test\n\nContent here.",
            content_html="<h1>Test</h1><p>Content here.</p>",
            excerpt="Test excerpt",
            status="draft",
            category_id=category.id,
        )

        post = await crud_post.create_post(db_session, post_data)

        assert post.id is not None
        assert post.title == "Test Post"
        assert post.slug == "test-post"
        assert post.status == "draft"
        assert post.category_id == category.id

    @pytest.mark.asyncio
    async def test_create_post_published_sets_published_at(
        self, db_session: AsyncSession, category: Category
    ):
        """Test that creating a published post sets published_at."""
        post_data = PostCreate(
            title="Published Post",
            slug="published-post",
            content_markdown="Content",
            content_html="<p>Content</p>",
            excerpt="Excerpt for Published Post",
            status="published",
            category_id=category.id,
        )

        post = await crud_post.create_post(db_session, post_data)

        assert post.status == "published"
        assert post.published_at is not None

    @pytest.mark.asyncio
    async def test_create_post_without_auto_commit(
        self, db_session: AsyncSession, category: Category
    ):
        """Test creating a post without auto commit."""
        post_data = PostCreate(
            title="No Auto Commit Post",
            slug="no-auto-commit",
            content_markdown="Content",
            content_html="<p>Content</p>",
            excerpt="Excerpt for No Auto Commit Post",
            status="draft",
            category_id=category.id,
        )

        post = await crud_post.create_post(db_session, post_data, auto_commit=False)
        await db_session.commit()

        assert post.id is not None
        assert post.title == "No Auto Commit Post"

    @pytest.mark.asyncio
    async def test_get_post_by_id(self, db_session: AsyncSession, test_post: Post):
        """Test getting a post by ID."""
        retrieved = await crud_post.get_post_by_id(db_session, test_post.id)

        assert retrieved is not None
        assert retrieved.id == test_post.id
        assert retrieved.title == test_post.title

    @pytest.mark.asyncio
    async def test_get_post_by_id_not_found(self, db_session: AsyncSession):
        """Test getting a non-existent post returns None."""
        retrieved = await crud_post.get_post_by_id(db_session, uuid4())

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_post_by_slug(self, db_session: AsyncSession, test_post: Post):
        """Test getting a post by slug."""
        retrieved = await crud_post.get_post_by_slug(db_session, test_post.slug)

        assert retrieved is not None
        assert retrieved.slug == test_post.slug

    @pytest.mark.asyncio
    async def test_get_post_by_slug_not_found(self, db_session: AsyncSession):
        """Test getting a non-existent slug returns None."""
        retrieved = await crud_post.get_post_by_slug(db_session, "non-existent-slug")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_update_post(self, db_session: AsyncSession, test_post: Post):
        """Test updating a post."""
        update_data = PostUpdate(title="Updated Title", excerpt="Updated excerpt")

        updated = await crud_post.update_post(db_session, test_post.id, update_data)

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.excerpt == "Updated excerpt"

    @pytest.mark.asyncio
    async def test_update_post_to_published(
        self, db_session: AsyncSession, category: Category
    ):
        """Test that updating status to published sets published_at."""
        # Create draft post
        post_data = PostCreate(
            title="Draft Post",
            slug="draft-post",
            content_markdown="Content",
            content_html="<p>Content</p>",
            excerpt="Excerpt for Draft Post",
            status="draft",
            category_id=category.id,
        )
        post = await crud_post.create_post(db_session, post_data)
        assert post.published_at is None

        # Update to published
        update_data = PostUpdate(status="published")
        updated = await crud_post.update_post(db_session, post.id, update_data)

        assert updated.status == "published"
        assert updated.published_at is not None

    @pytest.mark.asyncio
    async def test_update_post_not_found(self, db_session: AsyncSession):
        """Test updating a non-existent post returns None."""
        update_data = PostUpdate(title="New Title")
        updated = await crud_post.update_post(db_session, uuid4(), update_data)

        assert updated is None

    @pytest.mark.asyncio
    async def test_delete_post(self, db_session: AsyncSession, test_post: Post):
        """Test deleting a post."""
        result = await crud_post.delete_post(db_session, test_post.id)

        assert result is True

        # Verify it's deleted
        retrieved = await crud_post.get_post_by_id(db_session, test_post.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_post_not_found(self, db_session: AsyncSession):
        """Test deleting a non-existent post returns False."""
        result = await crud_post.delete_post(db_session, uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_get_posts_pagination(
        self, db_session: AsyncSession, category: Category
    ):
        """Test getting posts with pagination."""
        # Create multiple posts
        for i in range(5):
            post_data = PostCreate(
                title=f"Post {i}",
                slug=f"post-{i}",
                content_markdown=f"Content {i}",
                content_html=f"<p>Content {i}</p>",
                excerpt=f"Excerpt for Post {i}",
                status="published",
                category_id=category.id,
            )
            await crud_post.create_post(db_session, post_data)

        # Test pagination
        posts, total = await crud_post.get_posts(db_session, skip=0, limit=3)

        assert len(posts) == 3
        assert total == 5

    @pytest.mark.asyncio
    async def test_get_posts_filter_by_status(
        self, db_session: AsyncSession, category: Category
    ):
        """Test filtering posts by status."""
        # Create published post
        published_data = PostCreate(
            title="Published",
            slug="published",
            content_markdown="Content",
            content_html="<p>Content</p>",
            excerpt="Excerpt for Published",
            status="published",
            category_id=category.id,
        )
        await crud_post.create_post(db_session, published_data)

        # Create draft post
        draft_data = PostCreate(
            title="Draft",
            slug="draft",
            content_markdown="Content",
            content_html="<p>Content</p>",
            excerpt="Excerpt for Draft",
            status="draft",
            category_id=category.id,
        )
        await crud_post.create_post(db_session, draft_data)

        # Filter by published
        posts, total = await crud_post.get_posts(db_session, status="published")

        assert total == 1
        assert posts[0].status == "published"

    @pytest.mark.asyncio
    async def test_get_recent_posts(
        self, db_session: AsyncSession, category: Category
    ):
        """Test getting recent posts since a date."""
        # Create a post
        post_data = PostCreate(
            title="Recent Post",
            slug="recent-post",
            content_markdown="Content",
            content_html="<p>Content</p>",
            excerpt="Excerpt for Recent Post",
            status="published",
            category_id=category.id,
        )
        await crud_post.create_post(db_session, post_data)

        # Get recent posts from start of today (naive datetime for DB compatibility)
        since = datetime.utcnow().replace(hour=0, minute=0, second=0)
        recent = await crud_post.get_recent_posts(db_session, since)

        assert len(recent) >= 1

    @pytest.mark.asyncio
    async def test_search_posts(self, db_session: AsyncSession, category: Category):
        """Test searching posts by title or content."""
        # Create searchable post
        post_data = PostCreate(
            title="Bitcoin Price Analysis",
            slug="bitcoin-price-analysis",
            content_markdown="Analysis of Bitcoin market trends",
            content_html="<p>Analysis of Bitcoin market trends</p>",
            excerpt="Excerpt for Bitcoin Price Analysis",
            status="published",
            category_id=category.id,
        )
        await crud_post.create_post(db_session, post_data)

        # Search
        results = await crud_post.search_posts(db_session, "Bitcoin")

        assert len(results) >= 1
        assert "Bitcoin" in results[0].title

    @pytest.mark.asyncio
    async def test_search_posts_sanitization(
        self, db_session: AsyncSession, category: Category
    ):
        """Test that search query is sanitized."""
        # Create post
        post_data = PostCreate(
            title="Test Post",
            slug="test-search",
            content_markdown="Content",
            content_html="<p>Content</p>",
            excerpt="Excerpt for Test Post",
            status="published",
            category_id=category.id,
        )
        await crud_post.create_post(db_session, post_data)

        # Search with special characters (should be escaped)
        results = await crud_post.search_posts(db_session, "Test%Post")

        # Should not cause SQL errors
        assert isinstance(results, list)
