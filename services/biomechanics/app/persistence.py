"""SQLite metadata persistence; large artifacts remain in artifact storage."""

import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.migrations import migrate
from app.schemas.operations import ProcessingOperation
from app.schemas.pose import PoseSequenceSummary, Recording
from app.schemas.sessions import (
    AnalysisMetadata,
    ComparisonMetric,
    PoseSequenceMetadata,
    RecordingMetadata,
    SelectedSessionComparison,
    SessionComparisonEntry,
    SessionMetric,
    SessionSummary,
)


class SessionNotFound(LookupError):
    pass


class SQLiteSessionRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path.resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            migrate(connection)
            connection.execute(
                """UPDATE processing_operations
                SET status = 'failed', stage = 'interrupted', completed_at = ?,
                    error_code = 'InterruptedOperation',
                    error_detail = 'The workstation stopped before the operation completed.'
                WHERE status = 'running'""",
                (_utc_now(),),
            )

    def record_pose_extraction(
        self,
        recording: Recording,
        pose_sequence: PoseSequenceSummary,
        processing_operation_id: UUID | None = None,
        processing_duration_ms: int | None = None,
    ) -> UUID:
        session_id = uuid4()
        now = _utc_now()
        recorded_at = recording.captured_at.isoformat() if recording.captured_at else now
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO sessions
                (id, exercise_type, recorded_at, created_at, status)
                VALUES (?, 'squat', ?, ?, 'pose_extracted')""",
                (str(session_id), recorded_at, now),
            )
            connection.execute(
                """
                INSERT INTO recordings
                (id, session_id, schema_version, original_filename, content_type,
                 storage_reference, size_bytes, duration_ms, fps, width, height,
                 captured_at, protocol, camera_view, orientation, laterality_context,
                 capture_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(recording.id),
                    str(session_id),
                    recording.schema_version,
                    recording.original_filename,
                    recording.content_type,
                    recording.storage_reference,
                    recording.size_bytes,
                    recording.duration_ms,
                    recording.fps,
                    recording.width,
                    recording.height,
                    recording.captured_at.isoformat() if recording.captured_at else None,
                    recording.protocol,
                    recording.camera_view,
                    recording.orientation,
                    recording.laterality_context,
                    recording.capture_notes,
                ),
            )
            connection.execute(
                """
                INSERT INTO pose_sequences
                (id, session_id, recording_id, schema_version, pose_model, pose_model_version,
                 raw_landmarks_reference, annotated_video_reference, frame_count,
                 detected_frame_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(pose_sequence.id),
                    str(session_id),
                    str(pose_sequence.recording_id),
                    pose_sequence.schema_version,
                    pose_sequence.pose_model,
                    pose_sequence.pose_model_version,
                    pose_sequence.raw_landmarks_reference,
                    pose_sequence.annotated_video_reference,
                    pose_sequence.frame_count,
                    pose_sequence.detected_frame_count,
                ),
            )
            if processing_operation_id is not None and processing_duration_ms is not None:
                connection.execute(
                    """UPDATE processing_operations
                    SET status = 'complete', stage = 'published', pose_sequence_id = ?,
                        completed_at = ?, duration_ms = ?
                    WHERE id = ?""",
                    (
                        str(pose_sequence.id),
                        _utc_now(),
                        processing_duration_ms,
                        str(processing_operation_id),
                    ),
                )
        return session_id

    def start_processing_operation(self, operation_id: UUID, input_bytes: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO processing_operations
                (id, operation_type, status, stage, input_bytes, started_at)
                VALUES (?, 'pose_extraction', 'running', 'artifact_staging', ?, ?)""",
                (str(operation_id), input_bytes, _utc_now()),
            )

    def fail_processing_operation(
        self,
        operation_id: UUID,
        stage: str,
        duration_ms: int,
        error: Exception,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """UPDATE processing_operations
                SET status = 'failed', stage = ?, completed_at = ?, duration_ms = ?,
                    error_code = ?, error_detail = ?
                WHERE id = ?""",
                (
                    stage,
                    _utc_now(),
                    duration_ms,
                    type(error).__name__,
                    str(error)[:500],
                    str(operation_id),
                ),
            )

    def list_processing_operations(self, limit: int = 50) -> list[ProcessingOperation]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM processing_operations ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [ProcessingOperation.model_validate(dict(row)) for row in rows]

    def record_analysis(
        self,
        pose_sequence_id: UUID,
        analysis_type: str,
        analysis_version: str,
        artifact_reference: str,
        status: str,
        metrics: Iterable[tuple[str, float, str]] = (),
        capture_quality_status: str | None = None,
    ) -> None:
        now = _utc_now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT session_id FROM pose_sequences WHERE id = ?",
                (str(pose_sequence_id),),
            ).fetchone()
            if row is None:
                return
            session_id = row["session_id"]
            connection.execute(
                """
                INSERT INTO analyses
                (session_id, pose_sequence_id, analysis_type, analysis_version,
                 artifact_reference, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (pose_sequence_id, analysis_type, analysis_version)
                DO UPDATE SET artifact_reference = excluded.artifact_reference
                """,
                (
                    session_id,
                    str(pose_sequence_id),
                    analysis_type,
                    analysis_version,
                    artifact_reference,
                    now,
                ),
            )
            analysis_id = connection.execute(
                """
                SELECT id FROM analyses
                WHERE pose_sequence_id = ? AND analysis_type = ? AND analysis_version = ?
                """,
                (str(pose_sequence_id), analysis_type, analysis_version),
            ).fetchone()["id"]
            connection.execute(
                "DELETE FROM session_metrics WHERE analysis_id = ?",
                (analysis_id,),
            )
            for name, value, unit in metrics:
                connection.execute(
                    """
                    INSERT INTO session_metrics
                    (analysis_id, name, value, unit, source_analysis_version)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (analysis_id, name)
                    DO UPDATE SET value = excluded.value, unit = excluded.unit
                    """,
                    (analysis_id, name, value, unit, analysis_version),
                )
            connection.execute(
                """
                UPDATE sessions
                SET status = CASE WHEN status = 'complete' THEN status ELSE ? END
                WHERE id = ?
                """,
                (status, session_id),
            )
            if capture_quality_status is not None:
                connection.execute(
                    "UPDATE sessions SET capture_quality_status = ? WHERE id = ?",
                    (capture_quality_status, session_id),
                )

    def list_sessions(self, limit: int = 50) -> list[SessionSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id FROM sessions ORDER BY recorded_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [self._session(connection, UUID(row["id"])) for row in rows]

    def get_session(self, session_id: UUID) -> SessionSummary:
        with self._connect() as connection:
            return self._session(connection, session_id)

    def delete_session(self, session_id: UUID) -> None:
        with self._connect() as connection:
            deleted = connection.execute(
                "DELETE FROM sessions WHERE id = ?",
                (str(session_id),),
            ).rowcount
        if deleted == 0:
            raise SessionNotFound(f"Session {session_id} was not found.")

    def compare_sessions(self, limit: int = 10) -> list[SessionComparisonEntry]:
        sessions = list(reversed(self.list_sessions(limit)))
        output: list[SessionComparisonEntry] = []
        previous_mean_rom: float | None = None
        for session in sessions:
            values = {metric.name: metric.value for metric in session.metrics}
            mean_rom = values.get("mean_rom_degrees")
            output.append(
                SessionComparisonEntry(
                    session_id=session.id,
                    recorded_at=session.recorded_at,
                    repetition_count=int(values.get("repetition_count", 0)),
                    mean_left_rom_degrees=values.get("mean_left_rom_degrees"),
                    mean_right_rom_degrees=values.get("mean_right_rom_degrees"),
                    mean_rom_degrees=mean_rom,
                    mean_duration_ms=values.get("mean_duration_ms"),
                    mean_confidence=values.get("mean_confidence"),
                    mean_rom_change_from_previous_degrees=(
                        mean_rom - previous_mean_rom
                        if mean_rom is not None and previous_mean_rom is not None
                        else None
                    ),
                )
            )
            if mean_rom is not None:
                previous_mean_rom = mean_rom
        return list(reversed(output))

    def compare_selected_sessions(
        self,
        baseline_session_id: UUID,
        current_session_id: UUID,
    ) -> SelectedSessionComparison:
        baseline = self.get_session(baseline_session_id)
        current = self.get_session(current_session_id)
        incompatibilities: list[str] = []
        if baseline.id == current.id:
            incompatibilities.append("Baseline and current session must be different.")
        for label, baseline_value, current_value in (
            ("protocol", baseline.recording.protocol, current.recording.protocol),
            ("camera view", baseline.recording.camera_view, current.recording.camera_view),
            ("orientation", baseline.recording.orientation, current.recording.orientation),
            (
                "laterality context",
                baseline.recording.laterality_context,
                current.recording.laterality_context,
            ),
            ("pose model", baseline.pose_sequence.pose_model, current.pose_sequence.pose_model),
            (
                "pose model version",
                baseline.pose_sequence.pose_model_version,
                current.pose_sequence.pose_model_version,
            ),
            (
                "coordinate convention",
                baseline.pose_sequence.coordinate_convention,
                current.pose_sequence.coordinate_convention,
            ),
        ):
            if baseline_value != current_value:
                incompatibilities.append(
                    f"{label.capitalize()} differs: {baseline_value!s} vs {current_value!s}."
                )
            elif baseline_value == "unknown":
                incompatibilities.append(f"{label.capitalize()} is unknown.")

        baseline_version = _latest_analysis_version(baseline, "squat_repetitions")
        current_version = _latest_analysis_version(current, "squat_repetitions")
        if baseline_version != current_version:
            incompatibilities.append("Repetition analysis versions differ.")
        if baseline_version is None:
            incompatibilities.append("A repetition analysis is missing.")

        metrics: list[ComparisonMetric] = []
        if not incompatibilities:
            baseline_metrics = {metric.name: metric for metric in baseline.metrics}
            current_metrics = {metric.name: metric for metric in current.metrics}
            for name in sorted(baseline_metrics.keys() & current_metrics.keys()):
                baseline_metric = baseline_metrics[name]
                current_metric = current_metrics[name]
                if (
                    baseline_metric.unit == current_metric.unit
                    and baseline_metric.source_analysis_version
                    == current_metric.source_analysis_version
                ):
                    metrics.append(
                        ComparisonMetric(
                            name=name,
                            baseline_value=baseline_metric.value,
                            current_value=current_metric.value,
                            change=current_metric.value - baseline_metric.value,
                            unit=baseline_metric.unit,
                        )
                    )
        return SelectedSessionComparison(
            baseline_session_id=baseline.id,
            current_session_id=current.id,
            compatible=not incompatibilities,
            incompatibilities=incompatibilities,
            analysis_version=current_version if not incompatibilities else None,
            metrics=metrics,
        )

    def _session(self, connection: sqlite3.Connection, session_id: UUID) -> SessionSummary:
        row = connection.execute(
            """
            SELECT s.*, r.id AS recording_id, r.schema_version AS recording_schema_version,
                   r.original_filename, r.content_type, r.storage_reference, r.size_bytes,
                   r.duration_ms, r.fps, r.width, r.height, r.captured_at, r.protocol,
                   r.camera_view, r.orientation, r.laterality_context, r.capture_notes,
                   p.id AS pose_sequence_id, p.schema_version AS pose_schema_version,
                   p.pose_model, p.pose_model_version, p.raw_landmarks_reference,
                   p.annotated_video_reference, p.frame_count, p.detected_frame_count
            FROM sessions s
            JOIN recordings r ON r.session_id = s.id
            JOIN pose_sequences p ON p.session_id = s.id
            WHERE s.id = ?
            """,
            (str(session_id),),
        ).fetchone()
        if row is None:
            raise SessionNotFound(f"Session {session_id} was not found.")
        analyses = connection.execute(
            "SELECT * FROM analyses WHERE session_id = ? ORDER BY created_at, id",
            (str(session_id),),
        ).fetchall()
        metrics = connection.execute(
            """
            SELECT m.* FROM session_metrics m
            JOIN analyses a ON a.id = m.analysis_id
            WHERE a.id IN (
                SELECT MAX(id) FROM analyses
                WHERE session_id = ?
                GROUP BY analysis_type
            )
            ORDER BY m.name
            """,
            (str(session_id),),
        ).fetchall()
        return SessionSummary(
            id=row["id"],
            recorded_at=row["recorded_at"],
            created_at=row["created_at"],
            status=row["status"],
            capture_quality_status=row["capture_quality_status"],
            recording=RecordingMetadata(
                schema_version=row["recording_schema_version"],
                id=row["recording_id"],
                original_filename=row["original_filename"],
                content_type=row["content_type"],
                storage_reference=row["storage_reference"],
                size_bytes=row["size_bytes"],
                duration_ms=row["duration_ms"],
                fps=row["fps"],
                width=row["width"],
                height=row["height"],
                captured_at=row["captured_at"],
                protocol=row["protocol"],
                camera_view=row["camera_view"],
                orientation=row["orientation"],
                laterality_context=row["laterality_context"],
                capture_notes=row["capture_notes"],
            ),
            pose_sequence=PoseSequenceMetadata(
                schema_version=row["pose_schema_version"],
                id=row["pose_sequence_id"],
                recording_id=row["recording_id"],
                pose_model=row["pose_model"],
                pose_model_version=row["pose_model_version"],
                coordinate_convention="mediapipe-pose-world-v1",
                raw_landmarks_reference=row["raw_landmarks_reference"],
                annotated_video_reference=row["annotated_video_reference"],
                frame_count=row["frame_count"],
                detected_frame_count=row["detected_frame_count"],
            ),
            analyses=[
                AnalysisMetadata(
                    id=analysis["id"],
                    analysis_type=analysis["analysis_type"],
                    analysis_version=analysis["analysis_version"],
                    artifact_reference=analysis["artifact_reference"],
                    created_at=analysis["created_at"],
                )
                for analysis in analyses
            ],
            metrics=[
                SessionMetric(
                    name=metric["name"],
                    value=metric["value"],
                    unit=metric["unit"],
                    source_analysis_version=metric["source_analysis_version"],
                )
                for metric in metrics
            ],
        )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _latest_analysis_version(session: SessionSummary, analysis_type: str) -> str | None:
    matches = [
        analysis.analysis_version
        for analysis in session.analyses
        if analysis.analysis_type == analysis_type
    ]
    return matches[-1] if matches else None
