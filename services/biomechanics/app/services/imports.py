import json
import math
import zipfile
from collections.abc import Sequence
from pathlib import Path
from statistics import median
from typing import Any
from uuid import UUID, uuid4

import cv2
import pydicom
from pydicom.errors import InvalidDicomError

from app.evidence_repository import SQLiteEvidenceRepository
from app.schemas.evidence import ObservationCreate
from app.schemas.imports import (
    ArthroscopyImportMetadataV1,
    ArthroscopyManifestV1,
    DeidentificationReportV1,
    DicomSeriesManifestV1,
    ImportQualitySignal,
    MultiViewCaptureInputV1,
    MultiViewCaptureManifestV1,
    ObservationImportResultV1,
)
from app.storage import LocalArtifactStore

MAX_ARCHIVE_MEMBERS = 20_000
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 8 * 1024 * 1024 * 1024
CONSISTENCY_TOLERANCE = 1e-4
SLICE_SPACING_RELATIVE_TOLERANCE = 0.05
DIRECT_IDENTIFIER_KEYWORDS = (
    "PatientName",
    "PatientID",
    "PatientBirthDate",
    "PatientAddress",
    "PatientTelephoneNumbers",
    "AccessionNumber",
    "ReferringPhysicianName",
)


class InvalidObservationImport(ValueError):
    pass


class ObservationImportService:
    def __init__(
        self,
        artifacts: LocalArtifactStore,
        evidence: SQLiteEvidenceRepository,
        max_upload_bytes: int,
    ) -> None:
        self._artifacts = artifacts
        self._evidence = evidence
        self.max_upload_bytes = max_upload_bytes

    def create_temporary_upload(self, extension: str) -> Path:
        return self._artifacts.create_temporary_upload(extension)

    def delete_temporary_upload(self, path: Path) -> None:
        self._artifacts.delete_temporary_upload(path)

    def import_mri_zip(
        self,
        source: Path,
        *,
        timepoint_id: UUID,
        knee_target_ids: list[UUID],
        authorization: dict[str, Any],
    ) -> ObservationImportResultV1:
        manifest = inspect_dicom_zip(source)
        if manifest.status == "fail":
            raise InvalidObservationImport("The DICOM series failed acquisition validation.")
        if manifest.dicom_laterality != "unknown":
            knee_lateralities = {
                str(knee.id): knee.laterality for knee in self._evidence.list_knees()
            }
            selected = [knee_lateralities.get(str(knee_id)) for knee_id in knee_target_ids]
            if selected != [manifest.dicom_laterality]:
                raise InvalidObservationImport(
                    "DICOM laterality must match exactly one selected knee target."
                )
        return self._publish(
            source_files={"source_dicom_series.zip": source},
            manifest=manifest,
            modality="mri",
            primary_filename="source_dicom_series.zip",
            timepoint_id=timepoint_id,
            knee_target_ids=knee_target_ids,
            authorization=authorization,
        )

    def import_arthroscopy(
        self,
        source: Path,
        metadata: ArthroscopyImportMetadataV1,
        *,
        timepoint_id: UUID,
        knee_target_ids: list[UUID],
        authorization: dict[str, Any],
    ) -> ObservationImportResultV1:
        width, height, fps, frame_count = inspect_video(source)
        duration_ms = frame_count / fps * 1000
        for region in metadata.visible_regions:
            if region.end_ms > duration_ms + 1:
                raise InvalidObservationImport(
                    "A visible-region annotation extends beyond the decoded video duration."
                )
        signals = [
            ImportQualitySignal(
                name="video_decode",
                status="pass",
                value=frame_count,
                unit="frames",
                explanation="The container opened and reported decodable frame metadata.",
            ),
            ImportQualitySignal(
                name="camera_calibration_evidence",
                status="pass",
                value=metadata.calibration_error_px,
                unit="px",
                explanation=(
                    "Calibration evidence and its reported image-space error were supplied; "
                    "the importer does not independently certify that calibration."
                ),
            ),
            ImportQualitySignal(
                name="visible_region_annotations",
                status="pass" if metadata.visible_regions else "warning",
                value=len(metadata.visible_regions),
                unit="intervals",
                explanation=(
                    "Expert-authored visible-region intervals were supplied."
                    if metadata.visible_regions
                    else "No visible-region intervals were supplied."
                ),
            ),
        ]
        manifest = ArthroscopyManifestV1(
            **metadata.model_dump(),
            video_width_px=width,
            video_height_px=height,
            fps=fps,
            frame_count=frame_count,
            duration_ms=duration_ms,
            quality_signals=signals,
            status="warning" if not metadata.visible_regions else "pass",
        )
        return self._publish(
            source_files={"source_arthroscopy.mp4": source},
            manifest=manifest,
            modality="arthroscopy",
            primary_filename="source_arthroscopy.mp4",
            timepoint_id=timepoint_id,
            knee_target_ids=knee_target_ids,
            authorization=authorization,
        )

    def import_multiview(
        self,
        sources: Sequence[Path],
        manifest_input: MultiViewCaptureInputV1,
        *,
        timepoint_id: UUID,
        knee_target_ids: list[UUID],
        authorization: dict[str, Any],
    ) -> ObservationImportResultV1:
        if len(sources) != 4:
            raise InvalidObservationImport("Exactly four source videos are required.")
        source_files: dict[str, Path] = {}
        source_references: dict[str, str] = {}
        for camera, source in zip(manifest_input.cameras, sources, strict=True):
            width, height, fps, _frame_count = inspect_video(source)
            if width != camera.width_px or height != camera.height_px:
                raise InvalidObservationImport(
                    f"Decoded dimensions for camera {camera.camera_id} do not match its manifest."
                )
            if not math.isclose(fps, camera.fps, rel_tol=0.01, abs_tol=0.1):
                raise InvalidObservationImport(
                    f"Decoded frame rate for camera {camera.camera_id} does not match its manifest."
                )
            filename = f"camera_{camera.view}.mp4"
            source_files[filename] = source
            source_references[camera.camera_id] = filename
        signals = [
            ImportQualitySignal(
                name="camera_protocol",
                status="pass",
                value=4,
                unit="cameras",
                explanation="Four unique calibrated views meet the 1080p/60 fps minimum.",
            ),
            ImportQualitySignal(
                name="visible_synchronization_event",
                status="pass",
                value=manifest_input.synchronization.maximum_offset_ms,
                unit="ms",
                explanation="A visible synchronization event and measured maximum offset exist.",
            ),
            ImportQualitySignal(
                name="capture_volume_validation",
                status="pass",
                value=manifest_input.capture_volume.rms_error_mm,
                unit="mm",
                explanation="Capture-volume validation evidence was supplied.",
            ),
            ImportQualitySignal(
                name="anatomical_calibration_pose",
                status="pass",
                value=True,
                explanation="The standardized pose is reported visible in all cameras.",
            ),
        ]
        manifest = MultiViewCaptureManifestV1(
            **manifest_input.model_dump(),
            source_artifacts=source_references,
            quality_signals=signals,
            status="pass",
        )
        return self._publish(
            source_files=source_files,
            manifest=manifest,
            modality="video",
            primary_filename="acquisition_manifest.json",
            timepoint_id=timepoint_id,
            knee_target_ids=knee_target_ids,
            authorization=authorization,
        )

    def _publish(
        self,
        *,
        source_files: dict[str, Path],
        manifest: DicomSeriesManifestV1
        | ArthroscopyManifestV1
        | MultiViewCaptureManifestV1,
        modality: str,
        primary_filename: str,
        timepoint_id: UUID,
        knee_target_ids: list[UUID],
        authorization: dict[str, Any],
    ) -> ObservationImportResultV1:
        observation_id = uuid4()
        staging = self._artifacts.begin_bundle(observation_id)
        published = False
        try:
            for filename, source in source_files.items():
                self._artifacts.copy_to_staging(staging, filename, source)
            manifest_payload = manifest.model_dump(mode="json")
            self._artifacts.write_staged_json(
                staging, "acquisition_manifest.json", manifest_payload
            )
            self._artifacts.publish_bundle(observation_id, staging)
            published = True
            integrity = self._artifacts.verify_bundle(observation_id)
            primary = next(item for item in integrity if item["filename"] == primary_filename)
            if primary["integrity"] != "verified":
                raise InvalidObservationImport(
                    "Published source artifact failed integrity checking."
                )
            observation = self._evidence.create_observation(
                ObservationCreate(
                    timepoint_id=timepoint_id,
                    modality=modality,
                    source_artifact_reference=self._artifacts.reference(
                        observation_id, primary_filename
                    ),
                    source_sha256=primary["sha256"],
                    acquisition_manifest=manifest_payload,
                    authorization=authorization,
                    quality={
                        "status": manifest.status,
                        "signals": [
                            signal.model_dump(mode="json")
                            for signal in manifest.quality_signals
                        ],
                    },
                    knee_target_ids=knee_target_ids,
                ),
                observation_id=observation_id,
            )
            return ObservationImportResultV1(
                observation=observation,
                acquisition_manifest=manifest,
                artifact_integrity=integrity,
            )
        except Exception:
            if published:
                self._artifacts.delete_bundle(observation_id)
            else:
                self._artifacts.abort_bundle(staging)
            raise


def inspect_video(path: Path) -> tuple[int, int, float, int]:
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise InvalidObservationImport("The uploaded video container could not be decoded.")
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        ok, _frame = capture.read()
        if not ok or width <= 0 or height <= 0 or fps <= 0 or frame_count <= 0:
            raise InvalidObservationImport("The uploaded video has invalid decoded metadata.")
        return width, height, fps, frame_count
    finally:
        capture.release()


def inspect_dicom_zip(path: Path) -> DicomSeriesManifestV1:
    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as error:
        raise InvalidObservationImport("The MRI source must be a readable ZIP archive.") from error
    with archive:
        members = [item for item in archive.infolist() if not item.is_dir()]
        if not members or len(members) > MAX_ARCHIVE_MEMBERS:
            raise InvalidObservationImport("The DICOM archive has an invalid member count.")
        if len({member.filename for member in members}) != len(members):
            raise InvalidObservationImport("The DICOM archive contains duplicate paths.")
        if any(_unsafe_archive_name(member.filename) for member in members):
            raise InvalidObservationImport("The DICOM archive contains an unsafe path.")
        if sum(member.file_size for member in members) > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
            raise InvalidObservationImport("The expanded DICOM archive is too large.")
        datasets = []
        for member in members:
            try:
                with archive.open(member) as dicom_source:
                    datasets.append(
                        pydicom.dcmread(
                            dicom_source,
                            stop_before_pixels=True,
                            force=False,
                        )
                    )
            except (InvalidDicomError, OSError, ValueError) as error:
                raise InvalidObservationImport(
                    f"Archive member {member.filename!r} is not a valid DICOM instance."
                ) from error

    required = (
        "StudyInstanceUID",
        "SeriesInstanceUID",
        "FrameOfReferenceUID",
        "SOPInstanceUID",
        "Rows",
        "Columns",
        "PixelSpacing",
        "ImageOrientationPatient",
        "ImagePositionPatient",
    )
    for dataset in datasets:
        missing = [keyword for keyword in required if not hasattr(dataset, keyword)]
        if missing:
            raise InvalidObservationImport(
                "A DICOM instance lacks required spatial metadata: " + ", ".join(missing)
            )
        if str(getattr(dataset, "Modality", "")) != "MR":
            raise InvalidObservationImport("Every DICOM instance must have Modality=MR.")

    populated_identifiers = sorted(
        {
            keyword
            for dataset in datasets
            for keyword in DIRECT_IDENTIFIER_KEYWORDS
            if str(getattr(dataset, keyword, "")).strip()
        }
    )
    deidentification = DeidentificationReportV1(
        direct_identifier_tags_checked=list(DIRECT_IDENTIFIER_KEYWORDS),
        populated_direct_identifier_tags=populated_identifiers,
        status="fail" if populated_identifiers else "pass",
        explanation=(
            "Detected populated direct-identifier tags; import is refused."
            if populated_identifiers
            else (
                "No populated direct identifiers were found in the checked tag subset. "
                "This is not a complete DICOM confidentiality-profile assessment."
            )
        ),
    )
    if populated_identifiers:
        raise InvalidObservationImport(
            "The DICOM archive contains populated direct-identifier tags: "
            + ", ".join(populated_identifiers)
        )

    first = datasets[0]
    shared_keywords = (
        "StudyInstanceUID",
        "SeriesInstanceUID",
        "FrameOfReferenceUID",
        "Rows",
        "Columns",
        "PixelSpacing",
        "ImageOrientationPatient",
    )
    for keyword in shared_keywords:
        expected = _numeric_or_text(getattr(first, keyword))
        if any(
            not _consistent(_numeric_or_text(getattr(item, keyword)), expected)
            for item in datasets
        ):
            raise InvalidObservationImport(f"DICOM series has inconsistent {keyword} values.")

    sop_uids = [str(item.SOPInstanceUID) for item in datasets]
    if len(set(sop_uids)) != len(sop_uids):
        raise InvalidObservationImport("DICOM SOP Instance UIDs must be unique.")
    orientation = tuple(float(value) for value in first.ImageOrientationPatient)
    row = orientation[:3]
    column = orientation[3:]
    normal = (
        row[1] * column[2] - row[2] * column[1],
        row[2] * column[0] - row[0] * column[2],
        row[0] * column[1] - row[1] * column[0],
    )
    if not math.isclose(_norm(row), 1, abs_tol=1e-3) or not math.isclose(
        _norm(column), 1, abs_tol=1e-3
    ) or not math.isclose(sum(a * b for a, b in zip(row, column, strict=True)), 0, abs_tol=1e-3):
        raise InvalidObservationImport("DICOM orientation direction cosines are not orthonormal.")
    positioned = sorted(
        (
            sum(
                float(value) * axis
                for value, axis in zip(item.ImagePositionPatient, normal, strict=True)
            ),
            tuple(float(value) for value in item.ImagePositionPatient),
        )
        for item in datasets
    )
    spacings = [
        positioned[index + 1][0] - positioned[index][0]
        for index in range(len(positioned) - 1)
    ]
    slice_spacing = median(spacings) if spacings else None
    if slice_spacing is not None and slice_spacing <= 0:
        raise InvalidObservationImport("DICOM slice positions must be unique.")
    spacing_consistent = slice_spacing is None or all(
        math.isclose(
            spacing,
            slice_spacing,
            rel_tol=SLICE_SPACING_RELATIVE_TOLERANCE,
            abs_tol=CONSISTENCY_TOLERANCE,
        )
        for spacing in spacings
    )
    if not spacing_consistent:
        raise InvalidObservationImport("DICOM slice spacing is inconsistent.")
    slice_thickness_values = [
        float(item.SliceThickness) for item in datasets if hasattr(item, "SliceThickness")
    ]
    slice_thickness = median(slice_thickness_values) if slice_thickness_values else None
    lateralities = {
        str(value).upper()
        for item in datasets
        for value in (getattr(item, "ImageLaterality", None), getattr(item, "Laterality", None))
        if value is not None and str(value).strip()
    }
    if not lateralities.issubset({"L", "R"}) or len(lateralities) > 1:
        raise InvalidObservationImport("DICOM laterality values are invalid or inconsistent.")
    dicom_laterality = (
        "left" if lateralities == {"L"} else "right" if lateralities == {"R"} else "unknown"
    )
    acquisition_datetimes = {
        str(item.AcquisitionDateTime)
        for item in datasets
        if hasattr(item, "AcquisitionDateTime") and str(item.AcquisitionDateTime).strip()
    }
    if len(acquisition_datetimes) > 1:
        raise InvalidObservationImport("DICOM AcquisitionDateTime is inconsistent.")
    status = "pass" if len(datasets) > 1 else "warning"
    signals = [
        ImportQualitySignal(
            name="series_consistency",
            status="pass",
            value=len(datasets),
            unit="instances",
            explanation=(
                "Required identity, matrix, spacing, and orientation fields are consistent."
            ),
        ),
        ImportQualitySignal(
            name="deidentification_screen",
            status="pass",
            value=0,
            unit="populated-direct-identifier-tags",
            explanation=deidentification.explanation,
        ),
        ImportQualitySignal(
            name="volumetric_slice_coverage",
            status="pass" if len(datasets) > 1 else "warning",
            value=len(datasets),
            unit="slices",
            explanation=(
                "Multiple spatially ordered slices are present."
                if len(datasets) > 1
                else "Only one slice is present; a volumetric reconstruction is not supported."
            ),
        ),
    ]
    return DicomSeriesManifestV1(
        study_instance_uid=str(first.StudyInstanceUID),
        series_instance_uid=str(first.SeriesInstanceUID),
        frame_of_reference_uid=str(first.FrameOfReferenceUID),
        sop_instance_uids=sop_uids,
        instance_count=len(datasets),
        rows=int(first.Rows),
        columns=int(first.Columns),
        pixel_spacing_mm=tuple(float(value) for value in first.PixelSpacing),
        slice_spacing_mm=slice_spacing,
        slice_thickness_mm=slice_thickness,
        image_orientation_patient=orientation,
        first_image_position_patient_mm=positioned[0][1],
        last_image_position_patient_mm=positioned[-1][1],
        dicom_laterality=dicom_laterality,
        acquisition_datetime=next(iter(acquisition_datetimes), None),
        deidentification=deidentification,
        quality_signals=signals,
        status=status,
    )


def parse_json_object(raw: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise InvalidObservationImport(f"{label} must be valid JSON.") from error
    if not isinstance(value, dict):
        raise InvalidObservationImport(f"{label} must be a JSON object.")
    return value


def _unsafe_archive_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    parts = normalized.split("/")
    return normalized.startswith("/") or ":" in parts[0] or any(part == ".." for part in parts)


def _numeric_or_text(value: Any) -> tuple[float, ...] | str:
    if isinstance(value, (list, tuple)) or value.__class__.__name__ == "MultiValue":
        return tuple(float(item) for item in value)
    try:
        return (float(value),)
    except (TypeError, ValueError):
        return str(value)


def _consistent(left: tuple[float, ...] | str, right: tuple[float, ...] | str) -> bool:
    if isinstance(left, str) or isinstance(right, str):
        return left == right
    return len(left) == len(right) and all(
        math.isclose(a, b, abs_tol=CONSISTENCY_TOLERANCE)
        for a, b in zip(left, right, strict=True)
    )


def _norm(vector: tuple[float, ...]) -> float:
    return math.sqrt(sum(value * value for value in vector))
