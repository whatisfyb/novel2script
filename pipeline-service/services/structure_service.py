"""
Structure Service — Analyzer + Segmenter.

Combines Stage 3 (structure analysis) and Stage 4 (scene segmentation) of
the legacy monolithic pipeline into a single FastAPI service.

Endpoints:
  POST /analyze — body {chapters: [Chapter]}, returns StructureResult
                  (synopsis, characters, locations)
  POST /segment — body {chapters, characters, locations}, returns
                  scenes_by_chapter (chapter_id → [Scene])
  POST /pipeline — convenience: analyze + segment in one call

Each request:
  1. Publishes pipeline events to Redis
  2. Updates run status

Run mode: `uvicorn services.structure_service:app --port 8002`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline.analyzer import analyze_structure, StructureResult
from pipeline.splitter import Chapter as SplitterChapter
from pipeline.segmenter import segment_scenes
from services.redis_store import RedisStore, get_default_store

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Novel-to-Script Structure Service",
    description="Structure analysis + scene segmentation",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# Pydantic schemas
class ChapterIn(BaseModel):
    id: int
    order: int
    title: str
    text: str


class AnalyzeRequest(BaseModel):
    chapters: list[ChapterIn]
    run_id: str | None = None


class Character(BaseModel):
    id: str
    name: str
    aliases: list[str] = []
    role: str = "extra"
    description: str = ""


class Location(BaseModel):
    id: str
    name: str
    type: str = "mixed"
    description: str = ""


class AnalyzeResponse(BaseModel):
    run_id: str | None = None
    synopsis: str
    characters: list[Character]
    locations: list[Location]


class SegmentRequest(BaseModel):
    chapters: list[ChapterIn]
    characters: list[Character]
    locations: list[Location]
    run_id: str | None = None


class Scene(BaseModel):
    id: str
    number: int
    heading: dict
    description: str
    text_segment: list[int]
    location: str
    time: str
    type: str


class SegmentResponse(BaseModel):
    run_id: str | None = None
    scenes_by_chapter: dict[int, list[Scene]]


class PipelineRequest(BaseModel):
    chapters: list[ChapterIn]
    run_id: str | None = None


class PipelineResponse(BaseModel):
    run_id: str | None = None
    synopsis: str
    characters: list[Character]
    locations: list[Location]
    scenes_by_chapter: dict[int, list[Scene]]


def get_store() -> RedisStore:
    return get_default_store()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "structure"}


def _chapter_to_internal(c: ChapterIn) -> SplitterChapter:
    """Convert API chapter to internal Chapter dataclass."""
    return SplitterChapter(order=c.order, title=c.title, text=c.text)


def _scenes_to_api(scenes: list) -> list[Scene]:
    return [
        Scene(
            id=s.id, number=s.number,
            heading=s.heading, description=s.description,
            text_segment=list(s.text_segment),
            location=s.location, time=s.time, type=s.type,
        )
        for s in scenes
    ]


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(req: AnalyzeRequest) -> AnalyzeResponse:
    store = get_store() if req.run_id else None
    if store and req.run_id:
        await store.append_event(
            run_id=req.run_id, event_type="structure.analyzing",
            source="structure_service", correlation_id=req.run_id,
            payload={"n_chapters": len(req.chapters)},
        )

    chapters = [_chapter_to_internal(c) for c in req.chapters]
    try:
        result: StructureResult = await analyze_structure(chapters)
    except Exception as e:
        if store and req.run_id:
            await store.append_event(
                run_id=req.run_id, event_type="structure.analyze_failed",
                source="structure_service", correlation_id=req.run_id,
                payload={"error": str(e)},
            )
        raise HTTPException(status_code=500, detail=f"Analyze failed: {e}")

    if store and req.run_id:
        await store.append_event(
            run_id=req.run_id, event_type="structure.analyzed",
            source="structure_service", correlation_id=req.run_id,
            payload={"n_characters": len(result.characters), "n_locations": len(result.locations)},
        )
        await store.set_status(req.run_id, stage="structure_analyzed", progress=40)

    return AnalyzeResponse(
        run_id=req.run_id,
        synopsis=result.synopsis,
        characters=[
            Character(id=getattr(c, "id", c.name), name=c.name, aliases=c.aliases,
                      role=c.role, description=c.description)
            for c in result.characters
        ],
        locations=[
            Location(id=getattr(l, "id", l.name), name=l.name, type=l.type, description=l.description)
            for l in result.locations
        ],
    )


@app.post("/segment", response_model=SegmentResponse)
async def segment_endpoint(req: SegmentRequest) -> SegmentResponse:
    store = get_store() if req.run_id else None
    if store and req.run_id:
        await store.append_event(
            run_id=req.run_id, event_type="structure.segmenting",
            source="structure_service", correlation_id=req.run_id,
            payload={"n_chapters": len(req.chapters)},
        )

    chapters = [_chapter_to_internal(c) for c in req.chapters]
    characters_internal = [c.model_dump() for c in req.characters]
    locations_internal = [l.model_dump() for l in req.locations]

    # Segment per chapter in parallel
    async def segment_one(ch) -> tuple[int, list]:
        scenes = await segment_scenes(
            ch, characters=characters_internal, locations=locations_internal,
        )
        return ch.order, scenes

    try:
        results = await asyncio.gather(
            *(segment_one(c) for c in chapters), return_exceptions=True,
        )
    except Exception as e:
        if store and req.run_id:
            await store.append_event(
                run_id=req.run_id, event_type="structure.segment_failed",
                source="structure_service", correlation_id=req.run_id,
                payload={"error": str(e)},
            )
        raise HTTPException(status_code=500, detail=f"Segment failed: {e}")

    scenes_by_chapter: dict[int, list[Scene]] = {}
    for order, result in zip((c.order for c in chapters), results):
        if isinstance(result, Exception):
            logger.warning("Segment chapter %d failed: %s", order, result)
            scenes_by_chapter[order] = []
        else:
            _, scenes = result
            scenes_by_chapter[order] = _scenes_to_api(scenes)

    if store and req.run_id:
        n_scenes = sum(len(s) for s in scenes_by_chapter.values())
        await store.append_event(
            run_id=req.run_id, event_type="structure.segmented",
            source="structure_service", correlation_id=req.run_id,
            payload={"n_scenes": n_scenes},
        )
        await store.set_status(req.run_id, stage="structure_done", progress=60)

    return SegmentResponse(run_id=req.run_id, scenes_by_chapter=scenes_by_chapter)


@app.post("/pipeline", response_model=PipelineResponse)
async def pipeline_endpoint(req: PipelineRequest) -> PipelineResponse:
    """Analyze + segment in one call."""
    analyze_resp = await analyze_endpoint(AnalyzeRequest(
        chapters=req.chapters, run_id=req.run_id,
    ))
    seg_resp = await segment_endpoint(SegmentRequest(
        chapters=req.chapters,
        characters=analyze_resp.characters,
        locations=analyze_resp.locations,
        run_id=req.run_id,
    ))
    return PipelineResponse(
        run_id=req.run_id,
        synopsis=analyze_resp.synopsis,
        characters=analyze_resp.characters,
        locations=analyze_resp.locations,
        scenes_by_chapter=seg_resp.scenes_by_chapter,
    )
