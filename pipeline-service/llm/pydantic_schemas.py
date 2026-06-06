"""
Pydantic schemas for LLM Structured Output.

These Pydantic models define the exact response format expected from the LLM.
Used with LiteLLM's response_format parameter to enforce structured output
via OpenAI-compatible JSON Schema. Each Pydantic model has a corresponding
Pydantic → JSON Schema serializer (`model_json_schema()`) that LiteLLM
embeds into the request as the `response_format.schema` field, forcing
the LLM to return only JSON matching the schema.

Why Pydantic (over plain JSON Schema dicts):
- Type-safe field declarations
- Auto-validation of LLM output
- Enum constraints for categorical fields
- IDE autocomplete and self-documentation
- A single source of truth for both client-side validation
  (model_validate) and LLM-side schema instruction (model_json_schema)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Stage 3: Structure Analysis
# ---------------------------------------------------------------------------


class Character(BaseModel):
    """A character in the story."""
    name: str = Field(description="Standard name (中文名用汉字)")
    aliases: list[str] = Field(
        default_factory=list,
        description="Other names used in the novel (nicknames, relation titles)"
    )
    role: Literal["protagonist", "supporting", "antagonist", "extra"] = Field(
        default="extra",
        description="Character role"
    )
    description: str = Field(default="", description="One-line character description")


class Location(BaseModel):
    """A scene location."""
    name: str = Field(description="Location name")
    type: Literal["indoor", "outdoor", "mixed", "virtual"] = Field(
        default="indoor",
        description="Location type"
    )
    description: str = Field(default="", description="One-line location description")


class AnalyzeStructureOutput(BaseModel):
    """Output of structure analysis."""
    synopsis: str = Field(default="", description="Overall story synopsis (max 200 characters)")
    characters: list[Character] = Field(default_factory=list, description="All characters")
    locations: list[Location] = Field(default_factory=list, description="All locations")


# ---------------------------------------------------------------------------
# Stage 4: Scene Segmentation
# ---------------------------------------------------------------------------


class SceneSegment(BaseModel):
    """A single scene segment."""
    location: str = Field(description="Location name or ID")
    time: Literal["day", "night", "dawn", "dusk", "continuous"] = Field(
        default="continuous",
        description="Time of day"
    )
    type: Literal["interior", "exterior"] = Field(
        default="interior",
        description="Interior or exterior"
    )
    description: str = Field(default="", description="One-line scene description")
    text_segment: list[int] = Field(
        description="[start_offset, end_offset] in the chapter text"
    )


class SegmentScenesOutput(BaseModel):
    """Output of scene segmentation."""
    scenes: list[SceneSegment] = Field(description="All scenes in the chapter")


# ---------------------------------------------------------------------------
# Stage 5: Beat Extraction
# ---------------------------------------------------------------------------


class Beat(BaseModel):
    """A single narrative beat."""
    type: Literal["action", "dialogue", "transition", "voiceover", "montage"] = Field(
        description="Beat type"
    )
    character_id: str | None = Field(
        default=None,
        description="Character ID from the global table, null for non-character beats"
    )
    character_text: str | None = Field(
        default=None,
        description="Original name as it appears in the novel"
    )
    content: str = Field(description="Beat content in screenplay language")
    parenthetical: str | None = Field(
        default=None,
        description="Acting direction in parentheses"
    )
    emotion: str | None = Field(
        default=None,
        description="Emotional state of the character"
    )


class ExtractBeatsOutput(BaseModel):
    """Output of beat extraction."""
    beats: list[Beat] = Field(description="All extracted beats")


# ---------------------------------------------------------------------------
# Stage 5b: Critic Agent
# ---------------------------------------------------------------------------


class CriticFix(BaseModel):
    """A fix proposed by the critic."""
    type: Literal["action", "dialogue", "voiceover", "transition", "montage"] | None = Field(
        default=None,
        description="Corrected beat type"
    )
    character_id: str | None = Field(default=None, description="Corrected character ID")
    character_text: str | None = Field(default=None, description="Corrected original name")
    content: str | None = Field(default=None, description="Corrected content")
    parenthetical: str | None = Field(default=None, description="Corrected parenthetical")
    emotion: str | None = Field(default=None, description="Corrected emotion")


class CriticCorrection(BaseModel):
    """A single correction proposed by the critic."""
    beat_id: str = Field(description="ID of the beat to correct")
    issue: Literal[
        "wrong_speaker", "wrong_type", "missing_character",
        "wrong_content", "duplicate_beat", "should_be_split",
        "incomplete_dialogue",
    ] = Field(description="Type of issue found")
    fix: CriticFix = Field(description="Fix to apply (only changed fields)")
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in this correction (0.0-1.0)"
    )
    reasoning: str = Field(default="", description="One-sentence explanation")


class CriticOutput(BaseModel):
    """Output of critic review."""
    corrections: list[CriticCorrection] = Field(
        default_factory=list,
        description="List of corrections (empty if all beats are correct)"
    )


# ---------------------------------------------------------------------------
# Stage 5c: Refiner Agent
# ---------------------------------------------------------------------------


class RefinerOutput(BaseModel):
    """Output of refiner — final beats after applying corrections."""
    beats: list[Beat] = Field(
        description="Final, definitive beats after applying critic's corrections"
    )


# ---------------------------------------------------------------------------
# Stage 2 fallback: Chapter Detection
# ---------------------------------------------------------------------------


class ChapterDetection(BaseModel):
    """A detected chapter."""
    title: str = Field(description="Chapter title")
    line_start: int = Field(default=0, description="0-based starting line number")


class ChapterDetectOutput(BaseModel):
    """Output of chapter detection."""
    chapters: list[ChapterDetection] = Field(description="Detected chapters")
