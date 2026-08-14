import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.evidence_repository import SQLiteEvidenceRepository
from app.schemas.evidence import ReconstructionCreate, SubjectCreate, TimepointCreate
from app.schemas.reconstruction import REQUIRED_KNEE_STRUCTURES
from app.synthetic_fixture import synthetic_fe_manifest


def simulation_context(evidence: SQLiteEvidenceRepository):
    subject = evidence.create_subject(
        SubjectCreate(research_code="CASE-M14", deidentified_confirmed=True)
    )
    knee = next(item for item in evidence.list_knees(subject.id) if item.laterality == "left")
    timepoint = evidence.create_timepoint(
        TimepointCreate(
            subject_id=subject.id,
            observed_at=datetime(2026, 2, 1, tzinfo=UTC),
            label="Synthetic FE fixture",
        )
    )
    reconstruction = evidence.create_reconstruction(
        ReconstructionCreate(
            knee_id=knee.id,
            timepoint_id=timepoint.id,
            version="synthetic-complete-knee-v1",
            geometry_class="generic",
            structures=list(REQUIRED_KNEE_STRUCTURES),
            artifact_references={"fixture": "cc0"},
            coordinate_system={"name": "synthetic-knee-right-handed-mm", "unit": "mm"},
            review_state="draft",
        )
    )
    return knee, timepoint, reconstruction


def finite_element_manifest(reconstruction_id: str) -> dict[str, object]:
    return synthetic_fe_manifest(
        UUID(reconstruction_id),
        "left",
        "synthetic-knee-right-handed-mm",
    )


def write_fe_package(path: Path, manifest: dict[str, object]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "finite_element_model_manifest_v1.json",
            json.dumps(manifest, sort_keys=True),
        )
        archive.writestr("README.txt", "Synthetic CC0 Knee Twin finite-element fixture.\n")
    return path


def sourced(value: float, unit: str, source: str = "fixture-author") -> dict[str, object]:
    return {
        "value": value,
        "unit": unit,
        "source": source,
        "range": [value, value],
        "rationale": "Explicit synthetic fixture assumption.",
        "individual_measurement": False,
        "evidence_class": "expert-assumption",
    }


def flexion_experiment(model_id: str, model_sha256: str) -> dict[str, object]:
    deformable = [
        "femoral_cartilage",
        "medial_tibial_cartilage",
        "lateral_tibial_cartilage",
        "medial_meniscus",
        "lateral_meniscus",
    ]
    return {
        "experiment_type": "febio-tibiofemoral-flexion-sweep",
        "simulation_model_id": model_id,
        "simulation_model_sha256": model_sha256,
        "scientific_question": (
            "Under a manually specified compressive load, how do simulated tibiofemoral "
            "contact and strain fields change from 0 to 90 degrees of prescribed flexion?"
        ),
        "flexion_angles_degrees": [0, 15, 30, 45, 60, 75, 90],
        "materials": [
            {
                "structure": structure,
                "model": "neo-Hookean",
                "young_modulus": sourced(5, "MPa"),
                "poisson_ratio": sourced(0.45, "1"),
            }
            for structure in deformable
        ],
        "ligaments": [
            {
                "structure": structure,
                "stiffness": sourced(50, "N/mm"),
                "slack_length": sourced(4, "mm"),
            }
            for structure in ("acl", "pcl", "mcl", "lcl")
        ],
        "contacts": [
            {
                "name": "tibiofemoral-contact",
                "primary_surface": "femoral_contact",
                "secondary_surface": "tibial_contact",
                "penalty": sourced(1, "1"),
                "friction_coefficient": sourced(0, "1"),
            }
        ],
        "boundary": {
            "compressive_load": sourced(500, "N"),
            "rotation_axis": "x",
        },
        "convergence": {
            "displacement_tolerance": sourced(0.001, "mm"),
            "energy_tolerance": sourced(0.01, "1"),
            "maximum_reformations": sourced(25, "count"),
            "timeout_seconds_per_pose": sourced(30, "s"),
        },
        "requested_outputs": [
            "contact-pressure",
            "contact-area",
            "displacement",
            "cartilage-meniscus-strain",
            "ligament-strain",
            "reaction-force",
            "convergence-residual",
        ],
        "software_versions": {"knee-twin": "milestone-14", "febio": "4.12"},
        "validation_tier": "synthetic",
    }
