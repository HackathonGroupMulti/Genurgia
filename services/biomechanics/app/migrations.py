"""Small ordered SQLite migrations for the offline workstation."""

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

DEFAULT_RESEARCH_SUBJECT_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_LEFT_KNEE_ID = "00000000-0000-0000-0000-000000000002"
DEFAULT_RIGHT_KNEE_ID = "00000000-0000-0000-0000-000000000003"


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
    Migration(
        version=3,
        name="processing_operation_provenance",
        statements=(
            """CREATE TABLE processing_operations (
                id TEXT PRIMARY KEY,
                operation_type TEXT NOT NULL,
                status TEXT NOT NULL,
                stage TEXT NOT NULL,
                input_bytes INTEGER NOT NULL,
                pose_sequence_id TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                duration_ms INTEGER,
                error_code TEXT,
                error_detail TEXT
            )""",
            (
                "CREATE INDEX idx_processing_operations_started_at "
                "ON processing_operations(started_at DESC)"
            ),
        ),
    ),
    Migration(
        version=4,
        name="canonical_knee_evidence_graph",
        statements=(
            """CREATE TABLE subjects (
                id TEXT PRIMARY KEY,
                research_code TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE knees (
                id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
                laterality TEXT NOT NULL CHECK (laterality IN ('left', 'right')),
                created_at TEXT NOT NULL,
                UNIQUE (subject_id, laterality)
            )""",
            """CREATE TABLE episodes (
                id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
                episode_type TEXT NOT NULL,
                label TEXT NOT NULL,
                started_at TEXT,
                ended_at TEXT,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE timepoints (
                id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
                episode_id TEXT REFERENCES episodes(id),
                observed_at TEXT NOT NULL,
                label TEXT NOT NULL,
                legacy_session_id TEXT UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE observations (
                id TEXT PRIMARY KEY,
                timepoint_id TEXT NOT NULL REFERENCES timepoints(id) ON DELETE CASCADE,
                modality TEXT NOT NULL,
                source_artifact_reference TEXT NOT NULL,
                source_sha256 TEXT,
                acquisition_manifest_json TEXT NOT NULL,
                authorization_json TEXT NOT NULL,
                quality_json TEXT NOT NULL,
                immutable INTEGER NOT NULL CHECK (immutable = 1),
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE observation_knees (
                observation_id TEXT NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
                knee_id TEXT NOT NULL REFERENCES knees(id),
                PRIMARY KEY (observation_id, knee_id)
            )""",
            """CREATE TABLE annotations (
                id TEXT PRIMARY KEY,
                observation_id TEXT NOT NULL REFERENCES observations(id),
                annotation_type TEXT NOT NULL,
                version TEXT NOT NULL,
                author_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                review_state TEXT NOT NULL,
                supersedes_id TEXT REFERENCES annotations(id),
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE reconstructions (
                id TEXT PRIMARY KEY,
                knee_id TEXT NOT NULL REFERENCES knees(id),
                timepoint_id TEXT NOT NULL REFERENCES timepoints(id),
                version TEXT NOT NULL,
                geometry_class TEXT NOT NULL,
                structures_json TEXT NOT NULL,
                artifact_references_json TEXT NOT NULL,
                coordinate_system_json TEXT NOT NULL,
                review_state TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE registrations (
                id TEXT PRIMARY KEY,
                source_reference TEXT NOT NULL,
                target_reference TEXT NOT NULL,
                source_coordinate_system_json TEXT NOT NULL,
                target_coordinate_system_json TEXT NOT NULL,
                transform_json TEXT NOT NULL,
                method TEXT NOT NULL,
                coverage_json TEXT NOT NULL,
                error_json TEXT NOT NULL,
                uncertainty_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE derivations (
                id TEXT PRIMARY KEY,
                derivation_type TEXT NOT NULL,
                inputs_json TEXT NOT NULL,
                outputs_json TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                algorithm_version TEXT NOT NULL,
                configuration_json TEXT NOT NULL,
                code_revision TEXT NOT NULL,
                environment_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE virtual_experiments (
                id TEXT PRIMARY KEY,
                knee_id TEXT NOT NULL REFERENCES knees(id),
                timepoint_id TEXT NOT NULL REFERENCES timepoints(id),
                definition_version TEXT NOT NULL,
                definition_json TEXT NOT NULL,
                validation_tier TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE simulation_results (
                id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL REFERENCES virtual_experiments(id),
                status TEXT NOT NULL,
                outputs_json TEXT NOT NULL,
                sensitivity_json TEXT NOT NULL,
                validation_evidence_json TEXT NOT NULL,
                artifact_references_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""",
            (
                "INSERT INTO subjects (id, research_code, created_at) "
                f"VALUES ('{DEFAULT_RESEARCH_SUBJECT_ID}', 'LOCAL-RESEARCH-SUBJECT', "
                "CURRENT_TIMESTAMP)"
            ),
            (
                "INSERT INTO knees (id, subject_id, laterality, created_at) "
                f"VALUES ('{DEFAULT_LEFT_KNEE_ID}', '{DEFAULT_RESEARCH_SUBJECT_ID}', "
                "'left', CURRENT_TIMESTAMP)"
            ),
            (
                "INSERT INTO knees (id, subject_id, laterality, created_at) "
                f"VALUES ('{DEFAULT_RIGHT_KNEE_ID}', '{DEFAULT_RESEARCH_SUBJECT_ID}', "
                "'right', CURRENT_TIMESTAMP)"
            ),
            (
                "INSERT INTO timepoints "
                "(id, subject_id, episode_id, observed_at, label, legacy_session_id, created_at) "
                f"SELECT id, '{DEFAULT_RESEARCH_SUBJECT_ID}', NULL, recorded_at, "
                "'Migrated squat session', id, created_at FROM sessions"
            ),
            """INSERT INTO observations
                (id, timepoint_id, modality, source_artifact_reference, source_sha256,
                 acquisition_manifest_json, authorization_json, quality_json,
                 immutable, created_at)
                SELECT recordings.id, sessions.id, 'video', recordings.storage_reference, NULL,
                       '{"migration":"legacy-session-v1","protocol":"squat"}',
                       '{"status":"not-recorded","restriction":"research-only"}',
                       '{"status":"legacy-or-derived"}', 1, sessions.created_at
                FROM sessions JOIN recordings ON recordings.session_id = sessions.id""",
            (
                "INSERT INTO observation_knees (observation_id, knee_id) "
                f"SELECT id, '{DEFAULT_LEFT_KNEE_ID}' FROM observations"
            ),
            (
                "INSERT INTO observation_knees (observation_id, knee_id) "
                f"SELECT id, '{DEFAULT_RIGHT_KNEE_ID}' FROM observations"
            ),
            "CREATE INDEX idx_timepoints_subject_observed ON timepoints(subject_id, observed_at)",
            "CREATE INDEX idx_observations_timepoint ON observations(timepoint_id)",
            "CREATE INDEX idx_annotations_observation ON annotations(observation_id, created_at)",
            "CREATE INDEX idx_derivations_created ON derivations(created_at)",
        ),
    ),
    Migration(
        version=5,
        name="durable_local_jobs",
        statements=(
            """CREATE TABLE jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL,
                progress REAL NOT NULL,
                request_json TEXT NOT NULL,
                result_artifact_reference TEXT,
                logs_json TEXT NOT NULL,
                attempts INTEGER NOT NULL,
                cancel_requested INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_detail TEXT
            )""",
            "CREATE INDEX idx_jobs_status_created ON jobs(status, created_at)",
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
