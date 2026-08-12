import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import numpy as np

from app.migrations import migrate
from app.schemas.experiments import MotionReplayRequestV1, MotionReplayResultV1
from app.schemas.jobs import JobCreateV1, JobV1
from app.storage import LocalArtifactStore


class JobNotFound(LookupError):
    pass


class JobConflict(ValueError):
    pass


class SQLiteJobRunner:
    """Durable single-claim local worker for bounded offline jobs."""

    def __init__(self, database_path: Path, artifacts: LocalArtifactStore) -> None:
        self.database_path = database_path.resolve()
        self.artifacts = artifacts
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
        try:
            job = self.get(job_id)
            if job.cancel_requested:
                return self._finish(job_id, "cancelled", None, None)
            if job.job_type != "anatomical-motion-replay-v1":
                raise ValueError(f"Unsupported job type {job.job_type}.")
            result = _motion_replay(MotionReplayRequestV1.model_validate(job.request))
            staging = self.artifacts.begin_bundle(job_id)
            try:
                self.artifacts.write_staged_json(
                    staging, "motion_replay_result_v1.json", result.model_dump(mode="json")
                )
                self.artifacts.publish_bundle(job_id, staging)
            except Exception:
                self.artifacts.abort_bundle(staging)
                raise
            verified = self.artifacts.verify_bundle(job_id)
            if not verified or any(item["integrity"] != "verified" for item in verified):
                self.artifacts.delete_bundle(job_id)
                raise ValueError("Motion replay result failed artifact integrity verification.")
            reference = self.artifacts.reference(job_id, "motion_replay_result_v1.json")
            return self._finish(job_id, "succeeded", reference, None)
        except Exception as error:
            return self._finish(job_id, "failed", None, str(error)[:1000])

    def _finish(
        self, job_id: UUID, status: str, result: str | None, error: str | None
    ) -> JobV1:
        with self._connect() as connection:
            connection.execute(
                """UPDATE jobs SET status=?, progress=?, result_artifact_reference=?,
                   completed_at=?, error_detail=? WHERE id=?""",
                (status, 1 if status == "succeeded" else 0, result, _now(), error, str(job_id)),
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
