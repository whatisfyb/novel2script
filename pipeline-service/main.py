"""
Novel-to-Script Pipeline Service — FastAPI entry point.

Handles the 6-stage novel-to-screenplay conversion pipeline:
  1. File parsing (txt/md/docx → raw text)
  2. Chapter splitting (regex + LLM fallback)
  3. Structure analysis (LLM: synopsis, characters, locations)
  4. Scene segmentation (LLM: per-chapter scenes)
  5. Beat extraction (LLM: per-scene dialogue/action beats)
  6. YAML assembly (code: structured output → YAML)
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from api.websocket import router as ws_router

# Load .env file (must happen before any module that reads env vars)
load_dotenv(Path(__file__).parent / ".env")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup/shutdown hooks."""
    yield
    # Close gRPC channel on shutdown
    try:
        from grpc_client.auth_client import auth_client
        auth_client.close()
    except Exception:
        pass


app = FastAPI(
    title="Novel-to-Script Pipeline Service",
    description="AI-powered novel-to-screenplay conversion engine",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — read allowed origins from environment
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(api_router, prefix="/api")
app.include_router(ws_router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker / load balancer probes."""
    return {"status": "ok", "service": "pipeline-service"}
