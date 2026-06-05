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

        # 4a. Name-in-content: dialogue explicitly addresses a character
        # by name at the very start, followed by address punctuation
        # (，。：！？ + whitespace). Only address patterns trigger;
        # passive mentions like "张明的遗书" or "张明死了" do NOT —
        # those are referents, not addressees.
        content = b.content or ""
        _ADDRESS_PUNCT = set("，,。.！!？?：: 　")
        addressed: list[str] = []
        for s in active_speakers:
            if not content.startswith(s):
                continue
            tail_idx = len(s)
            if tail_idx >= len(content):
                continue
            next_char = content[tail_idx]
            if next_char in _ADDRESS_PUNCT:
                addressed.append(s)
        if addressed:
            others = [s for s in active_speakers if s not in addressed]
            if others:
                b.character_text = others[0]
                last_dialogue_speaker = others[0]
                logger.debug(
                    "Fallback attribution (name-address): beat '%s' → %s (addressed=%s)",
                    b.id, others[0], addressed,
                )
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

    # 5. Action beat attribution: assign unowned actions to their subject.
    _attribute_action_beats(beats, active_speakers, characters)

    return beats


def _attribute_action_beats(
    beats: list[Beat],
    active_speakers: list[str],
    characters: list,
) -> None:
    """
    Fill in character_text for action beats that the LLM left as None.

    Action content usually has a clear grammatical subject:
      - "周远把车停在C区第三排" → subject=周远
      - "她拉开车门" → pronoun 她 → most recent female character
      - "从包里掏出一个信封" → no subject → most recent action character

    Heuristics (applied per beat in order):

    1. **Name at start**: content starts with a character name + optional
       particle → attribute to that character.
    2. **Pronoun**: content starts with 她/他/她们/他们 (followed by
       action verb) → resolve via most recent gendered character mention
       in the scene so far. (Gender is inferred from character name via
       a tiny heuristic; in Chinese, 一/二/三/.../十 leading names tend
       to be ambiguous and we fall back to a default.)
    3. **Most recent action character**: if no name or pronoun, attribute
       to the most recent action beat's character (continuation of activity).
    """

    # 1. Build valid name set
    valid_names: set[str] = set()
    for c in characters:
        name = getattr(c, "name", "")
        if name:
            valid_names.add(name)
        for alias in getattr(c, "aliases", []):
            if alias:
                valid_names.add(alias)

    # 2. Build gender map for known names. Simple heuristic:
    #    female = name ends in common female suffixes or includes 薇/娜/丽/芳/红/梅/兰/莲/花/英/萍
    #    male   = name ends in common male suffixes or includes 远/明/强/军/勇/刚/伟
    #    unknown = default to "他" = "last mentioned" fallback.
    _FEMALE_HINTS = "薇娜丽芳红梅兰莲花英萍"
    _MALE_HINTS = "远明强军勇刚伟国建"
    name_gender: dict[str, str] = {}
    for n in valid_names:
        last = n[-1] if n else ""
        if last in _FEMALE_HINTS:
            name_gender[n] = "female"
        elif last in _MALE_HINTS:
            name_gender[n] = "male"
        # else: unknown, fall through

    # 3. Walk beats in order, fill unowned actions
    last_action_char: str | None = None

    for b in beats:
        if b.type != "action":
            continue
        if b.character_text:
            last_action_char = b.character_text
            continue

        content = (b.content or "").lstrip()
        assigned: str | None = None

        # Rule 1: name at start (possibly followed by 的/了/着/是/把/给/向 + verb)
        for n in valid_names:
            if content.startswith(n):
                tail_idx = len(n)
                # Allow particle + verb continuation
                if tail_idx >= len(content) or content[tail_idx] in "的了着是把给向/":
                    assigned = n
                    break

        # Rule 2: pronoun at start (他/她/他们/她们)
        if not assigned and content:
            first_two = content[:2]
            first_one = content[0]
            pronoun_gender: str | None = None
            if first_two in ("她们", "他们"):
                pronoun_gender = "female" if first_one == "她" else "male"
            elif first_one == "她":
                pronoun_gender = "female"
            elif first_one == "他":
                pronoun_gender = "male"
            if pronoun_gender:
                # Resolve to most recent gendered char in beats
                for prev in reversed(beats):
                    if prev.character_text and prev.character_text in name_gender:
                        if name_gender[prev.character_text] == pronoun_gender:
                            assigned = prev.character_text
                            break
                if not assigned:
                    # Fall back to any active speaker with matching gender
                    for s in active_speakers:
                        if name_gender.get(s) == pronoun_gender:
                            assigned = s
                            break

        # Rule 3: most recent action character
        if not assigned and last_action_char:
            assigned = last_action_char

        if assigned:
            b.character_text = assigned
            last_action_char = assigned
            logger.debug(
                "Action beat attribution: beat '%s' → %s", b.id, assigned,
            )


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


def refine_cross_scene_attribution(
    beats_by_scene: dict[str, list[Beat]],
    scene_order: list[str],
) -> dict[str, list[Beat]]:
    """
    Post-pass: refine dialogue attribution using cross-scene context.

    The per-scene fallback runs in parallel and has no view of neighbouring
    scenes. This pass walks scenes in their natural order and uses the
    PREVIOUS scene's last attributed beat as a prior for the next scene's
    first dialogue.

    Rule (conservative — only flips when the current scene has no internal
    evidence to contradict the prior):

    If a scene's FIRST dialogue beat has character_text=Y AND the previous
    scene's last attributed beat is an ACTION by character X (X ≠ Y) AND
    the current scene has NO attributed action beats (no internal evidence
    for Y) AND the current scene contains exactly 1 dialogue beat, then Y
    is likely an LLM hallucination → flip Y → X.

    Why so narrow? Multi-beat scenes with internal attributed actions
    already have evidence. Scenes with multiple dialogue beats would have
    the LLM give multiple attributions. Only the "single dialogue beat,
    no actions, immediately after a scene-ending action by X" pattern is
    safe to flip — it matches the common case where a continuous speech
    was split across scene boundaries by the segmenter.

    Args:
        beats_by_scene: mapping of scene_key → list of Beat objects.
        scene_order: list of scene_keys in narrative order. Scenes not in
            this list are skipped.

    Returns:
        The same dict (mutated in place) with possibly-flipped
        attributions.
    """
    prev_last_action_char: str | None = None

    for scene_key in scene_order:
        beats = beats_by_scene.get(scene_key)
        if not beats:
            prev_last_action_char = None
            continue

        # Find prev scene's last attributed beat's character (action only)
        # Note: this was set in the previous iteration

        # Check the current scene's structure
        attributed_actions = [
            b for b in beats
            if b.type == "action" and b.character_text
        ]
        dialogue_beats = [
            b for b in beats
            if b.type == "dialogue" and b.character_text
        ]

        # Apply flip rule
        if (
            prev_last_action_char
            and len(dialogue_beats) == 1
            and not attributed_actions
        ):
            d = dialogue_beats[0]
            if d.character_text != prev_last_action_char:
                logger.debug(
                    "Cross-scene flip: scene %s dialogue '%s' %s → %s "
                    "(prev scene ended with action by %s, scene has no "
                    "internal attributed action)",
                    scene_key, d.id, d.character_text, prev_last_action_char,
                    prev_last_action_char,
                )
                d.character_text = prev_last_action_char

        # Update prev_last_action_char for next iteration: only from
        # ACTION beats. Dialogue/voiceover in the prev scene should NOT
        # set this prior — only an action implies the same character is
        # the "continuation" of activity in the next scene.
        prev_last_action_char = None
        for b in reversed(beats):
            if b.type == "action" and b.character_text:
                prev_last_action_char = b.character_text
                break

    return beats_by_scene
