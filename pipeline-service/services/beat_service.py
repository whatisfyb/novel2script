"""
Beat Service — Extractor + Critic + optional Refiner (LangGraph).

The most complex service: implements a 3-node LangGraph workflow that
takes a single scene and produces character-attributed beats with
self-correction.

Graph:
                 ┌──────────────┐
                 │  extractor   │  LLM call + heuristic fallback
                 └──────┬───────┘
                        │ beats
                        ▼
                 ┌──────────────┐
                 │   critic     │  LLM call (HAR review)
                 └──────┬───────┘
                        │ corrections (or empty)
                        ▼
                ┌──────────────────┐
                │  has_corrections? │
                └───┬──────────────┘
                    │ yes        │ no
                    ▼            │
             ┌──────────┐        │
             │ refiner  │        │
             └────┬─────┘        │
                  │              │
                  ▼              ▼
                 ┌──────────────┐
                 │   finalize   │
                 └──────────────┘

Endpoint:
  POST /extract — body {scene, characters, run_id}, returns {beats, corrections}
  POST /extract_batch — body {scenes, characters, run_id}, returns beats_by_scene

Run mode: `uvicorn services.beat_service:app --port 8003`.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, TypedDict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from llm.client import llm_complete
from llm.prompts import CRITIC_PROMPT, EXTRACT_BEATS_PROMPT, REFINER_PROMPT
from llm.pydantic_schemas import (
    CriticOutput,
    ExtractBeatsOutput,
    RefinerOutput,
)
from llm.schemas import CRITIC_SCHEMA, EXTRACT_SCHEMA, REFINER_SCHEMA  # legacy fallback
from services.redis_store import RedisStore, get_default_store

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Novel-to-Script Beat Service",
    description="LLM-based beat extraction with critic+refiner self-correction (LangGraph)",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class CharacterIn(BaseModel):
    id: str
    name: str
    aliases: list[str] = []
    role: str = "extra"
    description: str = ""


class SceneIn(BaseModel):
    scene_id: str           # e.g. "ch1_s1"
    chapter_order: int
    scene_text: str
    chapter_text: str | None = None
    scene_meta: dict | None = None   # description, location, time, etc.


class ExtractRequest(BaseModel):
    scene: SceneIn
    characters: list[CharacterIn]
    run_id: str | None = None


class BeatOut(BaseModel):
    id: str
    type: str
    character_id: str | None = None
    character_text: str | None = None
    content: str
    parenthetical: str | None = None
    emotion: str | None = None


class CorrectionOut(BaseModel):
    beat_id: str
    issue: str
    fix: dict
    confidence: float
    reasoning: str | None = None


class ExtractResponse(BaseModel):
    scene_id: str
    beats: list[BeatOut]
    corrections: list[CorrectionOut] = []
    refined: bool = False
    error: str | None = None


class BatchExtractRequest(BaseModel):
    scenes: list[SceneIn]
    characters: list[CharacterIn]
    run_id: str | None = None


class BatchExtractResponse(BaseModel):
    beats_by_scene: dict[str, list[BeatOut]]
    run_id: str | None = None


# ---------------------------------------------------------------------------
# Local Beat dataclass (kept simple; service-internal representation)
# ---------------------------------------------------------------------------

@dataclass
class Beat:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = "action"
    character_id: str | None = None
    character_text: str | None = None
    content: str = ""
    parenthetical: str | None = None
    emotion: str | None = None


# ---------------------------------------------------------------------------
# In-line attribution heuristics (kept here so the service is self-contained)
# ---------------------------------------------------------------------------

_FEMALE_HINTS = "薇娜丽芳红梅兰莲花英萍素"
_MALE_HINTS = "远明强军勇刚伟国建"


# Chinese speech-verb patterns for speaker attribution. These regexes
# find a character's name (1-4 Chinese chars) followed by a speech verb
# like 说/道/问/答/喊/叫/吼/叹/笑/哭. Used in the attribution pass to
# detect who is actually speaking when the LLM gets it wrong.
_SPEECH_VERB_BEFORE = re.compile(
    r'([\u4e00-\u9fa5]{1,4})'
    r'(?:说|道|问|答|喊|叫|吼|骂|叹|笑|哭|喝道|说道|问道|答道|喊道|答道)'
    r'(?:道|着)?'
    r'[:：]?\s*[""\u201c]'
)
_SPEECH_VERB_AFTER = re.compile(
    r'[""\u201d]\s*'
    r'([\u4e00-\u9fa5]{1,4})'
    r'(?:说|道|问|答|喊|叫|吼|骂道)'
)
_SPEECH_VERB_X_TO_Y = re.compile(
    r'([\u4e00-\u9fa5]{1,4})'
    r'(?:对|向|跟|和|冲|朝)'
    r'([\u4e00-\u9fa5]{1,4})'
    r'(?:说|道|问|喊|叫道)'
)

# Phone-call scene indicators
_PHONE_KEYWORDS = (
    "电话", "手机", "来电", "拨打", "接通", "挂断",
    "那头", "听筒", "话筒", "来电显示",
)

# Phone-receiver indicators (who got awakened/answered)
_RECEIVER_PATTERNS = [
    re.compile(r'([\u4e00-\u9fa5]{1,4})被.{0,5}惊醒'),
    re.compile(r'([\u4e00-\u9fa5]{1,4})犹豫.{0,3}接'),
    re.compile(r'([\u4e00-\u9fa5]{1,4})接了'),
    re.compile(r'([\u4e00-\u9fa5]{1,4})摸到.{0,5}手机'),
    re.compile(r'([\u4e00-\u9fa5]{1,4})拿起.{0,3}手机'),
]

# Phone-caller indicators
_CALLER_PATTERNS = [
    re.compile(r'([\u4e00-\u9fa5]{1,4})——'),
    re.compile(r'([\u4e00-\u9fa5]{1,4})打.{0,3}电话'),
    re.compile(r'来电.{0,3}显示.{0,5}([\u4e00-\u9fa5]{1,4})'),
]


def _detect_phone_speakers(scene_text: str, characters: list[dict]) -> tuple[str | None, str | None]:
    """For phone call scenes, identify receiver and caller.

    Returns (receiver, caller) — both can be None if not detectable.
    """
    is_phone = any(kw in scene_text for kw in _PHONE_KEYWORDS)
    if not is_phone:
        return None, None

    valid_names = {c.get("name", "") for c in characters if c.get("name")}

    receiver = None
    for pat in _RECEIVER_PATTERNS:
        m = pat.search(scene_text)
        if m and m.group(1) in valid_names:
            receiver = m.group(1)
            break

    caller = None
    for pat in _CALLER_PATTERNS:
        m = pat.search(scene_text)
        if m and m.group(1) in valid_names and m.group(1) != receiver:
            caller = m.group(1)
            break

    # If still no caller, pick the first character who is NOT the receiver.
    if not caller and receiver:
        for c in characters:
            name = c.get("name", "")
            if name and name != receiver:
                caller = name
                break

    return receiver, caller


def _find_speaker_from_speech_verb(
    content: str, scene_text: str, characters: list[dict]
) -> str | None:
    """Find a character's name in the scene text near this dialogue using
    Chinese speech-verb patterns.

    Returns the most likely speaker name, or None if not found.
    """
    valid_names = {c.get("name", "") for c in characters if c.get("name")}
    if not valid_names:
        return None

    # Look for "X说：" right before the dialogue in the scene text
    if content:
        # Strip surrounding quotes for matching
        clean = content.strip().strip('""\u201c\u201d"').strip()
        if clean:
            # Find this dialogue in scene text, look at preceding 30 chars
            pos = scene_text.find(clean[:15]) if clean else -1
            if pos > 0:
                preceding = scene_text[max(0, pos - 30):pos]
                m = _SPEECH_VERB_BEFORE.search(preceding + clean)
                if m and m.group(1) in valid_names:
                    return m.group(1)
                m = _SPEECH_VERB_AFTER.search(clean)
                if m and m.group(1) in valid_names:
                    return m.group(1)
                m = _SPEECH_VERB_X_TO_Y.search(preceding)
                if m:
                    # Could be X speaking TO Y, or Y speaking (rarely)
                    for grp in (m.group(1), m.group(2)):
                        if grp in valid_names:
                            return grp

    # Fall back: search the whole scene text
    for pat in (_SPEECH_VERB_BEFORE, _SPEECH_VERB_AFTER, _SPEECH_VERB_X_TO_Y):
        for m in pat.finditer(scene_text):
            for grp in m.groups():
                if grp in valid_names:
                    return grp

    return None


def _apply_attribution(beats: list[Beat], characters: list[dict], scene_text: str) -> list[Beat]:
    """Deterministic attribution pass on the LLM output.

    Heuristics (in order):
      1. Pre-pass: clear `character_text` that is not a known name/alias.
      2. Pre-pass: clear dialogue self-references (content starts with the
         attributed name + address punctuation).
      3. Phone call special-case: if scene is a phone call, force every
         unowned dialogue to the caller, and dialogue ending in "？" to the
         receiver (who usually asks "why/how").
      4. Speech-verb inference: for unowned dialogue, search the scene
         text for Chinese speech-verb patterns ("X说：", "X问：") to find
         the actual speaker.
      5. Alternation (smart): only switch to a different speaker if the
         previous dialogue was the OTHER speaker. Allows A-A-B-A patterns.
      6. Fallback: voiceover → first speaker; dialogue without prior → non-PoV.
      7. Action: attribute to most recent action char.
    """
    # Build valid names
    valid_names: set[str] = set()
    for c in characters:
        n = c.get("name", "")
        if n:
            valid_names.add(n)
        for a in c.get("aliases", []) or []:
            if a:
                valid_names.add(a)

    # Determine active speakers (in scene text)
    active_speakers = [
        c["name"] for c in characters
        if c.get("name") and c["name"] in scene_text
    ]

    # Detect phone call scene
    receiver, caller = _detect_phone_speakers(scene_text, characters)
    is_phone_call = receiver is not None and caller is not None

    # Pre-pass: clear invalid / self-referencing
    for b in beats:
        if b.type not in ("dialogue", "voiceover"):
            continue
        if not b.character_text:
            continue
        if b.character_text not in valid_names:
            b.character_text = None
            continue
        if b.type == "dialogue":
            content = b.content or ""
            name = b.character_text
            if content.startswith(name) and len(content) > len(name):
                nxt = content[len(name)]
                if nxt in "，,。.！!？?：: 　":
                    b.character_text = None

    # Heuristic loop on dialogue/voiceover
    last_dialogue_speaker: str | None = None
    for b in beats:
        if b.type not in ("dialogue", "voiceover"):
            continue
        if b.character_text:
            if b.type == "dialogue":
                last_dialogue_speaker = b.character_text
            continue

        # Phone call: questions → receiver, statements → caller
        if is_phone_call and b.type == "dialogue":
            content = (b.content or "").strip()
            if content.endswith(("？", "?")):
                b.character_text = receiver
            else:
                b.character_text = caller
            last_dialogue_speaker = b.character_text
            continue

        # Speech-verb inference
        inferred = _find_speaker_from_speech_verb(
            b.content or "", scene_text, characters
        )
        if inferred and inferred in valid_names:
            b.character_text = inferred
            last_dialogue_speaker = inferred
            continue

        # Smart alternation: only switch if the dialogue has explicit
        # evidence of a different speaker (e.g. content contains the
        # other speaker's name, or alternates A-A-B-A-B pattern that
        # has been seen in the scene). Otherwise, keep the same speaker
        # — it's common for one person to deliver 2-3 lines in a row.
        if last_dialogue_speaker and len(active_speakers) > 1:
            other_speakers = [s for s in active_speakers if s != last_dialogue_speaker]
            if other_speakers:
                # Check if content hints at a different speaker
                content = b.content or ""
                explicit_other = None
                for s in other_speakers:
                    if content.startswith(s) or f"{s}说" in content or f"{s}道" in content:
                        explicit_other = s
                        break
                if explicit_other:
                    b.character_text = explicit_other
                    last_dialogue_speaker = explicit_other
                else:
                    # No evidence of switch — keep same speaker
                    b.character_text = last_dialogue_speaker
                continue
        # voiceover → first speaker
        if b.type == "voiceover" and active_speakers:
            b.character_text = active_speakers[0]
            continue
        # dialogue without prior → pick non-PoV (last in list = "visitor")
        if b.type == "dialogue" and active_speakers:
            b.character_text = active_speakers[-1]
            last_dialogue_speaker = b.character_text

    # Action beats: attribute to most recent action char
    last_action_char: str | None = None
    for b in beats:
        if b.type != "action":
            continue
        if b.character_text:
            last_action_char = b.character_text
            continue
        if last_action_char:
            b.character_text = last_action_char
        elif active_speakers:
            b.character_text = active_speakers[0]
            last_action_char = b.character_text

    # Post-pass: voiceover validation. LLM misclassifies "角色注释"
    # (e.g. "林薇——三年没联系的前女友") as voiceover. Real voiceover
    # MUST contain an inner-thought marker like "心里想" / "暗自思忖"
    # / "回忆起" / "脑海". Anything else gets demoted to transition
    # (or action if it has a character).
    _VOICEOVER_MARKERS = ("心里想", "暗自思忖", "脑海中", "脑海里", "回想起",
                          "心里说", "心中想", "心里念", "暗自想", "暗想")
    for b in beats:
        if b.type != "voiceover":
            continue
        content = b.content or ""
        if not any(marker in content for marker in _VOICEOVER_MARKERS):
            # Demote to transition (or action if it has a character)
            if b.character_id:
                b.type = "action"
                logger.info(
                    "Demoted voiceover -> action (no inner-thought marker): %s",
                    content[:40],
                )
            else:
                b.type = "transition"
                logger.info(
                    "Demoted voiceover -> transition (no inner-thought marker): %s",
                    content[:40],
                )

    # Post-pass: transition with character check.
    # LLMs frequently attribute environmental/descriptive content like
    # "林薇比三年前瘦了很多" (a transition beat about 林薇) to
    # character=林薇. Strict rule: a transition beat should have
    # character=null UNLESS the beat is explicitly about a character's
    # transition (e.g. "周远走出房间"). Detect by checking if the beat
    # is *naming* the character (subject) vs *describing* them.
    for b in beats:
        if b.type != "transition":
            continue
        if not b.character_id:
            continue
        content = b.content or ""
        # If the beat's content doesn't contain an action verb after the
        # character name (e.g. "林薇走出房间" vs "林薇比三年前瘦了"),
        # the beat is *describing* the character, not transitioning them.
        # In that case, demote character.
        char_name = b.character_text or b.character_id
        # Heuristic: if the content is a sentence starting with
        # "[Name] + [comparison/state verb]" (e.g. 比, 显得, 看起来, 像是),
        # it's description, not action.
        _DESCRIBE_VERBS = ("比", "显得", "看起来", "像是", "在", "已经", "正在")
        if any(content.startswith(f"{char_name}{v}") for v in _DESCRIBE_VERBS):
            b.character_id = None
            b.character_text = None
            logger.info(
                "Demoted transition.character -> null (description of %s): %s",
                char_name, content[:40],
            )

    # Post-pass: pronoun inference in action beats.
    # "她拉开车门坐进副驾驶" — LLM left character=null. Resolve "她"/"他"
    # to the most recent female/male character in the beat list.
    # Determine gender for each character from description keywords.
    _FEMALE_HINT = ("女", "妻", "女友", "母亲", "女儿", "前女友", "妻子", "妈妈",
                    "姐姐", "妹妹", "妹", "姑", "姨", "婶")
    _MALE_HINT = ("男", "丈夫", "男友", "父亲", "儿子", "前男友", "丈夫", "爸爸",
                  "哥哥", "弟弟", "兄", "伯", "叔", "舅")
    gender_by_name: dict[str, str] = {}
    for c in characters:
        name = c.get("name", "")
        if not name:
            continue
        desc = c.get("description", "") or ""
        # Female cues first (more specific)
        if any(h in desc for h in _FEMALE_HINT) and not any(h in desc for h in _MALE_HINT):
            gender_by_name[name] = "F"
        elif any(h in desc for h in _MALE_HINT):
            gender_by_name[name] = "M"
        else:
            gender_by_name[name] = "?"  # unknown
    recent_female: str | None = None
    recent_male: str | None = None
    for b in beats:
        # Track most recent speaker by gender (from character_text).
        # If character was demoted, peek at content for a name.
        name_to_track = b.character_text
        if not name_to_track:
            _c = b.content or ""
            for n in active_speakers:
                if _c.startswith(n):
                    name_to_track = n
                    break
        if name_to_track:
            g = gender_by_name.get(name_to_track, "?")
            if g == "F":
                recent_female = name_to_track
            elif g == "M":
                recent_male = name_to_track
        # Resolve pronoun beats
        if b.type == "action" and not b.character_id and (b.content or "").startswith(("她", "他")):
            if (b.content or "").startswith("她") and recent_female:
                b.character_id = recent_female
                b.character_text = recent_female
                logger.info(
                    "Resolved pronoun 她 -> %s: %s",
                    recent_female, b.content[:40],
                )
            elif (b.content or "").startswith("他") and recent_male:
                b.character_id = recent_male
                b.character_text = recent_male
                logger.info(
                    "Resolved pronoun 他 -> %s",
                    recent_male, b.content[:40],
                )

    # Post-pass: fill character from content if content starts with a name.
    # LLM often leaves character=null for action beats whose content is
    # "周远把车停在C区..." — the speaker is obvious from context. Recover
    # it from the content prefix.
    for b in beats:
        if b.type not in ("action", "dialogue"):
            continue
        if b.character_text:
            continue
        content = b.content or ""
        # Find the longest matching active speaker name at the start
        matched: str | None = None
        for name in sorted(active_speakers, key=len, reverse=True):
            if content.startswith(name):
                # Make sure it's the start of a clause, not a name embedded
                # in a longer sentence. The next char (or end) must NOT be
                # a Chinese character (which would mean the name is a
                # substring of a longer word).
                end = len(name)
                if end < len(content):
                    nxt = content[end]
                    if "\u4e00" <= nxt <= "\u9fff":
                        # The name is a prefix of a longer word, skip
                        continue
                matched = name
                break
        if matched:
            b.character_id = matched
            b.character_text = matched
            # Also update recent_gender tracking
            g = gender_by_name.get(matched, "?")
            if g == "F":
                recent_female = matched
            elif g == "M":
                recent_male = matched
            logger.info(
                "Filled character from content prefix: %s -> %s: %s",
                matched, b.type, content[:40],
            )

    return beats


# ---------------------------------------------------------------------------
# LangGraph state and nodes
# ---------------------------------------------------------------------------

class BeatGraphState(TypedDict, total=False):
    # Inputs
    scene_id: str
    scene_text: str
    chapter_text: str | None
    characters: list[dict]
    run_id: str | None

    # Populated by nodes
    beats: list[dict]
    corrections: list[dict]
    has_corrections: bool
    refined: bool
    error: str | None
    start_ts: float
    extract_ts: float
    critic_ts: float
    refine_ts: float


# ---------------- Extractor node (ReAct) ----------------

EXTRACTOR_SYSTEM_PROMPT = """\
你是一位专业的剧本节拍提取师。你的任务是从场景文本中提取所有叙事节拍(beats)。

【工作流程 - ReAct 范式】

第一步: 调用 analyze_scene 工具分析场景类型
第二步 (仅当电话场景): 调用 check_phone_speaker 工具识别 receiver/caller
第三步: 调用 find_missing_dialogue 工具检查漏掉的引号对话
第四步: 基于所有观察结果,输出最终的 beats 列表

【节拍类型】
- action: 人物动作 (如"他站起来"、"她拿起杯子")
- dialogue: 对话 (含说话人)
- transition: 场景/环境/时间描写 (character=null)
- voiceover: 仅限内心独白 (有"心里想"、"暗自思忖"等标记)
- montage: 蒙太奇

【关键规则】

1. 对话归属:
   - 电话场景: dialogue 的 character = caller(打电话的人),不是 receiver
   - 面对面对话: 找最近的动作主语
   - 引号包裹的对话必须全部提取

2. 环境/时间描写: type=transition, character_id=null, character_text=null

3. 每 beat 一个独立句子 (不要把 3-4 句话堆成一个 beat)

4. 主语推断: 代词("他"/"她")必须解析到具体人物,character_id 不能为 null

5. type 必须是英文 enum: action | dialogue | transition | voiceover | montage
"""

CRITIC_SYSTEM_PROMPT = """\
你是一位资深的剧本编辑,负责审查 extract agent 提取的 beats 是否正确。

【工作流程 - ReAct 范式】

对每个 dialogue beat:
  1. 调用 verify_dialogue_speaker 工具验证说话人
  2. 如果工具返回 is_correct=False, 输出一条 correction (issue=wrong_speaker)

对每个 beat:
  3. 调用 check_beat_type 工具验证 type 字段
  4. 如果工具返回 needs_correction=True, 输出一条 correction (issue=wrong_type)

如果原文有引号对话但 beats 中没有,输出一条 correction (issue=missing_dialogue)

【关键规则】

1. 只标注 confidence >= 0.5 的问题 (宁可漏报)
2. fix 字段只包含需要修改的字段
3. reasoning 用一句话解释
4. 没有问题就返回空 corrections 列表
"""

REFINER_SYSTEM_PROMPT = """\
你是一位资深的剧本定稿编辑。基于 critic 的 corrections 输出最终的 beats 列表。

【工作流程 - ReAct 范式】

1. 阅读 critic 的 corrections
2. 如果 corrections 非空: 应用每条 fix, 调整对应的 beat
3. 调用 validate_refined_beats 工具验证最终结果
4. 如果 validate 返回 issues, 修正后再验证
5. 验证通过后, 输出最终答案

【关键规则】

- 如果 critic 的修正与原文一致 → 采纳
- 如果 critic 的修正与原文矛盾 → 优先原文
- 不要凭空添加原文中没有的内容
- type 必须是英文 enum
"""


async def extractor_node(state: BeatGraphState) -> dict:
    """ReAct agent: extract beats using scene analysis + phone speaker tools."""
    from services.react_agent import run_react_agent
    from services.react_tools import TOOLS as REACT_TOOLS
    from llm.react_schema import ExtractorFinalAnswer

    characters = state["characters"]
    char_parts = [
        f"{c['name']}(id:{c.get('id', c['name'])})" for c in characters
    ]
    char_str = ", ".join(char_parts) if char_parts else "无"

    user_context = f"""\
【已知角色】: {char_str}

【场景文本】:
---
{state["scene_text"]}
---

请开始 ReAct 推理。
"""

    try:
        result = await run_react_agent(
            system_prompt=EXTRACTOR_SYSTEM_PROMPT,
            user_context=user_context,
            tools=REACT_TOOLS,
            final_schema=ExtractorFinalAnswer,
            max_iterations=5,
        )
        beats = []
        for b in result.get("beats", []):
            beats.append(Beat(
                type=b.get("type", "action"),
                character_id=b.get("character_id"),
                character_text=b.get("character_text"),
                content=b.get("content", ""),
                parenthetical=b.get("parenthetical"),
                emotion=b.get("emotion"),
            ))
    except Exception as e:
        logger.error("Extractor ReAct failed: %s; falling back to legacy prompt", e)
        # Fallback to legacy single-shot extraction
        prompt = EXTRACT_BEATS_PROMPT.format(
            characters=char_str, scene_text=state["scene_text"],
        )
        data = await llm_complete(prompt, pydantic_model=ExtractBeatsOutput)
        beats = []
        for b in data.get("beats", []):
            beats.append(Beat(
                type=b.get("type", "action"),
                character_id=b.get("character_id"),
                character_text=b.get("character_text"),
                content=b.get("content", ""),
                parenthetical=b.get("parenthetical"),
                emotion=b.get("emotion"),
            ))

    # Apply in-service attribution (programmatic fallback for any remaining issues)
    _apply_attribution(beats, characters, state["scene_text"])

    beats_payload = [
        {
            "id": b.id, "type": b.type, "character_id": b.character_id,
            "character_text": b.character_text, "content": b.content,
            "parenthetical": b.parenthetical, "emotion": b.emotion,
        }
        for b in beats
    ]

    return {
        "beats": beats_payload,
        "extract_ts": time.time(),
    }


# ---------------- Critic node (ReAct) ----------------

async def critic_node(state: BeatGraphState) -> dict:
    """ReAct agent: review beats using verify_dialogue_speaker + check_beat_type tools."""
    from services.react_agent import run_react_agent
    from services.react_tools import TOOLS as REACT_TOOLS
    from llm.react_schema import CriticFinalAnswer, CriticFinalAnswerLenient

    beats = state.get("beats", [])
    if not beats:
        return {"corrections": [], "has_corrections": False, "critic_ts": time.time()}

    characters = state["characters"]
    char_parts = [
        f"{c['name']}(id:{c.get('id', c['name'])})" for c in characters
    ]
    char_str = ", ".join(char_parts) if char_parts else "无"

    beats_yaml = _beats_to_yaml(beats)

    user_context = f"""\
【已知角色】: {char_str}

【场景文本】:
---
{state["scene_text"]}
---

【待审查的 beats】:
{beats_yaml}

请开始 ReAct 推理。
"""

    try:
        result = await run_react_agent(
            system_prompt=CRITIC_SYSTEM_PROMPT,
            user_context=user_context,
            tools=REACT_TOOLS,
            final_schema=CriticFinalAnswerLenient,
            max_iterations=6,
        )
        corrections = result.get("corrections", [])
    except Exception as e:
        logger.error("Critic ReAct failed: %s; falling back to legacy prompt", e)
        # Fallback
        prompt = CRITIC_PROMPT.format(
            characters=char_str,
            scene_text=state["scene_text"],
            beats_yaml=beats_yaml,
        )
        data = await llm_complete(prompt, pydantic_model=CriticOutput)
        corrections = data.get("corrections", [])

    # Apply high-confidence corrections to beats in-place
    beat_by_id = {b["id"]: b for b in beats}
    applied: list[dict] = []
    confidence_threshold = 0.5
    for corr in corrections:
        if corr.get("confidence", 0.0) < confidence_threshold:
            continue
        bid = corr.get("beat_id")
        if bid not in beat_by_id:
            continue
        beat = beat_by_id[bid]
        fix = corr.get("fix", {})
        if not isinstance(fix, dict):
            continue
        for field, val in fix.items():
            if val is not None:
                beat[field] = val
        applied.append(corr)

    return {
        "beats": beats,
        "corrections": applied,
        "has_corrections": bool(applied),
        "critic_ts": time.time(),
    }


# ---------------- Refiner node (ReAct, conditional) ----------------

async def refiner_node(state: BeatGraphState) -> dict:
    """ReAct agent: refine beats based on critic feedback, with validation tool."""
    from services.react_agent import run_react_agent
    from services.react_tools import TOOLS as REACT_TOOLS
    from llm.react_schema import RefinerFinalAnswer

    beats = state.get("beats", [])
    corrections = state.get("corrections", [])
    characters = state["characters"]
    char_parts = [
        f"{c['name']}(id:{c.get('id', c['name'])})" for c in characters
    ]
    char_str = ", ".join(char_parts) if char_parts else "无"

    beats_yaml = _beats_to_yaml(beats)
    corrections_yaml = _corrections_to_yaml(corrections)

    user_context = f"""\
【已知角色】: {char_str}

【场景文本】:
---
{state["scene_text"]}
---

【当前 beats】:
{beats_yaml}

【Critic 的修正建议】:
{corrections_yaml}

请开始 ReAct 推理。
"""

    try:
        result = await run_react_agent(
            system_prompt=REFINER_SYSTEM_PROMPT,
            user_context=user_context,
            tools=REACT_TOOLS,
            final_schema=RefinerFinalAnswer,
            max_iterations=5,
        )
        refined_beats_payload = result.get("beats", beats)
    except Exception as e:
        logger.error("Refiner ReAct failed: %s; falling back to legacy prompt", e)
        # Fallback
        prompt = REFINER_PROMPT.format(
            characters=char_str,
            scene_text=state["scene_text"],
            beats_yaml=beats_yaml,
            corrections_yaml=corrections_yaml,
        )
        data = await llm_complete(prompt, pydantic_model=RefinerOutput)
        refined_beats_payload = data.get("beats", beats)

    # Auto-generate IDs for refined beats that lack them
    for b in refined_beats_payload:
        if not b.get("id"):
            b["id"] = str(uuid.uuid4())[:8]

    return {
        "beats": refined_beats_payload,
        "refined": True,
        "refine_ts": time.time(),
    }


# ---------------- Conditional routing ----------------

def should_refine(state: BeatGraphState) -> str:
    """Route to refiner if critic found issues, else END."""
    if state.get("has_corrections"):
        return "refiner"
    return END


# ---------------- Build the graph ----------------

def _build_graph():
    """Compile the LangGraph once and return the runnable."""
    workflow = StateGraph(BeatGraphState)

    workflow.add_node("extractor", extractor_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("refiner", refiner_node)

    workflow.add_edge(START, "extractor")
    workflow.add_edge("extractor", "critic")
    workflow.add_conditional_edges(
        "critic", should_refine, {"refiner": "refiner", END: END},
    )
    workflow.add_edge("refiner", END)

    return workflow.compile()


_beat_graph = None


def get_graph():
    """Lazy-init the compiled graph (allows tests to import the module)."""
    global _beat_graph
    if _beat_graph is None:
        _beat_graph = _build_graph()
    return _beat_graph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _beats_to_yaml(beats: list[dict]) -> str:
    lines = []
    for b in beats:
        lines.append(f"- id: {b.get('id', '?')}")
        lines.append(f"  type: {b.get('type', 'action')}")
        if b.get("character_text"):
            lines.append(f"  character: {b['character_text']}")
        if b.get("content"):
            c = b["content"].replace('"', '\\"')
            lines.append(f'  content: "{c}"')
        if b.get("parenthetical"):
            lines.append(f"  parenthetical: {b['parenthetical']}")
        if b.get("emotion"):
            lines.append(f"  emotion: {b['emotion']}")
    return "\n".join(lines) if lines else "（无节拍）"


def _corrections_to_yaml(corrections: list[dict]) -> str:
    if not corrections:
        return "（无修正）"
    lines = []
    for c in corrections:
        lines.append(f"- beat_id: {c.get('beat_id')}")
        lines.append(f"  issue: {c.get('issue')}")
        lines.append(f"  confidence: {c.get('confidence', 0)}")
        if c.get("reasoning"):
            lines.append(f"  reasoning: {c['reasoning']}")
        fix = c.get("fix", {})
        for k, v in fix.items():
            lines.append(f"  fix.{k}: {v}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

def get_store() -> RedisStore:
    return get_default_store()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "beat"}


def _beat_to_out(b: dict) -> BeatOut:
    # ID is generated at two points in the pipeline:
    #  - extractor node: explicit id via Beat dataclass factory
    #  - refiner node:   beats come straight from the LLM without an id
    # Auto-generate a UUID when missing so the API contract (id is required)
    # is preserved regardless of which node last wrote the beats.
    beat_id = b.get("id") or str(uuid.uuid4())[:8]
    return BeatOut(
        id=beat_id, type=b["type"],
        character_id=b.get("character_id"),
        character_text=b.get("character_text"),
        content=b.get("content", ""),
        parenthetical=b.get("parenthetical"),
        emotion=b.get("emotion"),
    )


def _correction_to_out(c: dict) -> CorrectionOut:
    return CorrectionOut(
        beat_id=c.get("beat_id", ""),
        issue=c.get("issue", ""),
        fix=c.get("fix", {}),
        confidence=c.get("confidence", 0.0),
        reasoning=c.get("reasoning"),
    )


async def _process_scene_internal(
    scene: SceneIn,
    characters: list[CharacterIn],
    run_id: str | None,
) -> ExtractResponse:
    store = get_store() if run_id else None
    chars_dicts = [c.model_dump() for c in characters]

    if store and run_id:
        await store.append_event(
            run_id=run_id, event_type="scene.submitted",
            source="beat_service", correlation_id=scene.scene_id,
            payload={
                "scene_id": scene.scene_id,
                "n_characters": len(characters),
            },
        )

    initial_state: BeatGraphState = {
        "scene_id": scene.scene_id,
        "scene_text": scene.scene_text,
        "chapter_text": scene.chapter_text,
        "characters": chars_dicts,
        "run_id": run_id,
        "start_ts": time.time(),
    }

    try:
        graph = get_graph()
        final_state = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.error("Beat service failed for %s: %s", scene.scene_id, e)
        if store and run_id:
            await store.append_event(
                run_id=run_id, event_type="scene.failed",
                source="beat_service", correlation_id=scene.scene_id,
                payload={"error": str(e), "stage": "graph"},
            )
        return ExtractResponse(
            scene_id=scene.scene_id, beats=[], error=str(e),
        )

    beats_out = [_beat_to_out(b) for b in final_state.get("beats", [])]
    corrections_out = [
        _correction_to_out(c) for c in final_state.get("corrections", [])
    ]

    if store and run_id:
        await store.append_event(
            run_id=run_id, event_type="beats.finalized",
            source="beat_service", correlation_id=scene.scene_id,
            payload={
                "n_beats": len(beats_out),
                "n_corrections": len(corrections_out),
                "refined": final_state.get("refined", False),
            },
        )

    return ExtractResponse(
        scene_id=scene.scene_id,
        beats=beats_out,
        corrections=corrections_out,
        refined=final_state.get("refined", False),
    )


@app.post("/extract", response_model=ExtractResponse)
async def extract_endpoint(req: ExtractRequest) -> ExtractResponse:
    return await _process_scene_internal(req.scene, req.characters, req.run_id)


@app.post("/extract_batch", response_model=BatchExtractResponse)
async def extract_batch_endpoint(req: BatchExtractRequest) -> BatchExtractResponse:
    import asyncio
    results = await asyncio.gather(
        *(_process_scene_internal(s, req.characters, req.run_id) for s in req.scenes),
        return_exceptions=True,
    )
    beats_by_scene: dict[str, list[BeatOut]] = {}
    for scene, result in zip(req.scenes, results):
        if isinstance(result, Exception):
            logger.warning("Batch extract failed for %s: %s", scene.scene_id, result)
            beats_by_scene[scene.scene_id] = []
        else:
            beats_by_scene[scene.scene_id] = result.beats
    return BatchExtractResponse(beats_by_scene=beats_by_scene, run_id=req.run_id)
