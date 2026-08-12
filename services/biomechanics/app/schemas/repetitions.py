from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

REPETITION_SCHEMA_VERSION = "1.1.0"
REPETITION_ANALYSIS_VERSION = "squat-repetition-analysis-v2"


class SquatPhaseModel(BaseModel):
    algorithm_version: Literal["bilateral-squat-state-machine-v1"]
    phase_states: list[Literal["standing", "descending", "bottom", "ascending"]]
    standing_max_degrees: float
    descent_start_min_degrees: float
    bottom_min_degrees: float
    bottom_exit_max_degrees: float
    minimum_duration_ms: int = Field(gt=0)
    maximum_duration_ms: int = Field(gt=0)
    maximum_gap_ms: int = Field(ge=0)
    minimum_side_rom_degrees: float = Field(ge=0)
    behavior: str


class SquatRepetition(BaseModel):
    repetition_index: int = Field(gt=0)
    start_timestamp_ms: int = Field(ge=0)
    bottom_timestamp_ms: int = Field(ge=0)
    end_timestamp_ms: int = Field(ge=0)
    duration_ms: int = Field(ge=0)
    left_max_flexion_degrees: float
    right_max_flexion_degrees: float
    left_rom_degrees: float = Field(ge=0)
    right_rom_degrees: float = Field(ge=0)
    mean_rom_degrees: float = Field(ge=0)
    signed_rom_difference_degrees: float
    absolute_rom_difference_degrees: float = Field(ge=0)
    signed_max_flexion_difference_degrees: float
    absolute_max_flexion_difference_degrees: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


class SquatRepetitionAnalysis(BaseModel):
    schema_version: Literal["1.1.0"] = REPETITION_SCHEMA_VERSION
    analysis_version: Literal["squat-repetition-analysis-v2"] = REPETITION_ANALYSIS_VERSION
    source_pose_sequence_id: UUID
    source_knee_flexion_analysis_version: Literal["knee-flexion-analysis-v1"]
    exercise: Literal["squat"] = "squat"
    angle_unit: Literal["degree"] = "degree"
    bilateral_difference_convention: Literal["left-minus-right-v1"] = "left-minus-right-v1"
    phase_model: SquatPhaseModel
    repetitions: list[SquatRepetition]
    artifact_reference: str
