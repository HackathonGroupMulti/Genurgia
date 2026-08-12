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
    captured_at: datetime | None = None
    protocol: Literal["squat"] = "squat"
    camera_view: Literal["front", "rear", "left_side", "right_side", "oblique", "unknown"]
    orientation: Literal["portrait", "landscape", "unknown"]
    laterality_context: Literal["bilateral", "left", "right", "unknown"]
    capture_notes: str | None


class PoseSequenceMetadata(BaseModel):
    schema_version: str
    id: UUID
    recording_id: UUID
    pose_model: str
    pose_model_version: str
    coordinate_convention: Literal["mediapipe-pose-world-v1"] = "mediapipe-pose-world-v1"
    raw_landmarks_reference: str
    annotated_video_reference: str
    frame_count: int = Field(gt=0)
    detected_frame_count: int = Field(ge=0)


class AnalysisMetadata(BaseModel):
    id: int = Field(gt=0)
    analysis_type: Literal["knee_flexion", "squat_repetitions", "capture_quality"]
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
        "mean_signed_rom_difference_degrees",
        "mean_absolute_rom_difference_degrees",
        "mean_signed_max_flexion_difference_degrees",
        "mean_absolute_max_flexion_difference_degrees",
        "pose_detection_coverage",
        "bilateral_valid_knee_coverage",
        "maximum_unavailable_bilateral_interval_ms",
        "required_landmark_framing_coverage",
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
    capture_quality_status: Literal["pass", "warning", "fail"] | None = None
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


class ComparisonMetric(BaseModel):
    name: str
    baseline_value: float
    current_value: float
    change: float
    unit: Literal["count", "degree", "millisecond", "ratio"]


class SelectedSessionComparison(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    baseline_session_id: UUID
    current_session_id: UUID
    compatible: bool
    compatibility_basis: Literal["local-single-subject-v1"] = "local-single-subject-v1"
    incompatibilities: list[str]
    analysis_version: str | None
    metrics: list[ComparisonMetric]


class ReanalysisRequest(BaseModel):
    analyses: list[
        Literal["knee_flexion", "squat_repetitions", "capture_quality"]
    ] = Field(
        default_factory=lambda: [
            "knee_flexion",
            "squat_repetitions",
            "capture_quality",
        ]
    )


class ReanalysisResponse(BaseModel):
    session: SessionSummary
    requested_analyses: list[str]
    behavior: Literal["reuse-current-or-derive-missing"] = "reuse-current-or-derive-missing"


class ExportArtifact(BaseModel):
    role: str
    artifact_reference: str
    analysis_type: str | None
    analysis_version: str | None
    exists: bool
    size_bytes: int | None
    sha256: str | None
    integrity: Literal["verified", "missing"]


class SessionExportManifest(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    generated_at: datetime
    session: SessionSummary
    artifacts: list[ExportArtifact]
