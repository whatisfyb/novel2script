"""
Pydantic schemas for ReAct agent output.

Each step in a ReAct loop follows:
  thought → action → observation → thought → ... → final_answer

The LLM is forced to return one of:
  - {action, action_input} for tool calls
  - {is_final: True, final_answer} for the final answer

This schema is sent as the LLM's response_format to enforce structured
output. The agent loop reads back, executes the tool, and feeds the
observation into the next step.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Beat type (kept here to avoid cross-module import cycle)
# ---------------------------------------------------------------------------

BeatType = Literal["action", "dialogue", "transition", "voiceover", "montage"]


# ---------------------------------------------------------------------------
# Tool call step
# ---------------------------------------------------------------------------

class ReActToolCall(BaseModel):
    """A single tool invocation in the ReAct loop."""
    action: str = Field(description="Name of the tool to call")
    action_input: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments to pass to the tool",
    )


# ---------------------------------------------------------------------------
# Extractor final answer
# ---------------------------------------------------------------------------

class ExtractorBeat(BaseModel):
    """A single beat produced by the extractor."""
    type: BeatType = Field(description="Beat type")
    character_id: str | None = Field(default=None, description="Character ID or null")
    character_text: str | None = Field(default=None, description="Original name or null")
    content: str = Field(description="Beat content")
    parenthetical: str | None = Field(default=None, description="Acting direction")
    emotion: str | None = Field(default=None, description="Emotional state")


class ExtractorFinalAnswer(BaseModel):
    """Final answer from the extractor agent."""
    beats: list[ExtractorBeat] = Field(description="All extracted beats")


# ---------------------------------------------------------------------------
# Critic final answer
# ---------------------------------------------------------------------------

class CriticFixField(BaseModel):
    """A fix proposed for a specific field. All fields optional except via Pydantic."""
    type: BeatType | None = None
    character_id: str | None = None
    character_text: str | None = None
    content: str | None = None
    parenthetical: str | None = None
    emotion: str | None = None


class CriticCorrection(BaseModel):
    """A single correction proposed by the critic."""
    beat_id: str = Field(description="ID of the beat to correct")
    issue: Literal[
        "wrong_speaker", "wrong_type", "missing_character",
        "wrong_content", "duplicate_beat", "should_be_split",
        "incomplete_dialogue", "missing_dialogue",
    ] = Field(description="Type of issue")
    fix: CriticFixField = Field(default_factory=CriticFixField)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reasoning: str = Field(default="")


class CriticFinalAnswer(BaseModel):
    """Final answer from the critic agent."""
    corrections: list[CriticCorrection] = Field(
        default_factory=list,
        description="List of corrections (empty = all correct)",
    )


# Lenient schema: Critic may return raw fix as dict instead of nested Pydantic model
class CriticCorrectionLenient(BaseModel):
    """Lenient critic correction - accepts fix as raw dict or CriticFixField."""
    beat_id: str = Field(default="", description="ID of the beat to correct")
    issue: str = Field(default="", description="Type of issue (any string)")
    fix: dict[str, Any] = Field(default_factory=dict, description="Fix as raw dict")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reasoning: str = Field(default="")


class CriticFinalAnswerLenient(BaseModel):
    """Lenient final answer from the critic - accepts any shape."""
    corrections: list[CriticCorrectionLenient] = Field(
        default_factory=list,
        description="List of corrections (empty = all correct)",
    )


# ---------------------------------------------------------------------------
# Refiner final answer
# ---------------------------------------------------------------------------

class RefinerFinalAnswer(BaseModel):
    """Final answer from the refiner agent."""
    beats: list[ExtractorBeat] = Field(description="Final refined beats")


# ---------------------------------------------------------------------------
# Combined ReAct step (LLM returns this each iteration)
# ---------------------------------------------------------------------------

class ReActStep(BaseModel):
    """One iteration of the ReAct loop.

    LLM must return either:
      - {thought, action, action_input} to call a tool
      - {thought, is_final: True, final_answer} to terminate with an answer
    """
    thought: str = Field(description="LLM's reasoning for this step")

    # Tool call (mutually exclusive with final answer)
    action: str | None = Field(default=None, description="Tool name if calling a tool")
    action_input: dict[str, Any] | None = Field(
        default=None,
        description="Tool arguments if calling a tool",
    )

    # Final answer (mutually exclusive with tool call)
    is_final: bool = Field(default=False, description="True if this is the final answer")
    final_answer: dict[str, Any] | None = Field(
        default=None,
        description="Final structured answer (validated by agent-specific schema)",
    )
