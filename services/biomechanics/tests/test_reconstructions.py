import json
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest

from app.evidence_repository import SQLiteEvidenceRepository
from app.schemas.evidence import ObservationCreate, SubjectCreate, TimepointCreate
from app.schemas.reconstruction import REQUIRED_KNEE_STRUCTURES
from app.services.reconstructions import (
    InvalidReconstructionPackage,
    ReconstructionImportService,
    inspect_reconstruction_package,
)
from app.storage import LocalArtifactStore


def npz(key: str, array: np.ndarray) -> bytes:
    target = BytesIO()
    np.savez_compressed(target, **{key: array})
    return target.getvalue()


def reconstruction_package(
    path: Path,
    *,
    observation_id: str,
    knee_id: str,
    timepoint_id: str,
    omit: str | None = None,
    independent_reviewer: str = "reviewer-b",
) -> Path:
    structure_labels = [
        {"structure": structure, "label_value": index + 1}
        for index, structure in enumerate(REQUIRED_KNEE_STRUCTURES)
    ]
    labels = np.zeros((len(REQUIRED_KNEE_STRUCTURES) + 2, 3, 3), dtype=np.uint16)
    for index in range(len(REQUIRED_KNEE_STRUCTURES)):
        labels[index + 1, 1, 1] = index + 1
    manifest = {
        "source_mri_observation_id": observation_id,
        "knee_id": knee_id,
        "timepoint_id": timepoint_id,
        "version": "manual-review-v1",
        "voxel_spacing_mm": [0.6, 0.6, 1.2],
        "structure_labels": structure_labels,
        "landmarks": [
            {
                "name": "femoral-center-fixture",
                "structure": "femur",
                "position_mm": [1, 2, 3],
                "author": "reviewer-a",
                "review_state": "approved",
            }
        ],
        "correction_history": [
            {
                "sequence": 1,
                "author": "reviewer-a",
                "structures": ["femur"],
                "description": "Synthetic correction fixture",
                "source_version": "draft-v1",
                "result_version": "manual-review-v1",
            }
        ],
        "independent_review": {
            "primary_reviewer": "reviewer-a",
            "independent_reviewer": independent_reviewer,
            "review_protocol": "manual-segmentation-independent-review-v1",
            "decision": "approved",
            "notes": "Synthetic package review only",
        },
        "threshold_profile": {
            "profile_id": "draft-complete-knee-v1",
            "approval_state": "draft",
            "thresholds_by_structure": {
                structure: {"dice_min": 0.8, "asd_max_mm": 1.0, "hd95_max_mm": 2.0}
                for structure in REQUIRED_KNEE_STRUCTURES
            },
        },
    }
    members = {
        "package_manifest.json": json.dumps(manifest).encode(),
        "reviewed_label_map.npz": npz("labels", labels),
        "independent_reference_label_map.npz": npz("labels", labels),
        "computational_volume.npz": npz("volume", np.zeros_like(labels, dtype=np.float32)),
    }
    for structure in REQUIRED_KNEE_STRUCTURES:
        members[f"scientific_meshes/{structure}.ply"] = b"ply\nfixture\n"
        members[f"web_meshes/{structure}.glb"] = b"glTF-fixture"
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members.items():
            if name != omit:
                archive.writestr(name, content)
    return path


def context(tmp_path: Path):
    store = LocalArtifactStore(tmp_path / "artifacts")
    evidence = SQLiteEvidenceRepository(tmp_path / "knee-twin.sqlite3")
    subject = evidence.create_subject(
        SubjectCreate(research_code="CASE-M11", deidentified_confirmed=True)
    )
    knee = next(knee for knee in evidence.list_knees(subject.id) if knee.laterality == "left")
    timepoint = evidence.create_timepoint(
        TimepointCreate(
            subject_id=subject.id,
            observed_at=datetime(2026, 2, 1, tzinfo=UTC),
            label="MRI reconstruction",
        )
    )
    observation = evidence.create_observation(
        ObservationCreate(
            timepoint_id=timepoint.id,
            modality="mri",
            source_artifact_reference="fixture://mri",
            source_sha256="a" * 64,
            acquisition_manifest={"coordinate_system": "dicom-patient-lps-mm"},
            authorization={"basis": "synthetic"},
            quality={"status": "pass"},
            knee_target_ids=[knee.id],
        )
    )
    return store, evidence, observation, timepoint, knee


def test_manual_reconstruction_import_preserves_complete_distinct_artifacts(
    tmp_path: Path,
) -> None:
    store, evidence, observation, timepoint, knee = context(tmp_path)
    package = reconstruction_package(
        tmp_path / "reconstruction.zip",
        observation_id=str(observation.id),
        knee_id=str(knee.id),
        timepoint_id=str(timepoint.id),
    )
    result = ReconstructionImportService(
        store, evidence, 10 * 1024 * 1024
    ).import_manual_package(package)
    assert set(result.reconstruction.structures) == set(REQUIRED_KNEE_STRUCTURES)
    assert result.reconstruction.geometry_class == "expert-reviewed"
    assert result.reconstruction.review_state == "in_review"
    assert result.quality.validation_status == "thresholds-unapproved"
    assert len(result.quality.structures) == len(REQUIRED_KNEE_STRUCTURES)
    assert all(item.dice_coefficient == 1 for item in result.quality.structures)
    assert all(item.acceptance == "not-evaluated" for item in result.quality.structures)
    assert all(item["integrity"] == "verified" for item in result.artifact_integrity)
    refs = result.reconstruction.artifact_references
    assert refs["reviewed_label_map"] != refs["computational_volume"]
    assert len(refs["scientific_meshes"]) == len(REQUIRED_KNEE_STRUCTURES)
    assert len(evidence.list_annotations()) == 0


def test_reconstruction_package_refuses_missing_structures_and_fake_independence(
    tmp_path: Path,
) -> None:
    _store, _evidence, observation, timepoint, knee = context(tmp_path)
    incomplete = reconstruction_package(
        tmp_path / "incomplete.zip",
        observation_id=str(observation.id),
        knee_id=str(knee.id),
        timepoint_id=str(timepoint.id),
        omit="web_meshes/acl.glb",
    )
    with pytest.raises(InvalidReconstructionPackage, match="incomplete"):
        inspect_reconstruction_package(incomplete)

    same_reviewer = reconstruction_package(
        tmp_path / "same-reviewer.zip",
        observation_id=str(observation.id),
        knee_id=str(knee.id),
        timepoint_id=str(timepoint.id),
        independent_reviewer="reviewer-a",
    )
    with pytest.raises(InvalidReconstructionPackage, match="different reviewer"):
        inspect_reconstruction_package(same_reviewer)
