import asyncio
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from httpx import ASGITransport, AsyncClient, Response

from app.evidence_repository import SQLiteEvidenceRepository
from app.main import create_app
from app.migrations import (
    DEFAULT_LEFT_KNEE_ID,
    DEFAULT_RESEARCH_SUBJECT_ID,
    DEFAULT_RIGHT_KNEE_ID,
    MIGRATIONS,
)
from app.persistence import SQLiteSessionRepository
from app.storage import LocalArtifactStore


def request(app, method: str, path: str, **kwargs) -> Response:
    async def send() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def test_migration_backfills_legacy_session_as_bilateral_video_observation(
    tmp_path: Path,
) -> None:
    database = tmp_path / "legacy-v3.sqlite3"
    now = datetime.now(UTC).isoformat()
    session_id = "11111111-1111-1111-1111-111111111111"
    recording_id = "22222222-2222-2222-2222-222222222222"
    sequence_id = "33333333-3333-3333-3333-333333333333"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY, name TEXT NOT NULL,
                checksum TEXT NOT NULL, applied_at TEXT NOT NULL
            )"""
        )
        for migration in MIGRATIONS[:3]:
            for statement in migration.statements:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations VALUES (?, ?, ?, ?)",
                (migration.version, migration.name, migration.checksum, now),
            )
        connection.execute(
            "INSERT INTO sessions VALUES (?, 'squat', ?, ?, 'pose_extracted', NULL)",
            (session_id, now, now),
        )
        connection.execute(
            """INSERT INTO recordings
            (id, session_id, schema_version, original_filename, content_type,
             storage_reference, size_bytes, duration_ms, fps, width, height,
             captured_at, protocol, camera_view, orientation, laterality_context,
             capture_notes)
            VALUES (?, ?, '1.1.0', 'legacy.mp4', 'video/mp4', ?, 10, 100, 10, 10, 10,
                    NULL, 'squat', 'front', 'landscape', 'bilateral', NULL)""",
            (recording_id, session_id, f"/artifacts/{sequence_id}/recording.mp4"),
        )
        connection.execute(
            """INSERT INTO pose_sequences VALUES
            (?, ?, ?, '1.0.0', 'model', 'v1', ?, ?, 1, 1)""",
            (
                sequence_id,
                session_id,
                recording_id,
                f"/artifacts/{sequence_id}/pose_sequence.json",
                f"/artifacts/{sequence_id}/annotated.mp4",
            ),
        )

    evidence = SQLiteEvidenceRepository(database)

    assert str(evidence.list_subjects()[0].id) == DEFAULT_RESEARCH_SUBJECT_ID
    assert {str(knee.id) for knee in evidence.list_knees()} == {
        DEFAULT_LEFT_KNEE_ID,
        DEFAULT_RIGHT_KNEE_ID,
    }
    assert str(evidence.list_timepoints()[0].id) == session_id
    observation = evidence.list_observations()[0]
    assert str(observation.id) == recording_id
    assert {str(knee_id) for knee_id in observation.knee_target_ids} == {
        DEFAULT_LEFT_KNEE_ID,
        DEFAULT_RIGHT_KNEE_ID,
    }
    assert observation.immutable is True
    assert observation.source_sha256 is None


def test_canonical_evidence_api_preserves_provenance_and_subject_boundaries(
    tmp_path: Path,
) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    sessions = SQLiteSessionRepository(tmp_path / "knee_twin.sqlite3")
    app = create_app(
        pose_analysis_service=None,
        artifact_store=store,
        session_repository=sessions,
    )
    subject_response = request(
        app,
        "POST",
        "/subjects",
        json={"research_code": "CASE-001", "deidentified_confirmed": True},
    )
    assert subject_response.status_code == 201
    subject = subject_response.json()
    knees = request(app, "GET", f"/knees?subject_id={subject['id']}").json()["knees"]
    assert {knee["laterality"] for knee in knees} == {"left", "right"}
    left_knee = next(knee for knee in knees if knee["laterality"] == "left")

    episode = request(
        app,
        "POST",
        "/episodes",
        json={
            "subject_id": subject["id"],
            "episode_type": "study",
            "label": "Paired evidence study",
            "started_at": "2026-02-01T12:00:00Z",
        },
    ).json()
    timepoint = request(
        app,
        "POST",
        "/timepoints",
        json={
            "subject_id": subject["id"],
            "episode_id": episode["id"],
            "observed_at": "2026-02-15T12:00:00Z",
            "label": "Baseline",
        },
    ).json()
    observation_response = request(
        app,
        "POST",
        "/observations",
        json={
            "timepoint_id": timepoint["id"],
            "modality": "mri",
            "source_artifact_reference": "/imports/case-001/source.dcm",
            "source_sha256": "a" * 64,
            "acquisition_manifest": {"series": "synthetic"},
            "authorization": {"basis": "licensed synthetic fixture"},
            "quality": {"status": "pending"},
            "knee_target_ids": [left_knee["id"]],
        },
    )
    assert observation_response.status_code == 201
    observation = observation_response.json()
    assert observation["immutable"] is True
    assert request(app, "GET", f"/observations/{observation['id']}").json() == observation

    annotation = request(
        app,
        "POST",
        "/annotations",
        json={
            "observation_id": observation["id"],
            "annotation_type": "structure-labels",
            "version": "v1",
            "author_type": "expert",
            "payload": {"structures": ["femur"]},
            "review_state": "approved",
        },
    )
    assert annotation.status_code == 201

    reconstruction = request(
        app,
        "POST",
        "/reconstructions",
        json={
            "knee_id": left_knee["id"],
            "timepoint_id": timepoint["id"],
            "version": "v1",
            "geometry_class": "expert-reviewed",
            "structures": ["femur"],
            "artifact_references": {"mesh": "/derived/femur.vtp"},
            "coordinate_system": {"name": "mri-ras-mm"},
            "review_state": "approved",
        },
    )
    assert reconstruction.status_code == 201

    registration = request(
        app,
        "POST",
        "/registrations",
        json={
            "source_reference": observation["id"],
            "target_reference": reconstruction.json()["id"],
            "source_coordinate_system": {"name": "mri-ras-mm"},
            "target_coordinate_system": {"name": "mesh-ras-mm"},
            "transform": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
            "method": "identity-fixture",
            "coverage": {"ratio": 1},
            "error": {"rms_mm": 0},
            "uncertainty": {"translation_mm": 0},
        },
    )
    assert registration.status_code == 201

    derivation = request(
        app,
        "POST",
        "/derivations",
        json={
            "derivation_type": "reconstruction",
            "inputs": [observation["id"]],
            "outputs": [reconstruction.json()["id"]],
            "algorithm": "manual-review",
            "algorithm_version": "v1",
            "configuration": {},
            "code_revision": "test-revision",
            "environment": {"fixture": True},
        },
    ).json()
    assert request(app, "GET", f"/derivations/{derivation['id']}").json() == derivation

    experiment = request(
        app,
        "POST",
        "/experiments",
        json={
            "knee_id": left_knee["id"],
            "timepoint_id": timepoint["id"],
            "definition_version": "experiment-definition-v1",
            "definition": {"purpose": "contract fixture"},
            "validation_tier": "synthetic",
        },
    ).json()
    result_response = request(
        app,
        "POST",
        "/simulation-results",
        json={
            "experiment_id": experiment["id"],
            "status": "complete",
            "outputs": {"replay": "not-run"},
            "sensitivity": {},
            "validation_evidence": {"tier": "synthetic"},
            "artifact_references": {},
        },
    )
    assert result_response.status_code == 201

    second_subject = request(
        app,
        "POST",
        "/subjects",
        json={"research_code": "CASE-002", "deidentified_confirmed": True},
    ).json()
    wrong_knee = request(app, "GET", f"/knees?subject_id={second_subject['id']}").json()[
        "knees"
    ][0]
    incompatible = request(
        app,
        "POST",
        "/observations",
        json={
            "timepoint_id": timepoint["id"],
            "modality": "other",
            "source_artifact_reference": "/fixture",
            "source_sha256": "b" * 64,
            "acquisition_manifest": {},
            "authorization": {},
            "quality": {},
            "knee_target_ids": [wrong_knee["id"]],
        },
    )
    assert incompatible.status_code == 409

    invalid_transform = request(
        app,
        "POST",
        "/registrations",
        json={
            "source_reference": "source",
            "target_reference": "target",
            "source_coordinate_system": {},
            "target_coordinate_system": {},
            "transform": [[1]],
            "method": "invalid",
            "coverage": {},
            "error": {},
            "uncertainty": {},
        },
    )
    assert invalid_transform.status_code == 422
