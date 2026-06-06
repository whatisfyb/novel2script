# Agent Architecture Spec — Multi-Service Pipeline with Redis Event Bus

> **Status**: DRAFT v0.1
> **Date**: 2026-06-05
> **Branch**: (to be created) `feat/agent-architecture`
> **Replaces**: 6-stage monolithic pipeline in `pipeline-service/pipeline/`

---

## 1. Background & Motivation

### 1.1 Current State

The novel-to-script pipeline today is a single Python process running 6 stages sequentially with some parallel fan-out:

```
file → parse → split → analyze → segment → extract → assemble → YAML
                       └────────── Chapter 1..N parallel ──────────┘
                                       └──── Scene 1..M parallel ────┘
```

**Problems**:

1. **Single attribution error breaks the whole beat** — Stage 5 (extractor) makes confident-but-wrong attributions that 13 commits of post-processing heuristics can only partially fix.
2. **No self-correction** — single LLM call per stage; no chance for the model to review and fix its own output.
3. **No observability for the frontend** — progress is coarse ("segmenter 60%"), not per-beat / per-scene.
4. **No audit trail** — debugging "why did this beat get attributed to 周远 instead of 林薇?" requires reading LLM logs, not a structured event log.
5. **No reusability** — extractor and critic logic is tightly coupled in one function; can't swap, can't parallel-experiment.

### 1.2 Goals

1. **Self-correcting extraction** — Extractor → Critic → optional Refiner pipeline per scene.
2. **Per-scene audit trail** — every event (LLM call, fallback, correction) recorded for replay.
3. **Real-time progress** — frontend sees "scene 3/5: critic reviewing 12 beats" not just "beat extraction 60%".
4. **Independent services** — each stage is a separately deployable FastAPI app.
5. **Future-proof for scale** — message bus is Redis, not in-memory; can run services on different machines.

### 1.3 Non-Goals

- Real-time multi-user collaboration (single-user, async pipeline runs only).
- Distributed training / fine-tuning (out of scope for v1).
- Sub-second latency (each stage takes seconds to tens of seconds; p50 < 60s/pipeline is acceptable).

---

## 2. High-Level Architecture

### 2.1 Service Topology

```
                    ┌─────────────────┐
                    │   Frontend      │
                    │  (React/Vite)   │
                    └────────┬────────┘
                             │ HTTP + WebSocket
                             ▼
                    ┌─────────────────┐
                    │  Orchestrator   │  (LangGraph)
                    │   (FastAPI)     │
                    └────────┬────────┘
                             │ HTTP
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
   │   Input     │   │  Structure  │   │    Beat     │
   │  Service    │   │  Service    │   │  Service    │
   │             │   │             │   │ (LangGraph  │
   │ Parser +    │   │ Analyzer +  │   │  Extractor  │
   │ Splitter    │   │ Segmenter   │   │  + Critic   │
   │             │   │             │   │  + Refiner) │
   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
          │                 │                  │
          └─────────────────┼──────────────────┘
                            ▼
                    ┌─────────────────┐
                    │     Redis       │
                    │  (event bus +   │
                    │   state store)  │
                    └─────────────────┘
```

### 2.2 Service Responsibilities

| Service | Combines | Responsibility | LLM Calls |
|---|---|---|---|
| **Input Service** | Parser + Splitter | Read file → `List[Chapter]` | 0-1 (splitter fallback) |
| **Structure Service** | Analyzer + Segmenter | Chapters → `StructureResult` (chars, locations, scenes) | 2 (analyze + segment per chapter) |
| **Beat Service** | Extractor + Critic + Refiner | `Scene` → `List[Beat]` (with attribution) | 2-3 per scene (extract + critic + optional refine) |
| **Orchestrator** | — | Coordinate 3 services, write Redis state, expose status API | 0 |

**Why 3 services + 1 orchestrator (not 6)**: Combining closely related stages reduces HTTP round-trips and lets each service own a coherent LLM workflow. Each of the 3 services is still internally decomposed (LangGraph for Beat Service).

### 2.3 Why LangGraph

LangGraph orchestrates **stateful, conditional, agent-based** workflows with built-in:
- **StateGraph** — typed state that flows through nodes
- **Conditional edges** — `critic → refiner` only if corrections needed
- **Checkpointing** — persist state to Redis backend, resume from any step
- **Streaming** — node-by-node updates for frontend progress
- **LangGraph Studio** — visual debugging

LangGraph is used at **two levels**:
1. **Inside Beat Service** — 3 agents (extractor/critic/refiner) as graph nodes
2. **Inside Orchestrator** — 3 service calls as graph nodes (with conditional retry on failure)

---

## 3. Redis: Dual Role

Redis is the **only** shared infrastructure. It serves two purposes:

### 3.1 As Message Bus (event distribution)

**Data structure**: Redis Streams + Pub/Sub

| Key | Type | Purpose | TTL |
|---|---|---|---|
| `pipeline:events:{run_id}` | Stream | Append-only audit trail of all events | 7 days |
| `pipeline:notify:{run_id}` | Pub/Sub channel | Real-time push to WebSocket subscribers | n/a (channel) |

**Why Streams (not Pub/Sub) for events**: Streams are persistent and replayable; Pub/Sub is fire-and-forget. We need both:
- Streams → audit log, debugging, replay
- Pub/Sub → live push to connected frontends

### 3.2 As State Store (run status)

| Key | Type | Purpose |
|---|---|---|
| `pipeline:status:{run_id}` | Hash | Current stage, progress %, ETA, last update |
| `pipeline:result:{run_id}` | String | Final YAML (after success) |
| `pipeline:error:{run_id}` | Hash | Error details (after failure) |
| `pipeline:runs` | Sorted Set | All run IDs sorted by start time (for listing) |

### 3.3 Why Redis (not RabbitMQ/Kafka/PostgreSQL)

- **Already in the stack** — README mentions "Redis (optional cache)"
- **Multi-role** — one tool for message bus + state + cache
- **LangGraph native support** — `langgraph-checkpoint-redis` exists
- **Light ops** — single binary, no ZooKeeper/etcd dependency
- **Horizontal scale** — Redis Cluster when needed
- **Trade-off** — not as durable as Kafka for high-throughput; acceptable for our QPS

### 3.4 Redis Schema (final)

```
# Event stream entry
pipeline:events:{run_id}    XADD   { "ts": 1234567890, "type": "scene.submitted",
                                       "actor": "input_service", "payload": {...} }

# Status hash
pipeline:status:{run_id}    HSET   stage=beat progress=60 current_scene=ch3_s5
                                eta_seconds=42 updated_at=1234567890

# Result string
pipeline:result:{run_id}    SET    "<yaml string>" EX 86400

# Run listing
pipeline:runs               ZADD   {run_id} {start_timestamp}
```

---

## 4. Event Model

### 4.1 Event Schema (canonical)

Every event published to Redis has this shape:

```json
{
  "event_id": "uuid-v4",
  "run_id": "novel_run_2026_06_05_abc123",
  "ts": 1717584000.123,
  "type": "scene.submitted" | "beats.extracted" | "beats.critiqued" | ...,
  "source": "input_service" | "structure_service" | "beat_service" | "orchestrator",
  "correlation_id": "ch3_s5",
  "payload": { ... type-specific ... },
  "metadata": { "duration_ms": 1234, "retry": 0 }
}
```

### 4.2 Event Types (v1)

| Event Type | Source | When | Payload |
|---|---|---|---|
| `pipeline.started` | orchestrator | Run submitted | `{input: {filename, size}}` |
| `pipeline.stage_changed` | orchestrator | Stage transition | `{from: "input", to: "structure"}` |
| `chapter.detected` | input_service | Chapter parsed | `{chapter_id, title, char_count}` |
| `chapter.split_failed` | input_service | Splitter LLM fallback | `{reason}` |
| `structure.analyzed` | structure_service | Per-chapter analysis | `{chapter_id, n_characters, n_locations}` |
| `scene.segmented` | structure_service | Per-chapter segmentation | `{chapter_id, n_scenes, scenes: [...]}` |
| `scene.submitted` | orchestrator → beat | Scene ready for beats | `{scene_id, scene_text, characters, chapter_text}` |
| `beats.extracted` | beat_service | Extractor finished | `{scene_id, n_beats, beats: [...]}` |
| `beats.critiqued` | beat_service | Critic applied corrections | `{scene_id, n_corrections, corrections: [...]}` |
| `beats.finalized` | beat_service | No more work needed | `{scene_id, beats: [...]}` |
| `scene.failed` | beat_service | Unrecoverable error | `{scene_id, error, stage}` |
| `pipeline.completed` | orchestrator | All done | `{yaml_length, total_beats}` |
| `pipeline.failed` | orchestrator | Unrecoverable | `{error, stage}` |

### 4.3 Frontend Event Stream

Frontend subscribes to:
- `GET /pipeline/{run_id}/status` (polling every 2s, or initial state)
- `WS /ws/pipeline/{run_id}` (real-time event push via Redis Pub/Sub)

For the WS endpoint, the backend process subscribes to `pipeline:notify:{run_id}` and forwards each event to the WebSocket.

---

## 5. Service Specifications

### 5.1 Input Service

**Endpoint**: `POST /parse` (multipart upload) and `POST /split` (chapters text)

**Input Service Graph (LangGraph or simple function)**:

```
upload_file → detect_format → parse_text → split_chapters → output List[Chapter]
                                                    ↓ (on failure)
                                              LLM fallback splitter
```

**State**:
```python
class InputState(TypedDict):
    raw_file: bytes
    filename: str
    raw_text: str | None
    chapters: list[Chapter]
    error: str | None
```

**Output**: `List[Chapter]` (id, title, order, text)

### 5.2 Structure Service

**Endpoint**: `POST /analyze` and `POST /segment`

**Two-step flow** (per chapter, parallel across chapters):

```
chapters → analyze_structure → segments_per_chapter
              ↓ (parallel)
         segment_scenes × N chapters
              ↓
         merge: StructureResult { characters, locations, scenes_by_chapter }
```

**State**:
```python
class StructureState(TypedDict):
    chapters: list[Chapter]
    characters: list[Character]
    locations: list[Location]
    synopsis: str
    scenes_by_chapter: dict[int, list[Scene]]
    error: str | None
```

**Output**: `StructureResult` (Character + Location + Scene lists)

### 5.3 Beat Service (the most complex)

**Endpoint**: `POST /extract` (one scene per call) or `POST /extract_batch` (multiple scenes)

**LangGraph workflow**:

```
                     ┌──────────────┐
                     │  extractor   │
                     │  (LLM call)  │
                     └──────┬───────┘
                            │ beats
                            ▼
                     ┌──────────────┐
                     │   critic     │ ◄── applies low-confidence heuristic
                     │  (LLM call)  │     corrections if any above threshold
                     └──────┬───────┘
                            │ corrections
                            ▼
                  ┌──────────────────┐
                  │  has_corrections? │
                  └──────┬────────┬───┘
                    True │        │ False
                         ▼        ▼
                ┌──────────────┐  │
                │   refiner    │  │
                │  (LLM call)  │  │
                └──────┬───────┘  │
                       │          │
                       ▼          ▼
                    ┌─────────────────┐
                    │  beats.finalized │
                    └─────────────────┘
```

**State**:
```python
class BeatState(TypedDict):
    run_id: str
    scene_id: str          # e.g. "ch3_s5"
    scene_text: str
    chapter_text: str | None
    characters: list[Character]
    # Populated by nodes:
    beats: list[Beat]
    corrections: list[Correction]
    has_corrections: bool
    error: str | None
```

**Each node**:
1. **extractor** — call LLM with `EXTRACT_BEATS_PROMPT`, parse to `Beat[]`, run all heuristic fallbacks (normalize, name-address, action attribution)
2. **critic** — call LLM with `CRITIC_PROMPT` (HAR-style review), apply corrections above `confidence_threshold=0.5`
3. **refiner** (conditional) — call LLM with critic's feedback + original beats, output refined beats
4. Final node writes `beats.finalized` event with final state

**Why Refiner is conditional**: If critic finds no issues, no point calling LLM again. Saves cost and latency.

### 5.4 Orchestrator

**Endpoints**:
- `POST /pipeline` — submit a new run (returns run_id)
- `GET /pipeline/{run_id}/status` — current status from Redis
- `GET /pipeline/{run_id}/events` — event list from Redis Stream
- `WS /ws/pipeline/{run_id}` — real-time event push
- `GET /pipeline/{run_id}/result` — final YAML
- `GET /pipeline/list` — list of recent runs

**LangGraph orchestrator workflow**:

```
                   ┌────────────┐
                   │   start    │
                   └─────┬──────┘
                         ▼
                  ┌─────────────┐
                  │ input_node  │  POST input_service/parse+split
                  └─────┬───────┘
                        ▼
              ┌──────────────────┐
              │  has_chapters?   │
              └────┬─────────┬───┘
                Yes│         │No
                   ▼         ▼
        ┌──────────────┐   ┌────────┐
        │structure_node│   │ failed │
        │ (HTTP calls) │   └────────┘
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │  beat_node   │  (parallel for each scene; HTTP to beat_service)
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │ assemble_node│  (in-process YAML assembly)
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │   finalize   │
        └──────────────┘
```

**State checkpointing**: Use `langgraph-checkpoint-redis` to persist state at each node. Supports:
- Resume from any step on crash
- Time-travel debugging
- Inspecting intermediate state

---

## 6. Data Flow Example

Let's trace one run end-to-end.

### 6.1 User submits novel

```
POST /pipeline  (file: novel.txt)
  ↓
Orchestrator creates run_id = "r_2026_06_05_abc"
  ↓
Writes Redis:
  pipeline:status:r_... = {stage: "starting", progress: 0}
  pipeline:events:r_... XADD {type: "pipeline.started", ...}
  pipeline:notify:r_... PUBLISH ...
  ↓
Returns run_id to client
```

### 6.2 Input stage

```
input_node (LangGraph)
  → HTTP POST input_service/parse  (file upload)
  → HTTP POST input_service/split  (raw_text → chapters)
  → 写 pipeline:events:r_... XADD {type: "chapter.detected", ...}
  → 写 pipeline:status:r_... = {stage: "structure", progress: 20}
```

### 6.3 Structure stage

```
structure_node
  → HTTP POST structure_service/analyze  (chapters → characters, locations, synopsis)
  → 并行: HTTP POST structure_service/segment × N chapters
  → 写 events: "structure.analyzed" × N
  → 写 events: "scene.segmented" × N
  → 写 status: {stage: "beat", progress: 50}
```

### 6.4 Beat stage (the most eventful)

```
beat_node
  for each scene (parallel):
    HTTP POST beat_service/extract {scene_id, scene_text, characters}
      → beat_service LangGraph runs:
        → extractor: LLM call, heuristic fallback
          → 写 events: "beats.extracted"
        → critic: LLM call
          → 写 events: "beats.critiqued" (with N corrections)
        → if corrections: refiner: LLM call
          → 写 events: "beats.refined"
        → 写 events: "beats.finalized"
    → return final beats
  → 收集 all beats_by_scene
  → 写 status: {stage: "assemble", progress: 90}
```

### 6.5 Assembly + finalize

```
assemble_node
  → 调用 pipeline.assembler.assemble_yaml (in-process)
  → 写 pipeline:result:r_... = yaml_str
  → 写 events: "pipeline.completed"
  → 写 status: {stage: "done", progress: 100}
```

### 6.6 Frontend experience

Throughout, the frontend:
- Polls `GET /pipeline/{run_id}/status` every 2s (cheap because Redis)
- Receives events via WebSocket → updates progress bar with per-stage detail
- On `pipeline.completed` → fetches YAML, displays in editor

---

## 7. Error Handling

### 7.1 Per-Stage Failure

| Service | Failure Mode | Recovery |
|---|---|---|
| Input | File parse fails | Return 400 with error, no retry |
| Input | Splitter LLM fails | Retry 2x, then regex-only fallback |
| Structure | Analyze LLM fails | Retry 2x, then return empty characters (degraded) |
| Structure | Segment LLM fails | Retry 2x, then return 1 scene = whole chapter |
| Beat | Extractor LLM fails | Retry 2x, then `scene.failed` event |
| Beat | Critic LLM fails | Log warning, use extractor's output (no refinement) |
| Beat | Refiner LLM fails | Log warning, use critiqued output |
| Orchestrator | HTTP to service fails | Retry 3x with backoff, then `pipeline.failed` |

### 7.2 Run-Level Failure

Any unrecoverable error publishes `pipeline.failed` event, writes `pipeline:error:{run_id}` to Redis, sets status to `{stage: "failed", error: "..."}`. Frontend shows error state with retry button.

### 7.3 LangGraph Checkpointing

All LangGraph state is checkpointed to Redis after each node. On orchestrator crash, the run can be resumed from the last successful node. Frontend gets notified of the resume via a `pipeline.resumed` event.

---

## 8. Migration Plan

### 8.1 Phasing

**Phase 1 (Week 1)**: Infrastructure
- Add `redis>=5.0` and `langgraph>=0.1` to `pipeline-service/pyproject.toml`
- Add Redis service to `docker-compose.yml`
- Implement `services/redis_store.py` (status, events, notify, result abstractions)
- Add `tests/test_redis_store.py` with in-memory fakeredis fixture

**Phase 2 (Week 2)**: Beat Service with LangGraph
- Move `pipeline/extractor.py` logic into `services/beat_service.py`
- Implement `CriticAgent` (uses `CRITIC_PROMPT` + `CRITIC_SCHEMA`)
- Implement `RefinerAgent` (uses refiner prompt)
- Wire into LangGraph StateGraph
- Add `tests/test_beat_service.py`

**Phase 3 (Week 3)**: Orchestrator + HTTP wiring
- Implement `services/orchestrator.py` (LangGraph + HTTP client to 3 services)
- Implement `services/input_service.py` and `services/structure_service.py`
- Wire all into docker-compose
- Add `tests/test_orchestrator.py` (e2e)

**Phase 4 (Week 4)**: Frontend integration
- New `PipelineStatus` component
- WebSocket client subscribes to `/ws/pipeline/{run_id}`
- Per-stage progress bar
- Event log viewer (for debugging)

### 8.2 Backwards Compatibility

- Keep `pipeline/run_pipeline()` as a thin wrapper that runs in-process (no HTTP, no Redis). This is what tests use.
- Production deployment uses `services/orchestrator.py` with full multi-service + Redis.
- A/B test: route 10% of production traffic through new architecture, compare output quality.

### 8.3 Feature Flag

Use env var `USE_AGENT_ARCHITECTURE=1` to switch between:
- Old: in-process pipeline (no Redis, no LangGraph)
- New: multi-service + Redis + LangGraph

Default to old until Phase 4 ships, then switch default.

---

## 9. Open Questions (need user input)

1. **Redis deployment** — self-hosted (Docker) or managed (Aliyun Redis / AWS ElastiCache)? We don't currently have a Redis instance.
2. **Auth integration** — does Orchestrator need to call Spring Boot Auth service for each request? Or just trust the gateway?
3. **Frontend WebSocket transport** — raw WS or Server-Sent Events (SSE)? WS is bidirectional but adds complexity; SSE is one-way and simpler.
4. **LLM call cost monitoring** — should we track per-call token usage in Redis and surface to the user? (Especially important for the new critic + refiner LLM calls.)
5. **Multi-tenancy** — single Redis namespace or per-tenant prefix?

---

## 10. References

- [LangGraph docs](https://langchain-ai.github.io/langgraph/)
- [langgraph-checkpoint-redis](https://pypi.org/project/langgraph-checkpoint-redis/)
- [Redis Streams docs](https://redis.io/docs/latest/develop/data-types/streams/)
- Existing pipeline: `pipeline-service/pipeline/`
- 13 commits of post-processing fixes in branch `fix/pipeline-output-quality` (reverted)
