from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.pose import CoordinateConvention

KINEMATICS_SCHEMA_VERSION = "1.0.0"
KINEMATICS_ANALYSIS_VERSION = "knee-flexion-analysis-v1"

MeasurementQuality = Literal[
    "valid",
    "low_confidence",
    "missing_pose",
    "missing_landmark",
    "invalid_coordinate",
    "degenerate_geometry",
]


class KneeFlexionSample(BaseModel):
    timestamp_ms: int = Field(ge=0)
    value_degrees: float | None
    filtered_value_degrees: float | None
    confidence: float | None = Field(default=None, ge=0, le=1)
    quality: MeasurementQuality


class KneeFlexionSeries(BaseModel):
    joint: Literal["knee"] = "knee"
    side: Literal["left", "right"]
    metric: Literal["flexion"] = "flexion"
    unit: Literal["degree"] = "degree"
    samples: list[KneeFlexionSample]


class FilterDescription(BaseModel):
    name: Literal["centered-moving-average-v1"] = "centered-moving-average-v1"
    window_size: int = Field(gt=0)
    minimum_valid_values: int = Field(gt=0)
    behavior: str


class KneeFlexionAnalysis(BaseModel):
    schema_version: Literal["1.0.0"] = KINEMATICS_SCHEMA_VERSION
    analysis_version: Literal["knee-flexion-analysis-v1"] = KINEMATICS_ANALYSIS_VERSION
    calculation_version: Literal["knee-flexion-world-3d-v1"]
    source_pose_sequence_id: UUID
    source_pose_model: str
    source_pose_model_version: str
    coordinate_convention: CoordinateConvention
    minimum_measurement_confidence: float = Field(ge=0, le=1)
    filtering: FilterDescription
    series: list[KneeFlexionSeries] = Field(min_length=2, max_length=2)
    artifact_reference: str
