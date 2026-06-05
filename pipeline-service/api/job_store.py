"""
In-memory job store for conversion pipeline state.

Production: replace with Redis-backed store.
"""

from __future__ import annotations

import asyncio
import enum
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    job_id: str
    session_id: str
    file_path: Path
    filename: str
    status: JobStatus = JobStatus.QUEUED
    progress: dict[str, Any] = field(default_factory=dict)  # stage → pct
    yaml_result: str | None = None
    error: str | None = None
    subscribers: list[asyncio.Queue] = field(default_factory=list)

    async def notify(self, message: dict) -> None:
        """Push a message to all WebSocket subscribers."""
        for q in self.subscribers:
            await q.put(message)

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to progress updates. Returns a queue."""
        q: asyncio.Queue = asyncio.Queue()
        self.subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        if q in self.subscribers:
            self.subscribers.remove(q)


class JobStore:
    """In-memory job store with TTL-based eviction."""

    _JOB_TTL = 3600  # 1 hour

    def __init__(self) -> None:
        self._jobs: dict[str, tuple[Job, float]] = {}  # job_id → (Job, created_at)
        self._sessions: dict[str, str] = {}  # session_id → job_id

    def _evict_expired(self) -> None:
        """Remove jobs older than TTL."""
        now = time.time()
        expired = [
            jid for jid, (_, created) in self._jobs.items()
            if now - created > self._JOB_TTL
        ]
        for jid in expired:
            del self._jobs[jid]

    def create_job(self, session_id: str, file_path: Path, filename: str) -> Job:
        self._evict_expired()
        job_id = uuid.uuid4().hex[:16]
        job = Job(
            job_id=job_id,
            session_id=session_id,
            file_path=file_path,
            filename=filename,
        )
        self._jobs[job_id] = (job, time.time())
        self._sessions[session_id] = job_id
        return job

    def get_job(self, job_id: str) -> Job | None:
        self._evict_expired()
        entry = self._jobs.get(job_id)
        return entry[0] if entry else None

    def get_job_by_session(self, session_id: str) -> Job | None:
        self._evict_expired()
        job_id = self._sessions.get(session_id)
        if not job_id:
            return None
        entry = self._jobs.get(job_id)
        return entry[0] if entry else None


# Global singleton
job_store = JobStore()
