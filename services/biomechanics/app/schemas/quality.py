from typing import Literal
from uuid import UUID

from pydantic import BaseModel

CAPTURE_QUALITY_SCHEMA_VERSION = "1.0.0"
CAPTURE_QUALITY_ANALYSIS_VERSION = "capture-quality-v1"


class CaptureQualitySignal(BaseModel):
    name: Literal[
        "decode_validity",
        "pose_detection_coverage",
        "bilateral_valid_knee_coverage",
        "maximum_unavailable_bilateral_interval",
        "required_landmark_framing_coverage",
        "complete_squat_cycle",
    ]
    value: float | bool | None
    unit: Literal["ratio", "millisecond", "count", "boolean"]
    status: Literal["pass", "warning", "fail", "unavailable"]
    criteria: str
    explanation: str


class CaptureQualityReport(BaseModel):
    schema_version: Literal["1.0.0"] = CAPTURE_QUALITY_SCHEMA_VERSION
    analysis_version: Literal["capture-quality-v1"] = CAPTURE_QUALITY_ANALYSIS_VERSION
    source_pose_sequence_id: UUID
    source_knee_flexion_analysis_version: Literal["knee-flexion-analysis-v1"]
    source_repetition_analysis_version: Literal["squat-repetition-analysis-v2"]
    protocol: Literal["squat"] = "squat"
    status: Literal["pass", "warning", "fail"]
    signals: list[CaptureQualitySignal]
    guidance: list[str]
    interpretation: str = (
        "Capture status describes whether the recording met versioned input criteria; "
        "it is not evidence of clinical accuracy."
    )
    artifact_reference: str
