from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

JsonObject = dict[str, Any]


def _require_timezone(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise ValueError("Timestamp must include a UTC offset.")
    return value


class SubjectCreate(BaseModel):
    research_code: str = Field(pattern=r"^[A-Z0-9][A-Z0-9-]{2,63}$")
    deidentified_confirmed: Literal[True]


class Subject(BaseModel):
    id: UUID
    research_code: str
    created_at: datetime


class SubjectList(BaseModel):
    subjects: list[Subject]


class Knee(BaseModel):
    id: UUID
    subject_id: UUID
    laterality: Literal["left", "right"]
    created_at: datetime


class KneeList(BaseModel):
    knees: list[Knee]


class EpisodeCreate(BaseModel):
    subject_id: UUID
    episode_type: Literal["injury", "procedure", "study", "recovery", "other"]
    label: str = Field(min_length=1, max_length=200)
    started_at: datetime | None = None
    ended_at: datetime | None = None

    _started_timezone = field_validator("started_at")(_require_timezone)
    _ended_timezone = field_validator("ended_at")(_require_timezone)


class Episode(EpisodeCreate):
    id: UUID
    created_at: datetime


class EpisodeList(BaseModel):
    episodes: list[Episode]


class TimepointCreate(BaseModel):
    subject_id: UUID
    episode_id: UUID | None = None
    observed_at: datetime
    label: str = Field(min_length=1, max_length=200)

    _observed_timezone = field_validator("observed_at")(_require_timezone)


class Timepoint(TimepointCreate):
    id: UUID
    legacy_session_id: UUID | None = None
    created_at: datetime


class TimepointList(BaseModel):
    timepoints: list[Timepoint]


class ObservationCreate(BaseModel):
    timepoint_id: UUID
    modality: Literal["video", "mri", "arthroscopy", "sensor", "other"]
    source_artifact_reference: str = Field(min_length=1)
    source_sha256: str | None = Field(pattern=r"^[0-9a-f]{64}$")
    acquisition_manifest: JsonObject
    authorization: JsonObject
    quality: JsonObject
    knee_target_ids: list[UUID] = Field(min_length=1)


class Observation(ObservationCreate):
    id: UUID
    immutable: Literal[True] = True
    created_at: datetime


class ObservationList(BaseModel):
    observations: list[Observation]


class AnnotationCreate(BaseModel):
    observation_id: UUID
    annotation_type: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=100)
    author_type: Literal["machine", "expert", "adjudicated"]
    payload: JsonObject
    review_state: Literal["draft", "in_review", "approved", "rejected"] = "draft"
    supersedes_id: UUID | None = None


class Annotation(AnnotationCreate):
    id: UUID
    created_at: datetime


class AnnotationList(BaseModel):
    annotations: list[Annotation]


class ReconstructionCreate(BaseModel):
    knee_id: UUID
    timepoint_id: UUID
    version: str = Field(min_length=1)
    geometry_class: Literal[
        "generic", "fitted", "machine-segmented", "expert-reviewed", "patient-specific"
    ]
    structures: list[str] = Field(min_length=1)
    artifact_references: JsonObject
    coordinate_system: JsonObject
    review_state: Literal["draft", "in_review", "approved", "rejected"] = "draft"


class Reconstruction(ReconstructionCreate):
    id: UUID
    created_at: datetime


class ReconstructionList(BaseModel):
    reconstructions: list[Reconstruction]


class SimulationModelCreate(BaseModel):
    reconstruction_id: UUID
    version: str = Field(min_length=1, max_length=100)
    adapter_id: str = Field(min_length=1, max_length=100)
    model_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_manifest: JsonObject
    artifact_references: JsonObject
    mesh_quality: JsonObject
    included_structures: list[str] = Field(min_length=1)
    excluded_structures: list[str]
    validation_state: Literal["structurally-valid", "invalid"]


class SimulationModel(SimulationModelCreate):
    id: UUID
    created_at: datetime


class SimulationModelList(BaseModel):
    simulation_models: list[SimulationModel]


class RegistrationCreate(BaseModel):
    source_reference: str = Field(min_length=1)
    target_reference: str = Field(min_length=1)
    source_coordinate_system: JsonObject
    target_coordinate_system: JsonObject
    transform: list[list[float]]
    method: str = Field(min_length=1)
    coverage: JsonObject
    error: JsonObject
    uncertainty: JsonObject

    @model_validator(mode="after")
    def validate_homogeneous_transform(self) -> "RegistrationCreate":
        if len(self.transform) != 4 or any(len(row) != 4 for row in self.transform):
            raise ValueError("Registration transform must be a 4x4 matrix.")
        return self


class Registration(RegistrationCreate):
    id: UUID
    created_at: datetime


class RegistrationList(BaseModel):
    registrations: list[Registration]


class DerivationCreate(BaseModel):
    derivation_type: str = Field(min_length=1)
    inputs: list[str] = Field(min_length=1)
    outputs: list[str] = Field(min_length=1)
    algorithm: str = Field(min_length=1)
    algorithm_version: str = Field(min_length=1)
    configuration: JsonObject
    code_revision: str = Field(min_length=1)
    environment: JsonObject


class Derivation(DerivationCreate):
    id: UUID
    created_at: datetime


class DerivationList(BaseModel):
    derivations: list[Derivation]


class VirtualExperimentCreate(BaseModel):
    knee_id: UUID
    timepoint_id: UUID
    definition_version: str = Field(min_length=1)
    definition: JsonObject
    validation_tier: Literal["synthetic", "integration", "research", "independent"]


class VirtualExperiment(VirtualExperimentCreate):
    id: UUID
    created_at: datetime


class VirtualExperimentList(BaseModel):
    experiments: list[VirtualExperiment]


class SimulationResultCreate(BaseModel):
    experiment_id: UUID
    status: Literal["complete", "failed", "cancelled"]
    outputs: JsonObject
    sensitivity: JsonObject
    validation_evidence: JsonObject
    artifact_references: JsonObject


class SimulationResult(SimulationResultCreate):
    id: UUID
    created_at: datetime


class SimulationResultList(BaseModel):
    results: list[SimulationResult]
