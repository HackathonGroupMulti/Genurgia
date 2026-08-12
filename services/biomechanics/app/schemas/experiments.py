from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class SourcedValueV1(BaseModel):
    name: str = Field(min_length=1)
    value: float | list[float] | str
    unit: str = Field(min_length=1)
    source: str = Field(min_length=1)
    range: tuple[float, float] | None = None
    individual_measurement: bool


class SensitivityConfigurationV1(BaseModel):
    parameters: list[str]
    method: Literal["one-at-a-time", "monte-carlo", "none"]
    samples: int = Field(ge=0)


class ExperimentDefinitionV1(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    experiment_type: Literal["anatomical-motion-replay"]
    anatomy_reconstruction_id: str = Field(min_length=1)
    motion_registration_id: str = Field(min_length=1)
    immutable_input_hashes: dict[str, str]
    coordinate_systems: dict[str, str]
    transforms: dict[str, list[list[float]]]
    properties: list[SourcedValueV1]
    loading_conditions: list[SourcedValueV1]
    boundary_conditions: list[SourcedValueV1]
    software_versions: dict[str, str]
    container_versions: dict[str, str]
    requested_outputs: list[str] = Field(min_length=1)
    sensitivity: SensitivityConfigurationV1
    validation_tier: Literal["synthetic", "integration", "research", "independent"]

    @model_validator(mode="after")
    def validate_hashes_and_sensitivity(self) -> "ExperimentDefinitionV1":
        if not self.immutable_input_hashes or any(
            len(value) != 64 or any(char not in "0123456789abcdef" for char in value)
            for value in self.immutable_input_hashes.values()
        ):
            raise ValueError("Every immutable experiment input requires a lowercase SHA-256.")
        if self.sensitivity.method == "none" and self.sensitivity.samples != 0:
            raise ValueError("Sensitivity method none requires zero samples.")
        return self


class MotionReplayFrameV1(BaseModel):
    timestamp_ms: float = Field(ge=0)
    transform: list[list[float]]
    projected_landmark_residual_mm: float = Field(ge=0)
    transform_uncertainty_mm: float = Field(ge=0)
    excluded: bool
    exclusion_reason: str | None = None
    anatomical_constraint_violations: list[str]

    @model_validator(mode="after")
    def validate_frame(self) -> "MotionReplayFrameV1":
        if len(self.transform) != 4 or any(len(row) != 4 for row in self.transform):
            raise ValueError("Motion replay frame transform must be 4x4.")
        if self.excluded != (self.exclusion_reason is not None):
            raise ValueError("Excluded replay frames require exactly one reason.")
        return self


class MotionReplayRequestV1(BaseModel):
    experiment: ExperimentDefinitionV1
    frames: list[MotionReplayFrameV1] = Field(min_length=1)


class MotionReplayResultV1(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    experiment_definition_sha256: str
    frame_count: int = Field(gt=0)
    included_frame_count: int = Field(ge=0)
    excluded_intervals: list[dict[str, Any]]
    residual_rms_mm: float | None = Field(default=None, ge=0)
    maximum_transform_uncertainty_mm: float = Field(ge=0)
    anatomical_constraint_violations: list[dict[str, Any]]
    registration_sensitivity: dict[str, Any]
    validation_tier: Literal["synthetic", "integration", "research", "independent"]
