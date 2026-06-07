"""
Orchestrator — LangGraph-driven HTTP client for the 3 services.

Coordinates the 3 services over HTTP, writes Redis state, and exposes
status endpoints. This is the entry point for the multi-service
architecture.

Endpoints:
  POST /pipeline                    — submit novel (file upload), returns run_id
  GET  /pipeline/{run_id}/status    — current run status from Redis
  GET  /pipeline/{run_id}/events    — audit log (Stream reverse range)
  GET  /pipeline/{run_id}/result    — final YAML
  GET  /pipeline/list               — recent runs
  WS   /ws/pipeline/{run_id}        — live event push via Redis pub/sub

Environment:
  INPUT_SERVICE_URL       (default: http://localhost:8001)
  STRUCTURE_SERVICE_URL   (default: http://localhost:8002)
  BEAT_SERVICE_URL        (default: http://localhost:8003)
  REDIS_URL               (default: redis://localhost:6379/0)

Run: `uvicorn services.orchestrator:app --port 8000`
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from services.redis_store import K, RedisStore, get_default_store

logger = logging.getLogger(__name__)

# Service URLs
INPUT_URL = os.getenv("INPUT_SERVICE_URL", "http://localhost:8001")
STRUCTURE_URL = os.getenv("STRUCTURE_SERVICE_URL", "http://localhost:8002")
BEAT_URL = os.getenv("BEAT_SERVICE_URL", "http://localhost:8003")


app = FastAPI(
    title="Novel-to-Script Orchestrator",
    description="Multi-service pipeline orchestrator with Redis state + LangGraph flow",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


def get_store() -> RedisStore:
    return get_default_store()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "orchestrator"}


@app.get("/pipeline/list")
async def list_runs(limit: int = 20) -> dict[str, Any]:
    store = get_store()
    runs = await store.list_runs(limit=limit)
    return {"runs": runs}


@app.get("/pipeline/{run_id}/status")
async def get_status(run_id: str) -> dict[str, str]:
    store = get_store()
    status = await store.get_status(run_id)
    if not status:
        raise HTTPException(status_code=404, detail="Run not found")
    return status


@app.get("/pipeline/{run_id}/events")
async def get_events(run_id: str, count: int = 100) -> dict[str, Any]:
    store = get_store()
    events = await store.get_events(run_id, count=count)
    return {"events": events}


@app.get("/pipeline/{run_id}/result")
async def get_result(run_id: str) -> dict[str, Any]:
    store = get_store()
    result = await store.get_result(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not ready")
    return {"yaml": result}


# ---------------------------------------------------------------------------
# Pipeline submission
# ---------------------------------------------------------------------------

@app.post("/pipeline")
async def submit_pipeline(
    file: UploadFile = File(...),
) -> dict[str, str]:
    """Submit a novel for conversion. Returns run_id; client should poll
    status or subscribe to /ws/pipeline/{run_id} for progress."""
    run_id = f"r_{int(time.time())}_{str(uuid.uuid4())[:6]}"
    store = get_store()
    await store.set_started(run_id)
    await store.set_status(run_id, filename=file.filename or "upload.txt")
    await store.append_event(
        run_id=run_id, event_type="pipeline.started",
        source="orchestrator", correlation_id=run_id,
        payload={"filename": file.filename, "size": file.size},
    )

    # Schedule the background run
    content = await file.read()
    asyncio.create_task(_run_pipeline(run_id, content, file.filename or "upload.txt"))

    return {"run_id": run_id}


async def _run_pipeline(run_id: str, file_content: bytes, filename: str) -> None:
    """Background task: drive the 3 services via HTTP and write state."""
    store = get_store()
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            # ----- Stage 1+2: Input Service -----
            await store.append_event(
                run_id=run_id, event_type="stage.input.started",
                source="orchestrator", correlation_id=run_id,
            )
            await store.set_status(run_id, stage="input", progress=5)
            resp = await client.post(
                f"{INPUT_URL}/pipeline",
                files={"file": (filename, file_content)},
                params={"run_id": run_id},
            )
            resp.raise_for_status()
            input_data = resp.json()
            chapters = input_data["chapters"]
            await store.append_event(
                run_id=run_id, event_type="stage.input.done",
                source="orchestrator", correlation_id=run_id,
                payload={"n_chapters": len(chapters)},
            )

            # ----- Stage 3+4: Structure Service -----
            await store.set_status(run_id, stage="structure", progress=30)
            resp = await client.post(
                f"{STRUCTURE_URL}/pipeline",
                json={"chapters": chapters, "run_id": run_id},
            )
            resp.raise_for_status()
            struct_data = resp.json()
            characters = struct_data["characters"]
            locations = struct_data["locations"]
            scenes_by_chapter = struct_data["scenes_by_chapter"]
            synopsis = struct_data.get("synopsis", "")
            logger.info("Structure service returned synopsis: %s", repr(synopsis))
            n_scenes = sum(len(s) for s in scenes_by_chapter.values())
            await store.append_event(
                run_id=run_id, event_type="stage.structure.done",
                source="orchestrator", correlation_id=run_id,
                payload={"n_characters": len(characters), "n_scenes": n_scenes},
            )

            # ----- Stage 5: Beat Service (parallel per scene) -----
            await store.set_status(run_id, stage="beat", progress=60)

            # Flatten scenes across chapters
            all_scenes: list[dict] = []
            for chapter_order, scene_list in scenes_by_chapter.items():
                # Find the matching chapter text
                # NOTE: chapter_order is str from JSON dict keys, c["order"] is int
                chapter_text = next(
                    (c["text"] for c in chapters if c["order"] == int(chapter_order)),
                    None,
                )
                logger.info("Chapter %s: chapter_text length=%s", chapter_order, len(chapter_text) if chapter_text else 0)
                for idx, scene in enumerate(scene_list, start=1):
                    start, end = scene["text_segment"]
                    scene_text = (
                        chapter_text[start:end]
                        if chapter_text and end > start
                        else (chapter_text or "")
                    )
                    logger.info("Scene ch%s_s%s: text_segment=[%s,%s], scene_text length=%s", chapter_order, idx, start, end, len(scene_text))
                    all_scenes.append({
                        "scene_id": f"ch{chapter_order}_s{idx}",
                        "chapter_order": chapter_order,
                        "scene_text": scene_text,
                        "chapter_text": chapter_text,
                    })

            await store.append_event(
                run_id=run_id, event_type="stage.beat.started",
                source="orchestrator", correlation_id=run_id,
                payload={"n_scenes": len(all_scenes)},
            )

            # Call beat service **strictly sequentially** to avoid triggering
            # upstream LLM rate limits. ReAct's 6-iteration loop per scene
            # pushes ~6-18 LLM calls per scene, so even 2 scenes in parallel
            # exceeds MiMo's 100 RPM. Sequential processing trades latency
            # for reliability.
            beats_by_scene: dict[str, list[dict]] = {}
            for idx, scene in enumerate(all_scenes):
                if idx > 0:
                    # Stagger between scenes. ~6 LLM calls per scene at
                    # ~2-3s each = 12-18s per scene. 5s extra buffer.
                    await asyncio.sleep(5.0)
                try:
                    resp = await client.post(
                        f"{BEAT_URL}/extract",
                        json={
                            "scene": scene,
                            "characters": characters,
                            "run_id": run_id,
                        },
                        timeout=180.0,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    beats_by_scene[scene["scene_id"]] = data.get("beats", [])
                except Exception as exc:
                    logger.warning(
                        "Beat failed for %s: %s", scene["scene_id"], exc,
                    )
                    beats_by_scene[scene["scene_id"]] = []
            scene_results = []  # unused after this rewrite
            for scene, result in zip(all_scenes, scene_results):
                if isinstance(result, Exception):
                    logger.warning("Beat failed for %s: %s", scene["scene_id"], result)
                    beats_by_scene[scene["scene_id"]] = []
                else:
                    sid, beats = result
                    beats_by_scene[sid] = beats

            await store.append_event(
                run_id=run_id, event_type="stage.beat.done",
                source="orchestrator", correlation_id=run_id,
                payload={"n_scenes_with_beats": sum(1 for v in beats_by_scene.values() if v)},
            )

            # ----- Stage 6: Assemble YAML (in-process) -----
            await store.set_status(run_id, stage="assemble", progress=90)
            from pipeline.assembler import assemble_yaml
            scenes_as_dicts = {
                int(k): [
                    {
                        "location": s["location"], "time": s["time"],
                        "type": s["type"], "description": s["description"],
                        "text_segment": list(s["text_segment"]),
                    }
                    for s in v
                ]
                for k, v in scenes_by_chapter.items()
            }
            yaml_str = assemble_yaml(
                meta={
                    "title": filename.rsplit(".", 1)[0],
                    "type": "tv",
                    "language": "zh",
                    "source_chapters": len(chapters),
                    "synopsis": synopsis,
                },
                characters=characters,
                locations=locations,
                scenes_by_chapter=scenes_as_dicts,
                beats_by_scene=beats_by_scene,
            )
            await store.set_result(run_id, yaml_str)
            await store.set_completed(run_id)
            await store.append_event(
                run_id=run_id, event_type="pipeline.completed",
                source="orchestrator", correlation_id=run_id,
                payload={"yaml_length": len(yaml_str)},
            )

        except Exception as e:
            logger.exception("Pipeline failed for %s", run_id)
            await store.set_failed(run_id, str(e), stage="orchestrator")
            await store.append_event(
                run_id=run_id, event_type="pipeline.failed",
                source="orchestrator", correlation_id=run_id,
                payload={"error": str(e)},
            )


# ---------------------------------------------------------------------------
# History API (frontend compatibility)
# ---------------------------------------------------------------------------

import re as _re
import yaml as _yaml


def _parse_yaml_stats(yaml_str: str) -> dict[str, int]:
    """Extract chapter/scene/character counts from assembled YAML."""
    try:
        data = _yaml.safe_load(yaml_str)
        if not data:
            return {"chapters": 0, "scenes": 0, "characters": 0, "acts": 0}
        meta = data.get("meta", {})
        characters = data.get("characters", [])
        acts = data.get("acts", [])
        scenes = sum(len(a.get("scenes", [])) for a in acts)
        return {
            "chapters": meta.get("source_chapters", 0),
            "scenes": scenes,
            "characters": len(characters),
            "acts": len(acts),
        }
    except Exception:
        return {"chapters": 0, "scenes": 0, "characters": 0, "acts": 0}


def _run_to_history_record(run_id: str, status: dict, yaml_str: str | None) -> dict:
    """Convert a Redis run to a HistoryRecord-compatible dict."""
    stage = status.get("stage", "unknown")
    if stage == "done":
        conv_status = "completed"
    elif stage.startswith("failed"):
        conv_status = "failed"
    else:
        conv_status = "processing"

    filename = status.get("filename", "unknown.txt")
    title = filename.rsplit(".", 1)[0] if "." in filename else filename
    start_ts = status.get("start_ts", status.get("updated_at", "0"))
    try:
        created_at = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(start_ts))
        )
    except (ValueError, TypeError):
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    stats = _parse_yaml_stats(yaml_str or "")
    return {
        "id": run_id,
        "runId": run_id,
        "filename": filename,
        "title": title,
        "scriptType": "tv",
        "language": "zh",
        "status": conv_status,
        "createdAt": created_at,
        "chapters": stats["chapters"],
        "acts": stats["acts"],
        "scenes": stats["scenes"],
        "characters": stats["characters"],
        "yaml": yaml_str or "",
        "error": status.get("error"),
    }


@app.get("/api/history")
async def api_history(
    page: int = 1, size: int = 20,
    scriptType: str | None = None, status: str | None = None,
) -> dict[str, Any]:
    """List history records (frontend-compatible format)."""
    store = get_store()
    runs = await store.list_runs(limit=100)

    records: list[dict] = []
    for run in runs:
        run_id = run.get("run_id", "")
        yaml_str = await store.get_result(run_id)
        rec = _run_to_history_record(run_id, run, yaml_str)

        # Apply filters
        if scriptType and scriptType != "all" and rec["scriptType"] != scriptType:
            continue
        if status and rec["status"] != status:
            continue
        records.append(rec)

    # Sort by createdAt desc
    records.sort(key=lambda r: r["createdAt"], reverse=True)
    total = len(records)
    start = (page - 1) * size
    items = records[start : start + size]
    return {"code": 200, "data": {"items": items, "total": total}}


@app.get("/api/history/{run_id}")
async def api_history_get(run_id: str) -> dict[str, Any]:
    """Get a single history record."""
    store = get_store()
    status = await store.get_status(run_id)
    if not status:
        raise HTTPException(status_code=404, detail="Record not found")
    yaml_str = await store.get_result(run_id)
    rec = _run_to_history_record(run_id, status, yaml_str)
    return {"code": 200, "data": rec}


@app.delete("/api/history/{run_id}")
async def api_history_delete(run_id: str) -> dict[str, Any]:
    """Delete a history record from Redis."""
    store = get_store()
    r = store.r
    # Check existence
    exists = await r.exists(K.STATUS.format(run_id=run_id))
    if not exists:
        raise HTTPException(status_code=404, detail="Record not found")
    # Delete all related keys
    await r.delete(
        K.STATUS.format(run_id=run_id),
        K.EVENTS.format(run_id=run_id),
        K.RESULT.format(run_id=run_id),
        K.ERROR.format(run_id=run_id),
    )
    await r.zrem(K.RUNS, run_id)
    return {"code": 200, "message": "Deleted"}


# ---------------------------------------------------------------------------
# WebSocket live event push
# ---------------------------------------------------------------------------

@app.websocket("/ws/pipeline/{run_id}")
async def ws_pipeline(websocket: WebSocket, run_id: str):
    """Forward Redis pub/sub events to the WebSocket client."""
    await websocket.accept()
    store = get_store()
    r = store.r
    pubsub = r.pubsub()
    await pubsub.subscribe(f"pipeline:notify:{run_id}")
    try:
        # Also send existing events first (replay)
        existing = await store.get_events(run_id, count=50)
        for ev in reversed(existing):  # chronological
            await websocket.send_json(ev)
        # Then live updates
        async for msg in pubsub.listen():
            if msg.get("type") == "message":
                try:
                    data = json.loads(msg["data"])
                    await websocket.send_json(data)
                except Exception:
                    pass
    except Exception as e:
        logger.info("WS closed: %s", e)
    finally:
        try:
            await pubsub.unsubscribe(f"pipeline:notify:{run_id}")
            await pubsub.close()
        except Exception:
            pass
