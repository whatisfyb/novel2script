# Novel-to-Script

AI-powered novel-to-screenplay converter. Upload a novel (txt / md / docx) and the system extracts characters, locations, scenes, and dialogue beats to produce a structured YAML screenplay.

## Features

- **Multi-format input** — `.txt` / `.md` / `.docx` novels
- **6-stage pipeline** — file parse → chapter split → structure analysis → scene segmentation → beat extraction → YAML assembly
- **Structured output** — script with characters, locations, acts, scenes, and beats (action / dialogue / voiceover / transition)
- **Real-time progress** — WebSocket streaming with 5-stage timeline and live LLM "thinking" tokens
- **In-browser editor** — Monaco-based YAML editor with side-by-side screenplay preview
- **Multiple script types** — TV / movie / short video / stage play

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vite + React 19 + TypeScript + Ant Design 6 + Tailwind CSS 4 + Monaco Editor |
| Pipeline backend | Python 3.13 + FastAPI + LiteLLM (MiMo v2.5 Pro) + PyYAML |
| Auth backend | Java 21 + Spring Boot 3 + Sa-Token + MyBatis-Plus + gRPC (Java/Spring stack) |
| Inter-service | gRPC (protobuf-defined AuthService) |
| Database | PostgreSQL (auth) + Redis (optional cache) |

## Repository Layout

```
novel2script/
├── frontend/                 Vite + React SPA
│   ├── src/
│   │   ├── components/       Reusable UI components
│   │   ├── pages/            Route-level pages
│   │   ├── services/         API client + mocks + exporters
│   │   ├── stores/           Zustand state stores
│   │   ├── types/            TypeScript domain types
│   │   └── App.tsx
│   └── package.json
├── pipeline-service/         Python FastAPI backend
│   ├── pipeline/             6-stage conversion pipeline
│   │   ├── parser.py
│   │   ├── splitter.py
│   │   ├── analyzer.py
│   │   ├── segmenter.py
│   │   ├── extractor.py
│   │   ├── assembler.py
│   │   ├── orchestrator.py
│   │   └── llm_client.py
│   ├── api/                  REST + WebSocket layer
│   ├── grpc_client/          gRPC client to auth-service
│   ├── tests/                pytest suite
│   └── main.py
├── auth-service/             Java Spring Boot (Sa-Token + DDD)
│   ├── src/main/java/        DDD 4-layer architecture
│   │   ├── interfaces/       REST controllers, gRPC server
│   │   ├── application/      Application services
│   │   ├── domain/           Entities, value objects, services
│   │   └── infrastructure/   Mappers, repository impls, config
│   ├── src/main/resources/
│   │   ├── db/migration/     Flyway scripts
│   │   └── application.yml
│   └── pom.xml
├── proto/                    gRPC protobuf definitions
├── docs/                     Design specs, schema, plans
├── .gitignore
├── start-backend.bat         Quick start: FastAPI
├── start-frontend.bat        Quick start: Vite dev server
└── README.md
```

## Quick Start

### 1. Install dependencies

```bash
# Frontend
cd frontend && npm install

# Pipeline backend (Python 3.13+ recommended)
cd ../pipeline-service
pip install -r requirements.txt

# Auth backend (Java 21)
cd ../auth-service
mvn install
```

### 2. Configure secrets

```bash
cd pipeline-service
cp .env.example .env
# Edit .env and set MIMO_API_KEY=your-key
```

### 3. Start the services

```bash
# Backend (FastAPI on http://127.0.0.1:8000)
start-backend.bat

# Frontend (Vite on http://localhost:3000)
start-frontend.bat
```

### 4. Open the app

Navigate to http://localhost:3000 in your browser. Register an account, upload a novel chapter file, and the pipeline will produce a structured YAML screenplay.

## Configuration

### Frontend `.env` (in `frontend/`)

```env
VITE_API_BASE=http://127.0.0.1:8000
```

### Backend `.env` (in `pipeline-service/`)

```env
LITELLM_MODEL=openai/mimo-v2.5-pro
MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
MIMO_API_KEY=your-key-here
GRPC_AUTH_HOST=localhost
GRPC_AUTH_PORT=9090
CORS_ORIGINS=*
```

## Pipeline Stages

```
[1] parser        Extract text from .txt / .md / .docx
       ↓
[2] splitter      Split into chapters (regex: 第X章 / Chapter N)
       ↓
[3] analyzer      LLM: extract characters, locations, synopsis
       ↓
[4] segmenter     LLM: per chapter, split into scenes
       ↓
[5] extractor     LLM: per scene, extract dialogue/action/beats
       ↓
[6] assembler     Code: validate + assemble final YAML
```

Each stage emits progress events via WebSocket. Stages 3 and 5 additionally stream LLM "thinking" tokens for live feedback.

## YAML Schema

See `docs/yaml-schema.md` for the full screenplay schema definition, field-by-field rationale, and examples.

## Development

- Frontend: `npm run dev` (port 3000)
- Backend: `python -m uvicorn main:app --reload` (port 8000)
- Tests: `pytest tests/` in `pipeline-service/`, `mvn test` in `auth-service/`

## License

Internal project — not yet licensed for public distribution.
