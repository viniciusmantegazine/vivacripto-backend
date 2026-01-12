"""
Integration tests for Posts API endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(api_client: AsyncClient):
    """Test root endpoint returns API info."""
    response = await api_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "VivaCripto API"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_endpoint(api_client: AsyncClient):
    """Test health check endpoint."""
    response = await api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_list_posts_empty(api_client: AsyncClient):
    """Test listing posts when database is empty."""
    response = await api_client.get("/api/v1/posts")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_posts_with_data(api_client: AsyncClient, test_post):
    """Test listing posts with existing data."""
    response = await api_client.get("/api/v1/posts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_list_posts_pagination(api_client: AsyncClient, test_post):
    """Test posts pagination parameters."""
    response = await api_client.get("/api/v1/posts?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 5


@pytest.mark.asyncio
async def test_list_posts_filter_by_status(api_client: AsyncClient, test_post, test_draft_post):
    """Test filtering posts by status."""
    # Filter published posts
    response = await api_client.get("/api/v1/posts?status=published")
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["status"] == "published"

    # Filter draft posts
    response = await api_client.get("/api/v1/posts?status=draft")
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["status"] == "draft"


@pytest.mark.asyncio
async def test_get_post_by_id(api_client: AsyncClient, test_post):
    """Test getting a post by ID."""
    response = await api_client.get(f"/api/v1/posts/{test_post.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_post.id)
    assert data["title"] == test_post.title


@pytest.mark.asyncio
async def test_get_post_by_id_not_found(api_client: AsyncClient):
    """Test getting a non-existent post."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await api_client.get(f"/api/v1/posts/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_post_by_slug(api_client: AsyncClient, test_post):
    """Test getting a post by slug."""
    response = await api_client.get(f"/api/v1/posts/slug/{test_post.slug}")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == test_post.slug


@pytest.mark.asyncio
async def test_get_post_by_slug_not_found(api_client: AsyncClient):
    """Test getting a non-existent post by slug."""
    response = await api_client.get("/api/v1/posts/slug/non-existent-slug")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_search_posts(api_client: AsyncClient, test_post):
    """Test searching posts."""
    # Search by title
    response = await api_client.get(f"/api/v1/posts/search?q={test_post.title[:10]}")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data


@pytest.mark.asyncio
async def test_search_posts_min_length(api_client: AsyncClient):
    """Test search requires minimum query length."""
    response = await api_client.get("/api/v1/posts/search?q=a")
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_post_requires_auth(api_client: AsyncClient):
    """Test creating a post requires authentication."""
    post_data = {
        "title": "New Post",
        "slug": "new-post",
        "content_markdown": "# New Post\n\nContent here.",
        "content_html": "<h1>New Post</h1><p>Content here.</p>",
        "excerpt": "New post excerpt",
        "status": "draft",
    }
    response = await api_client.post("/api/v1/posts", json=post_data)
    assert response.status_code == 403  # Forbidden without auth


@pytest.mark.asyncio
async def test_update_post_requires_auth(api_client: AsyncClient, test_post):
    """Test updating a post requires authentication."""
    update_data = {"title": "Updated Title"}
    response = await api_client.put(f"/api/v1/posts/{test_post.id}", json=update_data)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_post_requires_auth(api_client: AsyncClient, test_post):
    """Test deleting a post requires authentication."""
    response = await api_client.delete(f"/api/v1/posts/{test_post.id}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_404_handler(api_client: AsyncClient):
    """Test custom 404 handler."""
    response = await api_client.get("/nonexistent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "message" in data
    assert "available_endpoints" in data
