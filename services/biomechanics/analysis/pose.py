"""Pose-provider boundary and framework-independent raw observation types."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LandmarkObservation:
    """One provider landmark without interpolation or derived values."""

    index: int
    name: str
    x: float | None
    y: float | None
    z: float | None
    visibility: float | None
    presence: float | None


@dataclass(frozen=True, slots=True)
class PoseObservation:
    pose_index: int
    image_landmarks: tuple[LandmarkObservation, ...]
    world_landmarks: tuple[LandmarkObservation, ...]


@dataclass(frozen=True, slots=True)
class PoseFrameObservation:
    frame_index: int
    timestamp_ms: int
    poses: tuple[PoseObservation, ...]


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    duration_ms: int
    fps: float
    width: int
    height: int
    decoded_frame_count: int


@dataclass(frozen=True, slots=True)
class PoseExtraction:
    video: VideoMetadata
    frames: tuple[PoseFrameObservation, ...]


class PoseProvider(Protocol):
    """Replaceable boundary for pose inference and visual verification output."""

    @property
    def model_name(self) -> str: ...

    @property
    def model_version(self) -> str: ...

    def extract(self, video_path: Path, annotated_video_path: Path) -> PoseExtraction: ...


class PoseExtractionError(RuntimeError):
    """Raised when a recording cannot be decoded or processed."""
