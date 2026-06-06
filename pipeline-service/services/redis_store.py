"""
RedisStore — abstraction over Redis for the multi-service pipeline.

Provides four responsibilities:
  1. **status** — current run status (Hash) for `GET /pipeline/{id}/status`
  2. **events** — append-only audit log (Stream) for `GET /pipeline/{id}/events`
  3. **notify** — real-time push channel (Pub/Sub) for WebSocket subscribers
  4. **result** — final YAML (String with TTL) for `GET /pipeline/{id}/result`

For tests, pass a `fakeredis.FakeRedis()` instance to swap the backend.

Design notes:
  - The store is intentionally thin — just thin wrappers around Redis primitives.
  - The store does NOT know about the LangGraph state — that's stored separately
    via `langgraph-checkpoint-redis` using its own key prefix.
  - All write methods are async-safe via the underlying `redis.asyncio` client.
  - Event ordering is preserved by Redis Streams (XADD with auto IDs).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

try:
    import redis.asyncio as redis_async
except ImportError:  # fallback for older redis versions
    import redis as redis_sync  # type: ignore
    redis_async = redis_sync

logger = logging.getLogger(__name__)


# Redis key namespace constants
class K:
    STATUS = "pipeline:status:{run_id}"        # Hash
    EVENTS = "pipeline:events:{run_id}"         # Stream
    NOTIFY = "pipeline:notify:{run_id}"         # Pub/Sub channel
    RESULT = "pipeline:result:{run_id}"         # String
    ERROR = "pipeline:error:{run_id}"           # Hash
    RUNS = "pipeline:runs"                       # Sorted Set (score = start_ts)


# Default TTL for results (24 hours)
DEFAULT_RESULT_TTL = 86400


class RedisStore:
    """Thin async wrapper around Redis for pipeline state."""

    def __init__(self, client: Any) -> None:
        self.r = client

    # ------------------------------------------------------------------
    # Status (Hash)
    # ------------------------------------------------------------------

    async def set_status(self, run_id: str, **fields: Any) -> None:
        """Update one or more status fields. Auto-stamps `updated_at`."""
        fields = {k: _encode(v) for k, v in fields.items()}
        fields["updated_at"] = str(time.time())
        await self.r.hset(K.STATUS.format(run_id=run_id), mapping=fields)

    async def get_status(self, run_id: str) -> dict[str, str]:
        """Return all status fields as a dict (string values)."""
        result = await self.r.hgetall(K.STATUS.format(run_id=run_id))
        return {k.decode() if isinstance(k, bytes) else k:
                v.decode() if isinstance(v, bytes) else v
                for k, v in result.items()}

    async def set_started(self, run_id: str, total_stages: int = 4) -> None:
        """Mark a run as started; records start_ts in the runs sorted set."""
        await self.set_status(
            run_id,
            stage="starting",
            progress=0,
            total_stages=str(total_stages),
        )
        await self.r.zadd(K.RUNS, {run_id: time.time()})

    async def set_completed(self, run_id: str) -> None:
        await self.set_status(
            run_id,
            stage="done",
            progress=100,
        )

    async def set_failed(self, run_id: str, error: str, stage: str = "unknown") -> None:
        await self.set_status(run_id, stage=f"failed:{stage}", error=error)
        await self.r.hset(K.ERROR.format(run_id=run_id), mapping={
            "error": error, "stage": stage, "ts": str(time.time()),
        })

    # ------------------------------------------------------------------
    # Events (Stream)
    # ------------------------------------------------------------------

    async def append_event(
        self,
        run_id: str,
        event_type: str,
        source: str,
        correlation_id: str = "",
        payload: dict | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Append an event to the run's audit stream. Returns the event ID.

        Also publishes to the notify channel for live WebSocket subscribers.
        """
        event = {
            "ts": str(time.time()),
            "type": event_type,
            "source": source,
            "correlation_id": correlation_id,
            "payload": _encode(payload or {}),
            "metadata": _encode(metadata or {}),
        }
        # Redis Streams want flat string values
        flat = {k: v for k, v in event.items() if not isinstance(v, (dict, list))}
        for k in ("payload", "metadata"):
            if k in event:
                flat[k] = event[k]
        eid = await self.r.xadd(K.EVENTS.format(run_id=run_id), flat)
        # Publish for live subscribers
        await self.r.publish(
            K.NOTIFY.format(run_id=run_id),
            json.dumps({
                "event_id": eid.decode() if isinstance(eid, bytes) else eid,
                "type": event_type,
                "source": source,
                "correlation_id": correlation_id,
                "payload": payload or {},
                "metadata": metadata or {},
            }),
        )
        return eid.decode() if isinstance(eid, bytes) else eid

    async def get_events(
        self, run_id: str, count: int = 100, start: str = "-"
    ) -> list[dict[str, Any]]:
        """Read events from the run's audit stream (most recent first)."""
        raw = await self.r.xrevrange(
            K.EVENTS.format(run_id=run_id), max="+", min=start, count=count,
        )
        out: list[dict[str, Any]] = []
        for eid, fields in raw:
            ev: dict[str, Any] = {"_id": eid.decode() if isinstance(eid, bytes) else eid}
            for k, v in fields.items():
                kk = k.decode() if isinstance(k, bytes) else k
                vv = v.decode() if isinstance(v, bytes) else v
                if kk in ("payload", "metadata"):
                    try:
                        ev[kk] = json.loads(vv)
                    except (json.JSONDecodeError, TypeError):
                        ev[kk] = vv
                else:
                    ev[kk] = vv
            out.append(ev)
        return out

    # ------------------------------------------------------------------
    # Result (String with TTL)
    # ------------------------------------------------------------------

    async def set_result(self, run_id: str, yaml_str: str, ttl: int = DEFAULT_RESULT_TTL) -> None:
        await self.r.set(K.RESULT.format(run_id=run_id), yaml_str, ex=ttl)

    async def get_result(self, run_id: str) -> str | None:
        v = await self.r.get(K.RESULT.format(run_id=run_id))
        if v is None:
            return None
        return v.decode() if isinstance(v, bytes) else v

    # ------------------------------------------------------------------
    # Run listing
    # ------------------------------------------------------------------

    async def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the most recent N runs with their status."""
        ids = await self.r.zrevrange(K.RUNS, 0, limit - 1, withscores=True)
        out: list[dict[str, Any]] = []
        for run_id_bytes, start_ts in ids:
            run_id = run_id_bytes.decode() if isinstance(run_id_bytes, bytes) else run_id_bytes
            status = await self.get_status(run_id)
            status["run_id"] = run_id
            status["start_ts"] = int(start_ts)
            out.append(status)
        return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _encode(v: Any) -> str:
    """Encode a value for storage in a Redis field (JSON for non-strings)."""
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_default_store: RedisStore | None = None


def get_default_store() -> RedisStore:
    """Return the module-level default store (lazy-init from env).

    Uses REDIS_URL env var (default: redis://localhost:6379/0).
    For tests, set `pipeline.services.redis_store._default_store` to a
    FakeRedis-backed instance before calling this.
    """
    global _default_store
    if _default_store is None:
        import os
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = redis_async.from_url(url, decode_responses=False)
        _default_store = RedisStore(client)
    return _default_store


def set_default_store(store: RedisStore) -> None:
    """Override the default store (for tests)."""
    global _default_store
    _default_store = store
