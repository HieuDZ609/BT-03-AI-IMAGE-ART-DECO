"""Shared pydantic schemas for job messages and events (packages/shared/schemas.py)."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


JobSource = Literal["SEARCH", "AUTOPILOT"]
JobStatus = Literal["QUEUED", "CLAIMED", "RUNNING", "DONE", "FAILED", "DEAD"]
EventStatus = Literal["DONE", "FAILED"]


class JobMessage(BaseModel):
    job_id: UUID
    query: str
    slug: str
    source: JobSource
    style_id: str = "deco-v1"
    requested_at: datetime


class JobEvent(BaseModel):
    job_id: UUID
    status: EventStatus
    image_id: Optional[UUID] = None
    image_name: Optional[str] = None
    ai_code: Optional[str] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None


class ImageMeta(BaseModel):
    image_id: UUID
    image_name: str
    slug: str
    prompt: Optional[str] = None
    style_id: str = "deco-v1"
    worker_id: Optional[int] = None
    ai_code: Optional[str] = None
    storage_key: str
    sha256: str
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime


class SearchResponse(BaseModel):
    hit: bool
    images: list[ImageMeta] = Field(default_factory=list)
    job_id: Optional[UUID] = None
    status: Optional[str] = None  # QUEUED | RUNNING | DONE | ...
"