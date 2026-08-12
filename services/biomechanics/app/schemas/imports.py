from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.evidence import Observation


class ImportQualitySignal(BaseModel):
    name: str
    status: Literal["pass", "warning", "fail"]
    value: float | int | str | bool | None = None
    unit: str | None = None
    explanation: str


class DeidentificationReportV1(BaseModel):
    profile: Literal["knee-twin-research-screen-v1"] = "knee-twin-research-screen-v1"
    dicom_ps3_15_conformance_claimed: Literal[False] = False
    direct_identifier_tags_checked: list[str]
    populated_direct_identifier_tags: list[str]
    status: Literal["pass", "fail"]
    explanation: str


class DicomSeriesManifestV1(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    modality: Literal["MRI"] = "MRI"
    study_instance_uid: str
    series_instance_uid: str
    frame_of_reference_uid: str
    sop_instance_uids: list[str]
    instance_count: int = Field(gt=0)
    rows: int = Field(gt=0)
    columns: int = Field(gt=0)
    pixel_spacing_mm: tuple[float, float]
    slice_spacing_mm: float | None = Field(default=None, gt=0)
    slice_thickness_mm: float | None = Field(default=None, gt=0)
    image_orientation_patient: tuple[float, float, float, float, float, float]
    first_image_position_patient_mm: tuple[float, float, float]
    last_image_position_patient_mm: tuple[float, float, float]
    coordinate_system: Literal["dicom-patient-lps-mm"] = "dicom-patient-lps-mm"
    dicom_laterality: Literal["left", "right", "unknown"]
    acquisition_datetime: str | None = None
    source_representation: Literal["immutable-dicom-zip"] = "immutable-dicom-zip"
    computational_volume_status: Literal["not-generated"] = "not-generated"
    deidentification: DeidentificationReportV1
    quality_signals: list[ImportQualitySignal]
    status: Literal["pass", "warning", "fail"]


class CameraIntrinsicsV1(BaseModel):
    matrix: list[list[float]]
    distortion_coefficients: list[float]
    calibration_error_px: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_matrix(self) -> "CameraIntrinsicsV1":
        if len(self.matrix) != 3 or any(len(row) != 3 for row in self.matrix):
            raise ValueError("The intrinsic matrix must be 3x3.")
        return self


class CameraExtrinsicsV1(BaseModel):
    capture_from_camera_transform: list[list[float]]
    calibration_error_mm: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_transform(self) -> "CameraExtrinsicsV1":
        transform = self.capture_from_camera_transform
        if len(transform) != 4 or any(len(row) != 4 for row in transform):
            raise ValueError("The extrinsic transform must be 4x4.")
        return self


class CameraCaptureV1(BaseModel):
    camera_id: str = Field(min_length=1, max_length=100)
    view: Literal["front", "rear", "left_side", "right_side"]
    width_px: int = Field(ge=1920)
    height_px: int = Field(ge=1080)
    fps: float = Field(ge=60)
    intrinsic: CameraIntrinsicsV1
    extrinsic: CameraExtrinsicsV1


class SynchronizationEventV1(BaseModel):
    method: Literal["visible-event"]
    event_description: str = Field(min_length=1)
    maximum_offset_ms: float = Field(ge=0)


class CaptureVolumeValidationV1(BaseModel):
    method: str = Field(min_length=1)
    rms_error_mm: float = Field(ge=0)
    validated_at: datetime


class AnatomicalCalibrationPoseV1(BaseModel):
    protocol: Literal["standard-anatomical-pose-v1"]
    visible_in_all_cameras: Literal[True]
    landmark_set: list[str] = Field(min_length=1)


class MultiViewCaptureInputV1(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    captured_at: datetime
    cameras: list[CameraCaptureV1]
    synchronization: SynchronizationEventV1
    capture_volume: CaptureVolumeValidationV1
    anatomical_calibration_pose: AnatomicalCalibrationPoseV1
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_camera_set(self) -> "MultiViewCaptureInputV1":
        if len(self.cameras) != 4:
            raise ValueError("Exactly four calibrated cameras are required.")
        if len({camera.camera_id for camera in self.cameras}) != 4:
            raise ValueError("Camera identifiers must be unique.")
        required = {"front", "rear", "left_side", "right_side"}
        if {camera.view for camera in self.cameras} != required:
            raise ValueError("Front, rear, left-side, and right-side views are required.")
        return self


class MultiViewCaptureManifestV1(MultiViewCaptureInputV1):
    protocol: Literal["calibrated-four-camera-rgb-v1"] = (
        "calibrated-four-camera-rgb-v1"
    )
    coordinate_system: Literal["capture-volume-right-handed-mm"] = (
        "capture-volume-right-handed-mm"
    )
    source_artifacts: dict[str, str]
    quality_signals: list[ImportQualitySignal]
    status: Literal["pass", "warning", "fail"]


class ArthroscopyVisibleRegionV1(BaseModel):
    start_ms: float = Field(ge=0)
    end_ms: float = Field(gt=0)
    anatomical_region: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_interval(self) -> "ArthroscopyVisibleRegionV1":
        if self.end_ms <= self.start_ms:
            raise ValueError("Visible-region end time must follow start time.")
        return self


class ArthroscopyImportMetadataV1(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    procedure_at: datetime
    scope_manufacturer: str = Field(min_length=1, max_length=200)
    scope_model: str = Field(min_length=1, max_length=200)
    scope_angle_degrees: float = Field(ge=0, le=180)
    camera_manufacturer: str = Field(min_length=1, max_length=200)
    camera_model: str = Field(min_length=1, max_length=200)
    calibration_method: str = Field(min_length=1, max_length=300)
    calibration_artifact_reference: str = Field(min_length=1)
    calibration_error_px: float = Field(ge=0)
    visible_regions: list[ArthroscopyVisibleRegionV1]
    notes: str | None = Field(default=None, max_length=1000)


class ArthroscopyManifestV1(ArthroscopyImportMetadataV1):
    video_width_px: int = Field(gt=0)
    video_height_px: int = Field(gt=0)
    fps: float = Field(gt=0)
    frame_count: int = Field(gt=0)
    duration_ms: float = Field(gt=0)
    timestamp_basis: Literal["decoded-frame-index-and-container-fps"] = (
        "decoded-frame-index-and-container-fps"
    )
    coordinate_system: Literal["arthroscope-image-pixels"] = "arthroscope-image-pixels"
    quality_signals: list[ImportQualitySignal]
    status: Literal["pass", "warning", "fail"]


AcquisitionManifestV1 = Annotated[
    DicomSeriesManifestV1 | ArthroscopyManifestV1 | MultiViewCaptureManifestV1,
    Field(union_mode="left_to_right"),
]


class ObservationImportResultV1(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    observation: Observation
    acquisition_manifest: AcquisitionManifestV1
    artifact_integrity: list[dict[str, str | int | bool | None]]
    execution: Literal["synchronous-local-import"] = "synchronous-local-import"
    job_runner_status: Literal["deferred-to-milestone-13"] = "deferred-to-milestone-13"
