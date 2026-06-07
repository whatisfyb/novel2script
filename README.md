# Novel-to-Script

> AI 驱动的小说转剧本工具。上传小说文本（`.txt` / `.md` / `.docx`），系统自动提取角色、地点、场景与对白节拍，生成结构化的 YAML 剧本。

**[演示视频](https://www.bilibili.com/video/BV1kWEx6tEgf/)**

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
- [Docker 部署](#docker-部署)
- [开发指南](#开发指南)
- [FAQ](#faq)

---

## 功能概览

- **多格式输入** — 支持 `.txt`、`.md`、`.docx` 小说文件
- **6 阶段流水线** — 文件解析 → 章节拆分 → 结构分析 → 场景分割 → 节拍提取 → YAML 组装
- **ReAct 智能体** — 节拍提取阶段使用 ReAct（Reasoning + Acting）范式，LLM 自主调用工具验证对话归属、检查节拍类型
- **结构化输出** — 所有 LLM 调用通过 Pydantic 模型 + API 级别 `json_schema` strict 模式强制约束输出格式
- **实时进度** — WebSocket 流式推送，前端展示 6 阶段处理进度与事件日志
- **浏览器内编辑** — Monaco 编辑器 + 剧本预览，支持导出 YAML / Fountain 格式
- **历史记录** — 独立的 Java 历史服务（DDD 架构）持久化转换记录，支持分页查询、筛选、删除
- **用户认证** — 独立的 Java 认证服务，DDD 架构，Sa-Token 会话管理，gRPC 跨服务调用

---

## 系统架构

### 整体架构

系统由四部分组成：**Pipeline 服务群**（Python）、**Auth 认证服务**（Java）、**History 历史服务**（Java）、**前端**（React）。

```
                          ┌─────────────────┐
                          │   前端 (Vite)    │
                          │   :3000         │
                          └──┬──────┬────┬──┘
                             │      │    │
              Auth API       │      │    │  Pipeline API + WS
              (:8080)        │      │    │  (:8000)
                   ┌─────────▼┐  ┌──▼────────────┐
                   │Auth Svc  │  │ Orchestrator  │
                   │Java/DDD  │  │ :8000         │
                   └────┬─────┘  └──┬───┬───┬───┘
                        │gRPC:9090   │   │   │
                        │       ┌────┘   │   └──────┐
                   ┌────▼──┐  ┌▼──────┐ ┌▼────────┐
                   │gRPC   │  │Input  │ │Structure│
                   │Client │  │:8001  │ │:8002    │
                   └───────┘  └───────┘ └─────────┘
                                              ┌──▼──────┐
                                              │Beat svc │
                                              │:8003    │
                                              └─────────┘
                                                       │
              ┌─────────────────┐                      │
              │  History Svc    │    ┌─────────────┐   │
              │  Java/DDD       │    │   Redis     │◄──┘
              │  :8010          │    │   :6379     │
              │  MySQL          │    │ 状态/事件存储 │
              └─────────────────┘    └─────────────┘
```

### Pipeline 服务群（Python / FastAPI）

| 服务 | 端口 | 职责 |
|------|------|------|
| **Orchestrator** | `:8000` | 前端唯一入口，任务编排，进度推送（WebSocket），历史记录 API |
| **Input Service** | `:8001` | 文件解析（txt/md/docx），章节拆分 |
| **Structure Service** | `:8002` | 结构分析（角色/地点/摘要），场景分割 |
| **Beat Service** | `:8003` | 节拍提取（LangGraph ReAct 智能体：Extractor → Critic → Refiner） |

Orchestrator 通过 HTTP 调用其他三个子服务，任务状态和结果存储在 Redis 中。

### Auth 认证服务（Java / Spring Boot 3）

认证服务采用 **DDD（领域驱动设计）四层架构**，严格分离业务逻辑与技术实现：

```
com.novel.auth
├── interfaces/              接口层 — 对外暴露 API
│   ├── rest/                REST 控制器
│   │   ├── AuthController   POST /api/auth/{register,login,logout}
│   │   ├── dto/             请求/响应 DTO (LoginRequest, RegisterRequest, LoginResponse)
│   │   └── assembler/       Domain → DTO 装配器
│   └── grpc/                gRPC 服务端 — AuthService 实现
│       └── AuthGrpcService  VerifyToken / CheckQuota / RecordUsage
│
├── application/             应用层 — 用例编排
│   └── service/
│       ├── AuthAppService   注册 / 登录 / 登出
│       ├── QuotaAppService  配额查询 / 扣减
│       └── ApiKeyAppService API Key 管理（开发中）
│
├── domain/                  领域层 — 核心业务规则（无外部依赖）
│   ├── model/               实体 & 值对象 (User, UserId, Quota, AccountStatus)
│   ├── repository/          仓储接口 (UserRepository, QuotaRepository)
│   ├── service/             领域服务 (PasswordDomainService/BCrypt, QuotaDomainService)
│   └── event/               领域事件 (UserRegisteredEvent, QuotaExhaustedEvent)
│
├── infrastructure/          基础设施层 — 技术实现
│   ├── persistence/         MyBatis-Plus 持久化
│   │   ├── po/              持久化对象 (UserPO, QuotaPO, ApiKeyPO)
│   │   ├── mapper/          MyBatis Mapper
│   │   ├── converter/       PO ↔ Domain 转换器
│   │   └── repository/      仓储实现
│   └── config/              Spring 配置 (SaToken, CORS, MybatisPlus, gRPC)
│
└── common/                  公共层
    ├── result/              统一返回包装 R<T>
    └── exception/           全局异常处理
```

| 层级 | 职责 | 依赖方向 |
|------|------|----------|
| 接口层 | 接收请求，DTO 转换 | → 应用层 |
| 应用层 | 编排用例，事务管理 | → 领域层 |
| 领域层 | 核心业务规则（最内层，不依赖任何其他层） | 无 |
| 基础设施层 | 技术实现：数据库、gRPC、配置（实现领域层接口） | → 领域层 |

**技术选型**：Sa-Token（会话认证）、MyBatis-Plus（ORM）、BCrypt（密码加密 cost=12）、Flyway（数据库迁移）、MySQL、gRPC + Protobuf（跨服务调用）。

**数据库**（Flyway 管理，3 张表）：
- `users` — 用户表（UUID 主键，username/email 唯一）
- `user_quota` — 配额表（plan: 0=free/1=pro，remaining，reset_at）
- `api_keys` — API Key 表（开发中）

> **注意**：gRPC `VerifyToken` 和 `ApiKeyAppService` 目前是 stub，Pipeline 服务的 `grpc_client/auth_client.py` 已实现但尚未接入 orchestrator 路由的认证中间件。

### History 历史服务（Java / Spring Boot 3）

历史服务负责持久化每次转换记录，同样采用 **DDD 架构**：

```
com.novel.history
├── interfaces/rest/                接口层
│   ├── HistoryController           REST 端点 (5 个)
│   └── dto/                        请求/响应 DTO
├── application/service/
│   └── HistoryAppService           历史记录 CRUD 编排
├── domain/
│   ├── model/
│   │   ├── ConversionHistory       转换记录实体 (16 个字段)
│   │   └── ConversionStatus        枚举 (COMPLETED/PROCESSING/FAILED)
│   └── repository/
│       └── HistoryRepository       仓储接口
├── infrastructure/
│   ├── persistence/                MyBatis-Plus 实现
│   └── config/                     CORS + 分页配置
└── common/                         异常处理 + 统一返回
```

**REST 端点**（:8010）：

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/history` | 创建转换记录 |
| `GET` | `/api/history` | 分页列表（支持 scriptType / status 筛选） |
| `GET` | `/api/history/{runId}` | 按 run ID 查询详情 |
| `PATCH` | `/api/history/{runId}` | 部分更新（状态/章节数/YAML 等） |
| `DELETE` | `/api/history/{runId}` | 删除记录 |

**数据库**：MySQL，`conversion_history` 表（16 列：run_id, filename, title, script_type, language, status, chapters, acts, scenes, characters, yaml, error, timestamps 等）。

**技术选型**：Spring Boot 3.3.5、MyBatis-Plus 3.5.7、Flyway、UUID 主键、Jakarta Validation。

> **注意**：Orchestrator 目前也提供了 `/api/history` 端点（从 Redis 读取），用于 History Service 未启动时的兼容。前端 `history.ts` 优先调用 `VITE_API_BASE`（Orchestrator），生产环境可切换到 History Service `:8010`。

### 前端（React 19）

前端采用**状态驱动路由**（非 URL 路由），通过 Zustand store 的 `step` 字段切换页面：

```
LoginPage → UploadPage → ProgressPage → EditorPage
                            ↕
                        HistoryPage
```

| 页面 | 功能 |
|------|------|
| LoginPage | 登录/注册（调用 Auth Service `:8080`） |
| UploadPage | 文件上传 + 剧本类型选择 |
| ProgressPage | 实时进度条 + 事件日志（WebSocket） |
| EditorPage | Monaco YAML 编辑器 + 剧本预览 + 导出 |
| HistoryPage | 历史记录列表，搜索/筛选/删除 |

---

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| **Pipeline 后端** | | |
| 语言 | Python | 3.13+ |
| Web 框架 | FastAPI | 0.111+ |
| LLM 调用 | LiteLLM (OpenAI 兼容) | 1.0+ |
| 结构化输出 | Pydantic v2 | — |
| 智能体框架 | LangGraph | 1.0+ |
| 文档解析 | python-docx | 1.1+ |
| 状态存储 | Redis | 5.0+ |
| gRPC 客户端 | grpcio + grpcio-tools | 1.66+ |
| **Auth 后端** | | |
| 语言 | Java | 21 |
| 框架 | Spring Boot | 3.3.5 |
| 认证 | Sa-Token | 1.39.0 |
| ORM | MyBatis-Plus | 3.5.7 |
| 密码 | BCrypt (favre lib) | 0.10.2 |
| 数据库 | MySQL | — |
| 数据库迁移 | Flyway | — |
| gRPC | grpc-server-spring-boot-starter | 3.1.0 |
| **History 后端** | | |
| 语言 | Java | 21 |
| 框架 | Spring Boot | 3.3.5 |
| ORM | MyBatis-Plus | 3.5.7 |
| 数据库 | MySQL | — |
| 数据库迁移 | Flyway | — |
| **前端** | | |
| 框架 | React | 19 |
| UI 组件 | Ant Design | 6 |
| 样式 | Tailwind CSS | 4 |
| 代码编辑器 | Monaco Editor | — |
| 状态管理 | Zustand | 5 |
| 构建工具 | Vite | 8 |
| **LLM** | | |
| 默认模型 | 小米 MiMo v2.5 Pro | — |
| API 协议 | OpenAI 兼容 (json_schema strict) | — |

---

## 仓库结构

```
novel2script/
├── frontend/                      前端 SPA (React 19 + Vite)
│   ├── src/
│   │   ├── pages/                 路由页面 (5 个)
│   │   │   ├── LoginPage.tsx         登录/注册
│   │   │   ├── UploadPage.tsx        上传
│   │   │   ├── ProgressPage.tsx      转换进度
│   │   │   ├── EditorPage.tsx        编辑/预览
│   │   │   └── HistoryPage.tsx       历史记录
│   │   ├── components/            可复用组件 (8 个)
│   │   ├── services/              API 客户端
│   │   │   ├── orchestrator.ts       Pipeline API + WebSocket
│   │   │   ├── history.ts            历史 API
│   │   │   └── export.ts             YAML / Fountain 导出
│   │   ├── stores/                Zustand 状态管理
│   │   └── types/                 TypeScript 类型定义
│   ├── nginx.conf                 Docker Nginx 配置
│   └── package.json
│
├── pipeline-service/              后端 Pipeline 服务 (Python)
│   ├── pipeline/                  6 阶段处理流水线
│   │   ├── parser.py              [阶段1] 文件解析
│   │   ├── splitter.py            [阶段2] 章节拆分
│   │   ├── analyzer.py            [阶段3] 结构分析 + 别名补全
│   │   ├── segmenter.py           [阶段4] 场景分割 + 边界对齐 + 超长拆分
│   │   └── assembler.py           [阶段6] YAML 组装
│   ├── services/                  FastAPI 服务
│   │   ├── orchestrator.py        :8000 编排 + REST + WebSocket
│   │   ├── input_service.py       :8001 文件解析
│   │   ├── structure_service.py   :8002 结构分析
│   │   ├── beat_service.py        :8003 节拍提取 (LangGraph + 归属推断)
│   │   ├── react_agent.py         ReAct 执行器
│   │   ├── react_tools.py         6 个 ReAct 工具
│   │   └── redis_store.py         Redis 状态存储
│   ├── llm/                       LLM 客户端
│   │   ├── client.py              LiteLLM 封装 + Pydantic 结构化输出
│   │   ├── prompts.py             提示词模板
│   │   ├── pydantic_schemas.py    Pydantic 结构化模型
│   │   └── react_schema.py        ReAct 步骤模型
│   ├── grpc_client/               gRPC 认证客户端
│   ├── utils/                     工具函数
│   ├── tests/                     pytest 测试 (11 个文件)
│   ├── .env.example
│   └── requirements.txt
│
├── auth-service/                  认证服务 (Java 21 / Spring Boot 3)
│   └── src/main/java/com/novel/auth/
│       ├── interfaces/            接口层 (REST + gRPC)
│       ├── application/           应用层 (用例编排)
│       ├── domain/                领域层 (实体/值对象/领域服务/事件)
│       ├── infrastructure/        基础设施层 (MyBatis/gRPC/配置)
│       └── common/                公共层 (异常/返回包装)
│
├── history-service/               历史服务 (Java 21 / Spring Boot 3)
│   └── src/main/java/com/novel/history/
│       ├── interfaces/rest/       接口层 (REST 端点 + DTO)
│       ├── application/service/   应用层 (HistoryAppService)
│       ├── domain/                领域层 (ConversionHistory/Status)
│       ├── infrastructure/        基础设施层 (MyBatis-Plus 持久化)
│       └── common/                公共层 (异常/返回包装)
│
├── proto/                         gRPC Protobuf 定义
│   └── auth_service.proto         AuthService: VerifyToken/CheckQuota/RecordUsage
├── docs/                          设计文档
├── sample-novel.txt               示例小说 (完整)
├── test-chapters.txt              测试小说 (3 章短文本)
├── docker-compose.yml             Docker 编排
├── start-backend.bat              后端一键启动
├── start-frontend.bat             前端一键启动
└── README.md
```

---

## 快速开始

### 前置要求

- **Python** 3.13+
- **Node.js** 20+（推荐 22 LTS）
- **Redis** 5+
- **LLM API Key** — 默认使用小米 MiMo v2.5 Pro
- **Java 21** + **Maven**（Auth Service 和 History Service 需要，Pipeline 可独立运行）
- **MySQL**（Auth Service 和 History Service 需要）

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

# Pipeline 后端
cd ../pipeline-service
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
pip install -r requirements.txt

# Auth Service (可选)
cd ../auth-service
mvn install

# History Service (可选)
cd ../history-service
mvn install
```

### 3. 配置环境变量

```bash
cd pipeline-service
cp .env.example .env
```

编辑 `.env`：

```env
LITELLM_MODEL=openai/mimo-v2.5-pro
MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
MIMO_API_KEY=你的API密钥
```

前端环境变量（`frontend/.env`）：

```env
VITE_API_BASE=http://127.0.0.1:8000
```

### 4. 启动 Redis

```bash
# 直接安装
redis-server

# 或 Docker
docker run -d --name redis -p 6379:6379 redis:7
```

### 5. 启动服务

**Windows**：

```bash
# 后端 (4 个 FastAPI 服务)
start-backend.bat

# 前端 (Vite 开发服务器)
start-frontend.bat
```

**手动启动**：

```bash
# Pipeline 后端 — 4 个服务
cd pipeline-service
uvicorn services.input_service:app --host 127.0.0.1 --port 8001 &
uvicorn services.structure_service:app --host 127.0.0.1 --port 8002 &
uvicorn services.beat_service:app --host 127.0.0.1 --port 8003 &
uvicorn services.orchestrator:app --host 127.0.0.1 --port 8000 --reload

# Auth Service (可选)
cd ../auth-service
mvn spring-boot:run

# History Service (可选)
cd ../history-service
mvn spring-boot:run

# 前端
cd ../frontend
npm run dev
```

### 6. 使用

打开浏览器访问 **http://localhost:3000**

1. 注册/登录账户
2. 上传小说文件
3. 选择剧本类型（电视剧 / 电影 / 短视频 / 舞台剧）
4. 等待处理完成（实时进度展示）
5. 在编辑器中查看/修改 YAML 剧本

---

## 配置说明

### Pipeline 后端 (`pipeline-service/.env`)

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `LITELLM_MODEL` | 是 | — | LiteLLM 模型标识符 |
| `MIMO_BASE_URL` | 是 | — | MiMo API 地址 |
| `MIMO_API_KEY` | 是 | — | MiMo API 密钥 |
| `REDIS_URL` | 否 | `redis://localhost:6379/0` | Redis 连接地址 |
| `INPUT_SERVICE_URL` | 否 | `http://localhost:8001` | Input 服务地址 |
| `STRUCTURE_SERVICE_URL` | 否 | `http://localhost:8002` | Structure 服务地址 |
| `BEAT_SERVICE_URL` | 否 | `http://localhost:8003` | Beat 服务地址 |
| `AUTH_GRPC_HOST` | 否 | `localhost:9090` | Auth gRPC 地址 |
| `CORS_ORIGINS` | 否 | `*` | CORS 允许的源 |

### 前端 (`frontend/.env`)

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `VITE_API_BASE` | 是 | — | Orchestrator 地址。**不设置则前端自动使用 Mock 数据** |

---

## Pipeline 流水线详解

### 6 个处理阶段

```
[阶段1] 文件解析 (parser.py)
  输入: .txt / .md / .docx
  处理: 提取纯文本，自动检测编码
  输出: 全文字符串
       ↓
[阶段2] 章节拆分 (splitter.py)
  输入: 全文文本
  处理: 正则匹配 "第X章" / "Chapter N" 分割章节
  输出: 章节列表 [{order, title, text}]
       ↓
[阶段3] 结构分析 (analyzer.py)                  ← LLM + Pydantic
  输入: 全部章节文本
  处理: LLM 提取角色、地点、摘要
  后处理: 角色别名双向补全 (妻子↔丈夫, 前女友↔前男友)
  输出: {characters, locations, synopsis}
       ↓
[阶段4] 场景分割 (segmenter.py)                ← LLM + Pydantic
  输入: 每章文本
  处理: LLM 按地点/时间变化分割场景
  后处理:
    - 边界对齐: snap 到句末标点 (。！？\n)
    - 超长拆分: > 800 字在句号处自动拆分
    - 间隙填充: 相邻场景间未分配文本归入前一个场景
  输出: 场景列表 [{id, location, time, text_segment}]
       ↓
[阶段5] 节拍提取 (beat_service.py)             ← ReAct 智能体
  输入: 每个场景文本 + 角色列表
  处理: LangGraph 3 节点 (Extractor → Critic → Refiner)
  后处理: 对话归属推断 (详见下方)
  输出: 节拍列表 [{id, type, character, content}]
       ↓
[阶段6] YAML 组装 (assembler.py)
  输入: 全部阶段输出
  处理: 代码组装 → jsonschema 校验 → PyYAML 序列化
  输出: 完整剧本 YAML
```

### 速率限制策略

Beat Service 对 LLM 调用最密集（每个场景触发 3 个 ReAct 节点 × 最多 5 轮迭代）。为避免触发 MiMo API 的 100 RPM 限制：

- 场景间**顺序执行**（非并发），每个场景间 5 秒间隔
- 单场景内 Extractor → Critic → Refiner 顺序执行
- ReAct 失败时自动降级为单次 Pydantic 调用（保证可用性）

---

## ReAct 智能体架构

节拍提取阶段使用 **ReAct 范式**，由 LangGraph 编排 3 个智能体节点：

```
START → Extractor Agent → Critic Agent → (有问题?) → Refiner Agent → END
                                       └──(无问题)──────────────────────→ END
```

### ReAct 执行循环

每个节点内部遵循 `think → act → observe` 循环（最多 5 轮）：

```
Step 1: THINK   — LLM 分析当前状态，决定下一步
Step 2: ACT     — LLM 选择工具并传入参数
Step 3: OBSERVE — 系统执行工具，返回结果
         (重复，最多 5 轮)
Step N: FINAL   — LLM 输出 Pydantic 结构化答案
```

### 工具集

| 工具 | 所属节点 | 功能 |
|------|----------|------|
| `analyze_scene` | Extractor | 分析场景文本，返回角色/对话/动作概要 |
| `check_phone_speaker` | Extractor | 电话场景中判断来电方/接听方 |
| `find_missing_dialogue` | Extractor | 检查是否有遗漏的对话 |
| `verify_dialogue_speaker` | Critic | 验证对话的说话人是否正确 |
| `check_beat_type` | Critic | 验证 beat 的类型是否正确 |
| `validate_refined_beats` | Refiner | 验证修正后的 beats 完整性 |

工具参数采用 `**kwargs` 智能映射，容忍 LLM 的参数名猜测偏差。

### 结构化输出

所有 LLM 调用通过 Pydantic 模型 + API 级别 `json_schema` strict 模式约束：

```python
data = await llm_complete(
    prompt="...",
    pydantic_model=ExtractBeatsOutput,
)
# data 已通过 model_validate() 硬校验
```

共定义 12 个 Pydantic 模型覆盖所有 LLM 调用场景，9 个 ReAct 专用模型。

---

## 程序化后处理

LLM 输出不总是可靠，系统在关键阶段部署多层程序化后处理：

### 1. 角色别名双向补全（analyzer.py）

基于角色 description 中的互引关系自动补全缺失的反向别名：

```
周远.aliases = ["前男友"]           → 自动给林薇加 "前女友"
林薇.description = "周远的前女友"     → 自动给周远加反向别名
```

### 2. 场景边界对齐（segmenter.py）

LLM 经常把场景边界放在句子中间。后处理自动 snap 到最近的句末标点（`。！？\n`），搜索范围前后 80 字，选择距离更近的方向。

### 3. 超长场景拆分（segmenter.py）

超过 800 字的 segment 在句号处自动拆分为多个场景，重新编号。

### 4. 对话归属推断（beat_service.py）

采用 **Sieve 策略**分层推断说话人：

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

| Beat 类型 | 说明 | character |
|-----------|------|-----------|
| `action` | 角色动作 | 角色名或 null |
| `dialogue` | 对话 | 说话角色名 |
| `transition` | 场景转换/环境描写 | 通常为 null |
| `voiceover` | 内心独白/旁白 | 角色名 |
| `montage` | 蒙太奇序列 | null |

---

## API 接口文档

### Pipeline REST API（Orchestrator :8000）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/pipeline` | 上传文件，启动转换流水线 |
| `GET` | `/pipeline/list` | 列出所有转换任务 |
| `GET` | `/pipeline/{run_id}/status` | 查询任务状态 |
| `GET` | `/pipeline/{run_id}/events` | 获取任务事件列表 |
| `GET` | `/pipeline/{run_id}/result` | 获取转换结果 (YAML) |
| `GET` | `/api/history` | 获取历史记录列表（分页 + 筛选） |
| `GET` | `/api/history/{run_id}` | 获取单条历史记录 |
| `DELETE` | `/api/history/{run_id}` | 删除历史记录 |
| `GET` | `/health` | 健康检查 |

### WebSocket

| 路径 | 说明 |
|------|------|
| `ws://localhost:8000/ws/pipeline/{run_id}` | 实时推送任务进度（Redis Pub/Sub） |

### Auth REST API（Auth Service :8080）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/auth/register` | 注册（username, email, password） |
| `POST` | `/api/auth/login` | 登录，返回 token + 用户信息 |
| `POST` | `/api/auth/logout` | 登出 |

### gRPC 接口（Auth Service :9090）

Service: `novel.auth.AuthService`

| RPC | 请求 | 响应 |
|-----|------|------|
| `VerifyToken` | `{token}` | `{valid, user_id, username, plan}` |
| `CheckQuota` | `{user_id, action}` | `{allowed, remaining, reset_at}` |
| `RecordUsage` | `{user_id, action, chapters_processed, tokens_used}` | `{success}` |

### History REST API（History Service :8010）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/history` | 创建转换记录（runId, filename, scriptType, language） |
| `GET` | `/api/history` | 分页列表（支持 scriptType / status 筛选） |
| `GET` | `/api/history/{runId}` | 按 run ID 查询详情 |
| `PATCH` | `/api/history/{runId}` | 部分更新（状态/章节数/YAML 等） |
| `DELETE` | `/api/history/{runId}` | 删除记录 |

### 交互式文档

后端启动后访问 **http://localhost:8000/docs** 查看 Swagger UI。

---

## Docker 部署

```bash
docker-compose up -d
```

`docker-compose.yml` 包含以下服务：

| 容器 | 端口 | 说明 |
|------|------|------|
| `novel-redis` | 6379 | Redis 状态存储 |
| `novel-input` | 8001 | 文件解析服务 |
| `novel-structure` | 8002 | 结构分析服务 |
| `novel-beat` | 8003 | 节拍提取服务 |
| `novel-orchestrator` | 8000 | 任务编排（前端入口） |
| `novel-frontend` | 3000 | Nginx 静态文件 + 反向代理 |

> Auth Service 和 History Service 不在 docker-compose 中（依赖 MySQL 和 proto 编译，需单独部署）。

部署前在 `pipeline-service/` 下创建 `.env` 文件填入 `MIMO_API_KEY`，Docker Compose 会自动传入。

---

## 开发指南

### 项目约定

- **分支策略**：`master` 分支只接受通过 PR 合并的 `feat/*` 或 `fix/*` 分支
- **提交格式**：每个 commit 包含 ① 标题 ② 功能描述 ③ 实现思路 ④ 测试方式
- **结构化输出**：所有 LLM 调用使用 Pydantic schema + API 级别 `json_schema` strict 模式
- **密钥管理**：API Key 从 `.env` 加载，绝不硬编码

### 本地开发

```bash
# 前端 (热重载)
cd frontend && npm run dev

# 后端 (热重载)
cd pipeline-service && uvicorn services.orchestrator:app --reload --port 8000

# 测试
cd pipeline-service && pytest        # 11 个测试文件
cd frontend && npm test

# Auth Service
cd auth-service && mvn spring-boot:run
```

### 测试文件

```
pipeline-service/tests/
├── test_parser.py              文件解析测试
├── test_splitter.py            章节拆分测试
├── test_analyzer.py            结构分析测试
├── test_segmenter_extractor.py 场景分割测试
├── test_assembler.py           YAML 组装测试
├── test_llm_client.py          LLM 客户端测试
├── test_orchestrator.py        编排器测试
├── test_services.py            子服务测试
├── test_grpc_client.py         gRPC 客户端测试
├── test_health.py              健康检查测试
├── e2e_full.py                 端到端测试 (fakeredis)
└── e2e_real.py                 真实 LLM 端到端测试
```

---

## FAQ

### Q: 前端显示 Mock 数据？

`VITE_API_BASE` 未设置时前端自动使用 Mock 数据。确保 `frontend/.env` 存在且 Vite 从 `frontend/` 目录启动。

### Q: 某个场景的 beats 为空？

通常由 MiMo API 速率限制（100 RPM）导致。系统已采用顺序执行 + 5 秒间隔缓解，但章节过多时仍可能触发。重新运行即可。

### Q: 对话归属不准确？

系统已部署 6 层 Sieve 推断策略，但电话对话和缺乏 speech verb 标记的对话仍是难点。可在 YAML 编辑器中手动修正。

### Q: 如何切换 LLM 模型？

修改 `.env` 中的 `LITELLM_MODEL` 和对应的 API Key。支持所有 LiteLLM 兼容模型。更换模型后可能需要调整 prompt。

### Q: Auth Service 如何启动？

```bash
cd auth-service
# 确保 MySQL 运行，配置 application.yml 数据库连接
mvn spring-boot:run
```

默认监听 `:8080`（REST）和 `:9090`（gRPC）。

### Q: gRPC 认证是否已接入 Pipeline？

`grpc_client/auth_client.py` 已实现（VerifyToken / CheckQuota / RecordUsage），但 orchestrator 路由尚未加入认证中间件。目前 Pipeline API 无需认证即可访问。

### Q: History Service 如何启动？

```bash
cd history-service
# 确保 MySQL 运行，配置 application.yml 数据库连接
mvn spring-boot:run
```

默认监听 `:8010`。前端 `history.ts` 默认调用 Orchestrator 的 `/api/history`（从 Redis 读取），如需使用 History Service 的 MySQL 持久化，修改前端 API 指向 `:8010`。

---

## License

Internal project — 尚未开源授权。
