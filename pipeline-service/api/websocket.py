"""
WebSocket endpoint for real-time conversion progress updates.

Clients connect to /api/progress/{job_id} to receive stage-by-stage
progress notifications during the 6-stage conversion pipeline.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.job_store import job_store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/progress/{job_id}")
async def progress_websocket(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint — pushes conversion progress to the client.

    Validates job_id exists before accepting the connection.

    Messages sent:
      - {"type": "progress", "stage": "parser", "progress": 0.5, "message": "..."}
      - {"type": "thinking", "text": "..."}
      - {"type": "complete", "yaml": "..."}
      - {"type": "error", "error": "..."}
    """
    job = job_store.get_job(job_id)
    if not job:
        await websocket.close(code=4004, reason="Job not found")
        return

    await websocket.accept()
    queue = job.subscribe()
    logger.info("WebSocket connected: job=%s", job_id)

    try:
        # If already completed, send result immediately
        if job.yaml_result:
            await websocket.send_json({"type": "complete", "yaml": job.yaml_result})
        elif job.error:
            await websocket.send_json({"type": "error", "error": job.error})

        # Listen for progress updates
        while True:
            message = await queue.get()
            await websocket.send_json(message)
            # Close after terminal states
            if message.get("type") in ("complete", "error"):
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: job=%s", job_id)
    finally:
        job.unsubscribe(queue)
