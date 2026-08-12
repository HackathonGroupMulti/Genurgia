from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from analysis.pose import PoseProvider
from app.persistence import SQLiteSessionRepository
from app.schemas.pose import (
    Landmark,
    PoseAnalysisResponse,
    PoseFrame,
    PoseObservation,
    PoseSequence,
    PoseSequenceArtifact,
    PoseSequenceSummary,
    Recording,
)
from app.storage import LocalArtifactStore

SUPPORTED_VIDEO_TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
}


class InvalidVideoUpload(ValueError):
    pass


class PoseAnalysisService:
    def __init__(
        self,
        artifact_store: LocalArtifactStore,
        pose_provider: PoseProvider,
        max_upload_bytes: int,
        session_repository: SQLiteSessionRepository | None = None,
    ) -> None:
        self._artifacts = artifact_store
        self._pose_provider = pose_provider
        self._max_upload_bytes = max_upload_bytes
        self._sessions = session_repository

    @property
    def max_upload_bytes(self) -> int:
        return self._max_upload_bytes

    def analyze(
        self,
        filename: str | None,
        content_type: str | None,
        content: bytes,
        *,
        captured_at: datetime | None = None,
        camera_view: str = "unknown",
        orientation: str = "unknown",
        laterality_context: str = "bilateral",
        capture_notes: str | None = None,
    ) -> PoseAnalysisResponse:
        extension, normalized_content_type = self._validate_upload(filename, content_type, content)
        if captured_at is not None and captured_at.tzinfo is None:
            raise InvalidVideoUpload("Capture time must include a UTC offset.")
        recording_id = uuid4()
        pose_sequence_id = uuid4()
        self._artifacts.create_bundle(pose_sequence_id)
        try:
            recording_filename = f"recording{extension}"
            recording_path = self._artifacts.write_bytes(
                pose_sequence_id,
                recording_filename,
                content,
            )
            annotated_filename = "annotated.mp4"
            annotated_path = self._artifacts.path_for(pose_sequence_id, annotated_filename)
            extraction = self._pose_provider.extract(recording_path, annotated_path)

            recording = Recording(
                id=recording_id,
                original_filename=filename or recording_filename,
                content_type=normalized_content_type,
                size_bytes=len(content),
                duration_ms=extraction.video.duration_ms,
                fps=extraction.video.fps,
                width=extraction.video.width,
                height=extraction.video.height,
                storage_reference=self._artifacts.reference(pose_sequence_id, recording_filename),
                captured_at=captured_at,
                protocol="squat",
                camera_view=camera_view,
                orientation=orientation,
                laterality_context=laterality_context,
                capture_notes=capture_notes,
            )
            frames = [
                PoseFrame(
                    frame_index=frame.frame_index,
                    timestamp_ms=frame.timestamp_ms,
                    poses=[
                        PoseObservation(
                            pose_index=pose.pose_index,
                            image_landmarks=[
                                Landmark.model_validate(item, from_attributes=True)
                                for item in pose.image_landmarks
                            ],
                            world_landmarks=[
                                Landmark.model_validate(item, from_attributes=True)
                                for item in pose.world_landmarks
                            ],
                        )
                        for pose in frame.poses
                    ],
                )
                for frame in extraction.frames
            ]
            pose_sequence = PoseSequence(
                id=pose_sequence_id,
                recording_id=recording_id,
                pose_model=self._pose_provider.model_name,
                pose_model_version=self._pose_provider.model_version,
                frame_count=len(frames),
                detected_frame_count=sum(bool(frame.poses) for frame in frames),
                frames=frames,
            )
            artifact = PoseSequenceArtifact(recording=recording, pose_sequence=pose_sequence)
            raw_filename = "pose_sequence.json"
            self._artifacts.write_json(
                pose_sequence_id,
                raw_filename,
                artifact.model_dump(mode="json"),
            )

            summary = PoseSequenceSummary(
                **pose_sequence.model_dump(exclude={"frames"}),
                raw_landmarks_reference=self._artifacts.reference(pose_sequence_id, raw_filename),
                annotated_video_reference=self._artifacts.reference(
                    pose_sequence_id,
                    annotated_filename,
                ),
            )
            if self._sessions is not None:
                self._sessions.record_pose_extraction(recording, summary)
            return PoseAnalysisResponse(recording=recording, pose_sequence=summary)
        except Exception:
            self._artifacts.delete_bundle(pose_sequence_id)
            raise

    def artifact_path(self, pose_sequence_id: UUID, filename: str) -> Path:
        return self._artifacts.path_for(pose_sequence_id, filename)

    def _validate_upload(
        self,
        filename: str | None,
        content_type: str | None,
        content: bytes,
    ) -> tuple[str, str]:
        if not content:
            raise InvalidVideoUpload("The uploaded video is empty.")
        if len(content) > self._max_upload_bytes:
            raise InvalidVideoUpload(
                f"The uploaded video exceeds the {self._max_upload_bytes}-byte limit."
            )

        extension = Path(filename or "").suffix.lower()
        if extension not in SUPPORTED_VIDEO_TYPES:
            supported = ", ".join(sorted(SUPPORTED_VIDEO_TYPES))
            raise InvalidVideoUpload(f"Unsupported video extension. Expected one of: {supported}.")

        expected_type = SUPPORTED_VIDEO_TYPES[extension]
        if content_type not in {None, "", "application/octet-stream", expected_type}:
            raise InvalidVideoUpload(
                f"Content type {content_type!r} does not match the {extension} extension."
            )
        return extension, expected_type
