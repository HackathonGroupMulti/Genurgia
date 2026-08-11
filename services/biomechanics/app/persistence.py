"""SQLite metadata persistence; large artifacts remain in artifact storage."""

import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.schemas.pose import PoseSequenceSummary, Recording
from app.schemas.sessions import (
    AnalysisMetadata,
    PoseSequenceMetadata,
    RecordingMetadata,
    SessionComparisonEntry,
    SessionMetric,
    SessionSummary,
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    exercise_type TEXT NOT NULL CHECK (exercise_type = 'squat'),
    recorded_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recordings (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
    schema_version TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    storage_reference TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL,
    fps REAL NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS pose_sequences (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
    recording_id TEXT NOT NULL UNIQUE REFERENCES recordings(id),
    schema_version TEXT NOT NULL,
    pose_model TEXT NOT NULL,
    pose_model_version TEXT NOT NULL,
    raw_landmarks_reference TEXT NOT NULL,
    annotated_video_reference TEXT NOT NULL,
    frame_count INTEGER NOT NULL,
    detected_frame_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    pose_sequence_id TEXT NOT NULL REFERENCES pose_sequences(id) ON DELETE CASCADE,
    analysis_type TEXT NOT NULL,
    analysis_version TEXT NOT NULL,
    artifact_reference TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (pose_sequence_id, analysis_type, analysis_version)
);
CREATE TABLE IF NOT EXISTS session_metrics (
    analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    source_analysis_version TEXT NOT NULL,
    PRIMARY KEY (analysis_id, name)
);
CREATE INDEX IF NOT EXISTS idx_sessions_recorded_at ON sessions(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_session ON analyses(session_id, created_at);
"""


class SessionNotFound(LookupError):
    pass


class SQLiteSessionRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path.resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA_SQL)

    def record_pose_extraction(
        self,
        recording: Recording,
        pose_sequence: PoseSequenceSummary,
    ) -> UUID:
        session_id = uuid4()
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO sessions VALUES (?, 'squat', ?, ?, 'pose_extracted')",
                (str(session_id), now, now),
            )
            connection.execute(
                """
                INSERT INTO recordings
                (id, session_id, schema_version, original_filename, content_type,
                 storage_reference, size_bytes, duration_ms, fps, width, height)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        return session_id

    def record_analysis(
        self,
        pose_sequence_id: UUID,
        analysis_type: str,
        analysis_version: str,
        artifact_reference: str,
        status: str,
        metrics: Iterable[tuple[str, float, str]] = (),
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

    def _session(self, connection: sqlite3.Connection, session_id: UUID) -> SessionSummary:
        row = connection.execute(
            """
            SELECT s.*, r.id AS recording_id, r.schema_version AS recording_schema_version,
                   r.original_filename, r.content_type, r.storage_reference, r.size_bytes,
                   r.duration_ms, r.fps, r.width, r.height,
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
            WHERE m.analysis_id = (
                SELECT id FROM analyses
                WHERE session_id = ? AND analysis_type = 'squat_repetitions'
                ORDER BY id DESC LIMIT 1
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
            ),
            pose_sequence=PoseSequenceMetadata(
                schema_version=row["pose_schema_version"],
                id=row["pose_sequence_id"],
                recording_id=row["recording_id"],
                pose_model=row["pose_model"],
                pose_model_version=row["pose_model_version"],
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
