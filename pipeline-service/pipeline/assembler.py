"""
Stage 6: YAML Assembler — code-driven final assembly.

Assembles all extracted data into a valid screenplay YAML:
  1. Build PyYAML data structure matching the schema
  2. Normalize IDs (sequential ASCII IDs for Chinese names — schema requires
     pattern ^[a-z][a-z0-9_]*$ which Chinese characters cannot satisfy)
  3. Validate against the authoritative JSON Schema in models/schema.yaml
     (loaded once at module import; replaces the previous minimal stub)
  4. Serialize with PyYAML safe_dump (allow_unicode=True, sort_keys=False)
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import ValidationError, validate

logger = logging.getLogger(__name__)


class SchemaValidationError(Exception):
    """Assembled YAML fails schema validation."""


# Load the authoritative schema once at module import time. This replaces
# the previous minimal stub that only checked top-level keys; the real
# schema enforces character/location ID patterns, enum values for scene
# heading types/times, and other constraints that were previously silently
# allowed through.
_SCHEMA_PATH = Path(__file__).parent.parent / "models" / "schema.yaml"
try:
    with open(_SCHEMA_PATH, encoding="utf-8") as _f:
        _SCREENPLAY_SCHEMA = yaml.safe_load(_f)
except FileNotFoundError as e:
    raise RuntimeError(
        f"Screenplay schema not found at {_SCHEMA_PATH}. "
        "This file is required for output validation."
    ) from e


# Pattern mirrored from models/schema.yaml — used to validate caller-provided
# IDs before accepting them. If the caller's ID does not match, we generate a
# fresh sequential ASCII ID instead.
_ASCII_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def _make_ascii_id(prefix: str, index: int) -> str:
    """
    Generate a schema-compliant ASCII ID for a character or location.

    The schema requires character.id and location.id to match
    ^[a-z][a-z0-9_]*$. Chinese names cannot satisfy this directly; we
    generate sequential IDs (c1, c2, ... for characters; l1, l2, ... for
    locations) and preserve the original Chinese name in the `name` field.
    """
    return f"{prefix}{index}"


def _resolve_id(
    provided: str | None,
    prefix: str,
    seq: int,
) -> str:
    """
    Pick a schema-valid ID, preferring caller-provided value if compatible.

    Args:
        provided: ID supplied by the caller (may be None or non-ASCII)
        prefix: 'c' for characters, 'l' for locations
        seq: 1-based sequence number used as fallback suffix

    Returns:
        Validated or generated ID matching ^[a-z][a-z0-9_]*$.
    """
    if provided and _ASCII_ID_PATTERN.match(provided):
        return provided
    return _make_ascii_id(prefix, seq)


def assemble_yaml(
    *,
    meta: dict[str, Any],
    characters: list[dict[str, Any]],
    locations: list[dict[str, Any]],
    scenes_by_chapter: dict[int, list[dict[str, Any]]],
    beats_by_scene: dict[str, list[dict[str, Any]]],
) -> str:
    """
    Assemble the final screenplay YAML from pipeline data.

    Args:
        meta: metadata dict (title, type, language, synopsis, etc.)
        characters: list of character dicts from Stage 3
        locations: list of location dicts from Stage 3
        scenes_by_chapter: {chapter_order: [scene_dict, ...]} from Stage 4
        beats_by_scene: {scene_key: [beat_dict, ...]} from Stage 5

    Returns:
        Validated YAML string ready for export.

    Raises:
        SchemaValidationError: if assembled YAML fails schema validation
    """
    # 1. Build character table with sequential ASCII IDs (deduplicate by name)
    char_table = []
    char_id_map: dict[str, str] = {}  # name → id
    seen_names: set = set()
    char_seq = 0
    for c in characters:
        name = c.get("name", "")
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        char_seq += 1
        cid = _resolve_id(c.get("id"), "c", char_seq)
        char_id_map[name] = cid
        char_table.append({
            "id": cid,
            "name": name,
            "aliases": c.get("aliases", []),
            "role": c.get("role", "extra"),
            "description": c.get("description", ""),
        })

    # 2. Build location table with sequential ASCII IDs (deduplicate by name)
    loc_table = []
    loc_id_map: dict[str, str] = {}  # name → id
    seen_locs: set = set()
    loc_seq = 0
    for l in locations:
        name = l.get("name", "")
        if not name or name in seen_locs:
            continue
        seen_locs.add(name)
        loc_seq += 1
        lid = _resolve_id(l.get("id"), "l", loc_seq)
        loc_id_map[name] = lid
        loc_table.append({
            "id": lid,
            "name": name,
            "type": l.get("type", "mixed"),
            "description": l.get("description", ""),
        })

    # 3. Build scenes with beats
    all_scenes = []
    scene_counter = 0
    for chapter_order in sorted(scenes_by_chapter.keys()):
        scenes = scenes_by_chapter[chapter_order]
        for local_idx, scene in enumerate(scenes, 1):
            scene_counter += 1
            # Per-chapter scene key matching orchestrator's indexing
            scene_key = f"ch{chapter_order}_s{local_idx}"
            scene_id = f"S{scene_counter:03d}"

            # Map location name to location ID
            loc_name = scene.get("location", "未知")
            loc_ref = loc_id_map.get(loc_name, loc_name)

            # Get beats for this scene
            beats_raw = beats_by_scene.get(scene_key, [])
            beats = []
            for b in beats_raw:
                # Map character name to character ID
                char_name = b.get("character_text")
                char_ref = char_id_map.get(char_name) if char_name else None

                beats.append({
                    "id": b.get("id", ""),
                    "type": b.get("type", "action"),
                    "character": char_ref,
                    "content": b.get("content", ""),
                    "parenthetical": b.get("parenthetical"),
                    "emotion": b.get("emotion"),
                })

            all_scenes.append({
                "id": scene_id,
                "number": scene_counter,
                "heading": {
                    "location": loc_ref,
                    "time": scene.get("time", "continuous"),
                    "type": scene.get("type", "interior"),
                },
                "description": scene.get("description", ""),
                "beats": beats,
                "notes": f"Chapter {chapter_order}, segment {scene.get('text_segment', [0, 0])}",
            })

    # 4. Build top-level structure
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc = {
        "meta": {
            "title": meta.get("title", "未命名剧本"),
            "original_title": meta.get("original_title", ""),
            "author": meta.get("author", ""),
            "adapter": meta.get("adapter", "Novel-to-Script AI"),
            "type": meta.get("type", "movie"),
            "language": meta.get("language", "zh"),
            "created_at": now,
            "source_chapters": meta.get("source_chapters", 0),
            "synopsis": meta.get("synopsis", ""),
        },
        "characters": char_table,
        "locations": loc_table,
        "acts": [
            {
                "id": "act_1",
                "title": "第一幕",
                "chapters": sorted(scenes_by_chapter.keys()),
                "scenes": all_scenes,
            }
        ],
    }

    # 5. Validate against the authoritative schema
    _validate_doc(doc)

    # 6. Serialize to YAML
    return yaml.dump(
        doc,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=120,
    )


def _validate_doc(doc: dict) -> None:
    """Validate assembled document against the authoritative screenplay schema."""
    try:
        validate(instance=doc, schema=_SCREENPLAY_SCHEMA)
    except ValidationError as e:
        raise SchemaValidationError(f"Assembled YAML fails schema: {e.message}") from e
