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
   - aliases: 文中出现的其他称呼（如"汪教授"、"老王"）
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
- type: 场景类型，**只允许两个枚举值之一**：`interior`（室内）或 `exterior`（室外）。严禁使用 indoor / outdoor / 等其他写法。
- description: 一句话场景描述
- text_segment: [start_offset, end_offset] 在原文中的字符偏移量

【重要约束 — 必须严格遵守】

1. **全覆盖**：所有场景的 text_segment 加起来必须覆盖整章文本，不允许任何字符被遗漏。
   - 第一个场景的 start 必须为 0
   - 最后一个场景的 end 必须等于章节文本长度（{chapter_length}）
   - 相邻场景之间不允许有未覆盖的空隙（前一个的 end == 后一个的 start）

2. **边界对齐**：text_segment 的 start 和 end 必须落在句子边界上，严禁在词语或句子中间截断。
   - 合法的边界字符包括：`。` `！` `？` `…` `"` `"` `」` `』` `）` `(`（左引号开启处或右引号闭合处之后）
   - 严禁在汉字、词语、引号内部截断（例如 "我们在那里" / "了一台光谱仪" 这种切法绝对禁止）
   - 如对白跨越多个段落，整个对白块应归入同一个 scene，禁止将对白腰斩

3. **scene 内文本必须完整可读**：每个 scene 切出来的子串都应是可独立理解的叙事段落，不能以残字、半句开头或结尾。

已知角色：{characters}
已知地点：{locations}

章节文本（共 {chapter_length} 字符）：
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
- action: 人物动作描写
- dialogue: 对话（含说话人）
- transition: 场景转换
- voiceover: 旁白/内心独白
- montage: 蒙太奇段落

每个节拍需要标注：
- type: 节拍类型
- character_id: 人物ID（从已知角色中匹配，无明确角色时为null）
- character_text: 原文中出现的人物名称
- content: 节拍内容（精简后的剧本语言）
- parenthetical: 括号内的表演指示（如"低声"、"愤怒"，无则为null）
- emotion: 人物情绪状态（无则为null）

【角色归因 — 重要规则】

必须为每一段对白/旁白找到正确的说话人。常见易错场景：

1. **电话对白**：原文形如 `"..." 电话那头的声音沙哑` 或 `"..." 电话那头说`，对白属于电话**另一端**的人，**不是**拿起电话的现场人物。归因方法：根据上下文（"电话那头"+ 声音描写 + 后续揭示身份）锁定说话人。
2. **画外音 / 旁白 / 内心独白**：若文本明确标注"心里想"/"脑海中浮现"/"画外音"，归入 voiceover 类型，character 仍指向思考者本人。
3. **被动提及的人物**：仅被旁白提到但未发声（如"看了一眼熟睡的妻子"）不应产生 dialogue 节拍，只产生 action 节拍。
4. **代词指代**：原文用"她"/"他"指代时，根据上一句的明确主语解析；无法解析时 character_text 填代词本身、character_id 填 null。

示例（已知角色：周远, 林薇, 苏婉）：

原文片段：周远接起电话。"周远，是我，我需要你帮忙。"电话那头的声音沙哑。
正确抽取：
  - type: action, character: 周远, content: "接起电话"
  - type: dialogue, character: 林薇, content: "周远，是我，我需要你帮忙。", parenthetical: "沙哑"
  解析依据：声音从电话另一端传来，后续剧情揭示是林薇；不能归为接电话的周远。

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
