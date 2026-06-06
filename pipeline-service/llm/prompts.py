"""
Prompt templates for each LLM-powered pipeline stage.

Templates use Python string formatting with named placeholders.
Each template is paired with a JSON schema from schemas.py.
"""

# ---------------------------------------------------------------------------
# Stage 3: Structure Analysis — extract characters, locations, synopsis
# ---------------------------------------------------------------------------

ANALYZE_STRUCTURE_PROMPT = """\
你是一位专业的剧本结构分析师。请阅读以下小说文本，提取以下信息：

1. **synopsis**: 故事梗概（不超过200字）
2. **characters**: 所有出场人物列表
   - name: 标准姓名（中文名用汉字，如"林晓"）
   - aliases: 文中出现的其他称呼，包括：
     * 昵称/外号（如"老王"、"汪教授"）
     * 关系称谓（如"妻子"、"丈夫"、"母亲"）
     **重要规则**：如果角色A被称为"妻子"（相对于角色B），则角色B的aliases中必须包含"丈夫"。关系称谓必须双向对应。
   - role: 主角/配角/反派/龙套（protagonist/supporting/antagonist/extra）
   - description: 一句话人物描述
3. **locations**: 所有场景地点列表
   - name: 地点名称
   - type: 室内/室外/混合/虚拟（indoor/outdoor/mixed/virtual）
   - description: 一句话地点描述

小说文本：
---
{text}
---

请以 JSON 格式输出，严格按照以下结构：
{{"synopsis": "...", "characters": [...], "locations": [...]}}
"""

# ---------------------------------------------------------------------------
# Stage 4: Scene Segmentation — detect scene boundaries within a chapter
# ---------------------------------------------------------------------------

SEGMENT_SCENES_PROMPT = """\
你是一位专业的剧本场景分割师。请阅读以下小说章节文本，将它分割为独立场景。

每个场景需要标注：
- location: 场景发生地点（从已知地点中选择，或标注新地点）
- time: 时间（day/night/dawn/dusk/continuous）
- type: 室内/室外（interior/exterior）
- description: 一句话场景描述
- text_segment: [start_offset, end_offset] 在原文中的字符偏移量

【关键规则 — 必须严格遵守】

1. **不要分割对话**：
   - 场景边界**不能**在对话中间
   - 如果对话跨越多行（如"三楼，最西边的房间。当年我们在那里架了一台备用光谱仪。"），必须在**同一个 scene** 中
   - 场景边界应该在对话**之前**或**之后**，不要在对话中间

2. **场景边界判断**：
   - 时间变化（如"第二天早上"、"三小时后"）
   - 地点变化（如"他们来到咖啡馆"）
   - 人物变化（如"周远离开，林薇独自留下"）
   - **不要**仅因为段落换行就分割场景

3. **单场景章节**：
   - 如果整个章节只有一个连续的场景，返回一个 scene 覆盖全文
   - 不要强行分割

已知角色：{characters}
已知地点：{locations}

章节文本：
---
{chapter_text}
---

请以 JSON 格式输出：
{{"scenes": [{{"location": "...", "time": "...", "type": "...", "description": "...", "text_segment": [start, end]}}]}}
"""

# ---------------------------------------------------------------------------
# Stage 5: Beat Extraction — extract action/dialogue beats from a scene
# ---------------------------------------------------------------------------

EXTRACT_BEATS_PROMPT = """\
你是一位专业的剧本节拍提取师。请阅读以下场景文本，提取每一个叙事节拍（beat）。

节拍类型：
- action: 人物动作描写（如"他站起来"、"她拿起杯子"）
- dialogue: 对话（含说话人，如"你好"、"他说"）
- transition: 场景转换（如"第二天早上"、"三小时后"）
- voiceover: 仅限内心独白（如"他心里想"、"她暗自思忖"）
- montage: 蒙太奇段落

每个节拍需要标注：
- type: 节拍类型
- character_id: 人物ID（从已知角色中匹配，无明确角色时为null）
- character_text: 原文中出现的人物名称
- content: 节拍内容（精简后的剧本语言）
- parenthetical: 括号内的表演指示（如"低声"、"愤怒"，无则为null）
- emotion: 人物情绪状态（无则为null）

【关键规则 — 必须严格遵守】

1. **电话对话归属（最重要）**：
   - 如果场景中有"电话那头"、"来电"、"接听"、"手机"、"打电话"等关键词，说明是电话场景
   - 电话对白属于**打电话的人**（电话另一端），**不是**接电话的人
   - **判断方法**：
     * 找到接电话的人（如"周远被手机的震动惊醒" → 周远是接电话的人）
     * 电话对白属于**另一个人**（打电话的人）
     * 如果文中提到"林薇——三年没联系的前女友"，说明林薇是打电话的人
   - **示例**：
     * "周远，是我。" → 说话人是**林薇**（打电话的人），不是周远
     * "我需要你帮忙。" → 说话人是**林薇**，不是周远
     * "你怎么有我的电话？" → 说话人是**周远**（接电话的人）

2. **voiceover 定义**：
   - voiceover **仅限**内心独白，必须有明确的"心里想"、"暗自思忖"、"回忆起"等标记
   - **不要**把以下内容标为 voiceover：
     * 叙述性文字（如"老君山天文台在海拔两千四百米"）→ 应归 **transition**
     * 人物回忆（如"林薇——三年没联系的前女友"）→ 应归 **action** 或 **transition**
     * 场景描述（如"雨夜开车上山花了将近四个小时"）→ 应归 **transition**

3. **主语推断**：
   - 如果动作缺少主语，从上下文推断
   - 例："自己拿了一根撬棍" → 主语是前一个动作的执行者
   - 如果无法推断，character_text 设为 null

4. **对话完整性**：
   - 对话内容必须完整，不要截断
   - 如果对话被分割到两个 scene，应该在第一个 scene 中完整提取

已知角色：{characters}

场景文本：
---
{scene_text}
---

请以 JSON 格式输出：
{{"beats": [{{"type": "...", "character_id": "...", "character_text": "...", "content": "...", "parenthetical": "...", "emotion": "..."}}]}}
"""

# ---------------------------------------------------------------------------
# Stage 2 fallback: Chapter detection when regex fails
# ---------------------------------------------------------------------------

CHAPTER_DETECT_PROMPT = """\
你是一位专业的中文小说编辑。以下是一段小说文本的开头和结尾部分。
请判断这段文本是否包含多个章节，如果是，请标注每个章节的起始位置。

要求：
- 识别"第X章"、"第X回"、"第X节"等章节标记
- 如果没有明确标记，请根据叙事断裂点（如时间跳跃、场景大转换）来划分
- 返回每个章节的标题和在文本中的大致位置（行号）

小说文本（开头）：
---
{start_text}
---

小说文本（结尾）：
---
{end_text}
---

请以 JSON 格式输出：
{{"chapters": [{{"title": "...", "line_start": 0}}]}}
"""


# ---------------------------------------------------------------------------
# Stage 5b: Critic Agent (HAR-style review)
# ---------------------------------------------------------------------------
#
# The critic reviews the extractor's beat output against the original scene
# text and emits corrections only for beats that are likely wrong. It is
# invoked AFTER all heuristic fallbacks (normalize, name-address, action
# attribution, cross-scene refine) have run, so the input is already a
# best-effort attribution. The critic's job is to catch the LLM-level
# errors that heuristics cannot.

CRITIC_PROMPT = """\
你是一位资深的剧本编辑，负责审查另一位抽取师输出的场景节拍（beats）是否正确。

输入信息：
- 已知角色：{characters}
- 场景文本（原始中文小说片段）：
---
{scene_text}
---
- 待审查的节拍列表（已经过启发式 fallback 处理）：
{beats_yaml}

【审查目标 — 关键】

1. **说话人错误（wrong_speaker）**：对白的说话人是否正确？常见陷阱：
   - 电话对白：原文形如 `"..." 电话那头的声音沙哑`，对白属于电话**另一端**的人，**不是**接电话的现场人物
   - 连续对白：同一说话人的多句对白可能被错分给另一人
   - 自指归因：content 以 "X，" 开头但 character_text=X（X 是被呼叫者不是说话人）
   - 被动提及：content 中提到某角色名（如"张明的遗书"），但该角色并非说话人

2. **类型错误（wrong_type）**：是否被错分类？
   - 视觉/动作描述（如"看到来电显示"、"看到屏幕亮"）应归 action，不是 voiceover
   - 内心独白（明确"心里想"/"脑海"标记）应归 voiceover
   - 叙述性文字（如"老君山天文台在海拔两千四百米"）应归 transition 或 action，**不是** voiceover
   - 角色主动说出的对白应归 dialogue，不是 action

3. **缺失角色（missing_character）**：action/voiceover 应该有 character 但留空时，根据主语解析

4. **内容错误（wrong_content）**：节拍内容是否准确反映原文？有无幻觉/篡改？

5. **重复/合并（duplicate_beat / should_be_split）**：是否同一内容出现两次？是否应该拆分？

6. **对话完整性（incomplete_dialogue）**：对话内容是否被截断？

【审查方法】

逐条比对节拍内容与场景文本，**只标注有问题的节拍**。对每条怀疑的节拍：
- issue 归类（wrong_speaker / wrong_type / missing_character / wrong_content / duplicate_beat / should_be_split / incomplete_dialogue）
- fix 给出**只包含修改字段**的修正对象
- confidence 0-1（0.5 以下不要提交，宁可漏报）
- reasoning 一句话解释

**注意**：未经提示的 character_text 是合法 fallback 推断结果，不要因为不是原文字面就标记 wrong_speaker。只有明显矛盾（如她说自己名字/明显指向另一人）才标记。

【输出】

以 JSON 格式输出 corrections 列表。如果所有节拍都正确，返回空的 corrections 列表（不输出 corrections 也算通过）。
"""


# ---------------------------------------------------------------------------
# Stage 2 fallback: Chapter detection when regex fails
# ---------------------------------------------------------------------------
# Stage 5c: Refiner Agent — applies critic's corrections
# ---------------------------------------------------------------------------
#
# The refiner sees the original beats (already post-corrected by the
# extractor's heuristics) plus the critic's structured feedback. Its job
# is to produce the final, definitive beat list. Used only when the
# critic reports actual issues (otherwise the extractor's output is
# passed through as-is).

REFINER_PROMPT = """\
你是一位资深的剧本定稿编辑。另一位审查员（critic）已经指出了当前节拍（beats）中的问题。
请综合原始场景文本、当前节拍列表、critic 的修正建议，输出最终的节拍列表。

输入信息：
- 已知角色：{characters}
- 场景文本：
---
{scene_text}
---
- 当前节拍列表（已被 critic 修正过）：
{beats_yaml}

- critic 提出的修正建议（需要你判断采纳哪些、修改哪些、补充哪些）：
{corrections_yaml}

【任务】

输出最终的节拍列表。每个节拍都应该是：
- type 准确（action / dialogue / voiceover / transition / montage）
- character_text 反映真实说话人/动作主体
- content 精确反映原文，不夸大不漏写
- 必要的 parenthetical / emotion 保留

【采纳原则】

- 如果 critic 的修正与原文一致 → 直接采纳
- 如果 critic 的修正与原文矛盾 → 优先原文，以原文为准
- 如果 critic 漏掉了某些问题 → 你可以补
- 不要凭空添加原文中没有的内容

【输出】

以 JSON 格式输出最终的 beats 列表，结构与 EXTRACT_SCHEMA 一致：
{{"beats": [{{"type": "...", "character_id": "...", "character_text": "...", "content": "...", "parenthetical": "...", "emotion": "..."}}]}}
"""
