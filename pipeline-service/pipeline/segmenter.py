"""
Stage 4: Scene Segmenter — LLM-powered per-chapter scene detection.

For each chapter, identifies distinct scenes with:
  - location: scene setting
  - time: day/night/dawn/dusk/continuous
  - type: interior/exterior
  - description: environment description
  - text_segment: [start_offset, end_offset] into the chapter text

Runs per-chapter in parallel for throughput.
"""

from __future__ import annotations

from dataclasses import dataclass

from llm.client import llm_complete
from llm.prompts import SEGMENT_SCENES_PROMPT
from llm.schemas import SEGMENT_SCHEMA


@dataclass
class Scene:
    """A scene identified within a chapter."""

    location: str
    time: str  # day, night, dawn, dusk, continuous
    type: str  # interior, exterior
    description: str
    text_segment: tuple[int, int]  # (start_offset, end_offset) into chapter text
    chapter_order: int


async def segment_scenes(
    chapter,
    characters: list | None = None,
    locations: list | None = None,
) -> list[Scene]:
    """
    Segment a single chapter into distinct scenes.

    Args:
        chapter: Chapter object from Stage 2
        characters: list of Character objects from Stage 3 (for ID mapping)
        locations: list of Location objects from Stage 3

    Returns:
        List of Scene objects with text offset references.

    Raises:
        LLMError: if the LLM call fails after retries
    """
    # Build character/location context strings
    char_str = ", ".join(
        f"{c.name}({c.role})" for c in (characters or [])
    ) or "无"

    loc_str = ", ".join(
        f"{l.name}({l.type})" for l in (locations or [])
    ) or "无"

    prompt = SEGMENT_SCENES_PROMPT.format(
        characters=char_str,
        locations=loc_str,
        chapter_text=chapter.text,
        chapter_length=len(chapter.text),
    )
    data = await llm_complete(prompt, schema=SEGMENT_SCHEMA)

    scenes = []
    for s in data.get("scenes", []):
        seg = s.get("text_segment", [0, 0])
        scenes.append(
            Scene(
                location=s.get("location", "未知"),
                time=s.get("time", "continuous"),
                type=s.get("type", "interior"),
                description=s.get("description", ""),
                text_segment=(seg[0], seg[1]) if len(seg) == 2 else (0, 0),
                chapter_order=chapter.order,
            )
        )
    return scenes
