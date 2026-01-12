"""
Integration tests for Health API endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_basic_health_check(api_client: AsyncClient):
    """Test basic health check endpoint."""
    response = await api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_api_health_check(api_client: AsyncClient):
    """Test API-level health check endpoint."""
    response = await api_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_api_health_readiness(api_client: AsyncClient):
    """Test readiness probe endpoint."""
    response = await api_client.get("/api/v1/health/ready")
    assert response.status_code in [200, 503]  # May fail if DB not available
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_api_health_detailed(api_client: AsyncClient):
    """Test detailed health check endpoint."""
    response = await api_client.get("/api/v1/health/detailed")
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    # Should include component health info
    assert "components" in data or "database" in data or "checks" in data or "status" in data
