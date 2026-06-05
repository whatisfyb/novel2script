"""
Basic health check test — verifies FastAPI app starts and /health responds.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.anyio
async def test_health_endpoint():
    """GET /health should return 200 with status=ok."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "pipeline-service"
