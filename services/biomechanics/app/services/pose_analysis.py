from datetime import datetime
from pathlib import Path
from time import monotonic
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
    ProcessingMetrics,
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

    def create_temporary_upload(self, extension: str = ".upload") -> Path:
        return self._artifacts.create_temporary_upload(extension)

    def delete_temporary_upload(self, path: Path) -> None:
        self._artifacts.delete_temporary_upload(path)

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
        temporary = self._artifacts.create_temporary_upload(Path(filename or "").suffix)
        try:
            temporary.write_bytes(content)
            return self.analyze_file(
                filename,
                content_type,
                temporary,
                len(content),
                captured_at=captured_at,
                camera_view=camera_view,
                orientation=orientation,
                laterality_context=laterality_context,
                capture_notes=capture_notes,
            )
        finally:
            self._artifacts.delete_temporary_upload(temporary)

    def analyze_file(
        self,
        filename: str | None,
        content_type: str | None,
        upload_path: Path,
        size_bytes: int,
        *,
        captured_at: datetime | None = None,
        camera_view: str = "unknown",
        orientation: str = "unknown",
        laterality_context: str = "bilateral",
        capture_notes: str | None = None,
    ) -> PoseAnalysisResponse:
        started = monotonic()
        operation_id = uuid4()
        extension, normalized_content_type = self._validate_upload(
            filename,
            content_type,
            size_bytes,
        )
        if captured_at is not None and captured_at.tzinfo is None:
            raise InvalidVideoUpload("Capture time must include a UTC offset.")
        recording_id = uuid4()
        pose_sequence_id = uuid4()
        if self._sessions is not None:
            self._sessions.start_processing_operation(operation_id, size_bytes)
        staging: Path | None = None
        published = False
        stage = "artifact_staging"
        try:
            staging = self._artifacts.begin_bundle(pose_sequence_id)
            recording_filename = f"recording{extension}"
            recording_path = self._artifacts.copy_to_staging(
                staging,
                recording_filename,
                upload_path,
            )
            annotated_filename = "annotated.mp4"
            annotated_path = self._artifacts.staging_path(staging, annotated_filename)
            stage = "pose_extraction"
            extraction = self._pose_provider.extract(recording_path, annotated_path)

            recording = Recording(
                id=recording_id,
                original_filename=filename or recording_filename,
                content_type=normalized_content_type,
                size_bytes=size_bytes,
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
            self._artifacts.write_staged_json(
                staging,
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
            stage = "artifact_publication"
            self._artifacts.publish_bundle(pose_sequence_id, staging)
            published = True
            source_hash = next(
                (
                    item["sha256"]
                    for item in self._artifacts.verify_bundle(pose_sequence_id)
                    if item["filename"] == recording_filename and item["integrity"] == "verified"
                ),
                None,
            )
            duration_ms = max(0, round((monotonic() - started) * 1000))
            if self._sessions is not None:
                stage = "metadata_publication"
                self._sessions.record_pose_extraction(
                    recording,
                    summary,
                    processing_operation_id=operation_id,
                    processing_duration_ms=duration_ms,
                    source_sha256=source_hash,
                )
            return PoseAnalysisResponse(
                recording=recording,
                pose_sequence=summary,
                processing=ProcessingMetrics(
                    operation_id=operation_id,
                    upload_bytes=size_bytes,
                    processing_duration_ms=duration_ms,
                    processed_frames=len(frames),
                    average_frames_per_second=(
                        len(frames) / (duration_ms / 1000) if duration_ms > 0 else None
                    ),
                ),
            )
        except Exception as error:
            if published:
                self._artifacts.delete_bundle(pose_sequence_id)
            else:
                if staging is not None:
                    self._artifacts.abort_bundle(staging)
            if self._sessions is not None:
                self._sessions.fail_processing_operation(
                    operation_id,
                    stage,
                    max(0, round((monotonic() - started) * 1000)),
                    error,
                )
            raise

    def artifact_path(self, pose_sequence_id: UUID, filename: str) -> Path:
        return self._artifacts.path_for(pose_sequence_id, filename)

    def _validate_upload(
        self,
        filename: str | None,
        content_type: str | None,
        size_bytes: int,
    ) -> tuple[str, str]:
        if size_bytes <= 0:
            raise InvalidVideoUpload("The uploaded video is empty.")
        if size_bytes > self._max_upload_bytes:
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
