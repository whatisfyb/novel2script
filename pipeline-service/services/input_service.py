"""
Input Service — Parser + Splitter.

Combines Stage 1 (file parsing) and Stage 2 (chapter splitting) of the
legacy monolithic pipeline into a single FastAPI service.

Endpoints:
  POST /parse   — multipart upload, returns {filename, raw_text}
  POST /split   — body {raw_text, filename?}, returns {chapters: [Chapter]}
  POST /pipeline — convenience: upload + split in one call

Each request:
  1. Publishes pipeline events to Redis (pipeline:events:{run_id})
  2. Updates run status (pipeline:status:{run_id})

Run mode: standalone via `uvicorn services.input_service:app --port 8001`.
"""

from __future__ import annotations

import io
import logging
import os
import re
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline.parser import parse_file, RawText
from pipeline.splitter import split_chapters
from services.redis_store import RedisStore, get_default_store

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Local helper: parse bytes in-memory (without writing to disk)
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".docx"}


def parse_bytes(content: bytes, filename: str) -> str:
    """Parse file bytes → raw text. Mirrors `parse_file` but takes bytes."""
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file format: {suffix}")

    if suffix in (".txt",):
        import chardet
        detected = chardet.detect(content)
        encoding = detected.get("encoding") or "utf-8"
        return content.decode(encoding, errors="replace")
    if suffix in (".md", ".markdown"):
        import re
        text = content.decode("utf-8", errors="replace")
        # Convert markdown headings to "第N章"-style markers for the splitter
        text = re.sub(
            r"^(#{1,6})\s+(.+)$",
            lambda m: f"\n第X章 {m.group(2)}\n",
            text, flags=re.MULTILINE,
        )
        return text
    if suffix == ".docx":
        from docx import Document
        doc = Document(io.BytesIO(content))
        out: list[str] = []
        for para in doc.paragraphs:
            style = (para.style.name or "").lower() if para.style else ""
            if "heading 1" in style:
                out.append(f"\n第X章 {para.text}\n")
            else:
                out.append(para.text)
        return "\n".join(out)
    raise ValueError(f"Unhandled extension: {suffix}")


app = FastAPI(
    title="Novel-to-Script Input Service",
    description="File parsing + chapter splitting",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# Pydantic schemas
class SplitRequest(BaseModel):
    raw_text: str
    filename: str = "untitled.txt"
    run_id: str | None = None


class Chapter(BaseModel):
    id: int
    order: int
    title: str
    text: str


class SplitResponse(BaseModel):
    filename: str
    run_id: str | None = None
    chapters: list[Chapter]


def get_store() -> RedisStore:
    return get_default_store()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "input"}


@app.post("/parse")
async def parse_endpoint(
    file: UploadFile = File(...),
    run_id: str | None = None,
) -> dict[str, Any]:
    """Parse an uploaded file to raw text."""
    content = await file.read()
    try:
        raw_text = parse_bytes(content, file.filename or "upload.txt")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse failed: {e}")

    if run_id:
        store = get_store()
        await store.append_event(
            run_id=run_id, event_type="input.parsed",
            source="input_service", correlation_id=run_id,
            payload={"filename": file.filename, "char_count": len(raw_text)},
        )

    return {
        "filename": file.filename,
        "raw_text": raw_text,
        "char_count": len(raw_text),
    }


@app.post("/split", response_model=SplitResponse)
async def split_endpoint(req: SplitRequest) -> SplitResponse:
    """Split raw text into chapters."""
    store = get_store() if req.run_id else None
    if store and req.run_id:
        await store.append_event(
            run_id=req.run_id, event_type="input.splitting",
            source="input_service", correlation_id=req.run_id,
            payload={"filename": req.filename, "char_count": len(req.raw_text)},
        )

    try:
        chapters = split_chapters(req.raw_text)
    except Exception as e:
        if store and req.run_id:
            await store.append_event(
                run_id=req.run_id, event_type="input.split_failed",
                source="input_service", correlation_id=req.run_id,
                payload={"error": str(e)},
            )
        raise HTTPException(status_code=500, detail=f"Split failed: {e}")

    chapter_models = [
        Chapter(id=str(c.order), order=c.order, title=c.title, text=c.text)
        for c in chapters
    ]

    if store and req.run_id:
        await store.append_event(
            run_id=req.run_id, event_type="input.split_done",
            source="input_service", correlation_id=req.run_id,
            payload={"n_chapters": len(chapter_models)},
        )
        await store.set_status(req.run_id, stage="input_done", progress=20)

    return SplitResponse(
        filename=req.filename, run_id=req.run_id, chapters=chapter_models,
    )


@app.post("/pipeline", response_model=SplitResponse)
async def pipeline_endpoint(
    file: UploadFile = File(...),
    run_id: str | None = None,
) -> SplitResponse:
    """Convenience: upload + split in one call."""
    content = await file.read()
    try:
        raw_text = parse_bytes(content, file.filename or "upload.txt")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse failed: {e}")

    store = get_store() if run_id else None
    if store and run_id:
        await store.append_event(
            run_id=run_id, event_type="input.parsed",
            source="input_service", correlation_id=run_id,
            payload={"filename": file.filename, "char_count": len(raw_text)},
        )

    try:
        chapters = split_chapters(raw_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Split failed: {e}")

    chapter_models = [
        Chapter(id=str(c.order), order=c.order, title=c.title, text=c.text)
        for c in chapters
    ]

    if store and run_id:
        await store.append_event(
            run_id=run_id, event_type="input.split_done",
            source="input_service", correlation_id=run_id,
            payload={"n_chapters": len(chapter_models)},
        )
        await store.set_status(run_id, stage="input_done", progress=20)

    return SplitResponse(
        filename=file.filename or "upload.txt",
        run_id=run_id, chapters=chapter_models,
    )
