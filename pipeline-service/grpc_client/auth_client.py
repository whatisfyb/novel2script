"""
gRPC client for auth-service.

Handles token verification, quota checking, and usage recording
by calling the Java auth-service via gRPC.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import grpc

from grpc_client import auth_service_pb2 as pb2
from grpc_client import auth_service_pb2_grpc as pb2_grpc

logger = logging.getLogger(__name__)


@dataclass
class VerifyResult:
    """Result of token verification."""

    valid: bool
    user_id: str
    username: str
    plan: int


@dataclass
class QuotaResult:
    """Result of quota check."""

    allowed: bool
    remaining: int
    reset_at: str


class AuthGrpcClient:
    """
    gRPC client for the auth-service.

    Usage:
        client = AuthGrpcClient()
        result = client.verify_token("Bearer xxx")
        if not result.valid:
            raise HTTPException(401)
    """

    def __init__(self, host: str | None = None):
        self.host = host or os.getenv("AUTH_GRPC_HOST", "localhost:9090")
        self._channel: grpc.Channel | None = None
        self._stub: pb2_grpc.AuthServiceStub | None = None

    def _get_stub(self) -> pb2_grpc.AuthServiceStub:
        """Lazy-initialize gRPC channel and stub."""
        if self._stub is None:
            self._channel = grpc.insecure_channel(self.host)
            self._stub = pb2_grpc.AuthServiceStub(self._channel)
        return self._stub

    def verify_token(self, token: str) -> VerifyResult:
        """
        Verify a Sa-Token session token.

        Args:
            token: the session token (from Authorization header)

        Returns:
            VerifyResult with validity, user_id, username, and plan.
        """
        try:
            stub = self._get_stub()
            request = pb2.VerifyTokenRequest(token=token)
            response = stub.VerifyToken(request, timeout=5)
            return VerifyResult(
                valid=response.valid,
                user_id=response.user_id,
                username=response.username,
                plan=response.plan,
            )
        except grpc.RpcError as e:
            logger.warning("gRPC VerifyToken failed: %s", e)
            return VerifyResult(valid=False, user_id="", username="", plan=0)

    def check_quota(self, user_id: str, action: str) -> QuotaResult:
        """
        Check whether a user can perform an action.

        Args:
            user_id: the authenticated user's ID
            action: the action type ("convert", "export")

        Returns:
            QuotaResult with allowed flag, remaining count, and reset time.
        """
        try:
            stub = self._get_stub()
            request = pb2.CheckQuotaRequest(user_id=user_id, action=action)
            response = stub.CheckQuota(request, timeout=5)
            return QuotaResult(
                allowed=response.allowed,
                remaining=response.remaining,
                reset_at=response.reset_at,
            )
        except grpc.RpcError as e:
            logger.warning("gRPC CheckQuota failed: %s", e)
            return QuotaResult(allowed=False, remaining=0, reset_at="")

    def record_usage(
        self, user_id: str, action: str, chapters_processed: int, tokens_used: int
    ) -> bool:
        """
        Record usage after a successful conversion.

        Args:
            user_id: the authenticated user's ID
            action: the action type
            chapters_processed: number of chapters processed
            tokens_used: total LLM tokens consumed

        Returns:
            True if recording succeeded.
        """
        try:
            stub = self._get_stub()
            request = pb2.RecordUsageRequest(
                user_id=user_id,
                action=action,
                chapters_processed=chapters_processed,
                tokens_used=tokens_used,
            )
            response = stub.RecordUsage(request, timeout=5)
            return response.success
        except grpc.RpcError as e:
            logger.warning("gRPC RecordUsage failed: %s", e)
            return False

    def close(self) -> None:
        """Close the gRPC channel."""
        if self._channel:
            self._channel.close()
            self._channel = None
            self._stub = None


# Global singleton (lazy-initialized)
auth_client = AuthGrpcClient()
