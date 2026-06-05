"""
Stage 5: Beat Extractor — LLM-powered per-scene dialogue/action extraction.

For each scene, identifies atomic narrative beats:
  - action: character physical actions
  - dialogue: character spoken lines
  - transition: scene transition cues (CUT TO, FADE OUT)
  - voiceover: narrator/voiceover text
  - montage: time-lapse sequences

Post-LLM fallback: attributes unowned dialogue beats (character_text=None)
using speaker-alternation heuristics when the LLM fails to identify speakers
(e.g., phone dialogue where the speaker is not physically present).

Runs per-scene in parallel for throughput.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from llm.client import llm_complete, llm_stream_json, StreamCallback
from llm.prompts import EXTRACT_BEATS_PROMPT
from llm.schemas import EXTRACT_SCHEMA

logger = logging.getLogger(__name__)


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


def _normalize_character_attribution(
    beats: list[Beat],
    characters: list,
) -> set[str]:
    """
    Pre-pass: clear character_text when LLM produced a truthy-but-invalid value.

    Two failure modes are corrected before the main fallback runs:

    1. **Invalid name**: The LLM returned a string for character_text that is
       not in the known character name/alias set (e.g., "她", "电话那头",
       "那个女人"). These are truthy but the assembler cannot map them
       to a character ID — they would become character: null. Clearing
       them lets the fallback re-attribution run.

    2. **Self-reference**: The LLM attributed a dialogue beat to character X
       but the content opens with "X，" or "X。" — meaning X is the person
       being ADDRESSED, not the speaker. For example, "周远，是我。" was
       attributed to 周远 himself, but no one says their own name when
       calling someone. The speaker is a different character. Clearing
       character_text triggers the fallback to assign the actual speaker.

    Returns the set of valid character names (name + aliases) so the
    fallback does not recompute it.
    """
    # Build the set of valid names once
    valid_names: set[str] = set()
    for c in characters:
        name = getattr(c, "name", "")
        if name:
            valid_names.add(name)
        for alias in getattr(c, "aliases", []):
            if alias:
                valid_names.add(alias)

    # Punctuation that follows a name when it is being addressed, not spoken
    _ADDRESS_PUNCT = set("，,。.！!？?：: 　")

    for b in beats:
        if b.type not in ("dialogue", "voiceover"):
            continue
        if not b.character_text:
            continue

        # Mode 1: invalid name → clear
        if b.character_text not in valid_names:
            logger.debug(
                "Normalize: clearing invalid character_text %r on beat '%s'",
                b.character_text, b.id,
            )
            b.character_text = None
            continue

        # Mode 2: self-reference detection (dialogue only)
        if b.type == "dialogue":
            content = b.content or ""
            name = b.character_text
            if content.startswith(name):
                after = content[len(name):len(name) + 1]
                if after and after in _ADDRESS_PUNCT:
                    logger.debug(
                        "Normalize: self-reference detected on beat '%s' "
                        "(content starts with %r as address)",
                        b.id, name,
                    )
                    b.character_text = None

    return valid_names


def _fallback_attribute_dialogue(
    beats: list[Beat],
    characters: list,
    scene_text: str,
    chapter_text: str | None = None,
) -> list[Beat]:
    """
    Post-LLM fallback: assign character_text to dialogue/voiceover beats
    that the LLM left as character_text=None.

    A pre-pass (`_normalize_character_attribution`) first clears invalid
    or self-referencing attributions so this fallback can re-attempt them.

    Heuristics (applied in order of confidence):

    1. **Name-in-content**: If unowned dialogue content addresses a known
       character by name (e.g., "周远，是我"), the speaker is a DIFFERENT
       active character.
    2. **Speaker alternation**: In 2-person scenes, dialogue alternates.
       If the previous dialogue beat has a known speaker, assign the
       unowned beat to the other active speaker.
    3. **Action-context**: If no previous dialogue speaker exists, the
       nearest preceding action beat's character is the listener/PoV;
       assign dialogue to the other active speaker.
    4. **Single-speaker**: If only one active speaker exists in the scene,
       assign all unowned dialogue to them.
    5. **Voiceover → PoV**: Voiceover beats with no character are
       attributed to the PoV character (the one with the most action beats).

    "Active speakers" = non-extra characters whose names appear in
    scene_text (or chapter_text if provided). Extra/narrator-only
    characters are excluded. The chapter_text fallback ensures that
    scenes cut at points where character names are not present (e.g.,
    a long continuous speech with no name repetition) still get
    attribution: the surrounding chapter provides the speaker context.

    Args:
        beats: list of Beat objects from LLM output.
        characters: list of Character objects from Stage 3.
        scene_text: the scene's source text for primary name detection.
        chapter_text: optional wider-context text (full chapter) used as
            fallback for name-occurrence detection when scene_text does
            not mention any active character by name.

    Returns:
        The same list (mutated in place) with character_text filled in
        where heuristics could determine the speaker. Beats where the
        speaker remains ambiguous are left as None.
    """
    if not beats or not characters:
        return beats

    # 0. Pre-pass: clear invalid/self-referencing character_text
    _normalize_character_attribution(beats, characters)

    # 1. Determine active speakers: non-extra characters whose names
    #    appear in scene_text. If scene_text mentions no characters,
    #    fall back to chapter_text (provides surrounding context).
    name_source = scene_text
    if chapter_text and not any(
        getattr(c, "name", "") and getattr(c, "name", "") in scene_text
        and getattr(c, "role", "extra") != "extra"
        for c in characters
    ):
        # scene_text has no active character names → widen to chapter
        name_source = chapter_text
        logger.debug(
            "Fallback: scene_text has no active character names; "
            "using chapter_text for speaker detection"
        )

    active_speakers: list[str] = []
    for c in characters:
        name = getattr(c, "name", "")
        role = getattr(c, "role", "extra")
        if name and name in name_source and role != "extra":
            active_speakers.append(name)

    if not active_speakers:
        return beats

    # 2. Identify PoV character (most action beats attributed).
    action_counts: dict[str, int] = {}
    for b in beats:
        if b.type == "action" and b.character_text:
            action_counts[b.character_text] = action_counts.get(b.character_text, 0) + 1
    pov = max(action_counts, key=action_counts.get) if action_counts else active_speakers[0]

    # 3. Single-speaker scene: assign all unowned dialogue to that speaker.
    if len(active_speakers) == 1:
        only = active_speakers[0]
        for b in beats:
            if b.type in ("dialogue", "voiceover") and not b.character_text:
                b.character_text = only
                logger.debug("Fallback attribution (single-speaker): beat '%s' → %s", b.id, only)
        return beats

    # 4. Multi-speaker scene: apply heuristics in order.
    last_dialogue_speaker: str | None = None

    for idx, b in enumerate(beats):
        if b.type not in ("dialogue", "voiceover"):
            continue

        # Already attributed — track and skip.
        if b.character_text:
            if b.type == "dialogue":
                last_dialogue_speaker = b.character_text
            continue

        # --- Voiceover: attribute to PoV ---
        if b.type == "voiceover":
            b.character_text = pov
            logger.debug("Fallback attribution (voiceover→PoV): beat '%s' → %s", b.id, pov)
            continue

        # --- Dialogue heuristics ---

        # 4a. Name-in-content: dialogue addresses a character by name
        content = b.content or ""
        addressed = [s for s in active_speakers if s in content]
        if addressed:
            others = [s for s in active_speakers if s not in addressed]
            if others:
                b.character_text = others[0]
                last_dialogue_speaker = others[0]
                logger.debug("Fallback attribution (name-in-content): beat '%s' → %s", b.id, others[0])
                continue

        # 4b. Speaker alternation: previous dialogue speaker known
        if last_dialogue_speaker:
            for s in active_speakers:
                if s != last_dialogue_speaker:
                    b.character_text = s
                    last_dialogue_speaker = s
                    logger.debug("Fallback attribution (alternation): beat '%s' → %s", b.id, s)
                    break
            continue

        # 4c. Action-context: find nearest preceding beat with a character
        last_action_char: str | None = None
        for prev_idx in range(idx - 1, -1, -1):
            if beats[prev_idx].character_text:
                last_action_char = beats[prev_idx].character_text
                break

        if last_action_char:
            others = [s for s in active_speakers if s != last_action_char]
            if others:
                b.character_text = others[0]
                last_dialogue_speaker = others[0]
                logger.debug("Fallback attribution (action-context): beat '%s' → %s", b.id, others[0])
                continue

        # 4d. Last resort: assign to non-PoV (the "caller"/"visitor")
        others = [s for s in active_speakers if s != pov]
        if others:
            b.character_text = others[0]
            last_dialogue_speaker = others[0]
            logger.debug("Fallback attribution (non-PoV default): beat '%s' → %s", b.id, others[0])

    return beats


async def extract_beats(
    scene_text: str,
    characters: list | None = None,
    on_stream: StreamCallback | None = None,
    chapter_text: str | None = None,
) -> list[Beat]:
    """
    Extract narrative beats from a single scene.

    Args:
        scene_text: the text content of the scene
        characters: list of Character objects from Stage 3 (for ID mapping)
        on_stream: optional async callback for streaming LLM tokens
        chapter_text: optional wider-context text (full chapter). When
            provided, the fallback attribution uses it to detect active
            speakers even when scene_text itself contains no character
            names (e.g., a long continuous speech that was cut into a
            narrow scene segment).

    Returns:
        List of Beat objects forming the scene's narrative sequence.
        Unowned dialogue beats receive fallback attribution via
        _fallback_attribute_dialogue when the LLM leaves character_text=None.

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

    # Post-LLM fallback: fill in character_text for unowned dialogue beats
    beats = _fallback_attribute_dialogue(
        beats, characters or [], scene_text, chapter_text=chapter_text
    )

    return beats
