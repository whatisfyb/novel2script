"""
Stage 3: Structure Analyzer — LLM-powered global analysis.

Takes all chapter summaries (first 500 chars each) and extracts:
  - synopsis: overall story summary (≤200 chars)
  - characters: list of characters with names, aliases, roles
  - locations: list of locations with types and descriptions

Uses LiteLLM with Structured Output (JSON mode) to ensure valid response.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from llm.client import llm_complete, llm_stream_json, StreamCallback
from llm.prompts import ANALYZE_STRUCTURE_PROMPT
from llm.pydantic_schemas import AnalyzeStructureOutput
from llm.schemas import ANALYZE_SCHEMA  # legacy fallback

logger = logging.getLogger(__name__)


@dataclass
class Character:
    """A character identified in the novel."""

    name: str
    aliases: list[str] = field(default_factory=list)
    role: str = "extra"  # protagonist, supporting, antagonist, extra
    description: str = ""


@dataclass
class Location:
    """A location identified in the novel."""

    name: str
    type: str = "mixed"  # indoor, outdoor, mixed, virtual
    description: str = ""


# Bidirectional alias pairings. Whenever A carries alias X, the related
# character B should carry alias Y. Each entry maps X -> Y. The reverse
# (Y -> X) is automatically applied.
_ALIAS_PAIRS: dict[str, str] = {
    # Spouse
    "妻子": "丈夫", "丈夫": "妻子",
    # Romantic — past and present
    "前女友": "前男友", "前男友": "前女友",
    "女友": "男友", "男友": "女友",
    "前妻": "前夫", "前夫": "前妻",
    # Family — children
    "母亲": "儿子", "母亲": "女儿",
    "父亲": "儿子", "父亲": "女儿",
    "妈妈": "儿子", "妈妈": "女儿",
    "爸爸": "儿子", "爸爸": "女儿",
    "儿子": "父亲", "儿子": "母亲",
    "女儿": "父亲", "女儿": "母亲",
    # Sibling
    "哥哥": "弟弟", "哥哥": "妹妹",
    "姐姐": "弟弟", "姐姐": "妹妹",
    "弟弟": "哥哥", "弟弟": "姐姐",
    "妹妹": "哥哥", "妹妹": "姐姐",
}


def _find_related_character(
    char: Character,
    alias: str,
    characters: list[Character],
    full_text: str = "",
) -> Character | None:
    """Heuristically find the character most likely to be in a relation
    with `char` via the given relation-alias.

    Strategy (in priority order):
      1. **Description-based mutual reference**: if `char.description`
         mentions another character's name, that character is `related`.
         (E.g. "周远的前女友林薇" -> related is 林薇.)
      2. **Co-occurrence in source text**: if no description match,
         fall back to text-level co-occurrence.
      3. **None**: if no match, return None.
    """
    if not full_text:
        full_text = ""

    # Strategy 1: description-based mutual reference
    # Check if char.description mentions another character's name
    for other in characters:
        if other.name == char.name:
            continue
        if other.name in (char.description or ""):
            return other
    # Also check if other.description mentions char.name (mutual)
    for other in characters:
        if other.name == char.name:
            continue
        if char.name in (other.description or ""):
            return other

    # Strategy 2: text co-occurrence
    char_text = char.name
    scores: list[tuple[int, Character]] = []
    for other in characters:
        if other.name == char.name:
            continue
        count = full_text.count(other.name)
        score = count
        for a in other.aliases:
            if char.name in a or a in char.name:
                score += 5
        scores.append((score, other))

    if not scores:
        return None
    scores.sort(key=lambda x: -x[0])
    return scores[0][1] if scores[0][0] > 0 else None


def _enforce_bidirectional_aliases(
    characters: list[Character], full_text: str = ""
) -> list[Character]:
    """For each character, for each of their aliases that is a relation
    title, find the related character and ensure they carry the
    corresponding reverse alias. Mutates and returns the character list.
    """
    for char in characters:
        for alias in list(char.aliases):
            reverse = _ALIAS_PAIRS.get(alias)
            if not reverse:
                continue
            # Find the related character
            related = _find_related_character(
                char, alias, characters, full_text
            )
            if related is None:
                logger.warning(
                    "Bidirectional alias fix: no related for %s's %r",
                    char.name, alias,
                )
                continue
            # Add the reverse alias to the related character
            if reverse not in related.aliases:
                related.aliases.append(reverse)
                logger.info(
                    "Bidirectional alias fix: %s got alias %r (paired with %s's %r)",
                    related.name, reverse, char.name, alias,
                )
    return characters


@dataclass
class StructureResult:
    """Output of the structure analysis stage."""

    synopsis: str
    characters: list[Character]
    locations: list[Location]


_SUMMARY_MAX_LEN = 500  # chars per chapter summary


async def analyze_structure(
    chapters: list,
    on_stream: StreamCallback | None = None,
) -> StructureResult:
    """
    Analyze the novel's global structure using LLM.

    Args:
        chapters: list of Chapter objects from Stage 2
        on_stream: optional async callback for streaming LLM tokens

    Returns:
        StructureResult with synopsis, characters, and locations.

    Raises:
        LLMError: if the LLM call fails after retries
    """
    # Build chapter summaries (first 500 chars of each)
    summaries = []
    for ch in chapters:
        summary = ch.text[:_SUMMARY_MAX_LEN]
        if len(ch.text) > _SUMMARY_MAX_LEN:
            summary += "..."
        summaries.append(f"[第{ch.order}章 {ch.title}]\n{summary}")

    full_text = "\n\n".join(summaries)

    # Call LLM with streaming + structured output
    prompt = ANALYZE_STRUCTURE_PROMPT.format(text=full_text)

    if on_stream:
        data = await llm_stream_json(prompt, pydantic_model=AnalyzeStructureOutput, on_chunk=on_stream)
    else:
        data = await llm_complete(prompt, pydantic_model=AnalyzeStructureOutput)

    # Parse into dataclasses
    characters = [
        Character(
            name=c["name"],
            aliases=c.get("aliases", []),
            role=c.get("role", "extra"),
            description=c.get("description", ""),
        )
        for c in data.get("characters", [])
    ]

    # Programmatic bidirectional-alias fixup: LLM prompt rules are not
    # reliable enough. Enforce that whenever character A claims a relation
    # title like "妻子", the related character B gets the corresponding
    # "丈夫" — and vice versa. Other relation pairs handled too.
    characters = _enforce_bidirectional_aliases(
        characters, full_text=full_text
    )

    locations = [
        Location(
            name=l["name"],
            type=l.get("type", "mixed"),
            description=l.get("description", ""),
        )
        for l in data.get("locations", [])
    ]

    return StructureResult(
        synopsis=data.get("synopsis", ""),
        characters=characters,
        locations=locations,
    )
