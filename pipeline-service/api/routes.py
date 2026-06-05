"""
REST API routes for the pipeline service.

Endpoints:
  POST /upload       — Upload a novel file, returns session_id
  POST /convert      — Start conversion pipeline
  GET  /result/{id}  — Get conversion result YAML
  GET  /schema       — Get screenplay JSON Schema
  POST /validate     — Validate YAML text against schema
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from api.models import (
    ConvertRequest,
    ConvertResponse,
    ResultResponse,
    UploadResponse,
    ValidateRequest,
    ValidateResponse,
)
from api.job_store import JobStatus, job_store
from pipeline.orchestrator import run_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()

_UPLOAD_DIR = Path(tempfile.gettempdir()) / "novel-to-script-uploads"
_UPLOAD_DIR.mkdir(exist_ok=True)

_ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown", ".docx"}
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Track running pipeline tasks for graceful shutdown
_running_tasks: set[asyncio.Task] = set()


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a novel file (.txt, .md, or .docx).

    Returns a session_id that can be used to start conversion.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {suffix}. Allowed: {sorted(_ALLOWED_EXTENSIONS)}",
        )

    session_id = uuid.uuid4().hex[:16]
    save_path = _UPLOAD_DIR / f"{session_id}{suffix}"

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum {_MAX_FILE_SIZE // (1024*1024)}MB.")
    save_path.write_bytes(content)

    # Create job in store
    job_store.create_job(session_id, save_path, file.filename)

    logger.info("Uploaded %s → %s (session=%s)", file.filename, save_path, session_id)
    return UploadResponse(session_id=session_id, filename=file.filename)


@router.post("/convert", response_model=ConvertResponse)
async def start_conversion(body: ConvertRequest):
    """
    Start the 6-stage conversion pipeline.

    The pipeline runs in the background. Connect to
    WebSocket /api/progress/{job_id} for real-time updates.
    """
    job = job_store.get_job_by_session(body.session_id)
    if not job:
        raise HTTPException(status_code=404, detail="Session not found. Upload a file first.")

    if job.status == JobStatus.PROCESSING:
        return ConvertResponse(job_id=job.job_id, status="already_processing")

    if job.status == JobStatus.COMPLETED:
        return ConvertResponse(job_id=job.job_id, status="already_completed")

    # Kick off pipeline in background
    job.status = JobStatus.PROCESSING
    task = asyncio.create_task(_run_pipeline_task(job, body))
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)

    logger.info("Conversion started: job=%s", job.job_id)
    return ConvertResponse(job_id=job.job_id, status="queued")


async def _run_pipeline_task(job, body: ConvertRequest):
    """Background task that runs the pipeline and updates job state."""

    # Stage → (overall_start%, overall_end%) for progress calculation
    _STAGE_WEIGHTS = {
        "parser": (0, 10),
        "splitter": (10, 20),
        "analyzer": (20, 35),
        "segmenter": (35, 90),
        "assembler": (90, 100),
    }

    _STAGE_LABELS = {
        "parser": "正在解析文件...",
        "splitter": "正在拆分章节...",
        "analyzer": "正在分析人物关系与情节线索...",
        "segmenter": "正在分割场景与提取对话...",
        "assembler": "正在生成 YAML 剧本...",
    }

    try:
        async def progress_callback(stage: str, pct: int):
            base, ceiling = _STAGE_WEIGHTS.get(stage, (0, 100))
            overall = base + (ceiling - base) * (pct / 100)
            job.progress[stage] = pct
            await job.notify({
                "type": "progress",
                "stage": stage,
                "progress": round(overall),
                "message": _STAGE_LABELS.get(stage, stage),
            })

        async def stream_callback(chunk: str) -> None:
            """Forward streaming LLM tokens to the WebSocket as 'thinking' messages."""
            await job.notify({"type": "thinking", "text": chunk})

        yaml_str = await run_pipeline(
            job.file_path,
            title=body.title,
            author=body.author,
            script_type=body.script_type,
            language=body.language,
            progress_callback=progress_callback,
            stream_callback=stream_callback,
        )

        job.yaml_result = yaml_str
        job.status = JobStatus.COMPLETED
        await job.notify({"type": "complete", "yaml": yaml_str})
        logger.info("Conversion completed: job=%s", job.job_id)

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = f"{type(e).__name__}: {e}"
        logger.error("Conversion failed: job=%s error=%s", job.job_id, e, exc_info=True)
        try:
            await job.notify({"type": "error", "error": job.error})
        except Exception:
            logger.error("Failed to notify error for job=%s", job.job_id)


@router.get("/result/{job_id}", response_model=ResultResponse)
async def get_result(job_id: str):
    """
    Get the conversion result as YAML.

    Returns 200 with YAML if complete, 202 if still processing, 404 if not found.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == JobStatus.COMPLETED:
        return ResultResponse(job_id=job_id, status="completed", yaml=job.yaml_result)

    if job.status == JobStatus.FAILED:
        return ResultResponse(job_id=job_id, status="failed", error=job.error)

    return JSONResponse(
        status_code=202,
        content=ResultResponse(
            job_id=job_id,
            status=job.status.value,
        ).model_dump(),
    )


@router.get("/schema")
async def get_schema():
    """
    Get the screenplay JSON Schema — used by the frontend Monaco editor for validation.
    """
    # Return a minimal schema for now; full schema from docs/yaml-schema.md
    return {
        "schema": {
            "type": "object",
            "required": ["meta", "characters", "locations", "acts"],
            "properties": {
                "meta": {"type": "object"},
                "characters": {"type": "array"},
                "locations": {"type": "array"},
                "acts": {"type": "array"},
            },
        }
    }


@router.post("/validate", response_model=ValidateResponse)
async def validate_yaml(body: ValidateRequest):
    """
    Validate user-edited YAML against the screenplay schema.
    """
    import yaml

    try:
        doc = yaml.safe_load(body.yaml_text)
    except yaml.YAMLError as e:
        return ValidateResponse(valid=False, errors=[f"YAML parse error: {e}"])

    if not isinstance(doc, dict):
        return ValidateResponse(valid=False, errors=["YAML root must be a mapping"])

    errors = []
    for key in ("meta", "characters", "locations", "acts"):
        if key not in doc:
            errors.append(f"Missing required key: {key}")

    return ValidateResponse(valid=len(errors) == 0, errors=errors)
