import asyncio
import json
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient, Response
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, MRImageStorage, generate_uid

from app.evidence_repository import SQLiteEvidenceRepository
from app.main import create_app
from app.persistence import SQLiteSessionRepository
from app.schemas.evidence import SubjectCreate, TimepointCreate
from app.schemas.imports import (
    ArthroscopyImportMetadataV1,
    MultiViewCaptureInputV1,
)
from app.services.imports import (
    InvalidObservationImport,
    ObservationImportService,
    inspect_dicom_zip,
)
from app.storage import LocalArtifactStore


def request(app, method: str, path: str, **kwargs) -> Response:
    async def send() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def dicom_zip(
    path: Path,
    *,
    positions: list[float] | None = None,
    patient_name: str = "",
    modality: str = "MR",
    image_laterality: str | None = None,
) -> Path:
    positions = positions or [0.0, 1.5, 3.0]
    study_uid = generate_uid()
    series_uid = generate_uid()
    frame_uid = generate_uid()
    with zipfile.ZipFile(path, "w") as archive:
        for index, z_position in enumerate(positions):
            sop_uid = generate_uid()
            file_meta = FileMetaDataset()
            file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
            file_meta.MediaStorageSOPClassUID = MRImageStorage
            file_meta.MediaStorageSOPInstanceUID = sop_uid
            file_meta.ImplementationClassUID = generate_uid()
            dataset = FileDataset(None, {}, file_meta=file_meta, preamble=b"\0" * 128)
            dataset.SOPClassUID = MRImageStorage
            dataset.SOPInstanceUID = sop_uid
            dataset.StudyInstanceUID = study_uid
            dataset.SeriesInstanceUID = series_uid
            dataset.FrameOfReferenceUID = frame_uid
            dataset.Modality = modality
            if image_laterality is not None:
                dataset.ImageLaterality = image_laterality
            dataset.PatientName = patient_name
            dataset.Rows = 8
            dataset.Columns = 10
            dataset.PixelSpacing = [0.6, 0.7]
            dataset.SliceThickness = 1.5
            dataset.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
            dataset.ImagePositionPatient = [0, 0, z_position]
            dataset.SamplesPerPixel = 1
            dataset.PhotometricInterpretation = "MONOCHROME2"
            dataset.BitsAllocated = 16
            dataset.BitsStored = 12
            dataset.HighBit = 11
            dataset.PixelRepresentation = 0
            dataset.PixelData = np.zeros((8, 10), dtype=np.uint16).tobytes()
            content = BytesIO()
            dataset.save_as(content, enforce_file_format=True)
            archive.writestr(f"series/slice-{index:03}.dcm", content.getvalue())
    return path


def video(path: Path, *, width: int = 64, height: int = 48, fps: float = 30) -> Path:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    assert writer.isOpened()
    writer.write(np.zeros((height, width, 3), dtype=np.uint8))
    writer.write(np.full((height, width, 3), 100, dtype=np.uint8))
    writer.release()
    return path


def evidence_context(tmp_path: Path):
    store = LocalArtifactStore(tmp_path / "artifacts")
    evidence = SQLiteEvidenceRepository(tmp_path / "knee-twin.sqlite3")
    subject = evidence.create_subject(
        SubjectCreate(research_code="CASE-M10", deidentified_confirmed=True)
    )
    knee = evidence.list_knees(subject.id)[0]
    timepoint = evidence.create_timepoint(
        TimepointCreate(
            subject_id=subject.id,
            observed_at=datetime(2026, 2, 1, tzinfo=UTC),
            label="Multimodal acquisition",
        )
    )
    service = ObservationImportService(store, evidence, 10 * 1024 * 1024)
    return store, evidence, service, timepoint, knee


def authorization() -> dict[str, object]:
    return {
        "basis": "synthetic test fixture",
        "deidentified_confirmed": True,
        "restriction": "research-only",
    }


def arthroscopy_metadata() -> ArthroscopyImportMetadataV1:
    return ArthroscopyImportMetadataV1(
        procedure_at=datetime(2026, 2, 1, tzinfo=UTC),
        scope_manufacturer="Synthetic",
        scope_model="Fixture",
        scope_angle_degrees=30,
        camera_manufacturer="Synthetic",
        camera_model="Fixture",
        calibration_method="checkerboard fixture",
        calibration_artifact_reference="fixture://checkerboard-v1",
        calibration_error_px=0.4,
        visible_regions=[
            {
                "start_ms": 0,
                "end_ms": 50,
                "anatomical_region": "synthetic notch",
                "author": "fixture-author",
            }
        ],
    )


def multiview_manifest() -> MultiViewCaptureInputV1:
    identity = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    cameras = []
    for index, view_name in enumerate(("front", "rear", "left_side", "right_side")):
        transform = [row.copy() for row in identity]
        transform[0][3] = index * 1000
        cameras.append(
            {
                "camera_id": f"camera-{index + 1}",
                "view": view_name,
                "width_px": 1920,
                "height_px": 1080,
                "fps": 60,
                "intrinsic": {
                    "matrix": [[1000, 0, 960], [0, 1000, 540], [0, 0, 1]],
                    "distortion_coefficients": [0, 0, 0, 0, 0],
                    "calibration_error_px": 0.25,
                },
                "extrinsic": {
                    "capture_from_camera_transform": transform,
                    "calibration_error_mm": 1.0,
                },
            }
        )
    return MultiViewCaptureInputV1.model_validate(
        {
            "captured_at": "2026-02-01T10:00:00Z",
            "cameras": cameras,
            "synchronization": {
                "method": "visible-event",
                "event_description": "LED flash",
                "maximum_offset_ms": 2,
            },
            "capture_volume": {
                "method": "wand calibration",
                "rms_error_mm": 1.2,
                "validated_at": "2026-02-01T09:00:00Z",
            },
            "anatomical_calibration_pose": {
                "protocol": "standard-anatomical-pose-v1",
                "visible_in_all_cameras": True,
                "landmark_set": ["medial-knee", "lateral-knee", "ankle", "hip"],
            },
        }
    )


def test_mri_import_preserves_source_and_spatial_manifest(tmp_path: Path) -> None:
    store, evidence, service, timepoint, knee = evidence_context(tmp_path)
    source = dicom_zip(tmp_path / "source.zip")

    result = service.import_mri_zip(
        source,
        timepoint_id=timepoint.id,
        knee_target_ids=[knee.id],
        authorization=authorization(),
    )

    assert result.acquisition_manifest.coordinate_system == "dicom-patient-lps-mm"
    assert result.acquisition_manifest.pixel_spacing_mm == (0.6, 0.7)
    assert result.acquisition_manifest.slice_spacing_mm == 1.5
    assert result.acquisition_manifest.deidentification.dicom_ps3_15_conformance_claimed is False
    assert result.observation == evidence.get_observation(result.observation.id)
    preserved = store.path_for(result.observation.id, "source_dicom_series.zip")
    assert preserved.read_bytes() == source.read_bytes()
    assert all(item["integrity"] == "verified" for item in result.artifact_integrity)
    assert result.execution == "synchronous-local-import"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"patient_name": "Identified^Person"}, "direct-identifier"),
        ({"modality": "CT"}, "Modality=MR"),
        ({"positions": [0.0, 1.5, 4.0]}, "spacing is inconsistent"),
    ],
)
def test_mri_import_rejects_unsafe_or_inconsistent_evidence(
    tmp_path: Path, kwargs: dict[str, object], message: str
) -> None:
    source = dicom_zip(tmp_path / "invalid.zip", **kwargs)
    with pytest.raises(InvalidObservationImport, match=message):
        inspect_dicom_zip(source)


def test_mri_import_rejects_corrupt_archives(tmp_path: Path) -> None:
    source = tmp_path / "corrupt.zip"
    source.write_bytes(b"not a zip archive")
    with pytest.raises(InvalidObservationImport, match="readable ZIP"):
        inspect_dicom_zip(source)


def test_mri_import_rejects_a_wrong_knee_target(tmp_path: Path) -> None:
    _store, evidence, service, timepoint, left_knee = evidence_context(tmp_path)
    right_knee = next(
        knee
        for knee in evidence.list_knees(left_knee.subject_id)
        if knee.laterality == "right"
    )
    source = dicom_zip(tmp_path / "left-knee.zip", image_laterality="L")
    with pytest.raises(InvalidObservationImport, match="laterality"):
        service.import_mri_zip(
            source,
            timepoint_id=timepoint.id,
            knee_target_ids=[right_knee.id],
            authorization=authorization(),
        )


def test_arthroscopy_import_checks_timing_and_preserves_calibration(tmp_path: Path) -> None:
    store, _evidence, service, timepoint, knee = evidence_context(tmp_path)
    source = video(tmp_path / "scope.mp4")
    result = service.import_arthroscopy(
        source,
        arthroscopy_metadata(),
        timepoint_id=timepoint.id,
        knee_target_ids=[knee.id],
        authorization=authorization(),
    )
    manifest = result.acquisition_manifest
    assert manifest.coordinate_system == "arthroscope-image-pixels"
    assert manifest.timestamp_basis == "decoded-frame-index-and-container-fps"
    assert manifest.calibration_error_px == 0.4
    assert store.path_for(result.observation.id, "source_arthroscopy.mp4").is_file()

    invalid_payload = arthroscopy_metadata().model_dump()
    invalid_payload["visible_regions"] = [
        {
            "start_ms": 0,
            "end_ms": 1_000,
            "anatomical_region": "outside duration",
            "author": "fixture-author",
        }
    ]
    invalid = ArthroscopyImportMetadataV1.model_validate(invalid_payload)
    with pytest.raises(InvalidObservationImport, match="beyond"):
        service.import_arthroscopy(
            source,
                invalid,
            timepoint_id=timepoint.id,
            knee_target_ids=[knee.id],
            authorization=authorization(),
        )


def test_four_camera_import_requires_manifest_to_match_decoded_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _evidence, service, timepoint, knee = evidence_context(tmp_path)
    sources = []
    for index in range(4):
        source = tmp_path / f"camera-{index}.mp4"
        source.write_bytes(f"synthetic-camera-{index}".encode())
        sources.append(source)
    monkeypatch.setattr(
        "app.services.imports.inspect_video",
        lambda _source: (1920, 1080, 60.0, 120),
    )
    result = service.import_multiview(
        sources,
        multiview_manifest(),
        timepoint_id=timepoint.id,
        knee_target_ids=[knee.id],
        authorization=authorization(),
    )
    manifest = result.acquisition_manifest
    assert manifest.protocol == "calibrated-four-camera-rgb-v1"
    assert manifest.coordinate_system == "capture-volume-right-handed-mm"
    assert len(manifest.source_artifacts) == 4
    assert len(store.verify_bundle(result.observation.id)) == 5


def test_mri_import_api_returns_typed_observation_and_refuses_missing_authorization(
    tmp_path: Path,
) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    sessions = SQLiteSessionRepository(tmp_path / "knee-twin.sqlite3")
    app = create_app(
        pose_analysis_service=None,
        artifact_store=store,
        session_repository=sessions,
    )
    subject = request(
        app,
        "POST",
        "/subjects",
        json={"research_code": "CASE-API", "deidentified_confirmed": True},
    ).json()
    knee = request(app, "GET", f"/knees?subject_id={subject['id']}").json()["knees"][0]
    timepoint = request(
        app,
        "POST",
        "/timepoints",
        json={
            "subject_id": subject["id"],
            "observed_at": "2026-02-01T10:00:00Z",
            "label": "MRI",
        },
    ).json()
    source = dicom_zip(tmp_path / "api.zip")
    form = {
        "timepoint_id": timepoint["id"],
        "knee_target_ids": json.dumps([knee["id"]]),
        "authorization": json.dumps(authorization()),
    }
    response = request(
        app,
        "POST",
        "/observations/imports/mri",
        data=form,
        files={"archive": ("source.zip", source.read_bytes(), "application/zip")},
    )
    assert response.status_code == 201
    assert response.json()["observation"]["modality"] == "mri"
    assert response.json()["acquisition_manifest"]["instance_count"] == 3

    form["authorization"] = json.dumps({"basis": "unknown"})
    refused = request(
        app,
        "POST",
        "/observations/imports/mri",
        data=form,
        files={"archive": ("source.zip", source.read_bytes(), "application/zip")},
    )
    assert refused.status_code == 422
    assert "deidentified_confirmed" in refused.json()["detail"]
