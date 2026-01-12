"""
Pytest configuration and shared fixtures for VivaCripto Backend tests.
"""
import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.models import Author, Base, Category, Post, Tag


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_db_engine():
    """Create an async test database engine (in-memory SQLite)."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create an async database session for testing."""
    async_session_maker = async_sessionmaker(
        async_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


# ============================================================================
# Model Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def test_category(db_session: AsyncSession) -> Category:
    """Create a test category."""
    category = Category(
        id=uuid4(),
        name="Bitcoin",
        slug="bitcoin",
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture
async def test_author(db_session: AsyncSession) -> Author:
    """Create a test author."""
    author = Author(
        id=uuid4(),
        name="Test Author",
        bio="A test author for unit tests.",
        avatar_url="https://example.com/avatar.jpg",
    )
    db_session.add(author)
    await db_session.commit()
    await db_session.refresh(author)
    return author


@pytest_asyncio.fixture
async def test_tag(db_session: AsyncSession) -> Tag:
    """Create a test tag."""
    tag = Tag(
        id=uuid4(),
        name="Crypto",
        slug="crypto",
    )
    db_session.add(tag)
    await db_session.commit()
    await db_session.refresh(tag)
    return tag


@pytest_asyncio.fixture
async def test_post(
    db_session: AsyncSession,
    test_category: Category,
    test_author: Author,
) -> Post:
    """Create a test post."""
    post = Post(
        id=uuid4(),
        title="Test Post Title",
        slug="test-post-title",
        content_markdown="# Test Content\n\nThis is test content.",
        content_html="<h1>Test Content</h1><p>This is test content.</p>",
        excerpt="This is a test excerpt.",
        status="published",
        published_at=datetime.now(timezone.utc),
        category_id=test_category.id,
        author_id=test_author.id,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest_asyncio.fixture
async def test_draft_post(
    db_session: AsyncSession,
    test_category: Category,
) -> Post:
    """Create a test draft post."""
    post = Post(
        id=uuid4(),
        title="Draft Post Title",
        slug="draft-post-title",
        content_markdown="# Draft Content\n\nThis is draft content.",
        content_html="<h1>Draft Content</h1><p>This is draft content.</p>",
        excerpt="This is a draft excerpt.",
        status="draft",
        category_id=test_category.id,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_openai():
    """Mock OpenAI client for testing."""
    with patch("openai.AsyncOpenAI") as mock:
        client = AsyncMock()
        mock.return_value = client

        # Mock chat completions
        completion = MagicMock()
        completion.choices = [MagicMock()]
        completion.choices[0].message.content = "## Test Article\n\nThis is a test article about Bitcoin."
        client.chat.completions.create = AsyncMock(return_value=completion)

        # Mock image generation
        image_response = MagicMock()
        image_response.data = [MagicMock()]
        image_response.data[0].url = "https://oaidalleapiprodscus.blob.core.windows.net/test.png"
        client.images.generate = AsyncMock(return_value=image_response)

        yield client


@pytest.fixture
def mock_cloudinary():
    """Mock Cloudinary for testing."""
    with patch("cloudinary.uploader.upload") as mock_upload:
        mock_upload.return_value = {
            "secure_url": "https://res.cloudinary.com/test/image.jpg",
            "public_id": "test_image",
        }
        yield mock_upload


@pytest.fixture
def mock_httpx():
    """Mock httpx for external API calls."""
    with patch("httpx.AsyncClient") as mock:
        client = AsyncMock()
        mock.return_value.__aenter__.return_value = client

        # Mock response
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"status": "ok"}
        client.get = AsyncMock(return_value=response)
        client.post = AsyncMock(return_value=response)

        yield client


@pytest.fixture
def mock_redis():
    """Mock Redis for testing."""
    with patch("redis.asyncio.from_url") as mock:
        client = AsyncMock()
        mock.return_value = client
        client.ping = AsyncMock(return_value=True)
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock(return_value=True)
        client.delete = AsyncMock(return_value=1)
        client.aclose = AsyncMock()
        yield client


# ============================================================================
# API Client Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for API testing."""
    from app.db.base import get_db
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ============================================================================
# Helper Functions
# ============================================================================


def create_test_post_data(
    title: str = "Test Post",
    category_id: str = None,
) -> dict:
    """Create test post data dictionary."""
    return {
        "title": title,
        "slug": title.lower().replace(" ", "-"),
        "content_markdown": f"# {title}\n\nTest content for {title}.",
        "content_html": f"<h1>{title}</h1><p>Test content for {title}.</p>",
        "excerpt": f"Excerpt for {title}",
        "status": "draft",
        "category_id": category_id,
    }


def create_test_article_data() -> dict:
    """Create test article data for content generation tests."""
    return {
        "title": "Bitcoin Reaches New All-Time High",
        "slug": "bitcoin-reaches-new-all-time-high",
        "content_markdown": "# Bitcoin ATH\n\nBitcoin has reached a new all-time high.",
        "excerpt": "Bitcoin surges to new heights.",
        "meta_title": "Bitcoin ATH - VivaCripto",
        "meta_description": "Breaking: Bitcoin reaches new all-time high.",
    }


def create_test_news_item() -> dict:
    """Create test news item for pipeline tests."""
    return {
        "source": "CoinDesk",
        "source_language": "en",
        "title": "Bitcoin Breaks $100,000 For First Time",
        "url": "https://coindesk.com/test-article",
        "description": "Bitcoin has surpassed $100,000 for the first time, marking a historic milestone.",
        "published_at": datetime.now(timezone.utc),
        "collected_at": datetime.now(timezone.utc),
    }
