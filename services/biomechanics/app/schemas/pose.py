from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

POSE_SCHEMA_VERSION = "1.0.0"
RECORDING_SCHEMA_VERSION = "1.1.0"

CameraView = Literal["front", "rear", "left_side", "right_side", "oblique", "unknown"]
VideoOrientation = Literal["portrait", "landscape", "unknown"]
LateralityContext = Literal["bilateral", "left", "right", "unknown"]


class CoordinateConvention(BaseModel):
    image: Literal["mediapipe-normalized-image-v1"] = "mediapipe-normalized-image-v1"
    image_axes: str = "origin top-left; +x right; +y down; x/y normalized by image size"
    image_depth: str = "MediaPipe model-relative z; smaller values are closer to camera"
    world: Literal["mediapipe-pose-world-v1"] = "mediapipe-pose-world-v1"
    world_units: Literal["meter"] = "meter"
    world_origin: str = "MediaPipe model-defined origin at the midpoint of the hips"


class Landmark(BaseModel):
    index: int = Field(ge=0)
    name: str = Field(min_length=1)
    x: float | None
    y: float | None
    z: float | None
    visibility: float | None = Field(default=None, ge=0, le=1)
    presence: float | None = Field(default=None, ge=0, le=1)


class PoseObservation(BaseModel):
    pose_index: int = Field(ge=0)
    image_landmarks: list[Landmark]
    world_landmarks: list[Landmark]


class PoseFrame(BaseModel):
    frame_index: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    poses: list[PoseObservation]


class Recording(BaseModel):
    schema_version: Literal["1.0.0", "1.1.0"] = RECORDING_SCHEMA_VERSION
    id: UUID
    original_filename: str
    content_type: str
    size_bytes: int = Field(gt=0)
    duration_ms: int = Field(gt=0)
    fps: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    storage_reference: str
    captured_at: datetime | None = None
    protocol: Literal["squat"] = "squat"
    camera_view: CameraView = "unknown"
    orientation: VideoOrientation = "unknown"
    laterality_context: LateralityContext = "bilateral"
    capture_notes: str | None = Field(default=None, max_length=1000)


class PoseSequence(BaseModel):
    schema_version: Literal["1.0.0"] = POSE_SCHEMA_VERSION
    id: UUID
    recording_id: UUID
    pose_model: str
    pose_model_version: str
    coordinate_convention: CoordinateConvention = Field(default_factory=CoordinateConvention)
    frame_count: int = Field(gt=0)
    detected_frame_count: int = Field(ge=0)
    frames: list[PoseFrame]


class PoseSequenceArtifact(BaseModel):
    recording: Recording
    pose_sequence: PoseSequence


class PoseSequenceSummary(BaseModel):
    schema_version: Literal["1.0.0"] = POSE_SCHEMA_VERSION
    id: UUID
    recording_id: UUID
    pose_model: str
    pose_model_version: str
    coordinate_convention: CoordinateConvention
    frame_count: int = Field(gt=0)
    detected_frame_count: int = Field(ge=0)
    raw_landmarks_reference: str
    annotated_video_reference: str


class ProcessingMetrics(BaseModel):
    operation_id: UUID
    upload_bytes: int = Field(gt=0)
    processing_duration_ms: int = Field(ge=0)
    processed_frames: int = Field(gt=0)
    average_frames_per_second: float | None = Field(default=None, gt=0)


class PoseAnalysisResponse(BaseModel):
    recording: Recording
    pose_sequence: PoseSequenceSummary
    processing: ProcessingMetrics
