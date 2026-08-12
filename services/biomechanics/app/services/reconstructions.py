import json
import zipfile
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import numpy as np
from pydantic import ValidationError

from analysis.reconstruction_quality import evaluate_structure_agreement
from app.evidence_repository import SQLiteEvidenceRepository
from app.schemas.evidence import DerivationCreate, ReconstructionCreate
from app.schemas.reconstruction import (
    REQUIRED_KNEE_STRUCTURES,
    ManualReconstructionPackageV1,
    ReconstructionImportResultV1,
    ReconstructionQualityReportV1,
    StructureQualityV1,
)
from app.storage import LocalArtifactStore

PACKAGE_MANIFEST = "package_manifest.json"
LABEL_MAP = "reviewed_label_map.npz"
REFERENCE_LABEL_MAP = "independent_reference_label_map.npz"
COMPUTATIONAL_VOLUME = "computational_volume.npz"
MAX_MEMBERS = 200
MAX_EXPANDED_BYTES = 4 * 1024 * 1024 * 1024


class InvalidReconstructionPackage(ValueError):
    pass


class ReconstructionImportService:
    def __init__(
        self,
        artifacts: LocalArtifactStore,
        evidence: SQLiteEvidenceRepository,
        max_upload_bytes: int,
    ) -> None:
        self._artifacts = artifacts
        self._evidence = evidence
        self.max_upload_bytes = max_upload_bytes

    def create_temporary_upload(self) -> Path:
        return self._artifacts.create_temporary_upload(".zip")

    def delete_temporary_upload(self, path: Path) -> None:
        self._artifacts.delete_temporary_upload(path)

    def import_manual_package(self, source: Path) -> ReconstructionImportResultV1:
        package, extracted, candidate, reference = inspect_reconstruction_package(source)
        source_observation = self._evidence.get_observation(package.source_mri_observation_id)
        if source_observation.modality != "mri":
            raise InvalidReconstructionPackage(
                "The reconstruction source must be an MRI observation."
            )
        if source_observation.timepoint_id != package.timepoint_id:
            raise InvalidReconstructionPackage("Source MRI and reconstruction timepoints differ.")
        if package.knee_id not in source_observation.knee_target_ids:
            raise InvalidReconstructionPackage(
                "Source MRI does not target the reconstruction knee."
            )

        quality = _quality_report(package, candidate, reference)
        reconstruction_id = uuid4()
        staging = self._artifacts.begin_bundle(reconstruction_id)
        published = False
        try:
            self._artifacts.copy_to_staging(staging, "source_reconstruction_package.zip", source)
            for filename, content in extracted.items():
                target = self._artifacts.staging_path(staging, filename.replace("/", "__"))
                target.write_bytes(content)
            self._artifacts.write_staged_json(
                staging, "reconstruction_quality_v1.json", quality.model_dump(mode="json")
            )
            self._artifacts.publish_bundle(reconstruction_id, staging)
            published = True
            integrity = self._artifacts.verify_bundle(reconstruction_id)
            if not integrity or any(item["integrity"] != "verified" for item in integrity):
                raise InvalidReconstructionPackage(
                    "Published reconstruction failed integrity checks."
                )
            references = {
                "source_package": self._artifacts.reference(
                    reconstruction_id, "source_reconstruction_package.zip"
                ),
                "reviewed_label_map": self._artifacts.reference(
                    reconstruction_id, LABEL_MAP
                ),
                "independent_reference_label_map": self._artifacts.reference(
                    reconstruction_id, REFERENCE_LABEL_MAP
                ),
                "computational_volume": self._artifacts.reference(
                    reconstruction_id, COMPUTATIONAL_VOLUME
                ),
                "scientific_meshes": {
                    structure: self._artifacts.reference(
                        reconstruction_id, f"scientific_meshes__{structure}.ply"
                    )
                    for structure in REQUIRED_KNEE_STRUCTURES
                },
                "web_meshes": {
                    structure: self._artifacts.reference(
                        reconstruction_id, f"web_meshes__{structure}.glb"
                    )
                    for structure in REQUIRED_KNEE_STRUCTURES
                },
                "quality_report": self._artifacts.reference(
                    reconstruction_id, "reconstruction_quality_v1.json"
                ),
            }
            reconstruction = self._evidence.create_reconstruction(
                ReconstructionCreate(
                    knee_id=package.knee_id,
                    timepoint_id=package.timepoint_id,
                    version=package.version,
                    geometry_class="expert-reviewed",
                    structures=list(REQUIRED_KNEE_STRUCTURES),
                    artifact_references=references,
                    coordinate_system={
                        "name": package.coordinate_system,
                        "unit": "mm",
                        "voxel_spacing_mm": list(package.voxel_spacing_mm),
                    },
                    review_state=(
                        "approved" if quality.validation_status == "accepted" else "in_review"
                    ),
                ),
                reconstruction_id=reconstruction_id,
            )
            self._evidence.create_derivation(
                DerivationCreate(
                    derivation_type="manual-anatomical-reconstruction",
                    inputs=[str(package.source_mri_observation_id)],
                    outputs=[str(reconstruction.id)],
                    algorithm="manual-segmentation-independent-review",
                    algorithm_version="v1",
                    configuration=package.model_dump(mode="json"),
                    code_revision="recorded-by-package-version",
                    environment={"execution": "offline-workstation"},
                )
            )
            return ReconstructionImportResultV1(
                reconstruction=reconstruction,
                package=package,
                quality=quality,
                artifact_integrity=integrity,
            )
        except Exception:
            if published:
                self._artifacts.delete_bundle(reconstruction_id)
            else:
                self._artifacts.abort_bundle(staging)
            raise


def inspect_reconstruction_package(
    source: Path,
) -> tuple[ManualReconstructionPackageV1, dict[str, bytes], np.ndarray, np.ndarray]:
    try:
        archive = zipfile.ZipFile(source)
    except (zipfile.BadZipFile, OSError) as error:
        raise InvalidReconstructionPackage("The reconstruction package must be a ZIP.") from error
    with archive:
        members = [item for item in archive.infolist() if not item.is_dir()]
        names = {item.filename for item in members}
        if len(members) != len(names) or len(members) > MAX_MEMBERS:
            raise InvalidReconstructionPackage("Package member count or paths are invalid.")
        if any(_unsafe_path(name) for name in names):
            raise InvalidReconstructionPackage("The package contains an unsafe path.")
        if sum(item.file_size for item in members) > MAX_EXPANDED_BYTES:
            raise InvalidReconstructionPackage("The expanded reconstruction package is too large.")
        required = {PACKAGE_MANIFEST, LABEL_MAP, REFERENCE_LABEL_MAP, COMPUTATIONAL_VOLUME}
        required |= {
            f"scientific_meshes/{structure}.ply" for structure in REQUIRED_KNEE_STRUCTURES
        }
        required |= {f"web_meshes/{structure}.glb" for structure in REQUIRED_KNEE_STRUCTURES}
        missing = sorted(required - names)
        if missing:
            raise InvalidReconstructionPackage(
                "The reconstruction package is incomplete: " + ", ".join(missing[:5])
            )
        try:
            package = ManualReconstructionPackageV1.model_validate_json(
                archive.read(PACKAGE_MANIFEST)
            )
        except (ValidationError, ValueError, json.JSONDecodeError) as error:
            raise InvalidReconstructionPackage(f"Invalid package manifest: {error}") from error
        candidate = _npz_array(archive.read(LABEL_MAP), "labels")
        reference = _npz_array(archive.read(REFERENCE_LABEL_MAP), "labels")
        volume = _npz_array(archive.read(COMPUTATIONAL_VOLUME), "volume")
        if (
            candidate.ndim != 3
            or candidate.shape != reference.shape
            or candidate.shape != volume.shape
        ):
            raise InvalidReconstructionPackage(
                "Label maps and computational volume must share one 3D shape."
            )
        if not np.issubdtype(candidate.dtype, np.integer) or not np.issubdtype(
            reference.dtype, np.integer
        ):
            raise InvalidReconstructionPackage("Label maps must use integer labels.")
        expected = {item.label_value for item in package.structure_labels}
        for label_map, name in ((candidate, "reviewed"), (reference, "reference")):
            present = set(int(value) for value in np.unique(label_map) if int(value) != 0)
            if present != expected:
                raise InvalidReconstructionPackage(
                    f"The {name} label map must contain every declared label and no unknown labels."
                )
        extracted = {name: archive.read(name) for name in required}
    return package, extracted, candidate, reference


def _quality_report(
    package: ManualReconstructionPackageV1,
    candidate: np.ndarray,
    reference: np.ndarray,
) -> ReconstructionQualityReportV1:
    structures = []
    any_failed = False
    for item in package.structure_labels:
        agreement = evaluate_structure_agreement(
            candidate == item.label_value,
            reference == item.label_value,
            package.voxel_spacing_mm,
        )
        thresholds = package.threshold_profile.thresholds_by_structure[item.structure]
        if package.threshold_profile.approval_state == "approved":
            accepted = (
                agreement.dice_coefficient >= thresholds["dice_min"]
                and agreement.average_symmetric_surface_distance_mm
                <= thresholds["asd_max_mm"]
                and agreement.hausdorff_95_mm <= thresholds["hd95_max_mm"]
            )
            acceptance = "pass" if accepted else "fail"
            any_failed |= not accepted
        else:
            acceptance = "not-evaluated"
        structures.append(
            StructureQualityV1(
                structure=item.structure,
                **asdict(agreement),
                acceptance=acceptance,
            )
        )
    validation_status = (
        "thresholds-unapproved"
        if package.threshold_profile.approval_state == "draft"
        else "rejected"
        if any_failed or package.independent_review.decision != "approved"
        else "accepted"
    )
    return ReconstructionQualityReportV1(
        structures=structures,
        inter_rater_evaluation_present=True,
        threshold_profile_id=package.threshold_profile.profile_id,
        threshold_approval_state=package.threshold_profile.approval_state,
        validation_status=validation_status,
    )


def _npz_array(content: bytes, key: str) -> np.ndarray:
    try:
        with np.load(BytesIO(content), allow_pickle=False) as archive:
            if set(archive.files) != {key}:
                raise InvalidReconstructionPackage(f"NPZ must contain only {key!r}.")
            return np.array(archive[key], copy=True)
    except (ValueError, OSError) as error:
        raise InvalidReconstructionPackage(f"Invalid NPZ artifact for {key}.") from error


def _unsafe_path(name: str) -> bool:
    normalized = name.replace("\\", "/")
    parts = normalized.split("/")
    return normalized.startswith("/") or ":" in parts[0] or any(part == ".." for part in parts)
