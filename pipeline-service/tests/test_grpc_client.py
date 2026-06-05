"""
Unit tests for the gRPC auth client.

Mocks gRPC stub to avoid needing a running auth-service.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from grpc_client.auth_client import AuthGrpcClient, QuotaResult, VerifyResult


@pytest.fixture
def client():
    return AuthGrpcClient(host="localhost:9090")


class TestVerifyToken:
    def test_returns_valid_result(self, client: AuthGrpcClient):
        mock_stub = MagicMock()
        mock_response = MagicMock()
        mock_response.valid = True
        mock_response.user_id = "user-123"
        mock_response.username = "testuser"
        mock_response.plan = 1
        mock_stub.VerifyToken.return_value = mock_response

        with patch.object(client, "_get_stub", return_value=mock_stub):
            result = client.verify_token("Bearer test-token")

        assert isinstance(result, VerifyResult)
        assert result.valid is True
        assert result.user_id == "user-123"
        assert result.username == "testuser"
        assert result.plan == 1

    def test_handles_grpc_error(self, client: AuthGrpcClient):
        import grpc

        mock_stub = MagicMock()
        mock_stub.VerifyToken.side_effect = grpc.RpcError("connection refused")

        with patch.object(client, "_get_stub", return_value=mock_stub):
            result = client.verify_token("Bearer bad-token")

        assert result.valid is False
        assert result.user_id == ""


class TestCheckQuota:
    def test_returns_quota_result(self, client: AuthGrpcClient):
        mock_stub = MagicMock()
        mock_response = MagicMock()
        mock_response.allowed = True
        mock_response.remaining = 42
        mock_response.reset_at = "2026-07-01T00:00:00Z"
        mock_stub.CheckQuota.return_value = mock_response

        with patch.object(client, "_get_stub", return_value=mock_stub):
            result = client.check_quota("user-123", "convert")

        assert isinstance(result, QuotaResult)
        assert result.allowed is True
        assert result.remaining == 42
        assert result.reset_at == "2026-07-01T00:00:00Z"

    def test_handles_grpc_error(self, client: AuthGrpcClient):
        import grpc

        mock_stub = MagicMock()
        mock_stub.CheckQuota.side_effect = grpc.RpcError("timeout")

        with patch.object(client, "_get_stub", return_value=mock_stub):
            result = client.check_quota("user-123", "convert")

        assert result.allowed is False
        assert result.remaining == 0


class TestRecordUsage:
    def test_returns_success(self, client: AuthGrpcClient):
        mock_stub = MagicMock()
        mock_response = MagicMock()
        mock_response.success = True
        mock_stub.RecordUsage.return_value = mock_response

        with patch.object(client, "_get_stub", return_value=mock_stub):
            result = client.record_usage("user-123", "convert", 3, 1500)

        assert result is True

    def test_handles_grpc_error(self, client: AuthGrpcClient):
        import grpc

        mock_stub = MagicMock()
        mock_stub.RecordUsage.side_effect = grpc.RpcError("unavailable")

        with patch.object(client, "_get_stub", return_value=mock_stub):
            result = client.record_usage("user-123", "convert", 3, 1500)

        assert result is False


class TestClose:
    def test_close_clears_channel(self, client: AuthGrpcClient):
        mock_channel = MagicMock()
        client._channel = mock_channel
        client._stub = MagicMock()

        client.close()

        mock_channel.close.assert_called_once()
        assert client._channel is None
        assert client._stub is None
