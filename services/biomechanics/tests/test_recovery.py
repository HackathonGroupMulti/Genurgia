import shutil
from pathlib import Path

from app.persistence import SQLiteSessionRepository
from app.services.kinematics import KinematicsService
from app.services.pose_analysis import PoseAnalysisService
from app.services.sessions import SessionWorkflowService
from app.storage import LocalArtifactStore
from tests.fakes import FakePoseProvider


def test_encrypted_backup_payload_can_be_restored_with_verified_artifacts(
    tmp_path: Path,
) -> None:
    source_artifacts = tmp_path / "source" / "artifacts"
    source_database = tmp_path / "source" / "knee_twin.sqlite3"
    store = LocalArtifactStore(source_artifacts)
    repository = SQLiteSessionRepository(source_database)
    pose = PoseAnalysisService(store, FakePoseProvider(), 1024, repository)
    response = pose.analyze("capture.mp4", "video/mp4", b"video")
    kinematics = KinematicsService(store, repository)
    kinematics.analyze_knee_flexion(response.pose_sequence.id)
    kinematics.analyze_squat_repetitions(response.pose_sequence.id)
    kinematics.analyze_capture_quality(response.pose_sequence.id)
    session_id = repository.list_sessions()[0].id

    restored_root = tmp_path / "restored"
    restored_artifacts = restored_root / "artifacts"
    restored_database = restored_root / "knee_twin.sqlite3"
    shutil.copytree(source_artifacts, restored_artifacts)
    shutil.copy2(source_database, restored_database)

    recovered_store = LocalArtifactStore(restored_artifacts)
    recovered_repository = SQLiteSessionRepository(restored_database)
    recovered_kinematics = KinematicsService(recovered_store, recovered_repository)
    workflow = SessionWorkflowService(
        recovered_repository,
        recovered_store,
        recovered_kinematics,
    )
    manifest = workflow.export_manifest(session_id)

    assert manifest.session.id == session_id
    assert len(manifest.artifacts) == 6
    assert all(artifact.integrity == "verified" for artifact in manifest.artifacts)
