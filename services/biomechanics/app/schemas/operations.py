from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ProcessingOperation(BaseModel):
    id: UUID
    operation_type: Literal["pose_extraction"]
    status: Literal["running", "complete", "failed"]
    stage: str
    input_bytes: int = Field(ge=0)
    pose_sequence_id: UUID | None
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None = Field(default=None, ge=0)
    error_code: str | None
    error_detail: str | None


class ProcessingOperationList(BaseModel):
    operations: list[ProcessingOperation]
