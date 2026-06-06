"""
Tool implementations for the ReAct agents in beat_service.

Each tool is a plain async function with a typed signature. The agent
loop in `react_agent.run_react_agent` looks up the tool name in TOOLS
and invokes it with `**kwargs` from the LLM's `action_input`.

Tool results are JSON-serializable dicts that get fed back into the
LLM as the next "observation" in the ReAct loop.

Three categories of tools, each used by the corresponding agent:
  1. Extractor tools  — analyze_scene, check_phone_speaker, find_missing_dialogue
  2. Critic tools     — verify_dialogue_speaker, check_beat_type
  3. Refiner tools    — validate_refined_beats
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Extractor tools
# ---------------------------------------------------------------------------

# Argument aliases: LLM may pass these names instead of canonical names.
# The wrapper below maps them automatically.
_ALIASES = {
    "analyze_scene": {
        "scene_text": ["scene_text", "text", "scene", "content", "sceneText"],
        "characters": ["characters", "known_characters", "chars", "character_list", "knownChars"],
    },
    "check_phone_speaker": {
        "scene_text": ["scene_text", "text", "scene", "content", "sceneText"],
        "characters": ["characters", "known_characters", "chars", "character_list", "knownChars"],
    },
    "find_missing_dialogue": {
        "scene_text": ["scene_text", "text", "scene", "content", "sceneText"],
        "existing_beats": ["existing_beats", "beats", "current_beats", "extracted_beats", "known_beats"],
    },
    "verify_dialogue_speaker": {
        "beat": ["beat", "beat_info", "the_beat", "dialogue_beat", "beat_data"],
        "scene_text": ["scene_text", "text", "scene", "content", "sceneText"],
        "characters": ["characters", "known_characters", "chars", "character_list", "knownChars"],
    },
    "check_beat_type": {
        "beat": ["beat", "beat_info", "the_beat", "beat_data"],
        "scene_text": ["scene_text", "text", "scene", "content", "sceneText"],
    },
    "validate_refined_beats": {
        "beats": ["beats", "refined_beats", "final_beats", "result_beats"],
    },
}


def _normalize_args(tool_name: str, kwargs: dict) -> dict:
    """Map LLM-provided argument names to canonical tool parameter names."""
    aliases = _ALIASES.get(tool_name, {})
    normalized = {}
    for canonical, accepted in aliases.items():
        for name in accepted:
            if name in kwargs:
                normalized[canonical] = kwargs[name]
                break
    return normalized


def _make_wrapped(tool_name: str, tool_fn):
    """Wrap a tool to accept flexible argument names from the LLM."""
    async def wrapper(**kwargs):
        normalized = _normalize_args(tool_name, kwargs)
        return await tool_fn(**normalized)
    wrapper.__name__ = tool_name
    return wrapper


async def analyze_scene(scene_text: str = "", characters: list[str] = None) -> dict[str, Any]:
    """Analyze the scene type and identify which characters are present."""
    phone_keywords = ["电话", "来电", "手机", "拨打", "接通", "挂断", "那头"]
    found_keywords = [kw for kw in phone_keywords if kw in scene_text]

    quote_count = scene_text.count('"') + scene_text.count('"') + scene_text.count('"')

    if found_keywords and quote_count >= 2:
        scene_type = "phone_call"
        is_phone = True
    elif quote_count >= 4:
        scene_type = "face_to_face"
        is_phone = False
    elif quote_count >= 2:
        scene_type = "monologue"
        is_phone = False
    else:
        scene_type = "narration"
        is_phone = False

    return {
        "scene_type": scene_type,
        "is_phone_call": is_phone,
        "phone_keywords_found": found_keywords,
        "dialogue_quote_count": quote_count,
    }


async def check_phone_speaker(scene_text: str = "", characters: list[str] = None) -> dict[str, Any]:
    """For phone call scenes, identify who receives the call and who calls."""
    receiver_patterns = [
        r"(\w+)被.{0,5}惊醒",
        r"(\w+)接了",
        r"(\w+)犹豫.{0,3}接",
        r"(\w+)摸到",
        r"(\w+)听到",
    ]
    receiver = None
    for pat in receiver_patterns:
        m = re.search(pat, scene_text)
        if m:
            receiver = m.group(1)
            break

    caller_patterns = [
        r"(\w+)——",
        r"(\w+)打.{0,3}电话",
    ]
    caller = None
    for pat in caller_patterns:
        m = re.search(pat, scene_text)
        if m:
            candidate = m.group(1)
            if candidate != receiver:
                caller = candidate
                break

    if caller is None and characters:
        for c in characters:
            if c != receiver:
                caller = c
                break

    return {
        "receiver": receiver,
        "caller": caller,
        "reasoning": (
            f"receiver={receiver} (被惊醒/接听)"
            + (f"; caller={caller}" if caller else "")
        ),
    }


async def find_missing_dialogue(scene_text: str = "", existing_beats: list = None) -> dict[str, Any]:
    """Find quoted dialogue in the scene that wasn't extracted."""
    scene_dialogue = re.findall(r'"([^"]+)"', scene_text)
    scene_dialogue += re.findall(r'"([^"]+)"', scene_text)
    scene_dialogue += re.findall(r'"([^"]+)"', scene_text)

    seen = set()
    scene_dialogue_unique = []
    for d in scene_dialogue:
        if d not in seen:
            seen.add(d)
            scene_dialogue_unique.append(d)

    extracted = []
    if existing_beats:
        for b in existing_beats:
            if isinstance(b, dict):
                if b.get("type") == "dialogue":
                    extracted.append(b.get("content", ""))
            else:
                if getattr(b, "type", None) == "dialogue":
                    extracted.append(getattr(b, "content", ""))

    missing = []
    for d in scene_dialogue_unique:
        found = any(d[:10] in e or e[:10] in d for e in extracted if e)
        if not found:
            missing.append(d)

    return {
        "scene_dialogue": scene_dialogue_unique,
        "extracted_dialogue": extracted,
        "missing": missing,
        "missing_count": len(missing),
    }


# ---------------------------------------------------------------------------
# Critic tools
# ---------------------------------------------------------------------------

async def verify_dialogue_speaker(beat: dict = None, scene_text: str = "", characters: list[str] = None) -> dict[str, Any]:
    """Verify if a dialogue beat's speaker attribution is correct."""
    if beat is None:
        return {"error": "missing beat argument", "is_correct": None}

    content = beat.get("content", "").strip()
    char = beat.get("character_id") or beat.get("character_text")

    is_question = content.endswith("?") or content.endswith("？")

    pos = scene_text.find(content[:15]) if content else -1
    if pos > 0:
        preceding = scene_text[max(0, pos - 50):pos]
    else:
        preceding = ""

    speaker_patterns = [
        r"(\w+)说道?",
        r"(\w+)说[：:]",
        r"(\w+)问[：:]",
    ]
    context_speaker = None
    for pat in speaker_patterns:
        m = re.search(pat, preceding)
        if m:
            context_speaker = m.group(1)
            break

    is_phone = any(kw in scene_text for kw in ["电话", "手机", "来电"])

    reasoning_parts = []
    if context_speaker:
        reasoning_parts.append(f"前置动作主语={context_speaker}")
    if is_phone:
        if is_question:
            reasoning_parts.append("电话场景+问句→可能是 receiver")
        else:
            reasoning_parts.append("电话场景+陈述句→可能是 caller")

    return {
        "current_speaker": char,
        "likely_speaker": context_speaker,
        "is_correct": char == context_speaker if context_speaker else None,
        "is_question": is_question,
        "is_phone_scene": is_phone,
        "reasoning": "; ".join(reasoning_parts) or "无明确线索",
    }


async def check_beat_type(beat: dict = None, scene_text: str = "") -> dict[str, Any]:
    """Check if a beat's type is correct."""
    if beat is None:
        return {"error": "missing beat argument", "current_type": None}

    content = beat.get("content", "")
    current = beat.get("type")

    has_quotes = content.startswith('"') or content.startswith('"')

    suggested = current
    confidence = 0.5
    reasoning = "无明显冲突"

    if has_quotes and current != "dialogue":
        suggested = "dialogue"
        confidence = 0.9
        reasoning = "content 有引号，应为 dialogue"
    elif current == "dialogue" and not has_quotes:
        suggested = current
        confidence = 0.6
        reasoning = "type=dialogue 但无引号；可能是引号被剥离"

    return {
        "current_type": current,
        "suggested_type": suggested,
        "confidence": confidence,
        "needs_correction": current != suggested and confidence > 0.7,
        "reasoning": reasoning,
    }


# ---------------------------------------------------------------------------
# Refiner tools
# ---------------------------------------------------------------------------

async def validate_refined_beats(beats: list = None) -> dict[str, Any]:
    """Validate that refined beats are complete and well-formed."""
    if beats is None:
        return {"is_valid": False, "n_beats": 0, "issues": ["no beats provided"]}

    issues = []
    seen_ids = set()

    for b in beats:
        bid = b.get("id") if isinstance(b, dict) else getattr(b, "id", None)
        if bid and bid in seen_ids:
            issues.append(f"duplicate id: {bid}")
        seen_ids.add(bid or "")

        btype = b.get("type") if isinstance(b, dict) else getattr(b, "type", None)
        content = b.get("content") if isinstance(b, dict) else getattr(b, "content", None)
        if not content:
            issues.append(f"beat {bid} has empty content")
        if btype not in ("action", "dialogue", "transition", "voiceover", "montage"):
            issues.append(f"beat {bid} has invalid type: {btype}")

    return {
        "is_valid": len(issues) == 0,
        "n_beats": len(beats),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Tool registry (wrapped with arg-name normalization)
# ---------------------------------------------------------------------------

TOOLS: dict[str, Any] = {
    "analyze_scene": _make_wrapped("analyze_scene", analyze_scene),
    "check_phone_speaker": _make_wrapped("check_phone_speaker", check_phone_speaker),
    "find_missing_dialogue": _make_wrapped("find_missing_dialogue", find_missing_dialogue),
    "verify_dialogue_speaker": _make_wrapped("verify_dialogue_speaker", verify_dialogue_speaker),
    "check_beat_type": _make_wrapped("check_beat_type", check_beat_type),
    "validate_refined_beats": _make_wrapped("validate_refined_beats", validate_refined_beats),
}


# Tool descriptions for prompts
TOOL_DESCRIPTIONS = """\
可用工具（参数名很灵活，可使用下面的常见名称）:

【场景分析类】
1. analyze_scene
   - 参数: scene_text (或 text/scene/content) - 场景文本
            characters (或 known_characters/chars) - 角色名列表,可选
   - 返回: {scene_type, is_phone_call, phone_keywords_found, dialogue_quote_count}

2. check_phone_speaker
   - 参数: scene_text (或 text/scene/content) - 场景文本
            characters (或 known_characters/chars) - 角色名列表,可选
   - 返回: {receiver, caller, reasoning}

3. find_missing_dialogue
   - 参数: scene_text (或 text/scene/content) - 场景文本
            existing_beats (或 beats/current_beats) - 已提取的 beats,可选
   - 返回: {scene_dialogue, extracted_dialogue, missing}

【对话审查类】
4. verify_dialogue_speaker
   - 参数: beat (或 beat_info/the_beat) - 单个 beat 字典 {{id, type, character_id, content}}
            scene_text (或 text/scene/content) - 场景文本
            characters (或 known_characters/chars) - 角色名列表,可选
   - 返回: {{current_speaker, likely_speaker, is_correct, reasoning}}

5. check_beat_type
   - 参数: beat (或 beat_info/the_beat) - 单个 beat 字典
            scene_text (或 text/scene/content) - 场景文本
   - 返回: {{current_type, suggested_type, needs_correction, reasoning}}

【结果验证类】
6. validate_refined_beats
   - 参数: beats (或 refined_beats/final_beats) - 最终 beats 列表
   - 返回: {{is_valid, n_beats, issues}}

调用格式:
{{"action": "tool_name", "action_input": {{"arg1": "value1", ...}}}}

最终答案格式:
{{"is_final": true, "final_answer": {{...}}}}
"""
