"""Test API health endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint returns correct response."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Samscloak API"
    assert data["version"] == "1.0.0"
    assert "docs" in data


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
