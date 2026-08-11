from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

SessionStatus = Literal["pose_extracted", "knee_flexion_complete", "complete"]


class RecordingMetadata(BaseModel):
    schema_version: str
    id: UUID
    original_filename: str
    content_type: str
    storage_reference: str
    size_bytes: int = Field(gt=0)
    duration_ms: int = Field(gt=0)
    fps: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class PoseSequenceMetadata(BaseModel):
    schema_version: str
    id: UUID
    recording_id: UUID
    pose_model: str
    pose_model_version: str
    raw_landmarks_reference: str
    annotated_video_reference: str
    frame_count: int = Field(gt=0)
    detected_frame_count: int = Field(ge=0)


class AnalysisMetadata(BaseModel):
    id: int = Field(gt=0)
    analysis_type: Literal["knee_flexion", "squat_repetitions"]
    analysis_version: str
    artifact_reference: str
    created_at: datetime


class SessionMetric(BaseModel):
    name: Literal[
        "repetition_count",
        "mean_left_rom_degrees",
        "mean_right_rom_degrees",
        "mean_rom_degrees",
        "mean_duration_ms",
        "mean_confidence",
    ]
    value: float
    unit: Literal["count", "degree", "millisecond", "ratio"]
    source_analysis_version: str


class SessionSummary(BaseModel):
    id: UUID
    exercise_type: Literal["squat"] = "squat"
    recorded_at: datetime
    created_at: datetime
    status: SessionStatus
    recording: RecordingMetadata
    pose_sequence: PoseSequenceMetadata
    analyses: list[AnalysisMetadata]
    metrics: list[SessionMetric]


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]


class SessionComparisonEntry(BaseModel):
    session_id: UUID
    recorded_at: datetime
    repetition_count: int = Field(ge=0)
    mean_left_rom_degrees: float | None
    mean_right_rom_degrees: float | None
    mean_rom_degrees: float | None
    mean_duration_ms: float | None
    mean_confidence: float | None = Field(default=None, ge=0, le=1)
    mean_rom_change_from_previous_degrees: float | None


class SessionComparisonResponse(BaseModel):
    exercise_type: Literal["squat"] = "squat"
    sessions: list[SessionComparisonEntry]
