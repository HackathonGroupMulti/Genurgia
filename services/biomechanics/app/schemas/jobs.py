from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class JobCreateV1(BaseModel):
    job_type: Literal["anatomical-motion-replay-v1"]
    request: dict[str, Any]


class JobV1(BaseModel):
    id: UUID
    job_type: str
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    progress: float = Field(ge=0, le=1)
    request: dict[str, Any]
    result_artifact_reference: str | None
    logs: list[dict[str, Any]]
    attempts: int = Field(ge=0)
    cancel_requested: bool
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_detail: str | None


class JobListV1(BaseModel):
    jobs: list[JobV1]
