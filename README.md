# Novel-to-Script

> AI 驱动的小说转剧本工具。上传小说文本（`.txt` / `.md` / `.docx`），系统自动提取角色、地点、场景与对白节拍，生成结构化的 YAML 剧本。

## 目录

- [功能概览](#功能概览)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [仓库结构](#仓库结构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [Pipeline 流水线详解](#pipeline-流水线详解)
- [ReAct 智能体架构](#react-智能体架构)
- [程序化后处理](#程序化后处理)
- [YAML 输出格式](#yaml-输出格式)
- [API 接口文档](#api-接口文档)
- [开发指南](#开发指南)
- [FAQ](#faq)

---

## 功能概览

- **多格式输入** — 支持 `.txt`、`.md`、`.docx` 小说文件
- **6 阶段流水线** — 文件解析 → 章节拆分 → 结构分析 → 场景分割 → 节拍提取 → YAML 组装
- **ReAct 智能体** — 节拍提取阶段使用 ReAct（Reasoning + Acting）范式，LLM 自主调用工具验证对话归属、检查节拍类型
- **结构化输出** — 生成包含角色、地点、幕、场景、节拍的完整剧本 YAML
- **实时进度** — WebSocket 流式推送，前端展示 6 阶段处理进度
- **浏览器内编辑** — Monaco 编辑器 + 剧本预览，支持导出
- **历史记录** — 自动保存每次转换结果，可随时查看和删除

---

## 系统架构

### 多服务架构

系统采用微服务架构，由 4 个 FastAPI 服务 + 1 个前端服务组成：

```
                          ┌─────────────────┐
                          │   前端 (Vite)    │
                          │   :3000         │
                          └────────┬────────┘
                                   │ HTTP / WebSocket
                          ┌────────▼────────┐
                          │  Orchestrator   │
                          │  :8000          │  ← 前端唯一入口
                          └───┬────┬────┬───┘
                              │    │    │
                 ┌────────────┘    │    └────────────┐
                 │                 │                  │
          ┌──────▼──────┐  ┌──────▼──────┐  ┌───────▼───────┐
          │ Input svc   │  │Structure svc│  │  Beat svc     │
          │ :8001       │  │ :8002       │  │  :8003        │
          │ parse+split │  │ analyze+seg │  │ ReAct agents  │
          └─────────────┘  └─────────────┘  └───────────────┘
                 │                 │                  │
                 └─────────────────┼──────────────────┘
                                   │
                          ┌────────▼────────┐
                          │     Redis       │
                          │     :6379       │  ← 任务状态存储
                          └─────────────────┘
```

| 服务 | 端口 | 职责 |
|------|------|------|
| **Orchestrator** | `:8000` | 前端入口，任务编排，进度推送，历史记录 API |
| **Input Service** | `:8001` | 文件解析（txt/md/docx），章节拆分 |
| **Structure Service** | `:8002` | 结构分析（角色/地点/摘要），场景分割 |
| **Beat Service** | `:8003` | 节拍提取（ReAct 智能体：Extractor → Critic → Refiner） |
| **Frontend** | `:3000` | Vite + React SPA |
| **Redis** | `:6379` | 任务状态与结果存储 |

### 数据流

```
用户上传文件
    │
    ▼
[Orchestrator] 创建 run_id → Redis 存储初始状态
    │
    ├─→ [Input :8001]      文件解析 + 章节拆分
    │       返回: 全文 + 章节列表
    │
    ├─→ [Structure :8002]  结构分析 + 场景分割
    │       返回: 角色/地点/摘要 + 场景列表
    │
    ├─→ [Beat :8003]       ReAct 节拍提取 (逐场景, 顺序执行)
    │       返回: 每个场景的 beats 列表
    │
    ▼
[Orchestrator] 组装 YAML → Redis 存储 → 前端获取
```

---

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| **前端** | React + TypeScript | React 19, TS 6 |
| | UI 框架 | Ant Design 6 |
| | 样式 | Tailwind CSS 4 |
| | 代码编辑器 | Monaco Editor |
| | 状态管理 | Zustand 5 |
| | 路由 | React Router 7 |
| | 构建工具 | Vite 8 |
| **后端 (Pipeline)** | 语言 | Python 3.13+ |
| | Web 框架 | FastAPI |
| | ASGI 服务器 | Uvicorn |
| | LLM 调用 | LiteLLM (OpenAI 兼容) |
| | 结构化输出 | Pydantic v2 |
| | 智能体框架 | LangGraph |
| | 数据校验 | JSON Schema |
| | 配置管理 | python-dotenv |
| **LLM** | 默认模型 | 小米 MiMo v2.5 Pro |
| | API 协议 | OpenAI 兼容 (JSON Schema strict) |
| **基础设施** | 缓存/存储 | Redis 5+ |
| | 容器化 | Docker + docker-compose |

---

## 仓库结构

```
novel2script/
├── frontend/                      前端 SPA
│   ├── src/
│   │   ├── components/            可复用 UI 组件
│   │   ├── pages/                 路由页面
│   │   │   ├── UploadPage.tsx     上传页面
│   │   │   ├── ProgressPage.tsx   进度页面
│   │   │   ├── EditorPage.tsx     编辑/预览页面
│   │   │   ├── HistoryPage.tsx    历史记录页面
│   │   │   └── LoginPage.tsx      登录页面
│   │   ├── services/              API 客户端
│   │   │   ├── orchestrator.ts    Pipeline API + WebSocket
│   │   │   └── history.ts         历史记录 API
│   │   ├── stores/                Zustand 状态管理
│   │   └── types/                 TypeScript 类型定义
│   ├── .env                       前端环境变量
│   └── package.json
│
├── pipeline-service/              后端 Pipeline 服务
│   ├── pipeline/                  6 阶段处理流水线
│   │   ├── parser.py              [阶段1] 文件解析 (txt/md/docx)
│   │   ├── splitter.py            [阶段2] 章节拆分
│   │   ├── analyzer.py            [阶段3] 结构分析 (角色/地点/摘要)
│   │   ├── segmenter.py           [阶段4] 场景分割 + 边界对齐 + 超长拆分
│   │   └── assembler.py           [阶段6] YAML 组装
│   ├── services/                  FastAPI 服务
│   │   ├── orchestrator.py        :8000 任务编排 + REST API + WebSocket
│   │   ├── input_service.py       :8001 文件解析服务
│   │   ├── structure_service.py   :8002 结构分析服务
│   │   ├── beat_service.py        :8003 节拍提取 (ReAct 3 节点)
│   │   ├── react_agent.py         ReAct 执行器 (think→act→observe 循环)
│   │   ├── react_tools.py         ReAct 工具集 (6 个工具)
│   │   └── redis_store.py         Redis 状态存储
│   ├── llm/                       LLM 客户端与约束
│   │   ├── client.py              LiteLLM 封装 + Pydantic 结构化输出
│   │   ├── prompts.py             所有 LLM 提示词
│   │   ├── pydantic_schemas.py    Pydantic 结构化输出模型 (13 个)
│   │   ├── react_schema.py        ReAct 步骤 + FinalAnswer 模型
│   │   └── schemas.py             旧版 JSON Schema (兼容保留)
│   ├── grpc_client/               gRPC 认证客户端
│   ├── .env.example               环境变量模板
│   ├── requirements.txt           Python 依赖
│   └── Dockerfile
│
├── auth-service/                  Java 认证服务 (Spring Boot 3)
│   ├── src/main/java/             DDD 四层架构
│   ├── pom.xml
│   └── Dockerfile
│
├── docs/                          设计文档
│   └── architecture/
│       └── agent-architecture.md  多服务架构设计
├── sample-novel.txt               示例小说 (完整)
├── test-chapters.txt              测试小说 (3 章短文本)
├── start-backend.bat              后端一键启动
├── start-frontend.bat             前端一键启动
├── docker-compose.yml             Docker 编排
└── README.md
```

---

## 快速开始

### 前置要求

- **Python** 3.13+
- **Node.js** 20+ (推荐 22 LTS)
- **Redis** 5+ (本地运行或 Docker)
- **LLM API Key** — 默认使用小米 MiMo v2.5 Pro

### 1. 克隆仓库

```bash
git clone https://github.com/whatisfyb/novel2script.git
cd novel2script
```

### 2. 安装依赖

```bash
# 前端
cd frontend
npm install

# 后端
cd ../pipeline-service
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cd pipeline-service
cp .env.example .env
```

编辑 `.env`，填入你的 MiMo API Key：

```env
LITELLM_MODEL=openai/mimo-v2.5-pro
MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
MIMO_API_KEY=你的API密钥
```

前端环境变量（`frontend/.env`，通常已配置）：

```env
VITE_API_BASE=http://127.0.0.1:8000
```

### 4. 启动 Redis

```bash
# 方式一: 直接安装
redis-server

# 方式二: Docker
docker run -d --name redis -p 6379:6379 redis:7
```

### 5. 启动服务

**Windows**（双击或命令行执行）：

```bash
# 启动后端 (4 个 FastAPI 服务)
start-backend.bat

# 启动前端 (Vite 开发服务器)
start-frontend.bat
```

**手动启动**（Linux/macOS 或自定义环境）：

```bash
# 后端 - 依次启动 4 个服务
cd pipeline-service
uvicorn services.input_service:app --host 127.0.0.1 --port 8001 &
uvicorn services.structure_service:app --host 127.0.0.1 --port 8002 &
uvicorn services.beat_service:app --host 127.0.0.1 --port 8003 &
uvicorn services.orchestrator:app --host 127.0.0.1 --port 8000 --reload

# 前端
cd ../frontend
npm run dev
```

### 6. 使用

打开浏览器访问 **http://localhost:3000**

1. 上传小说文件（`.txt` / `.md` / `.docx`）
2. 选择剧本类型（电视剧 / 电影 / 短视频 / 舞台剧）
3. 等待处理完成（实时进度展示）
4. 在编辑器中查看/修改 YAML 剧本

---

## 配置说明

### 后端环境变量 (`pipeline-service/.env`)

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `LITELLM_MODEL` | 是 | — | LiteLLM 模型标识符 |
| `MIMO_BASE_URL` | 是 | — | MiMo API 地址 |
| `MIMO_API_KEY` | 是 | — | MiMo API 密钥 |
| `GRPC_AUTH_HOST` | 否 | `localhost` | 认证服务 gRPC 地址 |
| `GRPC_AUTH_PORT` | 否 | `9090` | 认证服务 gRPC 端口 |
| `CORS_ORIGINS` | 否 | `*` | CORS 允许的源（逗号分隔） |

### 前端环境变量 (`frontend/.env`)

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `VITE_API_BASE` | 是 | — | 后端 Orchestrator 地址。**不设置则自动使用 Mock 数据** |

> **注意**：如果前端页面显示 Mock 数据，检查 `VITE_API_BASE` 是否正确加载。Vite 必须在 `frontend/` 目录下启动才能读取 `.env` 文件。

---

## Pipeline 流水线详解

### 6 个处理阶段

```
 ┌─────────────────────────────────────────────────────────────┐
 │                    Pipeline 流水线                           │
 └─────────────────────────────────────────────────────────────┘

 [阶段1] 文件解析 (parser.py)
   输入: .txt / .md / .docx 文件
   处理: 提取纯文本，自动检测编码
   输出: 全文字符串
         ↓
 [阶段2] 章节拆分 (splitter.py)
   输入: 全文文本
   处理: 正则匹配 "第X章" / "Chapter N" 分割章节
   输出: 章节列表 [{order, title, text}]
         ↓
 [阶段3] 结构分析 (analyzer.py)                    ← LLM 调用
   输入: 全部章节文本
   处理: LLM 提取角色列表、地点列表、故事摘要
         Pydantic 约束: AnalyzeStructureOutput
   后处理: 角色别名双向关系补全 (妻子↔丈夫, 前女友↔前男友)
   输出: {characters, locations, synopsis}
         ↓
 [阶段4] 场景分割 (segmenter.py)                  ← LLM 调用
   输入: 每章文本
   处理: LLM 按地点/时间变化分割场景
         Pydantic 约束: SegmentScenesOutput
   后处理:
     - 边界对齐: 场景边界 snap 到句末标点 (。！？\n)
     - 超长拆分: 超过 800 字的 segment 在句号处自动拆分
     - 间隙填充: 相邻场景间的未分配文本自动归入前一个场景
   输出: 场景列表 [{id, location, time, text_segment, ...}]
         ↓
 [阶段5] 节拍提取 (beat_service.py)               ← ReAct 智能体
   输入: 每个场景文本 + 角色列表
   处理: ReAct 3 节点 (Extractor → Critic → Refiner)
         每节点最多 5 轮 think→act→observe 循环
         Pydantic 约束: ExtractBeatsOutput / CriticOutput / RefinerOutput
   后处理: 对话归属推断 (详见 [程序化后处理](#程序化后处理))
   输出: 节拍列表 [{id, type, character, content, ...}]
         ↓
 [阶段6] YAML 组装 (assembler.py)
   输入: 全部阶段输出
   处理: 代码组装，生成最终 YAML
   输出: 完整剧本 YAML
```

### 速率限制策略

Beat Service 对 LLM 的调用最为密集（每个场景触发 3 个 ReAct 节点 × 最多 5 轮迭代）。为避免触发 MiMo API 的 100 RPM 限制：

- 场景间**顺序执行**（非并发），每个场景间 5 秒间隔
- 单场景内 Extractor → Critic → Refiner 也是顺序执行
- ReAct 失败时自动降级为单次 Pydantic 调用（保证可用性）

---

## ReAct 智能体架构

节拍提取阶段（阶段 5）使用 **ReAct（Reasoning + Acting）范式**，由 3 个智能体节点组成：

### 架构图

```
         ┌──────────────────────────────────┐
         │        Beat Service              │
         └──────────┬───────────────────────┘
                    │
         ┌──────────▼──────────┐
         │   Extractor Agent   │     提取原始 beats
         │   (ReAct, 5 轮)     │     工具: analyze_scene, check_phone_speaker,
         └──────────┬──────────┘             find_missing_dialogue
                    │
         ┌──────────▼──────────┐
         │    Critic Agent     │     审查 beats 质量
         │   (ReAct, 5 轮)     │     工具: verify_dialogue_speaker, check_beat_type
         └──────────┬──────────┘
                    │
              有问题? │
              ├── 是 ──→ ┌──────────▼──────────┐
              │         │   Refiner Agent     │  修正 beats
              │         │   (ReAct, 5 轮)     │  工具: validate_refined_beats
              │         └──────────┬──────────┘
              │                    │
              └── 否 ──────────────┤
                                   │
                              ┌────▼────┐
                              │  END    │  输出最终 beats
                              └─────────┘
```

### ReAct 执行循环

每个 ReAct 节点内部遵循 `think → act → observe` 循环：

```
Step 1: THINK  — LLM 分析当前状态，决定下一步
Step 2: ACT    — LLM 选择一个工具并传入参数
Step 3: OBSERVE — 系统执行工具，返回结果给 LLM
        (重复 Step 1-3，最多 5 轮)
Step N: FINAL   — LLM 输出最终结构化答案 (Pydantic 约束)
```

### 工具集（6 个工具）

| 工具 | 所属节点 | 功能 |
|------|----------|------|
| `analyze_scene` | Extractor | 分析场景文本，返回角色、对话、动作概要 |
| `check_phone_speaker` | Extractor | 电话场景中判断来电方/接听方 |
| `find_missing_dialogue` | Extractor | 检查场景文本中是否有遗漏的对话 |
| `verify_dialogue_speaker` | Critic | 验证某条对话的说话人是否正确 |
| `check_beat_type` | Critic | 验证某条 beat 的类型是否正确 |
| `validate_refined_beats` | Refiner | 验证修正后的 beats 列表完整性 |

> 工具参数采用 `**kwargs` 智能映射，容忍 LLM 的参数名猜测偏差（如 `known_characters` 自动映射到 `characters`）。

### 降级机制

如果 ReAct 执行失败（LLM 异常、工具报错、超出迭代次数），自动降级为单次 Pydantic 结构化调用，保证服务可用性。

---

## 程序化后处理

LLM 输出不总是可靠的。系统在关键阶段部署了多层程序化后处理：

### 1. 角色别名双向补全（analyzer.py）

LLM 可能只给出一侧别名关系。后处理自动补全：

```
周远.aliases = ["前男友"]           → 自动给林薇加 "前女友"
林薇.description = "周远的前女友"     → 自动给周远加 "前女友" 的反向别名
```

规则：基于角色 description 中的互引关系（A 的 description 提到 B）。

### 2. 场景边界对齐（segmenter.py）

LLM 经常把场景边界放在句子中间。后处理自动 snap 到最近的句末标点：

```
修复前: S003 末尾 "一根从" ← 句子被截断
修复后: S003 末尾 "撬棍。" ← 完整句子
```

### 3. 超长场景拆分（segmenter.py）

超过 800 字的 scene segment 在句号处自动拆分为多个场景。

### 4. 对话归属推断（beat_service.py）

最复杂的后处理，采用 **Sieve 策略**分层推断：

| 优先级 | 方法 | 触发条件 | 示例 |
|--------|------|----------|------|
| 1 | Speech verb 检测 | content 中有 X说/X道/X问 | "周远压低声音说：..." → 周远 |
| 2 | 电话问号推断 | 电话场景 + 问号结尾 | "你怎么有我的电话？" → 接听方 |
| 3 | 代词推断 | content 以 她/他 开头 | 根据 description 性别线索映射 |
| 4 | Content-prefix 推断 | content 以角色名+动作开头 | "周远把车停在..." → 周远 |
| 5 | A-B-A-B 交替 | 连续 null dialogue | 双人对话交替推断 |
| 6 | "Name+比" 降级 | "XX比三年前瘦了" | 降级为 transition + null |

### 5. Voiceover 降级（beat_service.py）

被标记为 `voiceover` 但缺乏内心独白标记（心里想/暗自思忖）的 beat，自动降级为 `action`。

---

## YAML 输出格式

```yaml
meta:
  title: 小说标题
  author: 作者
  adapter: Novel-to-Script AI
  type: tv                          # tv / movie / short_video / stage_play
  language: zh
  created_at: '2026-06-06T15:56:11Z'
  source_chapters: 3                # 原始章节数
  synopsis: 故事摘要...

characters:
  - id: 周远
    name: 周远
    aliases: [前男友, 丈夫]          # 自动补全的双向别名
    role: protagonist               # protagonist / supporting / extra
    description: 角色描述

locations:
  - id: 周远的卧室
    name: 周远的卧室
    type: indoor                    # indoor / outdoor / mixed
    description: 地点描述

acts:
  - id: act_1
    title: 第一幕
    chapters: [1, 2, 3]
    synopsis: 幕摘要
    scenes:
      - id: S001
        number: 1
        heading:
          location: 周远的卧室
          time: night               # night / day / dawn / dusk / continuous
          type: interior            # interior / exterior
        description: 场景描述
        beats:
          - id: 5bd20ffd
            type: transition        # action / dialogue / transition / voiceover / montage
            character: null         # null 表示旁白/环境描写
            content: 凌晨两点十七分...
            parenthetical: null     # 表情/语气提示
            emotion: null           # 情绪标签
```

### Beat 类型说明

| 类型 | 说明 | character |
|------|------|-----------|
| `action` | 角色动作 | 角色名或 null |
| `dialogue` | 对话 | 说话角色名 |
| `transition` | 场景转换/环境描写 | 通常为 null |
| `voiceover` | 内心独白/旁白 | 角色名 |
| `montage` | 蒙太奇序列 | null |

---

## API 接口文档

### REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/pipeline` | 上传文件，启动转换流水线 |
| `GET` | `/pipeline/list` | 列出所有转换任务 |
| `GET` | `/pipeline/{run_id}/status` | 查询任务状态 |
| `GET` | `/pipeline/{run_id}/events` | 获取任务事件列表 |
| `GET` | `/pipeline/{run_id}/result` | 获取转换结果 (YAML) |
| `GET` | `/api/history` | 获取历史记录列表 |
| `GET` | `/api/history/{run_id}` | 获取单条历史记录详情 |
| `DELETE` | `/api/history/{run_id}` | 删除历史记录 |
| `GET` | `/health` | 健康检查 |

### WebSocket

| 路径 | 说明 |
|------|------|
| `ws://localhost:8000/ws/pipeline/{run_id}` | 实时推送任务进度 |

WebSocket 消息格式：

```json
{
  "stage": "beat_extraction",
  "status": "processing",
  "progress": 75,
  "message": "正在提取 S002 的节拍..."
}
```

### 交互式文档

后端启动后访问 **http://localhost:8000/docs** 查看 Swagger UI。

---

## 开发指南

### 项目约定

- **分支策略**：`master` 分支只接受通过 PR 合并的 `feat/*` 或 `fix/*` 分支
- **提交格式**：每个 commit 包含 ① 标题 ② 功能描述 ③ 实现思路 ④ 测试方式
- **PR 粒度**：每个 PR 只做一件事
- **结构化输出**：所有 LLM 调用使用 Pydantic schema 约束 + API 级别 `json_schema` strict 模式
- **密钥管理**：API Key 从 `.env` 加载，绝不硬编码

### 本地开发

```bash
# 前端开发 (热重载)
cd frontend
npm run dev

# 后端开发 (热重载)
cd pipeline-service
uvicorn services.orchestrator:app --reload --port 8000

# 运行测试
cd pipeline-service && pytest
cd frontend && npm test
```

### Pydantic 结构化输出

所有 LLM 调用通过 Pydantic 模型约束输出：

```python
from llm.client import llm_complete
from llm.pydantic_schemas import ExtractBeatsOutput

data = await llm_complete(
    prompt="...",
    pydantic_model=ExtractBeatsOutput,  # API 级别 json_schema strict
)
# data 已通过 model_validate() 硬校验
```

当前定义了 13 个 Pydantic 模型（`llm/pydantic_schemas.py`），覆盖所有 LLM 调用场景。

### 添加新的 ReAct 工具

1. 在 `services/react_tools.py` 中定义 `async def` 函数
2. 在 `llm/react_schema.py` 中更新对应 FinalAnswer 模型
3. 在 `services/beat_service.py` 中注册到对应节点的工具列表

---

## FAQ

### Q: 前端显示 Mock 数据？

检查 `frontend/.env` 中 `VITE_API_BASE` 是否设置。该变量未设置时前端自动使用 Mock 数据。确保 Vite 从 `frontend/` 目录启动。

### Q: 某个场景的 beats 为空？

通常由 MiMo API 速率限制（100 RPM）导致。系统已采用顺序执行 + 5 秒间隔缓解，但章节过多时仍可能触发。重新运行即可。

### Q: 对话归属不准确？

电话对话和缺乏 speech verb 标记的对话是主要难点。系统已部署 6 层 Sieve 推断策略，但 LLM 偶尔仍会混淆。可手动在 YAML 编辑器中修正。

### Q: 如何切换 LLM 模型？

修改 `.env` 中的 `LITELLM_MODEL` 和对应的 API Key。支持所有 LiteLLM 兼容模型（OpenAI / DeepSeek / Anthropic 等）。注意更换模型后可能需要调整 prompt。

### Q: Docker 部署？

```bash
docker-compose up -d
```

包含 Redis + Pipeline Service + Frontend（不含 Auth Service）。

---

## License

Internal project — 尚未开源授权。
