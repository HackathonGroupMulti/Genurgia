import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath
from uuid import uuid4

from pydantic import ValidationError

from analysis.finite_elements import signed_tetrahedron_volume_mm3
from app.evidence_repository import SQLiteEvidenceRepository
from app.schemas.evidence import DerivationCreate, SimulationModelCreate
from app.schemas.simulation import (
    FiniteElementModelImportResultV1,
    FiniteElementModelPackageV1,
    MeshQualityV1,
)
from app.storage import LocalArtifactStore

PACKAGE_MANIFEST = "finite_element_model_manifest_v1.json"
MAX_MEMBERS = 20
MAX_EXPANDED_BYTES = 256 * 1024 * 1024


class InvalidFiniteElementModelPackage(ValueError):
    pass


class SimulationModelImportService:
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

    def import_febio_package(self, source: Path) -> FiniteElementModelImportResultV1:
        package = inspect_finite_element_model_package(source)
        reconstruction = self._evidence.get_reconstruction(package.reconstruction_id)
        knee = self._evidence.get_knee(reconstruction.knee_id)
        coordinate_name = reconstruction.coordinate_system.get("name")
        coordinate_unit = reconstruction.coordinate_system.get("unit")
        if coordinate_name != package.coordinate_system.name or coordinate_unit != "mm":
            raise InvalidFiniteElementModelPackage(
                "Finite-element and reconstruction coordinate systems must match in millimetres."
            )
        if knee.laterality != package.coordinate_system.laterality:
            raise InvalidFiniteElementModelPackage(
                "Finite-element model laterality differs from the reconstruction knee."
            )
        if not set(package.included_structures) <= set(reconstruction.structures):
            raise InvalidFiniteElementModelPackage(
                "Finite-element structures must be present in the source reconstruction."
            )
        quality = evaluate_mesh_quality(package)
        canonical = _canonical_json(package.model_dump(mode="json"))
        model_sha256 = hashlib.sha256(canonical).hexdigest()
        model_id = uuid4()
        staging = self._artifacts.begin_bundle(model_id)
        published = False
        try:
            self._artifacts.copy_to_staging(staging, "source_fe_model_package.zip", source)
            self._artifacts.write_staged_json(
                staging,
                PACKAGE_MANIFEST,
                package.model_dump(mode="json"),
            )
            self._artifacts.write_staged_json(
                staging,
                "mesh_quality_v1.json",
                quality.model_dump(mode="json"),
            )
            self._artifacts.publish_bundle(model_id, staging)
            published = True
            integrity = self._artifacts.verify_bundle(model_id)
            if not integrity or any(item["integrity"] != "verified" for item in integrity):
                raise InvalidFiniteElementModelPackage(
                    "Published finite-element model failed artifact integrity verification."
                )
            references = {
                "source_package": self._artifacts.reference(
                    model_id, "source_fe_model_package.zip"
                ),
                "normalized_manifest": self._artifacts.reference(model_id, PACKAGE_MANIFEST),
                "mesh_quality": self._artifacts.reference(model_id, "mesh_quality_v1.json"),
            }
            model, _derivation = self._evidence.create_simulation_model_and_derivation(
                SimulationModelCreate(
                    reconstruction_id=package.reconstruction_id,
                    version=package.version,
                    adapter_id=package.adapter_id,
                    model_sha256=model_sha256,
                    model_manifest=package.model_dump(mode="json"),
                    artifact_references=references,
                    mesh_quality=quality.model_dump(mode="json"),
                    included_structures=package.included_structures,
                    excluded_structures=package.excluded_structures,
                    validation_state="structurally-valid",
                ),
                DerivationCreate(
                    derivation_type="finite-element-model-preparation",
                    inputs=[str(package.reconstruction_id)],
                    # Replaced by the repository with the canonical model ID.
                    outputs=["pending-simulation-model"],
                    algorithm="contributor-authored-fe-package-validation",
                    algorithm_version="v1",
                    configuration={
                        "adapter_id": package.adapter_id,
                        "model_sha256": model_sha256,
                    },
                    code_revision="recorded-by-package-version",
                    environment={"execution": "offline-workstation"},
                ),
                simulation_model_id=model_id,
            )
            return FiniteElementModelImportResultV1(
                simulation_model=model,
                package=package,
                mesh_quality=quality,
                artifact_integrity=integrity,
            )
        except Exception:
            if published:
                self._artifacts.delete_bundle(model_id)
            else:
                self._artifacts.abort_bundle(staging)
            raise


def inspect_finite_element_model_package(source: Path) -> FiniteElementModelPackageV1:
    try:
        archive = zipfile.ZipFile(source)
    except (zipfile.BadZipFile, OSError) as error:
        raise InvalidFiniteElementModelPackage("The FE model package must be a ZIP.") from error
    with archive:
        members = [item for item in archive.infolist() if not item.is_dir()]
        names = [item.filename for item in members]
        if len(names) != len(set(names)) or len(names) > MAX_MEMBERS:
            raise InvalidFiniteElementModelPackage("Package member count or paths are invalid.")
        if any(_unsafe_path(name) for name in names):
            raise InvalidFiniteElementModelPackage("The package contains an unsafe path.")
        if sum(item.file_size for item in members) > MAX_EXPANDED_BYTES:
            raise InvalidFiniteElementModelPackage("The expanded FE model package is too large.")
        if PACKAGE_MANIFEST not in names:
            raise InvalidFiniteElementModelPackage(
                f"The FE model package requires {PACKAGE_MANIFEST}."
            )
        try:
            return FiniteElementModelPackageV1.model_validate_json(
                archive.read(PACKAGE_MANIFEST)
            )
        except (ValidationError, ValueError, json.JSONDecodeError) as error:
            raise InvalidFiniteElementModelPackage(f"Invalid FE model manifest: {error}") from error


def evaluate_mesh_quality(package: FiniteElementModelPackageV1) -> MeshQualityV1:
    nodes = {node.id: node.position_mm for node in package.nodes}
    volumes = [
        signed_tetrahedron_volume_mm3(*(nodes[node_id] for node_id in element.node_ids))
        for element in package.elements
    ]
    if any(volume <= 0 for volume in volumes):
        raise InvalidFiniteElementModelPackage(
            "Every tet4 element must have a positive signed volume in the declared coordinates."
        )
    used_nodes = {node_id for element in package.elements for node_id in element.node_ids}
    return MeshQualityV1(
        minimum_signed_tetrahedron_volume_mm3=min(volumes),
        duplicate_node_ids=0,
        duplicate_element_ids=0,
        orphan_node_count=len(set(nodes) - used_nodes),
    )


def _unsafe_path(name: str) -> bool:
    path = PurePosixPath(name)
    return path.is_absolute() or ".." in path.parts or "\\" in name


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
