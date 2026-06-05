"""
Pydantic models for API request/response validation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    session_id: str
    filename: str


class ConvertRequest(BaseModel):
    session_id: str
    title: str = ""
    author: str = ""
    script_type: str = Field(default="movie", pattern="^(movie|tv|short_video|stage)$")
    language: str = Field(default="zh", pattern="^(zh|en|bilingual)$")


class ConvertResponse(BaseModel):
    job_id: str
    status: str


class ResultResponse(BaseModel):
    job_id: str
    status: str
    yaml: str | None = None
    error: str | None = None


class ValidateRequest(BaseModel):
    yaml_text: str


class ValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = []
