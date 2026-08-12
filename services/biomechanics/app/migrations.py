"""Small ordered SQLite migrations for the offline workstation."""

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]

    @property
    def checksum(self) -> str:
        payload = "\n".join(self.statements).encode()
        return hashlib.sha256(payload).hexdigest()


MIGRATIONS = (
    Migration(
        version=1,
        name="initial_session_schema",
        statements=(
            """CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                exercise_type TEXT NOT NULL CHECK (exercise_type = 'squat'),
                recorded_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS recordings (
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
            )""",
            """CREATE TABLE IF NOT EXISTS pose_sequences (
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
            )""",
            """CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                pose_sequence_id TEXT NOT NULL REFERENCES pose_sequences(id) ON DELETE CASCADE,
                analysis_type TEXT NOT NULL,
                analysis_version TEXT NOT NULL,
                artifact_reference TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (pose_sequence_id, analysis_type, analysis_version)
            )""",
            """CREATE TABLE IF NOT EXISTS session_metrics (
                analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                source_analysis_version TEXT NOT NULL,
                PRIMARY KEY (analysis_id, name)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_sessions_recorded_at ON sessions(recorded_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_analyses_session ON analyses(session_id, created_at)",
        ),
    ),
    Migration(
        version=2,
        name="capture_metadata_and_quality",
        statements=(
            "ALTER TABLE recordings ADD COLUMN captured_at TEXT",
            "ALTER TABLE recordings ADD COLUMN protocol TEXT NOT NULL DEFAULT 'squat'",
            "ALTER TABLE recordings ADD COLUMN camera_view TEXT NOT NULL DEFAULT 'unknown'",
            "ALTER TABLE recordings ADD COLUMN orientation TEXT NOT NULL DEFAULT 'unknown'",
            (
                "ALTER TABLE recordings ADD COLUMN laterality_context "
                "TEXT NOT NULL DEFAULT 'bilateral'"
            ),
            "ALTER TABLE recordings ADD COLUMN capture_notes TEXT",
            "ALTER TABLE sessions ADD COLUMN capture_quality_status TEXT",
        ),
    ),
)


def migrate(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )"""
    )
    applied = {
        row["version"]: row
        for row in connection.execute("SELECT * FROM schema_migrations").fetchall()
    }
    for migration in MIGRATIONS:
        existing = applied.get(migration.version)
        if existing is not None:
            if existing["checksum"] != migration.checksum:
                raise RuntimeError(
                    f"SQLite migration {migration.version} checksum does not match."
                )
            continue
        with connection:
            for statement in migration.statements:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations VALUES (?, ?, ?, ?)",
                (
                    migration.version,
                    migration.name,
                    migration.checksum,
                    datetime.now(UTC).isoformat(),
                ),
            )
