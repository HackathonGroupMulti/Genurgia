import json
import sqlite3
from pathlib import Path

import pytest

from app.evidence_repository import SQLiteEvidenceRepository
from app.job_runner import SQLiteJobRunner
from app.schemas.evidence import VirtualExperimentCreate
from app.schemas.jobs import JobCreateV1
from app.schemas.simulation import ExperimentDefinitionV2, FlexionPoseResultV1
from app.services.simulation_models import SimulationModelImportService
from app.storage import LocalArtifactStore
from tests.simulation_fixtures import (
    finite_element_manifest,
    flexion_experiment,
    simulation_context,
    write_fe_package,
)


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


class FakeFebioAdapter:
    def execute(
        self,
        experiment,
        simulation_model,
        workdir,
        *,
        is_cancelled,
        report_progress,
    ):
        assert not is_cancelled()
        poses = []
        for index, angle in enumerate(experiment.flexion_angles_degrees):
            field = workdir / f"flexion_{int(angle):03d}.vtk"
            field.write_text("synthetic field", encoding="utf-8")
            status = "nonconverged" if angle == 45 else "converged"
            poses.append(
                FlexionPoseResultV1(
                    flexion_angle_degrees=angle,
                    status=status,
                    contact_pressure_mpa=1 + index,
                    contact_area_mm2=10 + index,
                    maximum_displacement_mm=0.1 + index,
                    maximum_cartilage_meniscus_strain=0.01 + index,
                    maximum_ligament_strain=0.02 + index,
                    reaction_force_n=500,
                    convergence_residual=0.001,
                    diagnostic="Synthetic nonconvergence" if status == "nonconverged" else None,
                    field_artifact_reference=field.name,
                )
            )
            report_progress(0.1 + 0.8 * ((index + 1) / 7), f"fixture-{index}")
        return poses, "4.12", "f" * 64, False


def test_febio_job_registry_publishes_partial_pose_evidence_and_canonical_result(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knee-twin.sqlite3"
    store = LocalArtifactStore(tmp_path / "artifacts")
    evidence = SQLiteEvidenceRepository(database)
    knee, timepoint, reconstruction = simulation_context(evidence)
    package = write_fe_package(
        tmp_path / "synthetic-fe.zip",
        finite_element_manifest(str(reconstruction.id)),
    )
    model = SimulationModelImportService(store, evidence, 10_000_000).import_febio_package(
        package
    ).simulation_model
    definition = ExperimentDefinitionV2.model_validate(
        flexion_experiment(str(model.id), model.model_sha256)
    )
    experiment = evidence.create_experiment(
        VirtualExperimentCreate(
            knee_id=knee.id,
            timepoint_id=timepoint.id,
            definition_version="experiment-definition-v2",
            definition=definition.model_dump(mode="json"),
            validation_tier="synthetic",
        )
    )
    runner = SQLiteJobRunner(database, store)
    runner._febio = FakeFebioAdapter()
    queued = runner.create(
        JobCreateV1(
            job_type="febio-flexion-sweep-v1",
            request={
                "virtual_experiment_id": str(experiment.id),
                "experiment": definition.model_dump(mode="json"),
            },
        )
    )

    complete = runner.run_next()

    assert complete is not None and complete.status == "succeeded"
    payload = json.loads(
        store.path_for(queued.id, "febio_flexion_sweep_result_v1.json").read_text()
    )
    assert len(payload["poses"]) == 7
    assert payload["poses"][3]["status"] == "nonconverged"
    assert payload["interpretation"] == "exploratory-simulated-hypothesis"
    assert all(item["integrity"] == "verified" for item in store.verify_bundle(queued.id))
    canonical = evidence.list_simulation_results()
    assert len(canonical) == 1
    assert canonical[0].experiment_id == experiment.id
    derivations = evidence.list_derivations()
    assert len(derivations) == 2  # FE model import and completed simulation.
    assert derivations[-1].outputs == [str(canonical[0].id)]


def test_febio_job_removes_published_bundle_when_metadata_commit_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "knee-twin.sqlite3"
    store = LocalArtifactStore(tmp_path / "artifacts")
    evidence = SQLiteEvidenceRepository(database)
    knee, timepoint, reconstruction = simulation_context(evidence)
    package = write_fe_package(
        tmp_path / "synthetic-fe.zip",
        finite_element_manifest(str(reconstruction.id)),
    )
    model = SimulationModelImportService(store, evidence, 10_000_000).import_febio_package(
        package
    ).simulation_model
    definition = ExperimentDefinitionV2.model_validate(
        flexion_experiment(str(model.id), model.model_sha256)
    )
    experiment = evidence.create_experiment(
        VirtualExperimentCreate(
            knee_id=knee.id,
            timepoint_id=timepoint.id,
            definition_version="experiment-definition-v2",
            definition=definition.model_dump(mode="json"),
            validation_tier="synthetic",
        )
    )
    runner = SQLiteJobRunner(database, store)
    runner._febio = FakeFebioAdapter()
    queued = runner.create(
        JobCreateV1(
            job_type="febio-flexion-sweep-v1",
            request={
                "virtual_experiment_id": str(experiment.id),
                "experiment": definition.model_dump(mode="json"),
            },
        )
    )

    def fail_metadata(*_args, **_kwargs):
        raise RuntimeError("synthetic metadata failure")

    monkeypatch.setattr(
        runner.evidence,
        "create_simulation_result_and_derivation",
        fail_metadata,
    )
    complete = runner.run_next()

    assert complete is not None and complete.status == "failed"
    assert "metadata failure" in (complete.error_detail or "")
    assert not store.path_for(queued.id, "febio_flexion_sweep_result_v1.json").parent.exists()
    assert evidence.list_simulation_results() == []
