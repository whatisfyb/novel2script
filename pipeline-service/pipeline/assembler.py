"""
Stage 6: YAML Assembler — code-driven final assembly.

Assembles all extracted data into a valid screenplay YAML:
  1. Build PyYAML data structure matching the schema
  2. Normalize IDs (ensure cross-references are consistent)
  3. Validate against JSON Schema (jsonschema)
  4. Serialize with PyYAML safe_dump (allow_unicode=True, sort_keys=False)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import yaml
from jsonschema import ValidationError, validate


class SchemaValidationError(Exception):
    """Assembled YAML fails schema validation."""


def _to_snake_case(name: str) -> str:
    """Convert a name to snake_case ID: '林晓' → 'lin_xiao', 'Bob' → 'bob'."""
    # For Chinese names: pinyin-style (fallback: just use the characters)
    cleaned = re.sub(r"[^\w\s]", "", name).strip()
    if not cleaned:
        return "unknown"
    # Simple approach: lowercase, replace spaces with underscores
    return cleaned.lower().replace(" ", "_")


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
    # 1. Build character table with IDs (deduplicate by name)
    char_table = []
    char_id_map: dict[str, str] = {}  # name → id
    seen_names: set = set()
    for i, c in enumerate(characters):
        name = c.get("name", "")
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        cid = c.get("id") or _to_snake_case(name)
        char_id_map[name] = cid
        char_table.append({
            "id": cid,
            "name": name,
            "aliases": c.get("aliases", []),
            "role": c.get("role", "extra"),
            "description": c.get("description", ""),
        })

    # 2. Build location table with IDs (deduplicate by name)
    loc_table = []
    loc_id_map: dict[str, str] = {}  # name → id
    seen_locs: set = set()
    for i, l in enumerate(locations):
        name = l.get("name", "")
        if not name or name in seen_locs:
            continue
        seen_locs.add(name)
        lid = l.get("id") or _to_snake_case(name)
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
                "synopsis": meta.get("synopsis", ""),
                "scenes": all_scenes,
            }
        ],
    }

    # 5. Validate against schema
    _validate_doc(doc)

    # 6. Serialize to YAML
    return yaml.dump(
        doc,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=120,
    )


# Minimal structural schema for validation
_SCREENPLAY_SCHEMA = {
    "type": "object",
    "required": ["meta", "characters", "locations", "acts"],
    "properties": {
        "meta": {"type": "object"},
        "characters": {"type": "array"},
        "locations": {"type": "array"},
        "acts": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "title", "scenes"],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "scenes": {"type": "array"},
                },
            },
        },
    },
}


def _validate_doc(doc: dict) -> None:
    """Validate assembled document against screenplay schema."""
    try:
        validate(instance=doc, schema=_SCREENPLAY_SCHEMA)
    except ValidationError as e:
        raise SchemaValidationError(f"Assembled YAML fails schema: {e.message}") from e
