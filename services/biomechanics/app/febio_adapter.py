import hashlib
import json
import math
import subprocess
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

from app.schemas.evidence import SimulationModel
from app.schemas.simulation import (
    ExperimentDefinitionV2,
    FiniteElementModelPackageV1,
    FlexionPoseResultV1,
    NormalizedFieldManifestV1,
    NormalizedFieldValueV1,
)
from app.simulation_adapters import febio_preflight


class FebioAdapterUnavailable(RuntimeError):
    pass


class InvalidExperimentForModel(ValueError):
    pass


class FebioFlexionSweepAdapter:
    adapter_id = "febio-4.12"

    def __init__(self, configured_executable: str | None) -> None:
        self.configured_executable = configured_executable

    def execute(
        self,
        experiment: ExperimentDefinitionV2,
        simulation_model: SimulationModel,
        workdir: Path,
        *,
        is_cancelled: Callable[[], bool],
        report_progress: Callable[[float, str], None],
    ) -> tuple[list[FlexionPoseResultV1], str, str, bool]:
        capability = febio_preflight(self.configured_executable, workdir)
        if not capability.available or capability.executable_path is None:
            raise FebioAdapterUnavailable("; ".join(capability.unavailable_reasons))
        package = FiniteElementModelPackageV1.model_validate(simulation_model.model_manifest)
        validate_experiment_for_model(experiment, simulation_model, package)
        executable = Path(capability.executable_path)
        poses: list[FlexionPoseResultV1] = []
        total = len(experiment.flexion_angles_degrees)
        cancelled = False
        for index, angle in enumerate(experiment.flexion_angles_degrees):
            if is_cancelled():
                cancelled = True
                poses.extend(
                    FlexionPoseResultV1(
                        flexion_angle_degrees=pending,
                        status="cancelled",
                        diagnostic="Cancelled before this independent pose started.",
                    )
                    for pending in experiment.flexion_angles_degrees[index:]
                )
                break
            stem = f"flexion_{int(angle):03d}"
            input_path = workdir / f"{stem}.feb"
            input_path.write_bytes(build_febio_input(package, experiment, angle))
            pose = _run_pose(
                executable,
                input_path,
                workdir,
                angle,
                timeout_seconds=experiment.convergence.timeout_seconds_per_pose.value,
                is_cancelled=is_cancelled,
                package=package,
                experiment=experiment,
            )
            manifest_name = f"{stem}.normalized_fields_v1.json"
            pose.normalized_field_manifest_reference = manifest_name
            (workdir / manifest_name).write_text(
                json.dumps(
                    _normalized_field_manifest(pose).model_dump(mode="json"),
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            poses.append(pose)
            report_progress(
                0.1 + 0.8 * ((index + 1) / total),
                f"pose-{int(angle):03d}-{pose.status}",
            )
            if pose.status == "cancelled":
                cancelled = True
                poses.extend(
                    FlexionPoseResultV1(
                        flexion_angle_degrees=pending,
                        status="cancelled",
                        diagnostic="Cancelled before this independent pose started.",
                    )
                    for pending in experiment.flexion_angles_degrees[index + 1 :]
                )
                break
        return (
            poses,
            capability.detected_version or "unknown",
            capability.executable_sha256 or "0" * 64,
            cancelled,
        )


def _normalized_field_manifest(
    pose: FlexionPoseResultV1,
) -> NormalizedFieldManifestV1:
    values = (
        ("contact-pressure", pose.contact_pressure_mpa, "MPa"),
        ("contact-area", pose.contact_area_mm2, "mm2"),
        ("displacement", pose.maximum_displacement_mm, "mm"),
        (
            "cartilage-meniscus-strain",
            pose.maximum_cartilage_meniscus_strain,
            "1",
        ),
        ("ligament-strain", pose.maximum_ligament_strain, "1"),
        ("reaction-force", pose.reaction_force_n, "N"),
        ("convergence-residual", pose.convergence_residual, "1"),
    )
    return NormalizedFieldManifestV1(
        flexion_angle_degrees=pose.flexion_angle_degrees,
        pose_status=pose.status,
        source_field_artifact=pose.field_artifact_reference,
        fields=[
            NormalizedFieldValueV1(
                name=name,
                value=value,
                unit=unit,
                available=value is not None,
            )
            for name, value, unit in values
        ],
    )


def validate_experiment_for_model(
    experiment: ExperimentDefinitionV2,
    simulation_model: SimulationModel,
    package: FiniteElementModelPackageV1,
) -> None:
    if experiment.simulation_model_id != simulation_model.id:
        raise InvalidExperimentForModel("Experiment and simulation model IDs differ.")
    if experiment.simulation_model_sha256 != simulation_model.model_sha256:
        raise InvalidExperimentForModel("Experiment simulation-model SHA-256 is stale or wrong.")
    if simulation_model.adapter_id != "febio-4.12":
        raise InvalidExperimentForModel("The simulation model does not support this adapter.")
    included = set(package.included_structures)
    material_structures = {material.structure for material in experiment.materials}
    required_materials = included - {"femur", "tibia", "acl", "pcl", "mcl", "lcl"}
    if material_structures != required_materials:
        raise InvalidExperimentForModel(
            "Material assumptions must cover every included deformable structure exactly."
        )
    attachments = {attachment.name for attachment in package.ligament_attachments}
    assumptions = {ligament.structure for ligament in experiment.ligaments}
    if attachments != assumptions:
        raise InvalidExperimentForModel(
            "Ligament assumptions must match every declared attachment exactly."
        )
    nodes = {node.id: node.position_mm for node in package.nodes}
    attachment_by_name = {item.name: item for item in package.ligament_attachments}
    for ligament in experiment.ligaments:
        attachment = attachment_by_name[ligament.structure]
        geometric_length = math.dist(
            nodes[attachment.origin_node_id], nodes[attachment.insertion_node_id]
        )
        if not math.isclose(
            ligament.slack_length.value,
            geometric_length,
            rel_tol=1e-6,
            abs_tol=1e-6,
        ):
            raise InvalidExperimentForModel(
                f"{ligament.structure} slack length must match its v1 connector geometry "
                f"({geometric_length:.12g} mm)."
            )
    surfaces = {surface.name for surface in package.surfaces}
    for contact in experiment.contacts:
        if {contact.primary_surface, contact.secondary_surface} - surfaces:
            raise InvalidExperimentForModel("Contact assumptions reference an unknown surface.")


def build_febio_input(
    package: FiniteElementModelPackageV1,
    experiment: ExperimentDefinitionV2,
    flexion_angle_degrees: float,
) -> bytes:
    root = ET.Element("febio_spec", {"version": "4.0"})
    ET.SubElement(root, "Module", {"type": "solid"})
    control = ET.SubElement(root, "Control")
    ET.SubElement(control, "analysis").text = "STATIC"
    ET.SubElement(control, "time_steps").text = "10"
    ET.SubElement(control, "step_size").text = "0.1"
    ET.SubElement(control, "dtol").text = _number(
        experiment.convergence.displacement_tolerance.value
    )
    ET.SubElement(control, "etol").text = _number(experiment.convergence.energy_tolerance.value)
    ET.SubElement(control, "max_refs").text = str(
        int(experiment.convergence.maximum_reformations.value)
    )
    ET.SubElement(control, "symmetric_stiffness").text = "0"

    material_section = ET.SubElement(root, "Material")
    material_ids: dict[str, int] = {"femur": 1, "tibia": 2}
    for material_id, structure in enumerate(("femur", "tibia"), start=1):
        item = ET.SubElement(
            material_section,
            "material",
            {"id": str(material_id), "name": structure, "type": "rigid body"},
        )
        ET.SubElement(item, "density").text = "1"
    for material_id, assumption in enumerate(experiment.materials, start=3):
        material_ids[assumption.structure] = material_id
        item = ET.SubElement(
            material_section,
            "material",
            {
                "id": str(material_id),
                "name": assumption.structure,
                "type": assumption.model,
            },
        )
        ET.SubElement(item, "E").text = _number(assumption.young_modulus.value)
        ET.SubElement(item, "v").text = _number(assumption.poisson_ratio.value)

    geometry = ET.SubElement(root, "Mesh")
    nodes = ET.SubElement(geometry, "Nodes", {"name": "knee_nodes"})
    for node in package.nodes:
        ET.SubElement(nodes, "node", {"id": str(node.id)}).text = ",".join(
            _number(value) for value in node.position_mm
        )
    for structure in sorted({element.structure for element in package.elements}):
        if structure not in material_ids:
            continue
        elements = ET.SubElement(
            geometry,
            "Elements",
            {
                "type": "tet4",
                "name": structure,
            },
        )
        for element in package.elements:
            if element.structure == structure:
                ET.SubElement(elements, "elem", {"id": str(element.id)}).text = ",".join(
                    str(node_id) for node_id in element.node_ids
                )
    for node_set in package.node_sets:
        item = ET.SubElement(geometry, "NodeSet", {"name": node_set.name})
        for node_id in node_set.node_ids:
            ET.SubElement(item, "node", {"id": str(node_id)})
    for surface in package.surfaces:
        item = ET.SubElement(geometry, "Surface", {"name": surface.name})
        for index, facet in enumerate(surface.facets, start=1):
            ET.SubElement(item, "tri3", {"id": str(index)}).text = ",".join(
                str(node_id) for node_id in facet.node_ids
            )
    for assumption in experiment.contacts:
        pair = ET.SubElement(geometry, "SurfacePair", {"name": assumption.name})
        ET.SubElement(pair, "primary").text = assumption.primary_surface
        ET.SubElement(pair, "secondary").text = assumption.secondary_surface
    for attachment in package.ligament_attachments:
        discrete_set = ET.SubElement(
            geometry, "DiscreteSet", {"name": f"ligament-{attachment.name}"}
        )
        ET.SubElement(discrete_set, "delem").text = (
            f"{attachment.origin_node_id},{attachment.insertion_node_id}"
        )

    domains = ET.SubElement(root, "MeshDomains")
    for structure in sorted({element.structure for element in package.elements}):
        ET.SubElement(
            domains,
            "SolidDomain",
            {"name": structure, "mat": structure},
        )

    rigid = ET.SubElement(root, "Rigid")
    tibia_fixed = ET.SubElement(
        rigid, "rigid_bc", {"name": "fix-tibia", "type": "rigid_fixed"}
    )
    ET.SubElement(tibia_fixed, "rb").text = "tibia"
    for degree in ("Rx", "Ry", "Rz", "Ru", "Rv", "Rw"):
        ET.SubElement(tibia_fixed, f"{degree}_dof").text = "1"
    femur_translation = ET.SubElement(
        rigid,
        "rigid_bc",
        {"name": "guide-femur-compression", "type": "rigid_fixed"},
    )
    ET.SubElement(femur_translation, "rb").text = "femur"
    for degree, fixed in (
        ("Rx", 1),
        ("Ry", 1),
        ("Rz", 0),
        ("Ru", 0),
        ("Rv", 0),
        ("Rw", 0),
    ):
        ET.SubElement(femur_translation, f"{degree}_dof").text = str(fixed)
    prescribed = ET.SubElement(
        rigid,
        "rigid_bc",
        {"name": "prescribed-flexion", "type": "rigid_euler_angles"},
    )
    ET.SubElement(prescribed, "rb").text = "femur"
    axis_tag = {"x": "Ex", "y": "Ey", "z": "Ez"}[experiment.boundary.rotation_axis]
    for tag in ("Ex", "Ey", "Ez"):
        value = ET.SubElement(prescribed, tag)
        if tag == axis_tag:
            value.set("lc", "1")
            value.text = _number(flexion_angle_degrees)
        else:
            value.text = "0"
    load = ET.SubElement(
        rigid,
        "rigid_load",
        {"name": "manual-compressive-load", "type": "rigid_force"},
    )
    ET.SubElement(load, "rb").text = "femur"
    ET.SubElement(load, "dof").text = "Rz"
    load_value = ET.SubElement(load, "value", {"lc": "1"})
    load_value.text = _number(-experiment.boundary.compressive_load.value)
    ET.SubElement(load, "load_type").text = "LOAD"
    ET.SubElement(load, "relative").text = "0"

    contact_section = ET.SubElement(root, "Contact")
    for assumption in experiment.contacts:
        contact = ET.SubElement(
            contact_section,
            "contact",
            {
                "name": assumption.name,
                "surface_pair": assumption.name,
                "type": "sliding-elastic",
            },
        )
        ET.SubElement(contact, "penalty").text = _number(assumption.penalty.value)
        ET.SubElement(contact, "fric_coeff").text = _number(
            assumption.friction_coefficient.value
        )

    discrete = ET.SubElement(root, "Discrete")
    assumption_by_name = {item.structure: item for item in experiment.ligaments}
    for material_id, attachment in enumerate(package.ligament_attachments, start=1):
        ligament = assumption_by_name[attachment.name]
        material = ET.SubElement(
            discrete,
            "discrete_material",
            {
                "id": str(material_id),
                "name": f"ligament-{attachment.name}",
                "type": "tension-only linear spring",
            },
        )
        ET.SubElement(material, "E").text = _number(ligament.stiffness.value)
        ET.SubElement(
            discrete,
            "discrete",
            {
                "dmat": str(material_id),
                "discrete_set": f"ligament-{attachment.name}",
            },
        )

    load_data = ET.SubElement(root, "LoadData")
    controller = ET.SubElement(
        load_data,
        "load_controller",
        {"id": "1", "name": "linear-ramp", "type": "loadcurve"},
    )
    ET.SubElement(controller, "interpolate").text = "LINEAR"
    ET.SubElement(controller, "extend").text = "CONSTANT"
    points = ET.SubElement(controller, "points")
    ET.SubElement(points, "pt").text = "0,0"
    ET.SubElement(points, "pt").text = "1,1"

    output = ET.SubElement(root, "Output")
    plotfile = ET.SubElement(output, "plotfile", {"type": "vtk"})
    for variable in (
        "displacement",
        "Lagrange strain",
        "contact pressure",
        "reaction forces",
        "discrete element stretch",
        "discrete element force",
    ):
        ET.SubElement(plotfile, "var", {"type": variable})
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def _run_pose(
    executable: Path,
    input_path: Path,
    workdir: Path,
    angle: float,
    *,
    timeout_seconds: float,
    is_cancelled: Callable[[], bool],
    package: FiniteElementModelPackageV1 | None = None,
    experiment: ExperimentDefinitionV2 | None = None,
) -> FlexionPoseResultV1:
    stem = input_path.stem
    log_path = workdir / f"{stem}.log"
    plot_stem = f"{stem}_fields"
    stdout_path = workdir / f"{stem}.stdout.txt"
    stderr_path = workdir / f"{stem}.stderr.txt"
    command = [
        str(executable),
        "-i",
        input_path.name,
        "-o",
        log_path.name,
        "-p",
        plot_stem,
    ]
    started = time.monotonic()
    try:
        with (
            stdout_path.open("w", encoding="utf-8") as stdout_stream,
            stderr_path.open("w", encoding="utf-8") as stderr_stream,
        ):
            process = subprocess.Popen(
                command,
                cwd=workdir,
                stdout=stdout_stream,
                stderr=stderr_stream,
                text=True,
            )
            cancelled = False
            timed_out = False
            while process.poll() is None:
                if is_cancelled():
                    cancelled = True
                    process.terminate()
                    break
                if time.monotonic() - started > timeout_seconds:
                    timed_out = True
                    process.terminate()
                    break
                time.sleep(0.05)
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
    except OSError as error:
        return FlexionPoseResultV1(
            flexion_angle_degrees=angle,
            status="failed",
            diagnostic=f"FEBio could not start: {error}",
        )
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    if cancelled:
        return FlexionPoseResultV1(
            flexion_angle_degrees=angle,
            status="cancelled",
            diagnostic="FEBio process was terminated after cancellation was requested.",
        )
    if timed_out:
        return FlexionPoseResultV1(
            flexion_angle_degrees=angle,
            status="failed",
            diagnostic=f"FEBio exceeded the manual {timeout_seconds:g} second timeout.",
        )
    metrics_path = workdir / f"{stem}.metrics.json"
    metrics = _load_metrics(metrics_path)
    field_path = _latest_vtk(workdir, plot_stem)
    if field_path is not None:
        metrics = {**_load_vtk_metrics(field_path, package, experiment), **metrics}
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
    converged = process.returncode == 0 and (
        metrics.get("converged") is True
        or "NORMAL TERMINATION" in (
            stdout_text + "\n" + stderr_text + "\n" + log_text
        ).upper()
    )
    if process.returncode != 0:
        status = "failed"
        diagnostic = f"FEBio exited with code {process.returncode}."
    elif not converged:
        status = "nonconverged"
        diagnostic = "FEBio returned without an independently detected converged solution."
    else:
        status = "converged"
        diagnostic = None
    return FlexionPoseResultV1(
        flexion_angle_degrees=angle,
        status=status,
        contact_pressure_mpa=_optional_number(metrics, "contact_pressure_mpa"),
        contact_area_mm2=_optional_number(metrics, "contact_area_mm2"),
        maximum_displacement_mm=_optional_number(metrics, "maximum_displacement_mm"),
        maximum_cartilage_meniscus_strain=_optional_number(
            metrics, "maximum_cartilage_meniscus_strain"
        ),
        maximum_ligament_strain=_optional_number(metrics, "maximum_ligament_strain"),
        reaction_force_n=_optional_number(metrics, "reaction_force_n"),
        convergence_residual=_optional_number(metrics, "convergence_residual"),
        diagnostic=diagnostic,
        field_artifact_reference=field_path.name if field_path is not None else None,
    )


def _load_metrics(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _optional_number(values: dict[str, object], name: str) -> float | None:
    value = values.get(name)
    return float(value) if isinstance(value, int | float) else None


def _latest_vtk(workdir: Path, plot_stem: str) -> Path | None:
    candidates = list(workdir.glob(f"{plot_stem}.*.vtk"))
    if not candidates:
        direct = workdir / f"{plot_stem}.vtk"
        return direct if direct.is_file() else None

    def sequence(path: Path) -> int:
        suffix = path.name.removeprefix(plot_stem + ".").removesuffix(".vtk")
        return int(suffix) if suffix.isdigit() else -1

    return max(candidates, key=sequence)


def _load_vtk_metrics(
    path: Path,
    package: FiniteElementModelPackageV1 | None,
    experiment: ExperimentDefinitionV2 | None = None,
) -> dict[str, object]:
    """Normalize supported ASCII FEBio VTK arrays; unavailable fields remain absent."""
    try:
        lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    except (OSError, UnicodeError):
        return {}
    arrays: dict[str, list[tuple[float, ...]]] = {}
    points: list[tuple[float, float, float]] = []
    item_count = 0
    index = 0
    try:
        while index < len(lines):
            parts = lines[index].split()
            if not parts:
                index += 1
                continue
            if parts[0] == "POINTS" and len(parts) >= 2:
                count = int(parts[1])
                points = [
                    tuple(map(float, lines[index + offset + 1].split()))
                    for offset in range(count)
                ]
                index += count + 1
                continue
            if parts[0] in {"POINT_DATA", "CELL_DATA"} and len(parts) >= 2:
                item_count = int(parts[1])
            elif parts[0] == "SCALARS" and len(parts) >= 2 and item_count:
                name = parts[1]
                index += 2
                arrays[name] = [
                    (float(lines[index + offset]),) for offset in range(item_count)
                ]
                index += item_count
                continue
            elif parts[0] == "VECTORS" and len(parts) >= 2 and item_count:
                name = parts[1]
                arrays[name] = [
                    tuple(map(float, lines[index + offset + 1].split()))
                    for offset in range(item_count)
                ]
                index += item_count + 1
                continue
            elif parts[0] == "TENSORS" and len(parts) >= 2 and item_count:
                name = parts[1]
                values = []
                cursor = index + 1
                for _ in range(item_count):
                    tensor = tuple(
                        float(value)
                        for row in lines[cursor : cursor + 3]
                        for value in row.split()
                    )
                    values.append(tensor)
                    cursor += 3
                    while cursor < len(lines) and not lines[cursor].strip():
                        cursor += 1
                arrays[name] = values
                index = cursor
                continue
            index += 1
    except (ValueError, IndexError):
        return {}

    normalized: dict[str, object] = {}
    displacement = arrays.get("displacement")
    if displacement:
        normalized["maximum_displacement_mm"] = max(
            math.dist((0, 0, 0), item) for item in displacement
        )
    pressure = arrays.get("contact_pressure")
    if pressure:
        normalized["contact_pressure_mpa"] = max(abs(item[0]) for item in pressure)
    reactions = arrays.get("reaction_forces")
    if reactions:
        indices = range(len(reactions))
        if package is not None:
            tibia_nodes = next(
                item.node_ids for item in package.node_sets if item.name == "tibia_fixed"
            )
            node_index = {node.id: index for index, node in enumerate(package.nodes)}
            indices = [node_index[node_id] for node_id in tibia_nodes]
        normalized["reaction_force_n"] = abs(sum(reactions[index][2] for index in indices))
    strain = arrays.get("Lagrange_strain")
    if strain:
        selected = strain
        if package is not None and len(strain) == len(package.elements):
            tissue_structures = {
                "femoral_cartilage",
                "medial_tibial_cartilage",
                "lateral_tibial_cartilage",
                "medial_meniscus",
                "lateral_meniscus",
            }
            ordered_elements = [
                element
                for structure in sorted({item.structure for item in package.elements})
                for element in package.elements
                if element.structure == structure
            ]
            selected = [
                value
                for value, element in zip(strain, ordered_elements, strict=True)
                if element.structure in tissue_structures
            ]
        normalized["maximum_cartilage_meniscus_strain"] = max(
            math.sqrt(sum(component * component for component in item))
            for item in selected
        )
    if package is not None and points and len(points) == len(package.nodes):
        point_by_id = {node.id: points[index] for index, node in enumerate(package.nodes)}
        ligament_strains = []
        reference_point_by_id = {node.id: node.position_mm for node in package.nodes}
        for attachment in package.ligament_attachments:
            reference = math.dist(
                reference_point_by_id[attachment.origin_node_id],
                reference_point_by_id[attachment.insertion_node_id],
            )
            current = math.dist(
                point_by_id[attachment.origin_node_id],
                point_by_id[attachment.insertion_node_id],
            )
            ligament_strains.append(max(0.0, (current - reference) / reference))
        if ligament_strains:
            normalized["maximum_ligament_strain"] = max(ligament_strains)
        if (
            experiment is not None
            and pressure
            and len(pressure) == len(points)
        ):
            surface_by_name = {surface.name: surface for surface in package.surfaces}
            area = 0.0
            node_index = {node.id: index for index, node in enumerate(package.nodes)}
            for contact in experiment.contacts:
                for facet in surface_by_name[contact.secondary_surface].facets:
                    indices = [node_index[node_id] for node_id in facet.node_ids]
                    if max(abs(pressure[index][0]) for index in indices) <= 0:
                        continue
                    a, b, c = (points[index] for index in indices)
                    ab = tuple(b[i] - a[i] for i in range(3))
                    ac = tuple(c[i] - a[i] for i in range(3))
                    cross = (
                        ab[1] * ac[2] - ab[2] * ac[1],
                        ab[2] * ac[0] - ab[0] * ac[2],
                        ab[0] * ac[1] - ab[1] * ac[0],
                    )
                    area += 0.5 * math.sqrt(sum(value * value for value in cross))
            normalized["contact_area_mm2"] = area
    return normalized


def definition_sha256(experiment: ExperimentDefinitionV2) -> str:
    payload = json.dumps(
        experiment.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _number(value: float) -> str:
    return format(value, ".12g")
