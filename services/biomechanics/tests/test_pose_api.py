import asyncio
from pathlib import Path

from httpx import ASGITransport, AsyncClient, Response

from app.main import create_app
from app.persistence import SQLiteSessionRepository
from app.services.pose_analysis import PoseAnalysisService
from app.storage import LocalArtifactStore
from tests.fakes import FakePoseProvider

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_VIDEO = REPOSITORY_ROOT / "data" / "fixtures" / "pose-person.mp4"


def request(app, method: str, path: str, **kwargs) -> Response:
    async def send() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def test_upload_returns_pose_summary_and_serves_artifacts(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path)
    sessions = SQLiteSessionRepository(tmp_path / "sessions.sqlite3")
    service = PoseAnalysisService(
        store,
        FakePoseProvider(),
        max_upload_bytes=1024 * 1024,
        session_repository=sessions,
    )
    app = create_app(
        pose_analysis_service=service,
        artifact_store=store,
        session_repository=sessions,
    )

    response = request(
        app,
        "POST",
        "/pose-sequences",
        files={"video": ("fixture.mp4", FIXTURE_VIDEO.read_bytes(), "video/mp4")},
        data={
            "captured_at": "2026-02-14T10:30:00Z",
            "camera_view": "left_side",
            "orientation": "landscape",
            "laterality_context": "bilateral",
            "capture_notes": "Standardized research capture",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["pose_sequence"]["frame_count"] == 1
    assert payload["pose_sequence"]["detected_frame_count"] == 1
    assert payload["recording"]["captured_at"] == "2026-02-14T10:30:00Z"
    assert payload["recording"]["camera_view"] == "left_side"

    raw_response = request(
        app,
        "GET",
        payload["pose_sequence"]["raw_landmarks_reference"],
    )
    overlay_response = request(
        app,
        "GET",
        payload["pose_sequence"]["annotated_video_reference"],
    )
    assert raw_response.status_code == 200
    assert raw_response.headers["content-type"].startswith("application/json")
    assert overlay_response.status_code == 200
    assert overlay_response.headers["content-type"].startswith("video/mp4")

    kinematics_response = request(
        app,
        "POST",
        f"/pose-sequences/{payload['pose_sequence']['id']}/knee-flexion",
    )
    assert kinematics_response.status_code == 200
    analysis = kinematics_response.json()
    assert analysis["calculation_version"] == "knee-flexion-world-3d-v1"
    assert [series["side"] for series in analysis["series"]] == ["left", "right"]
    assert analysis["series"][0]["samples"][0]["value_degrees"] == 0.0

    analysis_artifact = request(app, "GET", analysis["artifact_reference"])
    assert analysis_artifact.status_code == 200

    repetitions_response = request(
        app,
        "POST",
        f"/pose-sequences/{payload['pose_sequence']['id']}/squat-repetitions",
    )
    assert repetitions_response.status_code == 200
    repetitions = repetitions_response.json()
    assert repetitions["phase_model"]["algorithm_version"] == (
        "bilateral-squat-state-machine-v1"
    )
    assert repetitions["repetitions"] == []
    repetition_artifact = request(app, "GET", repetitions["artifact_reference"])
    assert repetition_artifact.status_code == 200

    quality_response = request(
        app,
        "POST",
        f"/pose-sequences/{payload['pose_sequence']['id']}/capture-quality",
    )
    assert quality_response.status_code == 200
    quality = quality_response.json()
    assert quality["analysis_version"] == "capture-quality-v1"
    assert quality["status"] == "fail"
    assert quality["guidance"]
    assert request(app, "GET", quality["artifact_reference"]).status_code == 200

    sessions_response = request(app, "GET", "/sessions")
    assert sessions_response.status_code == 200
    stored_session = sessions_response.json()["sessions"][0]
    assert stored_session["status"] == "complete"
    assert stored_session["pose_sequence"]["id"] == payload["pose_sequence"]["id"]
    assert stored_session["recording"]["capture_notes"] == "Standardized research capture"
    assert [item["analysis_type"] for item in stored_session["analyses"]] == [
        "knee_flexion",
        "squat_repetitions",
        "capture_quality",
    ]
    assert stored_session["capture_quality_status"] == "fail"
    metrics = {item["name"]: item for item in stored_session["metrics"]}
    assert metrics["repetition_count"] == {
        "name": "repetition_count",
        "value": 0.0,
        "unit": "count",
        "source_analysis_version": "squat-repetition-analysis-v2",
    }
    assert metrics["pose_detection_coverage"]["value"] == 1.0

    comparison_response = request(app, "GET", "/sessions/comparison")
    assert comparison_response.status_code == 200
    assert comparison_response.json()["sessions"][0]["repetition_count"] == 0


def test_upload_rejects_unsupported_extension(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path)
    service = PoseAnalysisService(store, FakePoseProvider(), max_upload_bytes=1024)
    app = create_app(pose_analysis_service=service, artifact_store=store)

    response = request(
        app,
        "POST",
        "/pose-sequences",
        files={"video": ("fixture.txt", b"not-video", "text/plain")},
    )

    assert response.status_code == 422


def test_upload_reports_missing_pose_model(tmp_path: Path) -> None:
    app = create_app(pose_analysis_service=None, artifact_store=LocalArtifactStore(tmp_path))

    response = request(
        app,
        "POST",
        "/pose-sequences",
        files={"video": ("fixture.mp4", b"video", "video/mp4")},
    )

    assert response.status_code == 503
