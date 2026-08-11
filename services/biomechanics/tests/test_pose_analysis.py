import json
from pathlib import Path

import pytest

from analysis.pose import PoseExtractionError
from app.schemas.pose import PoseSequenceArtifact
from app.services.pose_analysis import InvalidVideoUpload, PoseAnalysisService
from app.storage import LocalArtifactStore
from tests.fakes import FakePoseProvider

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_VIDEO = REPOSITORY_ROOT / "data" / "fixtures" / "pose-person.mp4"


def create_service(tmp_path: Path, max_upload_bytes: int = 1024 * 1024) -> PoseAnalysisService:
    return PoseAnalysisService(
        artifact_store=LocalArtifactStore(tmp_path),
        pose_provider=FakePoseProvider(),
        max_upload_bytes=max_upload_bytes,
    )


def test_analysis_preserves_upload_raw_observations_and_overlay(tmp_path: Path) -> None:
    service = create_service(tmp_path)
    response = service.analyze(
        "fixture.mp4",
        "video/mp4",
        FIXTURE_VIDEO.read_bytes(),
    )

    sequence_id = response.pose_sequence.id
    raw_path = service.artifact_path(sequence_id, "pose_sequence.json")
    artifact = PoseSequenceArtifact.model_validate_json(raw_path.read_text(encoding="utf-8"))

    assert artifact.recording.original_filename == "fixture.mp4"
    assert artifact.pose_sequence.pose_model == "fake-pose-provider"
    assert artifact.pose_sequence.frames[0].timestamp_ms == 0
    assert artifact.pose_sequence.frames[0].poses[0].image_landmarks[0].visibility == 0.9
    stored_recording = service.artifact_path(sequence_id, "recording.mp4")
    assert stored_recording.read_bytes() == FIXTURE_VIDEO.read_bytes()
    assert service.artifact_path(sequence_id, "annotated.mp4").is_file()
    raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
    assert raw_payload["pose_sequence"]["schema_version"] == "1.0.0"


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("empty.mp4", "video/mp4", b""),
        ("recording.txt", "text/plain", b"video"),
        ("recording.mp4", "video/webm", b"video"),
    ],
)
def test_analysis_rejects_invalid_uploads(
    tmp_path: Path,
    filename: str,
    content_type: str,
    content: bytes,
) -> None:
    with pytest.raises(InvalidVideoUpload):
        create_service(tmp_path).analyze(filename, content_type, content)


def test_analysis_rejects_oversized_upload(tmp_path: Path) -> None:
    with pytest.raises(InvalidVideoUpload, match="exceeds"):
        create_service(tmp_path, max_upload_bytes=3).analyze(
            "recording.mp4",
            "video/mp4",
            b"four",
        )


def test_failed_extraction_removes_partial_artifacts(tmp_path: Path) -> None:
    class FailingProvider(FakePoseProvider):
        def extract(self, video_path: Path, annotated_video_path: Path):
            raise PoseExtractionError("expected failure")

    service = PoseAnalysisService(
        artifact_store=LocalArtifactStore(tmp_path),
        pose_provider=FailingProvider(),
        max_upload_bytes=1024,
    )

    with pytest.raises(PoseExtractionError, match="expected failure"):
        service.analyze("recording.mp4", "video/mp4", b"video")

    assert list(tmp_path.iterdir()) == []
