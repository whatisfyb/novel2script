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

from dataclasses import dataclass, field

from llm.client import llm_complete
from llm.prompts import SEGMENT_SCENES_PROMPT
from llm.pydantic_schemas import SegmentScenesOutput
from llm.schemas import SEGMENT_SCHEMA  # legacy fallback


@dataclass
class Scene:
    """A scene identified within a chapter."""

    id: str = ""
    number: int = 0
    heading: dict = field(default_factory=dict)
    location: str = ""
    time: str = "continuous"  # day, night, dawn, dusk, continuous
    type: str = "interior"    # interior, exterior
    description: str = ""
    text_segment: tuple[int, int] = (0, 0)  # (start_offset, end_offset) into chapter text
    chapter_order: int = 0


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
    )
    data = await llm_complete(prompt, pydantic_model=SegmentScenesOutput)

    # Get chapter text length for boundary checking
    text_len = len(chapter.text)

    scenes = []
    for idx, s in enumerate(data.get("scenes", []), start=1):
        seg = s.get("text_segment", [0, 0])
        if len(seg) == 2:
            start, end = seg
            # Boundary check: ensure text_segment is within chapter text bounds
            start = max(0, min(start, text_len))
            end = max(start, min(end, text_len))
        else:
            start, end = 0, text_len

        scenes.append(
            Scene(
                id=f"ch{chapter.order}_s{idx}",
                number=idx,
                heading={
                    "location": s.get("location", "未知"),
                    "time": s.get("time", "continuous"),
                    "type": s.get("type", "interior"),
                },
                location=s.get("location", "未知"),
                time=s.get("time", "continuous"),
                type=s.get("type", "interior"),
                description=s.get("description", ""),
                text_segment=(start, end),
                chapter_order=chapter.order,
            )
        )
    return scenes
