"""
Stage 3: Structure Analyzer — LLM-powered global analysis.

Takes all chapter summaries (first 500 chars each) and extracts:
  - synopsis: overall story summary (≤200 chars)
  - characters: list of characters with names, aliases, roles
  - locations: list of locations with types and descriptions

Uses LiteLLM with Structured Output (JSON mode) to ensure valid response.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from llm.client import llm_complete, llm_stream_json, StreamCallback
from llm.prompts import ANALYZE_STRUCTURE_PROMPT
from llm.schemas import ANALYZE_SCHEMA


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
        data = await llm_stream_json(prompt, schema=ANALYZE_SCHEMA, on_chunk=on_stream)
    else:
        data = await llm_complete(prompt, schema=ANALYZE_SCHEMA)

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
