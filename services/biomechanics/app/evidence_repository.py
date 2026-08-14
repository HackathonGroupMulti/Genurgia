"""Canonical additive knee-evidence persistence over the local SQLite database."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel

from app.migrations import migrate
from app.schemas.evidence import (
    Annotation,
    AnnotationCreate,
    Derivation,
    DerivationCreate,
    Episode,
    EpisodeCreate,
    Knee,
    Observation,
    ObservationCreate,
    Reconstruction,
    ReconstructionCreate,
    Registration,
    RegistrationCreate,
    SimulationModel,
    SimulationModelCreate,
    SimulationResult,
    SimulationResultCreate,
    Subject,
    SubjectCreate,
    Timepoint,
    TimepointCreate,
    VirtualExperiment,
    VirtualExperimentCreate,
)
from app.storage import LocalArtifactStore

Model = TypeVar("Model", bound=BaseModel)


class EvidenceNotFound(LookupError):
    pass


class EvidenceConflict(ValueError):
    pass


class SQLiteEvidenceRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path.resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            migrate(connection)

    def create_subject(self, request: SubjectCreate) -> Subject:
        subject_id = uuid4()
        now = _now()
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO subjects VALUES (?, ?, ?)",
                    (str(subject_id), request.research_code, now),
                )
                connection.executemany(
                    "INSERT INTO knees VALUES (?, ?, ?, ?)",
                    (
                        (str(uuid4()), str(subject_id), "left", now),
                        (str(uuid4()), str(subject_id), "right", now),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise EvidenceConflict("Research code already exists.") from error
        return Subject(id=subject_id, research_code=request.research_code, created_at=now)

    def list_subjects(self) -> list[Subject]:
        return self._models("SELECT * FROM subjects ORDER BY created_at", Subject)

    def reconcile_legacy_source_hashes(self, artifacts: LocalArtifactStore) -> int:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT observations.id, observations.source_artifact_reference,
                          pose_sequences.id AS bundle_id
                   FROM observations
                   JOIN recordings ON recordings.id = observations.id
                   JOIN pose_sequences ON pose_sequences.recording_id = recordings.id
                   WHERE observations.source_sha256 IS NULL"""
            ).fetchall()
            updates: list[tuple[str, str]] = []
            for row in rows:
                filename = Path(row["source_artifact_reference"]).name
                verified = next(
                    (
                        item
                        for item in artifacts.verify_bundle(UUID(row["bundle_id"]))
                        if item["filename"] == filename and item["integrity"] == "verified"
                    ),
                    None,
                )
                if verified is not None:
                    updates.append((verified["sha256"], row["id"]))
            connection.executemany(
                "UPDATE observations SET source_sha256 = ? WHERE id = ?",
                updates,
            )
        return len(updates)

    def list_knees(self, subject_id: UUID | None = None) -> list[Knee]:
        if subject_id is None:
            return self._models("SELECT * FROM knees ORDER BY subject_id, laterality", Knee)
        return self._models(
            "SELECT * FROM knees WHERE subject_id = ? ORDER BY laterality",
            Knee,
            (str(subject_id),),
        )

    def get_knee(self, knee_id: UUID) -> Knee:
        models = self._models("SELECT * FROM knees WHERE id = ?", Knee, (str(knee_id),))
        if not models:
            raise EvidenceNotFound(f"Knee {knee_id} was not found.")
        return models[0]

    def create_episode(self, request: EpisodeCreate) -> Episode:
        episode_id = uuid4()
        now = _now()
        self._execute_create(
            """INSERT INTO episodes
            (id, subject_id, episode_type, label, started_at, ended_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                str(episode_id),
                str(request.subject_id),
                request.episode_type,
                request.label,
                _iso(request.started_at),
                _iso(request.ended_at),
                now,
            ),
            "Episode subject does not exist.",
        )
        return Episode(id=episode_id, created_at=now, **request.model_dump())

    def list_episodes(self, subject_id: UUID | None = None) -> list[Episode]:
        return self._models(
            "SELECT * FROM episodes"
            + (" WHERE subject_id = ?" if subject_id else "")
            + " ORDER BY created_at",
            Episode,
            (str(subject_id),) if subject_id else (),
        )

    def create_timepoint(self, request: TimepointCreate) -> Timepoint:
        if request.episode_id is not None:
            episode = self._row("SELECT subject_id FROM episodes WHERE id = ?", request.episode_id)
            if episode["subject_id"] != str(request.subject_id):
                raise EvidenceConflict("Episode and timepoint subjects differ.")
        timepoint_id = uuid4()
        now = _now()
        self._execute_create(
            """INSERT INTO timepoints
            (id, subject_id, episode_id, observed_at, label, legacy_session_id, created_at)
            VALUES (?, ?, ?, ?, ?, NULL, ?)""",
            (
                str(timepoint_id),
                str(request.subject_id),
                str(request.episode_id) if request.episode_id else None,
                request.observed_at.isoformat(),
                request.label,
                now,
            ),
            "Timepoint subject or episode does not exist.",
        )
        return Timepoint(
            id=timepoint_id,
            legacy_session_id=None,
            created_at=now,
            **request.model_dump(),
        )

    def list_timepoints(self, subject_id: UUID | None = None) -> list[Timepoint]:
        return self._models(
            "SELECT * FROM timepoints"
            + (" WHERE subject_id = ?" if subject_id else "")
            + " ORDER BY observed_at",
            Timepoint,
            (str(subject_id),) if subject_id else (),
        )

    def create_observation(
        self,
        request: ObservationCreate,
        *,
        observation_id: UUID | None = None,
    ) -> Observation:
        timepoint = self._row(
            "SELECT subject_id FROM timepoints WHERE id = ?",
            request.timepoint_id,
        )
        unique_targets = list(dict.fromkeys(request.knee_target_ids))
        with self._connect() as connection:
            placeholders = ",".join("?" for _ in unique_targets)
            knees = connection.execute(
                f"SELECT id, subject_id FROM knees WHERE id IN ({placeholders})",
                tuple(str(knee_id) for knee_id in unique_targets),
            ).fetchall()
            if len(knees) != len(unique_targets):
                raise EvidenceConflict("One or more knee targets do not exist.")
            if any(knee["subject_id"] != timepoint["subject_id"] for knee in knees):
                raise EvidenceConflict("Observation timepoint and knee subjects differ.")
            observation_id = observation_id or uuid4()
            now = _now()
            connection.execute(
                """INSERT INTO observations
                (id, timepoint_id, modality, source_artifact_reference, source_sha256,
                 acquisition_manifest_json, authorization_json, quality_json,
                 immutable, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                (
                    str(observation_id),
                    str(request.timepoint_id),
                    request.modality,
                    request.source_artifact_reference,
                    request.source_sha256,
                    _json(request.acquisition_manifest),
                    _json(request.authorization),
                    _json(request.quality),
                    now,
                ),
            )
            connection.executemany(
                "INSERT INTO observation_knees VALUES (?, ?)",
                ((str(observation_id), str(knee_id)) for knee_id in unique_targets),
            )
        return Observation(
            id=observation_id,
            immutable=True,
            created_at=now,
            **request.model_dump(exclude={"knee_target_ids"}),
            knee_target_ids=unique_targets,
        )

    def get_observation(self, observation_id: UUID) -> Observation:
        rows = self._observation_rows("WHERE observations.id = ?", (str(observation_id),))
        if not rows:
            raise EvidenceNotFound(f"Observation {observation_id} was not found.")
        return rows[0]

    def list_observations(self, timepoint_id: UUID | None = None) -> list[Observation]:
        clause = "WHERE observations.timepoint_id = ?" if timepoint_id else ""
        parameters = (str(timepoint_id),) if timepoint_id else ()
        return self._observation_rows(clause, parameters)

    def create_annotation(self, request: AnnotationCreate) -> Annotation:
        if request.supersedes_id is not None:
            prior = self._row(
                "SELECT observation_id FROM annotations WHERE id = ?",
                request.supersedes_id,
            )
            if prior["observation_id"] != str(request.observation_id):
                raise EvidenceConflict("Superseded annotation belongs to another observation.")
        identifier, now = self._json_create(
            """INSERT INTO annotations
            (id, observation_id, annotation_type, version, author_type, payload_json,
             review_state, supersedes_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(request.observation_id),
                request.annotation_type,
                request.version,
                request.author_type,
                _json(request.payload),
                request.review_state,
                str(request.supersedes_id) if request.supersedes_id else None,
            ),
        )
        return Annotation(id=identifier, created_at=now, **request.model_dump())

    def list_annotations(self, observation_id: UUID | None = None) -> list[Annotation]:
        return self._json_models(
            "SELECT * FROM annotations"
            + (" WHERE observation_id = ?" if observation_id else "")
            + " ORDER BY created_at",
            Annotation,
            {"payload_json": "payload"},
            (str(observation_id),) if observation_id else (),
        )

    def create_reconstruction(
        self,
        request: ReconstructionCreate,
        *,
        reconstruction_id: UUID | None = None,
    ) -> Reconstruction:
        self._ensure_knee_timepoint_subject(request.knee_id, request.timepoint_id)
        identifier, now = self._json_create(
            """INSERT INTO reconstructions
            (id, knee_id, timepoint_id, version, geometry_class, structures_json,
             artifact_references_json, coordinate_system_json, review_state, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(request.knee_id),
                str(request.timepoint_id),
                request.version,
                request.geometry_class,
                _json(request.structures),
                _json(request.artifact_references),
                _json(request.coordinate_system),
                request.review_state,
            ),
            identifier=reconstruction_id,
        )
        return Reconstruction(id=identifier, created_at=now, **request.model_dump())

    def list_reconstructions(self) -> list[Reconstruction]:
        return self._json_models(
            "SELECT * FROM reconstructions ORDER BY created_at",
            Reconstruction,
            {
                "structures_json": "structures",
                "artifact_references_json": "artifact_references",
                "coordinate_system_json": "coordinate_system",
            },
        )

    def get_reconstruction(self, reconstruction_id: UUID) -> Reconstruction:
        models = self._json_models(
            "SELECT * FROM reconstructions WHERE id = ?",
            Reconstruction,
            {
                "structures_json": "structures",
                "artifact_references_json": "artifact_references",
                "coordinate_system_json": "coordinate_system",
            },
            (str(reconstruction_id),),
        )
        if not models:
            raise EvidenceNotFound(f"Reconstruction {reconstruction_id} was not found.")
        return models[0]

    def create_simulation_model(
        self,
        request: SimulationModelCreate,
        *,
        simulation_model_id: UUID | None = None,
    ) -> SimulationModel:
        self.get_reconstruction(request.reconstruction_id)
        identifier, now = self._json_create(
            """INSERT INTO simulation_models
            (id, reconstruction_id, version, adapter_id, model_sha256, model_manifest_json,
             artifact_references_json, mesh_quality_json, included_structures_json,
             excluded_structures_json, validation_state, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(request.reconstruction_id),
                request.version,
                request.adapter_id,
                request.model_sha256,
                _json(request.model_manifest),
                _json(request.artifact_references),
                _json(request.mesh_quality),
                _json(request.included_structures),
                _json(request.excluded_structures),
                request.validation_state,
            ),
            identifier=simulation_model_id,
        )
        return SimulationModel(id=identifier, created_at=now, **request.model_dump())

    def create_simulation_model_and_derivation(
        self,
        model_request: SimulationModelCreate,
        derivation_request: DerivationCreate,
        *,
        simulation_model_id: UUID,
    ) -> tuple[SimulationModel, Derivation]:
        """Record an imported FE model and its provenance atomically."""
        derivation_id = uuid4()
        now = _now()
        derivation_request = derivation_request.model_copy(
            update={"outputs": [str(simulation_model_id)]}
        )
        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO simulation_models
                    (id, reconstruction_id, version, adapter_id, model_sha256,
                     model_manifest_json, artifact_references_json, mesh_quality_json,
                     included_structures_json, excluded_structures_json, validation_state,
                     created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(simulation_model_id),
                        str(model_request.reconstruction_id),
                        model_request.version,
                        model_request.adapter_id,
                        model_request.model_sha256,
                        _json(model_request.model_manifest),
                        _json(model_request.artifact_references),
                        _json(model_request.mesh_quality),
                        _json(model_request.included_structures),
                        _json(model_request.excluded_structures),
                        model_request.validation_state,
                        now,
                    ),
                )
                connection.execute(
                    """INSERT INTO derivations
                    (id, derivation_type, inputs_json, outputs_json, algorithm,
                     algorithm_version, configuration_json, code_revision,
                     environment_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(derivation_id),
                        derivation_request.derivation_type,
                        _json(derivation_request.inputs),
                        _json(derivation_request.outputs),
                        derivation_request.algorithm,
                        derivation_request.algorithm_version,
                        _json(derivation_request.configuration),
                        derivation_request.code_revision,
                        _json(derivation_request.environment),
                        now,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise EvidenceConflict(
                "Simulation model or derivation references missing evidence."
            ) from error
        return (
            SimulationModel(
                id=simulation_model_id,
                created_at=now,
                **model_request.model_dump(),
            ),
            Derivation(id=derivation_id, created_at=now, **derivation_request.model_dump()),
        )

    def get_simulation_model(self, simulation_model_id: UUID) -> SimulationModel:
        models = self._simulation_models(" WHERE id = ?", (str(simulation_model_id),))
        if not models:
            raise EvidenceNotFound(f"Simulation model {simulation_model_id} was not found.")
        return models[0]

    def list_simulation_models(self) -> list[SimulationModel]:
        return self._simulation_models()

    def _simulation_models(
        self, clause: str = "", parameters: tuple[Any, ...] = ()
    ) -> list[SimulationModel]:
        return self._json_models(
            "SELECT * FROM simulation_models" + clause + " ORDER BY created_at",
            SimulationModel,
            {
                "model_manifest_json": "model_manifest",
                "artifact_references_json": "artifact_references",
                "mesh_quality_json": "mesh_quality",
                "included_structures_json": "included_structures",
                "excluded_structures_json": "excluded_structures",
            },
            parameters,
        )

    def create_registration(self, request: RegistrationCreate) -> Registration:
        identifier, now = self._json_create(
            """INSERT INTO registrations
            (id, source_reference, target_reference, source_coordinate_system_json,
             target_coordinate_system_json, transform_json, method, coverage_json,
             error_json, uncertainty_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.source_reference,
                request.target_reference,
                _json(request.source_coordinate_system),
                _json(request.target_coordinate_system),
                _json(request.transform),
                request.method,
                _json(request.coverage),
                _json(request.error),
                _json(request.uncertainty),
            ),
        )
        return Registration(id=identifier, created_at=now, **request.model_dump())

    def list_registrations(self) -> list[Registration]:
        return self._json_models(
            "SELECT * FROM registrations ORDER BY created_at",
            Registration,
            {
                "source_coordinate_system_json": "source_coordinate_system",
                "target_coordinate_system_json": "target_coordinate_system",
                "transform_json": "transform",
                "coverage_json": "coverage",
                "error_json": "error",
                "uncertainty_json": "uncertainty",
            },
        )

    def create_derivation(self, request: DerivationCreate) -> Derivation:
        identifier, now = self._json_create(
            """INSERT INTO derivations
            (id, derivation_type, inputs_json, outputs_json, algorithm, algorithm_version,
             configuration_json, code_revision, environment_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.derivation_type,
                _json(request.inputs),
                _json(request.outputs),
                request.algorithm,
                request.algorithm_version,
                _json(request.configuration),
                request.code_revision,
                _json(request.environment),
            ),
        )
        return Derivation(id=identifier, created_at=now, **request.model_dump())

    def get_derivation(self, derivation_id: UUID) -> Derivation:
        models = self._json_models(
            "SELECT * FROM derivations WHERE id = ?",
            Derivation,
            {
                "inputs_json": "inputs",
                "outputs_json": "outputs",
                "configuration_json": "configuration",
                "environment_json": "environment",
            },
            (str(derivation_id),),
        )
        if not models:
            raise EvidenceNotFound(f"Derivation {derivation_id} was not found.")
        return models[0]

    def list_derivations(self) -> list[Derivation]:
        return self._json_models(
            "SELECT * FROM derivations ORDER BY created_at",
            Derivation,
            {
                "inputs_json": "inputs",
                "outputs_json": "outputs",
                "configuration_json": "configuration",
                "environment_json": "environment",
            },
        )

    def create_experiment(self, request: VirtualExperimentCreate) -> VirtualExperiment:
        self._ensure_knee_timepoint_subject(request.knee_id, request.timepoint_id)
        identifier, now = self._json_create(
            """INSERT INTO virtual_experiments
            (id, knee_id, timepoint_id, definition_version, definition_json,
             validation_tier, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                str(request.knee_id),
                str(request.timepoint_id),
                request.definition_version,
                _json(request.definition),
                request.validation_tier,
            ),
        )
        return VirtualExperiment(id=identifier, created_at=now, **request.model_dump())

    def list_experiments(self) -> list[VirtualExperiment]:
        return self._json_models(
            "SELECT * FROM virtual_experiments ORDER BY created_at",
            VirtualExperiment,
            {"definition_json": "definition"},
        )

    def get_experiment(self, experiment_id: UUID) -> VirtualExperiment:
        models = self._json_models(
            "SELECT * FROM virtual_experiments WHERE id = ?",
            VirtualExperiment,
            {"definition_json": "definition"},
            (str(experiment_id),),
        )
        if not models:
            raise EvidenceNotFound(f"Experiment {experiment_id} was not found.")
        return models[0]

    def create_simulation_result(self, request: SimulationResultCreate) -> SimulationResult:
        identifier, now = self._json_create(
            """INSERT INTO simulation_results
            (id, experiment_id, status, outputs_json, sensitivity_json,
             validation_evidence_json, artifact_references_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(request.experiment_id),
                request.status,
                _json(request.outputs),
                _json(request.sensitivity),
                _json(request.validation_evidence),
                _json(request.artifact_references),
            ),
        )
        return SimulationResult(id=identifier, created_at=now, **request.model_dump())

    def create_simulation_result_and_derivation(
        self,
        result_request: SimulationResultCreate,
        derivation_request: DerivationCreate,
    ) -> tuple[SimulationResult, Derivation]:
        """Record a published simulation result and its provenance atomically."""
        result_id = uuid4()
        derivation_id = uuid4()
        now = _now()
        derivation_request = derivation_request.model_copy(
            update={"outputs": [str(result_id)]}
        )
        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO simulation_results
                    (id, experiment_id, status, outputs_json, sensitivity_json,
                     validation_evidence_json, artifact_references_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(result_id),
                        str(result_request.experiment_id),
                        result_request.status,
                        _json(result_request.outputs),
                        _json(result_request.sensitivity),
                        _json(result_request.validation_evidence),
                        _json(result_request.artifact_references),
                        now,
                    ),
                )
                connection.execute(
                    """INSERT INTO derivations
                    (id, derivation_type, inputs_json, outputs_json, algorithm,
                     algorithm_version, configuration_json, code_revision,
                     environment_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(derivation_id),
                        derivation_request.derivation_type,
                        _json(derivation_request.inputs),
                        _json(derivation_request.outputs),
                        derivation_request.algorithm,
                        derivation_request.algorithm_version,
                        _json(derivation_request.configuration),
                        derivation_request.code_revision,
                        _json(derivation_request.environment),
                        now,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise EvidenceConflict(
                "Simulation result or derivation references missing evidence."
            ) from error
        return (
            SimulationResult(id=result_id, created_at=now, **result_request.model_dump()),
            Derivation(id=derivation_id, created_at=now, **derivation_request.model_dump()),
        )

    def list_simulation_results(self) -> list[SimulationResult]:
        return self._json_models(
            "SELECT * FROM simulation_results ORDER BY created_at",
            SimulationResult,
            {
                "outputs_json": "outputs",
                "sensitivity_json": "sensitivity",
                "validation_evidence_json": "validation_evidence",
                "artifact_references_json": "artifact_references",
            },
        )

    def _ensure_knee_timepoint_subject(self, knee_id: UUID, timepoint_id: UUID) -> None:
        row = self._row(
            """SELECT knees.subject_id AS knee_subject,
                      timepoints.subject_id AS timepoint_subject
               FROM knees, timepoints WHERE knees.id = ? AND timepoints.id = ?""",
            knee_id,
            timepoint_id,
        )
        if row["knee_subject"] != row["timepoint_subject"]:
            raise EvidenceConflict("Knee and timepoint subjects differ.")

    def _observation_rows(
        self,
        clause: str,
        parameters: tuple[Any, ...],
    ) -> list[Observation]:
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT observations.* FROM observations {clause} ORDER BY created_at",
                parameters,
            ).fetchall()
            return [
                Observation(
                    id=row["id"],
                    timepoint_id=row["timepoint_id"],
                    modality=row["modality"],
                    source_artifact_reference=row["source_artifact_reference"],
                    source_sha256=row["source_sha256"],
                    acquisition_manifest=json.loads(row["acquisition_manifest_json"]),
                    authorization=json.loads(row["authorization_json"]),
                    quality=json.loads(row["quality_json"]),
                    knee_target_ids=[
                        target["knee_id"]
                        for target in connection.execute(
                            "SELECT knee_id FROM observation_knees WHERE observation_id = ?",
                            (row["id"],),
                        ).fetchall()
                    ],
                    immutable=True,
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def _json_create(
        self,
        sql: str,
        values_without_id_and_created: tuple[Any, ...],
        *,
        identifier: UUID | None = None,
    ) -> tuple[UUID, str]:
        identifier = identifier or uuid4()
        now = _now()
        self._execute_create(
            sql,
            (str(identifier), *values_without_id_and_created, now),
            "Referenced canonical evidence does not exist.",
        )
        return identifier, now

    def _execute_create(self, sql: str, values: tuple[Any, ...], conflict: str) -> None:
        try:
            with self._connect() as connection:
                connection.execute(sql, values)
        except sqlite3.IntegrityError as error:
            raise EvidenceConflict(conflict) from error

    def _row(self, sql: str, *identifiers: UUID) -> sqlite3.Row:
        with self._connect() as connection:
            row = connection.execute(sql, tuple(str(item) for item in identifiers)).fetchone()
        if row is None:
            raise EvidenceNotFound("Referenced canonical evidence was not found.")
        return row

    def _models(
        self,
        sql: str,
        model: type[Model],
        parameters: tuple[Any, ...] = (),
    ) -> list[Model]:
        with self._connect() as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return [model.model_validate(dict(row)) for row in rows]

    def _json_models(
        self,
        sql: str,
        model: type[Model],
        fields: dict[str, str],
        parameters: tuple[Any, ...] = (),
    ) -> list[Model]:
        with self._connect() as connection:
            rows = connection.execute(sql, parameters).fetchall()
        values = []
        for row in rows:
            item = dict(row)
            for column, field in fields.items():
                item[field] = json.loads(item.pop(column))
            values.append(model.model_validate(item))
        return values

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


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)
