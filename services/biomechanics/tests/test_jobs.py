import json
import sqlite3
from pathlib import Path

from app.job_runner import SQLiteJobRunner
from app.schemas.jobs import JobCreateV1
from app.storage import LocalArtifactStore


def replay_request() -> dict[str, object]:
    identity = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    return {
        "experiment": {
            "experiment_type": "anatomical-motion-replay",
            "anatomy_reconstruction_id": "reconstruction-v1",
            "motion_registration_id": "registration-v1",
            "immutable_input_hashes": {"anatomy": "a" * 64, "motion": "b" * 64},
            "coordinate_systems": {
                "anatomy": "dicom-patient-lps-mm",
                "motion": "capture-volume-right-handed-mm",
            },
            "transforms": {"anatomy_from_capture": identity},
            "properties": [],
            "loading_conditions": [],
            "boundary_conditions": [],
            "software_versions": {"knee-twin": "test"},
            "container_versions": {},
            "requested_outputs": ["motion-replay"],
            "sensitivity": {
                "parameters": ["registration-error"],
                "method": "one-at-a-time",
                "samples": 2,
            },
            "validation_tier": "synthetic",
        },
        "frames": [
            {
                "timestamp_ms": 0,
                "transform": identity,
                "projected_landmark_residual_mm": 1,
                "transform_uncertainty_mm": 0.5,
                "excluded": False,
                "anatomical_constraint_violations": [],
            },
            {
                "timestamp_ms": 10,
                "transform": identity,
                "projected_landmark_residual_mm": 2,
                "transform_uncertainty_mm": 1.5,
                "excluded": True,
                "exclusion_reason": "synthetic occlusion",
                "anatomical_constraint_violations": ["fixture-constraint"],
            },
        ],
    }


def test_durable_job_runs_once_and_publishes_verified_replay(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    runner = SQLiteJobRunner(tmp_path / "knee-twin.sqlite3", store)
    queued = runner.create(
        JobCreateV1(job_type="anatomical-motion-replay-v1", request=replay_request())
    )
    assert queued.status == "queued"
    complete = runner.run_next()
    assert complete is not None
    assert complete.id == queued.id
    assert complete.status == "succeeded"
    assert complete.attempts == 1
    assert complete.result_artifact_reference is not None
    assert all(item["integrity"] == "verified" for item in store.verify_bundle(queued.id))
    result = json.loads(store.path_for(queued.id, "motion_replay_result_v1.json").read_text())
    assert result["included_frame_count"] == 1
    assert result["maximum_transform_uncertainty_mm"] == 1.5
    assert result["excluded_intervals"][0]["reason"] == "synthetic occlusion"


def test_job_cancel_retry_failure_and_interruption_recovery(tmp_path: Path) -> None:
    database = tmp_path / "knee-twin.sqlite3"
    store = LocalArtifactStore(tmp_path / "artifacts")
    runner = SQLiteJobRunner(database, store)
    cancelled = runner.create(
        JobCreateV1(job_type="anatomical-motion-replay-v1", request=replay_request())
    )
    assert runner.cancel(cancelled.id).status == "cancelled"
    assert runner.retry(cancelled.id).status == "queued"

    failed = runner.create(
        JobCreateV1(job_type="anatomical-motion-replay-v1", request={"invalid": True})
    )
    assert runner.run_next().id == cancelled.id
    assert runner.run_next().id == failed.id
    assert runner.get(failed.id).status == "failed"
    assert runner.get(failed.id).error_detail

    interrupted = runner.create(
        JobCreateV1(job_type="anatomical-motion-replay-v1", request=replay_request())
    )
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE jobs SET status='running' WHERE id=?", (str(interrupted.id),))
    recovered = SQLiteJobRunner(database, store).get(interrupted.id)
    assert recovered.status == "queued"
    assert recovered.logs[-1]["event"] == "recovered-after-interruption"
