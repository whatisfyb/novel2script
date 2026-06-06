"""
Beat Service — Extractor + Critic + optional Refiner (LangGraph).

The most complex service: implements a 3-node LangGraph workflow that
takes a single scene and produces character-attributed beats with
self-correction.

Graph:
                 ┌──────────────┐
                 │  extractor   │  LLM call + heuristic fallback
                 └──────┬───────┘
                        │ beats
                        ▼
                 ┌──────────────┐
                 │   critic     │  LLM call (HAR review)
                 └──────┬───────┘
                        │ corrections (or empty)
                        ▼
                ┌──────────────────┐
                │  has_corrections? │
                └───┬──────────────┘
                    │ yes        │ no
                    ▼            │
             ┌──────────┐        │
             │ refiner  │        │
             └────┬─────┘        │
                  │              │
                  ▼              ▼
                 ┌──────────────┐
                 │   finalize   │
                 └──────────────┘

Endpoint:
  POST /extract — body {scene, characters, run_id}, returns {beats, corrections}
  POST /extract_batch — body {scenes, characters, run_id}, returns beats_by_scene

Run mode: `uvicorn services.beat_service:app --port 8003`.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, TypedDict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from llm.client import llm_complete
from llm.prompts import CRITIC_PROMPT, EXTRACT_BEATS_PROMPT, REFINER_PROMPT
from llm.schemas import CRITIC_SCHEMA, EXTRACT_SCHEMA, REFINER_SCHEMA
from services.redis_store import RedisStore, get_default_store

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Novel-to-Script Beat Service",
    description="LLM-based beat extraction with critic+refiner self-correction (LangGraph)",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class CharacterIn(BaseModel):
    id: str
    name: str
    aliases: list[str] = []
    role: str = "extra"
    description: str = ""


class SceneIn(BaseModel):
    scene_id: str           # e.g. "ch1_s1"
    chapter_order: int
    scene_text: str
    chapter_text: str | None = None
    scene_meta: dict | None = None   # description, location, time, etc.


class ExtractRequest(BaseModel):
    scene: SceneIn
    characters: list[CharacterIn]
    run_id: str | None = None


class BeatOut(BaseModel):
    id: str
    type: str
    character_id: str | None = None
    character_text: str | None = None
    content: str
    parenthetical: str | None = None
    emotion: str | None = None


class CorrectionOut(BaseModel):
    beat_id: str
    issue: str
    fix: dict
    confidence: float
    reasoning: str | None = None


class ExtractResponse(BaseModel):
    scene_id: str
    beats: list[BeatOut]
    corrections: list[CorrectionOut] = []
    refined: bool = False
    error: str | None = None


class BatchExtractRequest(BaseModel):
    scenes: list[SceneIn]
    characters: list[CharacterIn]
    run_id: str | None = None


class BatchExtractResponse(BaseModel):
    beats_by_scene: dict[str, list[BeatOut]]
    run_id: str | None = None


# ---------------------------------------------------------------------------
# Local Beat dataclass (kept simple; service-internal representation)
# ---------------------------------------------------------------------------

@dataclass
class Beat:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = "action"
    character_id: str | None = None
    character_text: str | None = None
    content: str = ""
    parenthetical: str | None = None
    emotion: str | None = None


# ---------------------------------------------------------------------------
# In-line attribution heuristics (kept here so the service is self-contained)
# ---------------------------------------------------------------------------

_FEMALE_HINTS = "薇娜丽芳红梅兰莲花英萍素"
_MALE_HINTS = "远明强军勇刚伟国建"


def _apply_attribution(beats: list[Beat], characters: list[dict], scene_text: str) -> list[Beat]:
    """Light attribution pass on the LLM output.

    Heuristics (in order):
      1. Pre-pass: clear `character_text` that is not a known name/alias.
      2. Pre-pass: clear dialogue self-references (content starts with the
         attributed name + address punctuation).
      3. For unowned dialogue, run alternation (last speaker → other).
      4. For unowned dialogue with no prior, fall back to a non-PoV char.
      5. For unowned action, attribute to the most recent action char.
    """
    # Build valid names
    valid_names: set[str] = set()
    for c in characters:
        n = c.get("name", "")
        if n:
            valid_names.add(n)
        for a in c.get("aliases", []) or []:
            if a:
                valid_names.add(a)

    # Pre-pass: clear invalid / self-referencing
    for b in beats:
        if b.type not in ("dialogue", "voiceover"):
            continue
        if not b.character_text:
            continue
        if b.character_text not in valid_names:
            b.character_text = None
            continue
        if b.type == "dialogue":
            content = b.content or ""
            name = b.character_text
            if content.startswith(name) and len(content) > len(name):
                nxt = content[len(name)]
                if nxt in "，,。.！!？?：: 　":
                    b.character_text = None

    # Determine active speakers
    active_speakers = [
        c["name"] for c in characters
        if c.get("name") and c["name"] in scene_text
    ]

    # Heuristic loop on dialogue/voiceover
    last_dialogue_speaker: str | None = None
    for b in beats:
        if b.type not in ("dialogue", "voiceover"):
            continue
        if b.character_text:
            if b.type == "dialogue":
                last_dialogue_speaker = b.character_text
            continue
        # alternation
        if last_dialogue_speaker and len(active_speakers) > 1:
            for s in active_speakers:
                if s != last_dialogue_speaker:
                    b.character_text = s
                    last_dialogue_speaker = s
                    break
            continue
        # voiceover → first speaker
        if b.type == "voiceover" and active_speakers:
            b.character_text = active_speakers[0]
            continue
        # dialogue without prior → pick non-PoV (last in list = "visitor")
        if b.type == "dialogue" and active_speakers:
            b.character_text = active_speakers[-1]
            last_dialogue_speaker = b.character_text

    # Action beats: attribute to most recent action char
    last_action_char: str | None = None
    for b in beats:
        if b.type != "action":
            continue
        if b.character_text:
            last_action_char = b.character_text
            continue
        if last_action_char:
            b.character_text = last_action_char
        elif active_speakers:
            b.character_text = active_speakers[0]
            last_action_char = b.character_text

    return beats


# ---------------------------------------------------------------------------
# LangGraph state and nodes
# ---------------------------------------------------------------------------

class BeatGraphState(TypedDict, total=False):
    # Inputs
    scene_id: str
    scene_text: str
    chapter_text: str | None
    characters: list[dict]
    run_id: str | None

    # Populated by nodes
    beats: list[dict]
    corrections: list[dict]
    has_corrections: bool
    refined: bool
    error: str | None
    start_ts: float
    extract_ts: float
    critic_ts: float
    refine_ts: float


# ---------------- Extractor node ----------------

async def extractor_node(state: BeatGraphState) -> dict:
    """Call LLM with EXTRACT_BEATS_PROMPT, apply fallback attribution."""
    characters = state["characters"]
    char_parts = [
        f"{c['name']}(id:{c.get('id', c['name'])})" for c in characters
    ]
    char_str = ", ".join(char_parts) if char_parts else "无"

    prompt = EXTRACT_BEATS_PROMPT.format(
        characters=char_str, scene_text=state["scene_text"],
    )
    data = await llm_complete(prompt, schema=EXTRACT_SCHEMA)

    beats = []
    for b in data.get("beats", []):
        beats.append(Beat(
            type=b.get("type", "action"),
            character_id=b.get("character_id"),
            character_text=b.get("character_text"),
            content=b.get("content", ""),
            parenthetical=b.get("parenthetical"),
            emotion=b.get("emotion"),
        ))

    # Apply in-service attribution
    _apply_attribution(beats, characters, state["scene_text"])

    beats_payload = [
        {
            "id": b.id, "type": b.type, "character_id": b.character_id,
            "character_text": b.character_text, "content": b.content,
            "parenthetical": b.parenthetical, "emotion": b.emotion,
        }
        for b in beats
    ]

    return {
        "beats": beats_payload,
        "extract_ts": time.time(),
    }


# ---------------- Critic node ----------------

async def critic_node(state: BeatGraphState) -> dict:
    """Call LLM with CRITIC_PROMPT to review extracted beats.

    Apply high-confidence corrections directly. The result is
    `corrections` (applied ones) + `has_corrections` boolean.
    """
    beats = state.get("beats", [])
    if not beats:
        return {"corrections": [], "has_corrections": False, "critic_ts": time.time()}

    characters = state["characters"]
    char_parts = [
        f"{c['name']}(id:{c.get('id', c['name'])})" for c in characters
    ]
    char_str = ", ".join(char_parts) if char_parts else "无"

    beats_yaml = _beats_to_yaml(beats)

    prompt = CRITIC_PROMPT.format(
        characters=char_str,
        scene_text=state["scene_text"],
        beats_yaml=beats_yaml,
    )

    data = await llm_complete(prompt, schema=CRITIC_SCHEMA)
    corrections = data.get("corrections", [])

    # Apply high-confidence corrections to beats in-place
    beat_by_id = {b["id"]: b for b in beats}
    applied: list[dict] = []
    confidence_threshold = 0.5
    for corr in corrections:
        if corr.get("confidence", 0.0) < confidence_threshold:
            continue
        bid = corr.get("beat_id")
        if bid not in beat_by_id:
            continue
        beat = beat_by_id[bid]
        for field, val in corr.get("fix", {}).items():
            beat[field] = val
        applied.append(corr)

    return {
        "beats": beats,
        "corrections": applied,
        "has_corrections": bool(applied),
        "critic_ts": time.time(),
    }


# ---------------- Refiner node (conditional) ----------------

async def refiner_node(state: BeatGraphState) -> dict:
    """Call LLM with REFINER_PROMPT to refine beats based on critic feedback.

    The refiner sees the original beats + critic's corrections + the source
    text. It produces the final beat list. This is the last node.
    """
    beats = state.get("beats", [])
    corrections = state.get("corrections", [])
    characters = state["characters"]
    char_parts = [
        f"{c['name']}(id:{c.get('id', c['name'])})" for c in characters
    ]
    char_str = ", ".join(char_parts) if char_parts else "无"

    beats_yaml = _beats_to_yaml(beats)
    corrections_yaml = _corrections_to_yaml(corrections)

    prompt = REFINER_PROMPT.format(
        characters=char_str,
        scene_text=state["scene_text"],
        beats_yaml=beats_yaml,
        corrections_yaml=corrections_yaml,
    )
    data = await llm_complete(prompt, schema=REFINER_SCHEMA)

    # Refiner returns full refined beats
    refined_beats = data.get("beats", beats)

    return {
        "beats": refined_beats,
        "refined": True,
        "refine_ts": time.time(),
    }


# ---------------- Conditional routing ----------------

def should_refine(state: BeatGraphState) -> str:
    """Route to refiner if critic found issues, else END."""
    if state.get("has_corrections"):
        return "refiner"
    return END


# ---------------- Build the graph ----------------

def _build_graph():
    """Compile the LangGraph once and return the runnable."""
    workflow = StateGraph(BeatGraphState)

    workflow.add_node("extractor", extractor_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("refiner", refiner_node)

    workflow.add_edge(START, "extractor")
    workflow.add_edge("extractor", "critic")
    workflow.add_conditional_edges(
        "critic", should_refine, {"refiner": "refiner", END: END},
    )
    workflow.add_edge("refiner", END)

    return workflow.compile()


_beat_graph = None


def get_graph():
    """Lazy-init the compiled graph (allows tests to import the module)."""
    global _beat_graph
    if _beat_graph is None:
        _beat_graph = _build_graph()
    return _beat_graph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _beats_to_yaml(beats: list[dict]) -> str:
    lines = []
    for b in beats:
        lines.append(f"- id: {b.get('id', '?')}")
        lines.append(f"  type: {b.get('type', 'action')}")
        if b.get("character_text"):
            lines.append(f"  character: {b['character_text']}")
        if b.get("content"):
            c = b["content"].replace('"', '\\"')
            lines.append(f'  content: "{c}"')
        if b.get("parenthetical"):
            lines.append(f"  parenthetical: {b['parenthetical']}")
        if b.get("emotion"):
            lines.append(f"  emotion: {b['emotion']}")
    return "\n".join(lines) if lines else "（无节拍）"


def _corrections_to_yaml(corrections: list[dict]) -> str:
    if not corrections:
        return "（无修正）"
    lines = []
    for c in corrections:
        lines.append(f"- beat_id: {c.get('beat_id')}")
        lines.append(f"  issue: {c.get('issue')}")
        lines.append(f"  confidence: {c.get('confidence', 0)}")
        if c.get("reasoning"):
            lines.append(f"  reasoning: {c['reasoning']}")
        fix = c.get("fix", {})
        for k, v in fix.items():
            lines.append(f"  fix.{k}: {v}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

def get_store() -> RedisStore:
    return get_default_store()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "beat"}


def _beat_to_out(b: dict) -> BeatOut:
    return BeatOut(
        id=b["id"], type=b["type"],
        character_id=b.get("character_id"),
        character_text=b.get("character_text"),
        content=b.get("content", ""),
        parenthetical=b.get("parenthetical"),
        emotion=b.get("emotion"),
    )


def _correction_to_out(c: dict) -> CorrectionOut:
    return CorrectionOut(
        beat_id=c.get("beat_id", ""),
        issue=c.get("issue", ""),
        fix=c.get("fix", {}),
        confidence=c.get("confidence", 0.0),
        reasoning=c.get("reasoning"),
    )


async def _process_scene_internal(
    scene: SceneIn,
    characters: list[CharacterIn],
    run_id: str | None,
) -> ExtractResponse:
    store = get_store() if run_id else None
    chars_dicts = [c.model_dump() for c in characters]

    if store and run_id:
        await store.append_event(
            run_id=run_id, event_type="scene.submitted",
            source="beat_service", correlation_id=scene.scene_id,
            payload={
                "scene_id": scene.scene_id,
                "n_characters": len(characters),
            },
        )

    initial_state: BeatGraphState = {
        "scene_id": scene.scene_id,
        "scene_text": scene.scene_text,
        "chapter_text": scene.chapter_text,
        "characters": chars_dicts,
        "run_id": run_id,
        "start_ts": time.time(),
    }

    try:
        graph = get_graph()
        final_state = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.error("Beat service failed for %s: %s", scene.scene_id, e)
        if store and run_id:
            await store.append_event(
                run_id=run_id, event_type="scene.failed",
                source="beat_service", correlation_id=scene.scene_id,
                payload={"error": str(e), "stage": "graph"},
            )
        return ExtractResponse(
            scene_id=scene.scene_id, beats=[], error=str(e),
        )

    beats_out = [_beat_to_out(b) for b in final_state.get("beats", [])]
    corrections_out = [
        _correction_to_out(c) for c in final_state.get("corrections", [])
    ]

    if store and run_id:
        await store.append_event(
            run_id=run_id, event_type="beats.finalized",
            source="beat_service", correlation_id=scene.scene_id,
            payload={
                "n_beats": len(beats_out),
                "n_corrections": len(corrections_out),
                "refined": final_state.get("refined", False),
            },
        )

    return ExtractResponse(
        scene_id=scene.scene_id,
        beats=beats_out,
        corrections=corrections_out,
        refined=final_state.get("refined", False),
    )


@app.post("/extract", response_model=ExtractResponse)
async def extract_endpoint(req: ExtractRequest) -> ExtractResponse:
    return await _process_scene_internal(req.scene, req.characters, req.run_id)


@app.post("/extract_batch", response_model=BatchExtractResponse)
async def extract_batch_endpoint(req: BatchExtractRequest) -> BatchExtractResponse:
    import asyncio
    results = await asyncio.gather(
        *(_process_scene_internal(s, req.characters, req.run_id) for s in req.scenes),
        return_exceptions=True,
    )
    beats_by_scene: dict[str, list[BeatOut]] = {}
    for scene, result in zip(req.scenes, results):
        if isinstance(result, Exception):
            logger.warning("Batch extract failed for %s: %s", scene.scene_id, result)
            beats_by_scene[scene.scene_id] = []
        else:
            beats_by_scene[scene.scene_id] = result.beats
    return BatchExtractResponse(beats_by_scene=beats_by_scene, run_id=req.run_id)
