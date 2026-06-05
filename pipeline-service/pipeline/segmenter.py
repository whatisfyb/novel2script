"""
Stage 4: Scene Segmenter — LLM-powered per-chapter scene detection.

For each chapter, identifies distinct scenes with:
  - location: scene setting
  - time: day/night/dawn/dusk/continuous
  - type: interior/exterior
  - description: environment description
  - text_segment: [start_offset, end_offset] into the chapter text

Runs per-chapter in parallel for throughput.

Defense-in-depth: LLM-returned offsets are snapped to the nearest sentence
boundary to prevent mid-sentence truncation, and coverage gaps/overlaps are
logged as warnings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from llm.client import llm_complete
from llm.prompts import SEGMENT_SCENES_PROMPT
from llm.schemas import SEGMENT_SCHEMA

logger = logging.getLogger(__name__)

# Characters that mark sentence/clause/dialogue boundaries for offset snapping.
# When a snap target is needed, we look for these characters and place the
# offset immediately AFTER them.
_BOUNDARY_CHARS = set("。！？…\n\"'\"'」』）")


@dataclass
class Scene:
    """A scene identified within a chapter."""

    location: str
    time: str  # day, night, dawn, dusk, continuous
    type: str  # interior, exterior
    description: str
    text_segment: tuple[int, int]  # (start_offset, end_offset) into chapter text
    chapter_order: int


def _snap_offset_to_boundary(text: str, offset: int, snap_forward: bool) -> int:
    """
    Snap an offset to the nearest sentence boundary.

    Used defensively on LLM-returned offsets to prevent mid-sentence
    truncation. Even when the prompt asks the LLM to align to boundaries,
    LLM output may still be imprecise; this function guarantees the returned
    offset falls immediately after a boundary character (or at text bounds).

    Args:
        text: full chapter text
        offset: original offset from LLM (0-indexed character position)
        snap_forward: if True (for end offsets), snap to next boundary at or
            after offset; if False (for start offsets), snap to previous
            boundary before offset.

    Returns:
        Adjusted offset that falls on a sentence boundary. Returns 0 if
        offset <= 0, len(text) if offset >= len(text).
    """
    if offset <= 0:
        return 0
    if offset >= len(text):
        return len(text)

    if snap_forward:
        # End offset: find next boundary char at or after offset, place end
        # right after it so the boundary char itself is included.
        for i in range(offset, len(text)):
            if text[i] in _BOUNDARY_CHARS:
                return i + 1
        return len(text)
    else:
        # Start offset: find previous boundary char before offset, place start
        # right after it so we begin cleanly at a new sentence.
        for i in range(offset - 1, -1, -1):
            if text[i] in _BOUNDARY_CHARS:
                return i + 1
        return 0


def _validate_coverage(
    scenes: list[Scene],
    chapter_length: int,
    chapter_order: int,
) -> None:
    """
    Log warnings if scenes do not cover the chapter contiguously.

    Detects three failure modes:
      - First scene does not start at offset 0
      - Last scene does not end at chapter_length
      - Gaps or overlaps between consecutive scenes

    Only logs warnings; does not modify scenes. Use this to surface prompt
    or LLM issues that the snap function cannot fully compensate for.
    """
    if not scenes:
        logger.warning(
            "Chapter %d: segmenter returned 0 scenes (chapter_length=%d)",
            chapter_order,
            chapter_length,
        )
        return

    sorted_scenes = sorted(scenes, key=lambda s: s.text_segment[0])

    first_start = sorted_scenes[0].text_segment[0]
    if first_start != 0:
        logger.warning(
            "Chapter %d: first scene starts at %d (expected 0; %d chars uncovered at head)",
            chapter_order,
            first_start,
            first_start,
        )

    last_end = sorted_scenes[-1].text_segment[1]
    if last_end != chapter_length:
        logger.warning(
            "Chapter %d: last scene ends at %d (expected %d; %d chars uncovered at tail)",
            chapter_order,
            last_end,
            chapter_length,
            chapter_length - last_end,
        )

    for i in range(1, len(sorted_scenes)):
        prev_end = sorted_scenes[i - 1].text_segment[1]
        curr_start = sorted_scenes[i].text_segment[0]
        if curr_start > prev_end:
            logger.warning(
                "Chapter %d: gap between scene #%d and scene #%d (%d chars uncovered: [%d, %d))",
                chapter_order,
                i,
                i + 1,
                curr_start - prev_end,
                prev_end,
                curr_start,
            )
        elif curr_start < prev_end:
            logger.warning(
                "Chapter %d: overlap between scene #%d and scene #%d (%d chars: [%d, %d))",
                chapter_order,
                i,
                i + 1,
                prev_end - curr_start,
                curr_start,
                prev_end,
            )


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
        List of Scene objects with text offset references. Offsets are
        snapped to sentence boundaries as a defense against LLM imprecision.

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

    chapter_text = chapter.text
    chapter_len = len(chapter_text)

    scenes = []
    for s in data.get("scenes", []):
        seg = s.get("text_segment", [0, 0])
        if len(seg) != 2:
            seg = [0, 0]
        raw_start, raw_end = seg

        # Defense-in-depth: snap LLM offsets to sentence boundaries so a
        # mid-sentence cut cannot survive into downstream stages.
        snapped_start = _snap_offset_to_boundary(
            chapter_text, raw_start, snap_forward=False
        )
        snapped_end = _snap_offset_to_boundary(
            chapter_text, raw_end, snap_forward=True
        )

        # Ensure end > start. If snapping collapsed the range (e.g., very
        # short text with no boundary chars), fall back to the raw offsets
        # clamped to chapter bounds.
        if snapped_end <= snapped_start:
            clamped_start = max(0, min(raw_start, chapter_len))
            clamped_end = max(clamped_start + 1, min(raw_end, chapter_len))
            logger.warning(
                "Chapter %d: snap collapsed segment [%d, %d] to [%d, %d]; falling back to [%d, %d]",
                chapter.order,
                raw_start,
                raw_end,
                snapped_start,
                snapped_end,
                clamped_start,
                clamped_end,
            )
            snapped_start, snapped_end = clamped_start, clamped_end

        scenes.append(
            Scene(
                location=s.get("location", "未知"),
                time=s.get("time", "continuous"),
                type=s.get("type", "interior"),
                description=s.get("description", ""),
                text_segment=(snapped_start, snapped_end),
                chapter_order=chapter.order,
            )
        )

    _validate_coverage(scenes, chapter_len, chapter.order)

    return scenes
