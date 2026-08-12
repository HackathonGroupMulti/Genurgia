from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RegistrationUncertaintyV1(BaseModel):
    method: Literal["synthetic-perturbation", "bootstrap", "not-evaluated"]
    translation_95_mm: float | None = Field(default=None, ge=0)
    rotation_95_degrees: float | None = Field(default=None, ge=0)
    explanation: str = Field(min_length=1)


class FunctionalMotionFrameV1(BaseModel):
    timestamp_ms: float = Field(ge=0)
    anatomy_from_capture_transform: list[list[float]]
    landmark_residual_rms_mm: float = Field(ge=0)
    triangulated_landmark_count: int = Field(ge=3)
    confidence: float = Field(ge=0, le=1)
    excluded: bool = False
    exclusion_reason: str | None = None

    @model_validator(mode="after")
    def valid_transform_and_exclusion(self) -> "FunctionalMotionFrameV1":
        if len(self.anatomy_from_capture_transform) != 4 or any(
            len(row) != 4 for row in self.anatomy_from_capture_transform
        ):
            raise ValueError("Functional motion transform must be 4x4.")
        if self.excluded != (self.exclusion_reason is not None):
            raise ValueError("Excluded frames require exactly one exclusion reason.")
        return self


class FunctionalRegistrationResultV1(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    method: Literal["calibrated-dlt-kabsch-v1"] = "calibrated-dlt-kabsch-v1"
    source_coordinate_system: Literal["capture-volume-right-handed-mm"]
    target_coordinate_system: Literal["dicom-patient-lps-mm"]
    calibration_transform: list[list[float]]
    frames: list[FunctionalMotionFrameV1]
    projected_landmark_residual_rms_mm: float = Field(ge=0)
    coverage_ratio: float = Field(ge=0, le=1)
    uncertainty: RegistrationUncertaintyV1
    validation_tier: Literal["synthetic", "paired-laboratory", "independent"]


class ArthroscopyCorrespondenceV1(BaseModel):
    anatomy_landmark: str = Field(min_length=1)
    anatomy_position_mm: tuple[float, float, float]
    image_position_px: tuple[float, float]
    author: str = Field(min_length=1)


class ArthroscopyOverlayResultV1(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    method: Literal["expert-seed-pnp-v1"] = "expert-seed-pnp-v1"
    correspondences: list[ArthroscopyCorrespondenceV1] = Field(min_length=4)
    anatomy_from_camera_transform: list[list[float]]
    rms_reprojection_error_px: float = Field(ge=0)
    visible_coverage_ratio: float = Field(ge=0, le=1)
    uncertainty: RegistrationUncertaintyV1
    gate_status: Literal["pass", "fail"]


class ArthroscopyRefinementGateV1(BaseModel):
    overlay_registration_id: str = Field(min_length=1)
    calibrated: bool
    parallax_sufficient: bool
    coverage_ratio: float = Field(ge=0, le=1)
    residual_rms_px: float = Field(ge=0)
    residual_threshold_px: float = Field(gt=0)
    output_reconstruction_version: str = Field(min_length=1)
    decision: Literal["create-new-reconstruction", "refuse"]

    @model_validator(mode="after")
    def enforce_refinement_gate(self) -> "ArthroscopyRefinementGateV1":
        supported = (
            self.calibrated
            and self.parallax_sufficient
            and self.coverage_ratio > 0
            and self.residual_rms_px <= self.residual_threshold_px
        )
        if self.decision == "create-new-reconstruction" and not supported:
            raise ValueError("Unsupported arthroscopy geometry refinement must be refused.")
        return self


class TissueScoreAnnotationV1(BaseModel):
    taxonomy_version: str = Field(min_length=1)
    expert_labels: dict[str, str]
    adjudicated_labels: dict[str, str] | None = None
    inter_rater_result: dict[str, float]
    automated: bool = False
    diagnostic_claim: Literal[False] = False

    @model_validator(mode="after")
    def preserve_independent_labels(self) -> "TissueScoreAnnotationV1":
        if len(self.expert_labels) < 2:
            raise ValueError("Research tissue scoring requires at least two expert labels.")
        return self
