"""
Stage 5: Beat Extractor — LLM-powered per-scene dialogue/action extraction.

For each scene, identifies atomic narrative beats:
  - action: character physical actions
  - dialogue: character spoken lines
  - transition: scene transition cues (CUT TO, FADE OUT)
  - voiceover: narrator/voiceover text
  - montage: time-lapse sequences

Runs per-scene in parallel for throughput.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from llm.client import llm_complete, llm_stream_json, StreamCallback
from llm.prompts import EXTRACT_BEATS_PROMPT
from llm.schemas import EXTRACT_SCHEMA


@dataclass
class Beat:
    """An atomic narrative beat within a scene."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = "action"  # action, dialogue, transition, voiceover, montage
    character_id: str | None = None  # reference to characters table
    character_text: str | None = None  # original name as it appears in the novel
    content: str = ""
    parenthetical: str | None = None  # acting direction ("whispering", "looking away")
    emotion: str | None = None  # emotional state


async def extract_beats(
    scene_text: str,
    characters: list | None = None,
    on_stream: StreamCallback | None = None,
) -> list[Beat]:
    """
    Extract narrative beats from a single scene.

    Args:
        scene_text: the text content of the scene
        characters: list of Character objects from Stage 3 (for ID mapping)
        on_stream: optional async callback for streaming LLM tokens

    Returns:
        List of Beat objects forming the scene's narrative sequence.

    Raises:
        LLMError: if the LLM call fails after retries
    """
    # Build character context with actual IDs
    char_parts = []
    for c in (characters or []):
        cid = getattr(c, "id", None) or getattr(c, "name", None) or c.name if hasattr(c, "name") else str(c)
        char_parts.append(f"{c.name}(id:{cid})")
    char_str = ", ".join(char_parts) if char_parts else "无"

    prompt = EXTRACT_BEATS_PROMPT.format(
        characters=char_str,
        scene_text=scene_text,
    )

    if on_stream:
        data = await llm_stream_json(prompt, schema=EXTRACT_SCHEMA, on_chunk=on_stream)
    else:
        data = await llm_complete(prompt, schema=EXTRACT_SCHEMA)

    beats = []
    for b in data.get("beats", []):
        beats.append(
            Beat(
                type=b.get("type", "action"),
                character_id=b.get("character_id"),
                character_text=b.get("character_text"),
                content=b.get("content", ""),
                parenthetical=b.get("parenthetical"),
                emotion=b.get("emotion"),
            )
        )
    return beats
