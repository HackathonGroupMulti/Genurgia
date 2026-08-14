import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from pydantic import ValidationError

from analysis.finite_elements import signed_tetrahedron_volume_mm3
from app.evidence_repository import SQLiteEvidenceRepository
from app.febio_adapter import (
    InvalidExperimentForModel,
    _load_vtk_metrics,
    _normalized_field_manifest,
    _run_pose,
    build_febio_input,
    validate_experiment_for_model,
)
from app.schemas.simulation import (
    ExperimentDefinitionV2,
    FiniteElementModelPackageV1,
    FlexionPoseResultV1,
)
from app.services.simulation_models import (
    InvalidFiniteElementModelPackage,
    SimulationModelImportService,
)
from app.simulation_adapters import febio_preflight
from app.storage import LocalArtifactStore
from tests.simulation_fixtures import (
    finite_element_manifest,
    flexion_experiment,
    simulation_context,
    write_fe_package,
)


def test_signed_tetrahedron_volume_preserves_orientation_and_mm3() -> None:
    positive = signed_tetrahedron_volume_mm3(
        (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)
    )
    negative = signed_tetrahedron_volume_mm3(
        (0, 0, 0), (0, 1, 0), (1, 0, 0), (0, 0, 1)
    )
    assert positive == pytest.approx(1 / 6)
    assert negative == pytest.approx(-1 / 6)


def test_normalized_field_manifest_keeps_unavailable_outputs_explicit() -> None:
    manifest = _normalized_field_manifest(
        FlexionPoseResultV1(
            flexion_angle_degrees=15,
            status="nonconverged",
            contact_pressure_mpa=2.5,
        )
    )

    assert manifest.pose_status == "nonconverged"
    assert manifest.fields[0].value == 2.5
    assert manifest.fields[0].available is True
    assert manifest.fields[1].value is None
    assert manifest.fields[1].available is False
    assert all(field.evidence_class == "simulated" for field in manifest.fields)


def test_imports_immutable_structurally_valid_fe_model(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    evidence = SQLiteEvidenceRepository(tmp_path / "knee-twin.sqlite3")
    _, _, reconstruction = simulation_context(evidence)
    source = write_fe_package(
        tmp_path / "synthetic-fe.zip",
        finite_element_manifest(str(reconstruction.id)),
    )

    result = SimulationModelImportService(store, evidence, 10_000_000).import_febio_package(source)

    assert result.simulation_model.reconstruction_id == reconstruction.id
    assert result.simulation_model.model_sha256
    assert result.mesh_quality.minimum_signed_tetrahedron_volume_mm3 > 0
    assert all(item["integrity"] == "verified" for item in result.artifact_integrity)
    assert evidence.get_simulation_model(result.simulation_model.id) == result.simulation_model


def test_fe_import_rejects_inverted_tetrahedron(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    evidence = SQLiteEvidenceRepository(tmp_path / "knee-twin.sqlite3")
    _, _, reconstruction = simulation_context(evidence)
    manifest = finite_element_manifest(str(reconstruction.id))
    manifest["elements"][0]["node_ids"] = [1, 3, 2, 4]
    source = write_fe_package(tmp_path / "inverted.zip", manifest)

    with pytest.raises(InvalidFiniteElementModelPackage, match="positive signed volume"):
        SimulationModelImportService(store, evidence, 10_000_000).import_febio_package(source)


def test_definition_requires_manual_values_and_deterministic_febio_xml(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    evidence = SQLiteEvidenceRepository(tmp_path / "knee-twin.sqlite3")
    _, _, reconstruction = simulation_context(evidence)
    package = FiniteElementModelPackageV1.model_validate(
        finite_element_manifest(str(reconstruction.id))
    )
    source = write_fe_package(tmp_path / "valid.zip", package.model_dump(mode="json"))
    model = SimulationModelImportService(store, evidence, 10_000_000).import_febio_package(
        source
    ).simulation_model
    definition = ExperimentDefinitionV2.model_validate(
        flexion_experiment(str(model.id), model.model_sha256)
    )

    validate_experiment_for_model(definition, model, package)
    first = build_febio_input(package, definition, 30)
    assert first == build_febio_input(package, definition, 30)
    assert b'febio_spec version="4.0"' in first
    assert b"prescribed-flexion" in first
    assert b">30<" in first
    assert b"tension-only linear spring" in first
    assert b"MeshDomains" in first
    assert b"rigid_euler_angles" in first
    assert b'surface_pair="tibiofemoral-contact"' in first
    root = ET.fromstring(first)
    assert root.find("./MeshDomains/SolidDomain[@name='femur']").attrib["mat"] == "femur"
    assert root.find("./Rigid/rigid_load[@type='rigid_force']/dof").text == "Rz"
    assert len(root.findall("./Discrete/discrete_material")) == 4
    assert root.find("./Output/plotfile").attrib["type"] == "vtk"

    incomplete = flexion_experiment(str(model.id), model.model_sha256)
    del incomplete["boundary"]["compressive_load"]
    with pytest.raises(ValidationError):
        ExperimentDefinitionV2.model_validate(incomplete)

    wrong_slack = ExperimentDefinitionV2.model_validate(
        flexion_experiment(str(model.id), model.model_sha256)
    )
    wrong_slack.ligaments[0].slack_length.value = 30
    wrong_slack.ligaments[0].slack_length.range = (30, 30)
    with pytest.raises(InvalidExperimentForModel, match="slack length must match"):
        validate_experiment_for_model(wrong_slack, model, package)


@pytest.mark.parametrize(
    ("path", "unit"),
    [
        (("contacts", 0, "penalty"), "MPa"),
        (("convergence", "maximum_reformations"), "iterations"),
    ],
)
def test_definition_rejects_unknown_units(path: tuple[object, ...], unit: str) -> None:
    definition = flexion_experiment(
        "11111111-1111-1111-1111-111111111111",
        "a" * 64,
    )
    target = definition
    for part in path:
        target = target[part]
    target["unit"] = unit

    with pytest.raises(ValidationError, match="units must be"):
        ExperimentDefinitionV2.model_validate(definition)


def test_model_manifest_is_canonical_json_serializable(tmp_path: Path) -> None:
    manifest = FiniteElementModelPackageV1.model_validate(
        finite_element_manifest("11111111-1111-1111-1111-111111111111")
    )
    assert json.loads(manifest.model_dump_json())["license"] == "CC0-1.0"


class FakeProcess:
    def __init__(self, command, cwd, **_kwargs) -> None:
        self.command = command
        self.cwd = Path(cwd)
        self.returncode = None
        self.terminated = False
        self.poll_count = 0
        log_name = command[command.index("-o") + 1]
        plot_name = command[command.index("-p") + 1]
        (self.cwd / log_name).write_text("NORMAL TERMINATION\n", encoding="utf-8")
        (self.cwd / f"{plot_name}.0.vtk").write_text(
            "# vtk DataFile Version 3.0\n", encoding="utf-8"
        )
        metrics_name = Path(command[command.index("-i") + 1]).stem + ".metrics.json"
        (self.cwd / metrics_name).write_text(
            json.dumps(
                {
                    "converged": True,
                    "contact_pressure_mpa": 2.5,
                    "reaction_force_n": 500,
                    "convergence_residual": 0.001,
                }
            ),
            encoding="utf-8",
        )

    def poll(self):
        self.poll_count += 1
        if self.poll_count > 1:
            self.returncode = 0
        return self.returncode

    def communicate(self, timeout=None):
        self.returncode = 0 if not self.terminated else -1
        return "FEBio 4.12 NORMAL TERMINATION", None

    def terminate(self):
        self.terminated = True
        self.returncode = -1

    def kill(self):
        self.terminated = True
        self.returncode = -9


def test_fake_febio_process_uses_argument_vector_and_normalizes_metrics(
    tmp_path: Path, monkeypatch
) -> None:
    captured = {}

    def start(command, **kwargs):
        captured["command"] = command
        return FakeProcess(command, **kwargs)

    monkeypatch.setattr("app.febio_adapter.subprocess.Popen", start)
    input_path = tmp_path / "flexion_030.feb"
    input_path.write_text("<febio_spec/>", encoding="utf-8")
    pose = _run_pose(
        tmp_path / "febio4.exe",
        input_path,
        tmp_path,
        30,
        timeout_seconds=5,
        is_cancelled=lambda: False,
    )

    assert isinstance(captured["command"], list)
    assert pose.status == "converged"
    assert pose.contact_pressure_mpa == 2.5
    assert pose.reaction_force_n == 500
    assert pose.field_artifact_reference == "flexion_030_fields.0.vtk"


def test_preflight_hashes_only_supported_febio_version(tmp_path: Path, monkeypatch) -> None:
    executable = tmp_path / "febio4.exe"
    executable.write_bytes(b"fixture executable")
    monkeypatch.setattr(
        "app.simulation_adapters.subprocess.run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[], returncode=0, stdout="FEBio version 4.12.0", stderr=""
        ),
    )

    capability = febio_preflight(str(executable), tmp_path)

    assert capability.available is True
    assert capability.detected_version == "4.12"
    assert len(capability.executable_sha256 or "") == 64


def test_normalizes_supported_febio_vtk_fields(tmp_path: Path) -> None:
    manifest = finite_element_manifest("11111111-1111-1111-1111-111111111111")
    package = FiniteElementModelPackageV1.model_validate(manifest)
    points = "\n".join(
        " ".join(map(str, node.position_mm)) for node in package.nodes
    )
    zeros = "\n".join("0 0 0" for _ in package.nodes)
    displacements = "\n".join(
        ["3 4 0", *("0 0 0" for _ in range(len(package.nodes) - 1))]
    )
    vtk = tmp_path / "fields.10.vtk"
    vtk.write_text(
        "\n".join(
            [
                "# vtk DataFile Version 3.0",
                "fixture",
                "ASCII",
                "DATASET UNSTRUCTURED_GRID",
                f"POINTS {len(package.nodes)} float",
                points,
                f"POINT_DATA {len(package.nodes)}",
                "VECTORS displacement float",
                displacements,
                "VECTORS reaction_forces float",
                zeros,
            ]
        ),
        encoding="utf-8",
    )

    metrics = _load_vtk_metrics(vtk, package)

    assert metrics["maximum_displacement_mm"] == pytest.approx(5)
    assert metrics["reaction_force_n"] == pytest.approx(0)
    assert metrics["maximum_ligament_strain"] == pytest.approx(0)
