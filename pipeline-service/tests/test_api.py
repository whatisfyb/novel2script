"""
Integration tests for the REST API endpoints.

Uses httpx.AsyncClient with TestClient for FastAPI testing.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from api.job_store import job_store, JobStatus
from main import app


@pytest.fixture(autouse=True)
def _reset_store():
    """Reset job store between tests."""
    job_store._jobs.clear()
    job_store._sessions.clear()
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


class TestUpload:
    @pytest.mark.asyncio
    async def test_upload_txt_file(self, client: AsyncClient):
        resp = await client.post(
            "/api/upload",
            files={"file": ("novel.txt", b"chapter 1\nhello", "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["filename"] == "novel.txt"

    @pytest.mark.asyncio
    async def test_upload_unsupported_format(self, client: AsyncClient):
        resp = await client.post(
            "/api/upload",
            files={"file": ("novel.pdf", b"dummy", "application/pdf")},
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_creates_job(self, client: AsyncClient):
        resp = await client.post(
            "/api/upload",
            files={"file": ("test.md", b"# Chapter 1", "text/markdown")},
        )
        session_id = resp.json()["session_id"]
        job = job_store.get_job_by_session(session_id)
        assert job is not None
        assert job.filename == "test.md"


# ---------------------------------------------------------------------------
# Convert
# ---------------------------------------------------------------------------


class TestConvert:
    @pytest.mark.asyncio
    async def test_convert_not_found(self, client: AsyncClient):
        resp = await client.post("/api/convert", json={"session_id": "nonexistent"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_convert_starts_job(self, client: AsyncClient):
        # Upload first
        upload_resp = await client.post(
            "/api/upload",
            files={"file": ("novel.txt", b"content", "text/plain")},
        )
        session_id = upload_resp.json()["session_id"]

        # Mock the pipeline to avoid LLM calls
        with patch("api.routes.run_pipeline", new_callable=AsyncMock) as mock:
            mock.return_value = "meta:\n  title: test"
            resp = await client.post(
                "/api/convert",
                json={"session_id": session_id, "title": "Test"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["status"] in ("queued", "already_processing", "already_completed")


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


class TestResult:
    @pytest.mark.asyncio
    async def test_result_not_found(self, client: AsyncClient):
        resp = await client.get("/api/result/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_result_processing(self, client: AsyncClient):
        # Upload + start convert
        upload_resp = await client.post(
            "/api/upload",
            files={"file": ("novel.txt", b"content", "text/plain")},
        )
        session_id = upload_resp.json()["session_id"]

        with patch("api.routes.run_pipeline", new_callable=AsyncMock) as mock:
            mock.return_value = "yaml: content"
            convert_resp = await client.post(
                "/api/convert",
                json={"session_id": session_id},
            )

        job_id = convert_resp.json()["job_id"]
        resp = await client.get(f"/api/result/{job_id}")
        # Should be 202 (processing) or 200 (completed if fast enough)
        assert resp.status_code in (200, 202)


# ---------------------------------------------------------------------------
# Schema + Validate
# ---------------------------------------------------------------------------


class TestSchemaAndValidate:
    @pytest.mark.asyncio
    async def test_get_schema(self, client: AsyncClient):
        resp = await client.get("/api/schema")
        assert resp.status_code == 200
        assert "schema" in resp.json()

    @pytest.mark.asyncio
    async def test_validate_valid_yaml(self, client: AsyncClient):
        yaml_text = "meta:\n  title: test\ncharacters: []\nlocations: []\nacts: []"
        resp = await client.post("/api/validate", json={"yaml_text": yaml_text})
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_missing_keys(self, client: AsyncClient):
        yaml_text = "meta:\n  title: test"
        resp = await client.post("/api/validate", json={"yaml_text": yaml_text})
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_invalid_yaml(self, client: AsyncClient):
        resp = await client.post("/api/validate", json={"yaml_text": "{{invalid"})
        assert resp.status_code == 200
        assert resp.json()["valid"] is False
