from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.evidence import Reconstruction

KneeStructure = Literal[
    "femur",
    "tibia",
    "fibula",
    "patella",
    "femoral_cartilage",
    "medial_tibial_cartilage",
    "lateral_tibial_cartilage",
    "patellar_cartilage",
    "medial_meniscus",
    "lateral_meniscus",
    "acl",
    "pcl",
    "mcl",
    "lcl",
    "quadriceps_tendon",
    "patellar_tendon",
    "quadriceps_musculotendon",
    "medial_hamstrings_musculotendon",
    "lateral_hamstrings_musculotendon",
    "medial_gastrocnemius_musculotendon",
    "lateral_gastrocnemius_musculotendon",
    "popliteus_musculotendon",
]

REQUIRED_KNEE_STRUCTURES = tuple(KneeStructure.__args__)


class StructureLabelV1(BaseModel):
    structure: KneeStructure
    label_value: int = Field(gt=0)


class AnatomicalLandmarkV1(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    structure: KneeStructure
    position_mm: tuple[float, float, float]
    author: str = Field(min_length=1)
    review_state: Literal["approved"]


class CorrectionEventV1(BaseModel):
    sequence: int = Field(gt=0)
    author: str = Field(min_length=1)
    structures: list[KneeStructure] = Field(min_length=1)
    description: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    result_version: str = Field(min_length=1)


class IndependentReviewV1(BaseModel):
    primary_reviewer: str = Field(min_length=1)
    independent_reviewer: str = Field(min_length=1)
    review_protocol: Literal["manual-segmentation-independent-review-v1"]
    decision: Literal["approved", "changes_requested"]
    notes: str = Field(min_length=1)

    @model_validator(mode="after")
    def reviewers_differ(self) -> "IndependentReviewV1":
        if self.primary_reviewer == self.independent_reviewer:
            raise ValueError("Independent review requires a different reviewer.")
        return self


class ThresholdProfileV1(BaseModel):
    profile_id: str = Field(min_length=1)
    approval_state: Literal["draft", "approved"]
    approving_authority: str | None = None
    thresholds_by_structure: dict[KneeStructure, dict[str, float]]

    @model_validator(mode="after")
    def approval_is_attributed(self) -> "ThresholdProfileV1":
        if self.approval_state == "approved" and not self.approving_authority:
            raise ValueError("An approved threshold profile requires an authority.")
        if set(self.thresholds_by_structure) != set(REQUIRED_KNEE_STRUCTURES):
            raise ValueError("Thresholds must cover every required knee structure.")
        required_metrics = {"dice_min", "asd_max_mm", "hd95_max_mm"}
        if any(set(values) != required_metrics for values in self.thresholds_by_structure.values()):
            raise ValueError("Each threshold requires dice_min, asd_max_mm, and hd95_max_mm.")
        for values in self.thresholds_by_structure.values():
            if not 0 <= values["dice_min"] <= 1:
                raise ValueError("dice_min must be within [0, 1].")
            if values["asd_max_mm"] < 0 or values["hd95_max_mm"] < 0:
                raise ValueError("Surface-distance thresholds cannot be negative.")
        return self


class ManualReconstructionPackageV1(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    source_mri_observation_id: UUID
    knee_id: UUID
    timepoint_id: UUID
    version: str = Field(min_length=1)
    geometry_class: Literal["expert-reviewed"] = "expert-reviewed"
    coordinate_system: Literal["dicom-patient-lps-mm"] = "dicom-patient-lps-mm"
    voxel_spacing_mm: tuple[float, float, float]
    structure_labels: list[StructureLabelV1]
    landmarks: list[AnatomicalLandmarkV1] = Field(min_length=1)
    correction_history: list[CorrectionEventV1]
    independent_review: IndependentReviewV1
    threshold_profile: ThresholdProfileV1
    label_map_format: Literal["numpy-npz-labels-v1"] = "numpy-npz-labels-v1"
    computational_volume_format: Literal["numpy-npz-volume-v1"] = "numpy-npz-volume-v1"
    scientific_mesh_format: Literal["ply-per-structure-v1"] = "ply-per-structure-v1"
    web_mesh_format: Literal["glb-per-structure-v1"] = "glb-per-structure-v1"

    @model_validator(mode="after")
    def complete_structure_set(self) -> "ManualReconstructionPackageV1":
        if any(value <= 0 for value in self.voxel_spacing_mm):
            raise ValueError("Voxel spacing must contain positive millimetre values.")
        structures = [item.structure for item in self.structure_labels]
        if len(structures) != len(set(structures)) or set(structures) != set(
            REQUIRED_KNEE_STRUCTURES
        ):
            raise ValueError("The package must label every required structure exactly once.")
        labels = [item.label_value for item in self.structure_labels]
        if len(labels) != len(set(labels)):
            raise ValueError("Structure label values must be unique.")
        return self


class StructureQualityV1(BaseModel):
    structure: KneeStructure
    dice_coefficient: float = Field(ge=0, le=1)
    average_symmetric_surface_distance_mm: float = Field(ge=0)
    hausdorff_95_mm: float = Field(ge=0)
    reference_voxels: int = Field(gt=0)
    candidate_voxels: int = Field(gt=0)
    acceptance: Literal["pass", "fail", "not-evaluated"]


class ReconstructionQualityReportV1(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    algorithm_version: Literal["label-map-surface-agreement-v1"] = (
        "label-map-surface-agreement-v1"
    )
    structures: list[StructureQualityV1]
    inter_rater_evaluation_present: bool
    threshold_profile_id: str
    threshold_approval_state: Literal["draft", "approved"]
    validation_status: Literal["accepted", "rejected", "thresholds-unapproved"]


class ReconstructionImportResultV1(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    reconstruction: Reconstruction
    package: ManualReconstructionPackageV1
    quality: ReconstructionQualityReportV1
    artifact_integrity: list[dict[str, str | int | bool | None]]
    evidence_class: Literal["expert-reviewed-reconstruction"] = (
        "expert-reviewed-reconstruction"
    )
