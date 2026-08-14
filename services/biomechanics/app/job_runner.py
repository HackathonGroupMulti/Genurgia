import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import numpy as np

from app.evidence_repository import SQLiteEvidenceRepository
from app.febio_adapter import FebioFlexionSweepAdapter, definition_sha256
from app.migrations import migrate
from app.schemas.evidence import DerivationCreate, SimulationResultCreate
from app.schemas.experiments import MotionReplayRequestV1, MotionReplayResultV1
from app.schemas.jobs import JobCreateV1, JobV1
from app.schemas.simulation import (
    FebioFlexionSweepRequestV1,
    FebioFlexionSweepResultV1,
    FiniteElementModelImportJobRequestV1,
)
from app.services.simulation_models import SimulationModelImportService
from app.settings import febio_executable
from app.storage import LocalArtifactStore


class JobNotFound(LookupError):
    pass


class JobConflict(ValueError):
    pass


class SQLiteJobRunner:
    """Durable single-claim local worker for bounded offline jobs."""

    def __init__(
        self,
        database_path: Path,
        artifacts: LocalArtifactStore,
        *,
        configured_febio_executable: str | None = None,
    ) -> None:
        self.database_path = database_path.resolve()
        self.artifacts = artifacts
        self.evidence = SQLiteEvidenceRepository(self.database_path)
        self._febio = FebioFlexionSweepAdapter(
            configured_febio_executable
            if configured_febio_executable is not None
            else febio_executable()
        )
        self._handlers = {
            "anatomical-motion-replay-v1": self._run_motion_replay,
            "febio-model-import-v1": self._run_febio_model_import,
            "febio-flexion-sweep-v1": self._run_febio_flexion_sweep,
        }
        with self._connect() as connection:
            migrate(connection)
            connection.execute(
                """UPDATE jobs SET status='queued', started_at=NULL,
                   logs_json=json_insert(logs_json, '$[#]', json_object(
                     'at', ?, 'event', 'recovered-after-interruption'))
                   WHERE status='running'""",
                (_now(),),
            )

    def create(self, request: JobCreateV1) -> JobV1:
        identifier = uuid4()
        now = _now()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO jobs VALUES
                (?, ?, 'queued', 0, ?, NULL, ?, 0, 0, ?, NULL, NULL, NULL)""",
                (
                    str(identifier),
                    request.job_type,
                    _json(request.request),
                    _json([{"at": now, "event": "queued"}]),
                    now,
                ),
            )
        return self.get(identifier)

    def get(self, job_id: UUID) -> JobV1:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (str(job_id),)).fetchone()
        if row is None:
            raise JobNotFound(f"Job {job_id} was not found.")
        return _job(row)

    def list(self) -> list[JobV1]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM jobs ORDER BY created_at")
            return [_job(row) for row in rows]

    def cancel(self, job_id: UUID) -> JobV1:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM jobs WHERE id = ?", (str(job_id),)
            ).fetchone()
            if row is None:
                raise JobNotFound(f"Job {job_id} was not found.")
            if row["status"] in {"succeeded", "failed", "cancelled"}:
                raise JobConflict("A terminal job cannot be cancelled.")
            status = "cancelled" if row["status"] == "queued" else "running"
            connection.execute(
                """UPDATE jobs SET status=?, cancel_requested=1,
                   completed_at=CASE WHEN ?='cancelled' THEN ? ELSE completed_at END
                   WHERE id=?""",
                (status, status, _now(), str(job_id)),
            )
        return self.get(job_id)

    def retry(self, job_id: UUID) -> JobV1:
        job = self.get(job_id)
        if job.status not in {"failed", "cancelled"}:
            raise JobConflict("Only failed or cancelled jobs can be retried.")
        with self._connect() as connection:
            connection.execute(
                """UPDATE jobs SET status='queued', progress=0, cancel_requested=0,
                   started_at=NULL, completed_at=NULL, error_detail=NULL WHERE id=?""",
                (str(job_id),),
            )
        return self.get(job_id)

    def run_next(self) -> JobV1 | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT id FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            job_id = UUID(row["id"])
            connection.execute(
                """UPDATE jobs SET status='running', progress=0.05, attempts=attempts+1,
                   started_at=? WHERE id=?""",
                (_now(), str(job_id)),
            )
            connection.commit()
        staging: Path | None = None
        published = False
        try:
            job = self.get(job_id)
            if job.cancel_requested:
                return self._finish(job_id, "cancelled", None, None)
            handler = self._handlers.get(job.job_type)
            if handler is None:
                raise ValueError(f"Unsupported job type {job.job_type}.")
            staging = self.artifacts.begin_bundle(job_id)
            try:
                result_filename, completion_status = handler(job_id, job.request, staging)
                self.artifacts.publish_bundle(job_id, staging)
                published = True
                staging = None
            except Exception:
                if staging is not None:
                    self.artifacts.abort_bundle(staging)
                raise
            verified = self.artifacts.verify_bundle(job_id)
            if not verified or any(item["integrity"] != "verified" for item in verified):
                self.artifacts.delete_bundle(job_id)
                raise ValueError("Job result failed artifact integrity verification.")
            reference = self.artifacts.reference(job_id, result_filename)
            if job.job_type == "febio-flexion-sweep-v1":
                self._record_febio_result(job, reference, completion_status)
            if job.job_type == "febio-model-import-v1":
                upload = FiniteElementModelImportJobRequestV1.model_validate(job.request)
                self.artifacts.delete_bundle(upload.upload_bundle_id)
            return self._finish(job_id, completion_status, reference, None)
        except Exception as error:
            if published:
                self.artifacts.delete_bundle(job_id)
            return self._finish(job_id, "failed", None, str(error)[:1000])

    def _run_motion_replay(
        self,
        _job_id: UUID,
        request: dict[str, object],
        staging: Path,
    ) -> tuple[str, str]:
        result = _motion_replay(MotionReplayRequestV1.model_validate(request))
        filename = "motion_replay_result_v1.json"
        self.artifacts.write_staged_json(staging, filename, result.model_dump(mode="json"))
        return filename, "succeeded"

    def _run_febio_model_import(
        self,
        _job_id: UUID,
        request: dict[str, object],
        staging: Path,
    ) -> tuple[str, str]:
        parsed = FiniteElementModelImportJobRequestV1.model_validate(request)
        source = self.artifacts.path_for(
            parsed.upload_bundle_id,
            "source_fe_model_package.zip",
        )
        if not source.is_file():
            raise ValueError("The queued finite-element model upload is missing.")
        service = SimulationModelImportService(
            self.artifacts,
            self.evidence,
            max_upload_bytes=source.stat().st_size,
        )
        result = service.import_febio_package(source)
        filename = "finite_element_model_import_result_v1.json"
        self.artifacts.write_staged_json(staging, filename, result.model_dump(mode="json"))
        return filename, "succeeded"

    def _run_febio_flexion_sweep(
        self,
        job_id: UUID,
        request: dict[str, object],
        staging: Path,
    ) -> tuple[str, str]:
        parsed = FebioFlexionSweepRequestV1.model_validate(request)
        canonical_experiment = self.evidence.get_experiment(parsed.virtual_experiment_id)
        if canonical_experiment.definition_version != "experiment-definition-v2" or (
            canonical_experiment.definition != parsed.experiment.model_dump(mode="json")
        ):
            raise ValueError("The queued definition differs from its canonical experiment.")
        model = self.evidence.get_simulation_model(parsed.experiment.simulation_model_id)
        self.artifacts.write_staged_json(
            staging,
            "experiment_definition_v2.json",
            parsed.experiment.model_dump(mode="json"),
        )
        poses, solver_version, executable_sha256, cancelled = self._febio.execute(
            parsed.experiment,
            model,
            staging,
            is_cancelled=lambda: self.get(job_id).cancel_requested,
            report_progress=lambda progress, event: self._report_progress(
                job_id, progress, event
            ),
        )
        self.artifacts.write_staged_json(
            staging,
            "adapter_configuration_v1.json",
            {
                "adapter_id": "febio-4.12",
                "solver_version": solver_version,
                "solver_executable_sha256": executable_sha256,
                "simulation_model_id": str(model.id),
                "simulation_model_sha256": model.model_sha256,
                "independent_pose_count": len(parsed.experiment.flexion_angles_degrees),
                "interpretation": "exploratory-simulated-hypothesis",
            },
        )
        for pose in poses:
            if pose.field_artifact_reference:
                pose.field_artifact_reference = self.artifacts.reference(
                    job_id, pose.field_artifact_reference
                )
            if pose.normalized_field_manifest_reference:
                pose.normalized_field_manifest_reference = self.artifacts.reference(
                    job_id, pose.normalized_field_manifest_reference
                )
        result = FebioFlexionSweepResultV1(
            experiment_definition_sha256=definition_sha256(parsed.experiment),
            solver_version=solver_version,
            solver_executable_sha256=executable_sha256,
            poses=poses,
            included_structures=model.included_structures,
            excluded_structures=model.excluded_structures,
            validation_tier=parsed.experiment.validation_tier,
        )
        filename = "febio_flexion_sweep_result_v1.json"
        self.artifacts.write_staged_json(staging, filename, result.model_dump(mode="json"))
        return filename, "cancelled" if cancelled else "succeeded"

    def _record_febio_result(
        self,
        job: JobV1,
        reference: str,
        completion_status: str,
    ) -> None:
        parsed = FebioFlexionSweepRequestV1.model_validate(job.request)
        payload = json.loads(
            self.artifacts.path_for(
                job.id, "febio_flexion_sweep_result_v1.json"
            ).read_text(encoding="utf-8")
        )
        self.evidence.create_simulation_result_and_derivation(
            SimulationResultCreate(
                experiment_id=parsed.virtual_experiment_id,
                status="cancelled" if completion_status == "cancelled" else "complete",
                outputs={
                    "interpretation": payload["interpretation"],
                    "experiment_definition_sha256": payload[
                        "experiment_definition_sha256"
                    ],
                    "solver_version": payload["solver_version"],
                    "solver_executable_sha256": payload[
                        "solver_executable_sha256"
                    ],
                    "poses": payload["poses"],
                    "included_structures": payload["included_structures"],
                    "excluded_structures": payload["excluded_structures"],
                },
                sensitivity={"status": "not-run", "reason": "explicit-child-experiments-only"},
                validation_evidence={
                    "tier": payload["validation_tier"],
                    "solver_version": payload["solver_version"],
                    "solver_executable_sha256": payload[
                        "solver_executable_sha256"
                    ],
                    "numerical_convergence_is_not_scientific_validation": True,
                },
                artifact_references={
                    "normalized_result": reference,
                    "experiment_definition": self.artifacts.reference(
                        job.id, "experiment_definition_v2.json"
                    ),
                    "adapter_configuration": self.artifacts.reference(
                        job.id, "adapter_configuration_v1.json"
                    ),
                    "artifact_manifest": self.artifacts.reference(
                        job.id, "artifact_manifest_v1.json"
                    ),
                },
            ),
            DerivationCreate(
                derivation_type="febio-flexion-sweep",
                inputs=[
                    str(parsed.experiment.simulation_model_id),
                    str(parsed.virtual_experiment_id),
                ],
                # The repository replaces this placeholder with the result ID in
                # the same SQLite transaction.
                outputs=["pending-simulation-result"],
                algorithm="febio-flexion-sweep-adapter",
                algorithm_version="v1",
                configuration={
                    "definition_sha256": payload["experiment_definition_sha256"],
                    "solver_version": payload["solver_version"],
                    "solver_executable_sha256": payload[
                        "solver_executable_sha256"
                    ],
                },
                code_revision="knee-twin-milestone-14",
                environment={"execution": "offline-workstation", "job_id": str(job.id)},
            ),
        )

    def _report_progress(self, job_id: UUID, progress: float, event: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """UPDATE jobs SET progress=?,
                   logs_json=json_insert(logs_json, '$[#]', json_object('at', ?, 'event', ?))
                   WHERE id=?""",
                (progress, _now(), event, str(job_id)),
            )

    def _finish(
        self, job_id: UUID, status: str, result: str | None, error: str | None
    ) -> JobV1:
        with self._connect() as connection:
            connection.execute(
                """UPDATE jobs SET status=?, progress=?, result_artifact_reference=?,
                   completed_at=?, error_detail=? WHERE id=?""",
                (
                    status,
                    1 if status == "succeeded" else self.get(job_id).progress,
                    result,
                    _now(),
                    error,
                    str(job_id),
                ),
            )
        return self.get(job_id)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _motion_replay(request: MotionReplayRequestV1) -> MotionReplayResultV1:
    definition_json = json.dumps(
        request.experiment.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode()
    included = [frame for frame in request.frames if not frame.excluded]
    residual = (
        float(np.sqrt(np.mean([frame.projected_landmark_residual_mm**2 for frame in included])))
        if included
        else None
    )
    excluded = [
        {"timestamp_ms": frame.timestamp_ms, "reason": frame.exclusion_reason}
        for frame in request.frames
        if frame.excluded
    ]
    violations = [
        {"timestamp_ms": frame.timestamp_ms, "violations": frame.anatomical_constraint_violations}
        for frame in request.frames
        if frame.anatomical_constraint_violations
    ]
    maximum_uncertainty = max(frame.transform_uncertainty_mm for frame in request.frames)
    return MotionReplayResultV1(
        experiment_definition_sha256=hashlib.sha256(definition_json).hexdigest(),
        frame_count=len(request.frames),
        included_frame_count=len(included),
        excluded_intervals=excluded,
        residual_rms_mm=residual,
        maximum_transform_uncertainty_mm=maximum_uncertainty,
        anatomical_constraint_violations=violations,
        registration_sensitivity={
            "method": request.experiment.sensitivity.method,
            "samples": request.experiment.sensitivity.samples,
            "maximum_input_transform_uncertainty_mm": maximum_uncertainty,
        },
        validation_tier=request.experiment.validation_tier,
    )


def _job(row: sqlite3.Row) -> JobV1:
    return JobV1(
        id=row["id"],
        job_type=row["job_type"],
        status=row["status"],
        progress=row["progress"],
        request=json.loads(row["request_json"]),
        result_artifact_reference=row["result_artifact_reference"],
        logs=json.loads(row["logs_json"]),
        attempts=row["attempts"],
        cancel_requested=bool(row["cancel_requested"]),
        created_at=row["created_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        error_detail=row["error_detail"],
    )


def _json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _now() -> str:
    return datetime.now(UTC).isoformat()
