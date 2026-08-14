import math
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.evidence import SimulationModel

REQUIRED_FLEXION_ANGLES = (0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0)
REQUIRED_MODEL_STRUCTURES = {
    "femur",
    "tibia",
    "femoral_cartilage",
    "medial_tibial_cartilage",
    "lateral_tibial_cartilage",
    "medial_meniscus",
    "lateral_meniscus",
}


class MeshNodeV1(BaseModel):
    id: int = Field(gt=0)
    position_mm: tuple[float, float, float]


class Tet4ElementV1(BaseModel):
    id: int = Field(gt=0)
    structure: str = Field(min_length=1)
    node_ids: tuple[int, int, int, int]


class SurfaceFacetV1(BaseModel):
    node_ids: tuple[int, int, int]


class NamedSurfaceV1(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    facets: list[SurfaceFacetV1] = Field(min_length=1)


class NamedNodeSetV1(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    node_ids: list[int] = Field(min_length=1)


class LigamentAttachmentV1(BaseModel):
    name: Literal["acl", "pcl", "mcl", "lcl"]
    origin_node_id: int = Field(gt=0)
    insertion_node_id: int = Field(gt=0)


class FiniteElementCoordinateSystemV1(BaseModel):
    name: str = Field(min_length=1)
    unit: Literal["mm"] = "mm"
    handedness: Literal["right-handed"] = "right-handed"
    laterality: Literal["left", "right"]


class MeshQualityV1(BaseModel):
    minimum_signed_tetrahedron_volume_mm3: float = Field(gt=0)
    duplicate_node_ids: Literal[0] = 0
    duplicate_element_ids: Literal[0] = 0
    orphan_node_count: int = Field(ge=0)


class FiniteElementModelPackageV1(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    reconstruction_id: UUID
    version: str = Field(min_length=1, max_length=100)
    adapter_id: Literal["febio-4.12"] = "febio-4.12"
    coordinate_system: FiniteElementCoordinateSystemV1
    nodes: list[MeshNodeV1] = Field(min_length=4)
    elements: list[Tet4ElementV1] = Field(min_length=1)
    surfaces: list[NamedSurfaceV1] = Field(min_length=1)
    node_sets: list[NamedNodeSetV1] = Field(min_length=2)
    ligament_attachments: list[LigamentAttachmentV1]
    included_structures: list[str] = Field(min_length=1)
    excluded_structures: list[str]
    source: str = Field(min_length=1)
    license: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_topology(self) -> "FiniteElementModelPackageV1":
        node_ids = [node.id for node in self.nodes]
        element_ids = [element.id for element in self.elements]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Finite-element node IDs must be unique.")
        if len(element_ids) != len(set(element_ids)):
            raise ValueError("Finite-element element IDs must be unique.")
        known_nodes = set(node_ids)
        referenced = {item for element in self.elements for item in element.node_ids}
        referenced |= {
            item for surface in self.surfaces for facet in surface.facets for item in facet.node_ids
        }
        referenced |= {item for node_set in self.node_sets for item in node_set.node_ids}
        referenced |= {
            item
            for attachment in self.ligament_attachments
            for item in (attachment.origin_node_id, attachment.insertion_node_id)
        }
        if not referenced <= known_nodes:
            raise ValueError("Finite-element topology references an unknown node ID.")
        if len({surface.name for surface in self.surfaces}) != len(self.surfaces):
            raise ValueError("Surface names must be unique.")
        node_set_names = {node_set.name for node_set in self.node_sets}
        if len(node_set_names) != len(self.node_sets):
            raise ValueError("Node-set names must be unique.")
        if not {"tibia_fixed", "femur_control"} <= node_set_names:
            raise ValueError("The model requires tibia_fixed and femur_control node sets.")
        structures = set(self.included_structures)
        if len(structures) != len(self.included_structures):
            raise ValueError("Included structures must be unique.")
        if structures & set(self.excluded_structures):
            raise ValueError("A structure cannot be both included and excluded.")
        if not REQUIRED_MODEL_STRUCTURES <= structures:
            missing = sorted(REQUIRED_MODEL_STRUCTURES - structures)
            raise ValueError("The first FEBio model is missing structures: " + ", ".join(missing))
        if {element.structure for element in self.elements} - structures:
            raise ValueError("Every element structure must be declared as included.")
        return self


class FiniteElementModelImportResultV1(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    simulation_model: SimulationModel
    package: FiniteElementModelPackageV1
    mesh_quality: MeshQualityV1
    artifact_integrity: list[dict[str, str | int | bool | None]]
    evidence_class: Literal["contributor-authored-finite-element-model"] = (
        "contributor-authored-finite-element-model"
    )


class FiniteElementModelImportJobRequestV1(BaseModel):
    upload_bundle_id: UUID


class SourcedScalarV2(BaseModel):
    value: float
    unit: str = Field(min_length=1)
    source: str = Field(min_length=1)
    range: tuple[float, float]
    rationale: str = Field(min_length=1)
    individual_measurement: bool
    evidence_class: Literal["observed", "reconstructed", "expert-assumption"]

    @model_validator(mode="after")
    def validate_range(self) -> "SourcedScalarV2":
        if not all(math.isfinite(item) for item in (self.value, *self.range)):
            raise ValueError("A sourced value and its range must be finite.")
        if self.range[0] > self.range[1]:
            raise ValueError("A sourced value range must be ordered low to high.")
        if self.range[0] > self.value or self.range[1] < self.value:
            raise ValueError("A sourced value must fall inside its declared range.")
        if self.individual_measurement and self.evidence_class == "expert-assumption":
            raise ValueError("An expert assumption is not an individual measurement.")
        return self


class MaterialAssumptionV1(BaseModel):
    structure: str = Field(min_length=1)
    model: Literal["neo-Hookean"] = "neo-Hookean"
    young_modulus: SourcedScalarV2
    poisson_ratio: SourcedScalarV2

    @model_validator(mode="after")
    def validate_units(self) -> "MaterialAssumptionV1":
        if self.young_modulus.unit != "MPa" or self.poisson_ratio.unit != "1":
            raise ValueError("Material units must be MPa for E and 1 for Poisson ratio.")
        if self.young_modulus.value <= 0:
            raise ValueError("Young's modulus must be positive.")
        if not -1 < self.poisson_ratio.value < 0.5:
            raise ValueError("Poisson ratio must be within (-1, 0.5).")
        return self


class LigamentAssumptionV1(BaseModel):
    structure: Literal["acl", "pcl", "mcl", "lcl"]
    stiffness: SourcedScalarV2
    slack_length: SourcedScalarV2

    @model_validator(mode="after")
    def validate_units(self) -> "LigamentAssumptionV1":
        if self.stiffness.unit != "N/mm" or self.slack_length.unit != "mm":
            raise ValueError("Ligament units must be N/mm and mm.")
        if self.stiffness.value <= 0 or self.slack_length.value <= 0:
            raise ValueError("Ligament stiffness and slack length must be positive.")
        return self


class ContactAssumptionV1(BaseModel):
    name: str = Field(min_length=1)
    primary_surface: str = Field(min_length=1)
    secondary_surface: str = Field(min_length=1)
    penalty: SourcedScalarV2
    friction_coefficient: SourcedScalarV2

    @model_validator(mode="after")
    def validate_contact(self) -> "ContactAssumptionV1":
        if self.penalty.unit != "1" or self.friction_coefficient.unit != "1":
            raise ValueError("Contact penalty and friction coefficient units must be 1.")
        if self.penalty.value <= 0 or self.friction_coefficient.value < 0:
            raise ValueError("Contact penalty must be positive and friction cannot be negative.")
        return self


class FlexionBoundaryAssumptionsV1(BaseModel):
    tibia_fixed_node_set: Literal["tibia_fixed"] = "tibia_fixed"
    femur_control_node_set: Literal["femur_control"] = "femur_control"
    compressive_load: SourcedScalarV2
    rotation_axis: Literal["x", "y", "z"]

    @model_validator(mode="after")
    def validate_load_unit(self) -> "FlexionBoundaryAssumptionsV1":
        if self.compressive_load.unit != "N":
            raise ValueError("The compressive load unit must be N.")
        if self.compressive_load.value <= 0:
            raise ValueError("The compressive load magnitude must be positive.")
        return self


class ConvergenceAssumptionsV1(BaseModel):
    displacement_tolerance: SourcedScalarV2
    energy_tolerance: SourcedScalarV2
    maximum_reformations: SourcedScalarV2
    timeout_seconds_per_pose: SourcedScalarV2

    @model_validator(mode="after")
    def validate_convergence(self) -> "ConvergenceAssumptionsV1":
        expected_units = (
            (self.displacement_tolerance, "mm"),
            (self.energy_tolerance, "1"),
            (self.maximum_reformations, "count"),
            (self.timeout_seconds_per_pose, "s"),
        )
        if any(item.unit != unit for item, unit in expected_units):
            raise ValueError("Convergence units must be mm, 1, count, and s respectively.")
        if any(item.value <= 0 for item, _unit in expected_units):
            raise ValueError("Every convergence value must be positive.")
        if not self.maximum_reformations.value.is_integer():
            raise ValueError("Maximum reformations must be an integer count.")
        return self


class ExperimentDefinitionV2(BaseModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    experiment_type: Literal["febio-tibiofemoral-flexion-sweep"]
    simulation_model_id: UUID
    simulation_model_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    scientific_question: Literal[
        "Under a manually specified compressive load, how do simulated tibiofemoral "
        "contact and strain fields change from 0 to 90 degrees of prescribed flexion?"
    ]
    flexion_angles_degrees: list[float]
    materials: list[MaterialAssumptionV1] = Field(min_length=1)
    ligaments: list[LigamentAssumptionV1]
    contacts: list[ContactAssumptionV1] = Field(min_length=1)
    boundary: FlexionBoundaryAssumptionsV1
    convergence: ConvergenceAssumptionsV1
    requested_outputs: list[
        Literal[
            "contact-pressure",
            "contact-area",
            "displacement",
            "cartilage-meniscus-strain",
            "ligament-strain",
            "reaction-force",
            "convergence-residual",
        ]
    ] = Field(min_length=1)
    software_versions: dict[str, str]
    validation_tier: Literal["synthetic", "integration", "research", "independent"]
    interpretation: Literal["exploratory-simulated-hypothesis"] = (
        "exploratory-simulated-hypothesis"
    )

    @model_validator(mode="after")
    def validate_sweep(self) -> "ExperimentDefinitionV2":
        if tuple(self.flexion_angles_degrees) != REQUIRED_FLEXION_ANGLES:
            raise ValueError("The v1 flexion sweep angles must be 0, 15, 30, 45, 60, 75, 90.")
        if len({item.structure for item in self.materials}) != len(self.materials):
            raise ValueError("Material assumptions must name each structure once.")
        if len({item.structure for item in self.ligaments}) != len(self.ligaments):
            raise ValueError("Ligament assumptions must name each structure once.")
        if len(set(self.requested_outputs)) != len(self.requested_outputs):
            raise ValueError("Requested outputs must be unique.")
        if not self.software_versions or any(
            not name.strip() or not version.strip()
            for name, version in self.software_versions.items()
        ):
            raise ValueError("Software names and versions must be explicit and non-empty.")
        return self


class FebioFlexionSweepRequestV1(BaseModel):
    virtual_experiment_id: UUID
    experiment: ExperimentDefinitionV2


class FlexionPoseResultV1(BaseModel):
    flexion_angle_degrees: float
    status: Literal["converged", "nonconverged", "failed", "cancelled"]
    contact_pressure_mpa: float | None = Field(default=None, ge=0)
    contact_area_mm2: float | None = Field(default=None, ge=0)
    maximum_displacement_mm: float | None = Field(default=None, ge=0)
    maximum_cartilage_meniscus_strain: float | None = Field(default=None, ge=0)
    maximum_ligament_strain: float | None = Field(default=None, ge=0)
    reaction_force_n: float | None = None
    convergence_residual: float | None = Field(default=None, ge=0)
    diagnostic: str | None = None
    field_artifact_reference: str | None = None
    normalized_field_manifest_reference: str | None = None


class NormalizedFieldValueV1(BaseModel):
    name: Literal[
        "contact-pressure",
        "contact-area",
        "displacement",
        "cartilage-meniscus-strain",
        "ligament-strain",
        "reaction-force",
        "convergence-residual",
    ]
    value: float | None
    unit: Literal["MPa", "mm2", "mm", "1", "N"]
    available: bool
    evidence_class: Literal["simulated"] = "simulated"


class NormalizedFieldManifestV1(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    flexion_angle_degrees: float
    pose_status: Literal["converged", "nonconverged", "failed", "cancelled"]
    source_field_artifact: str | None
    fields: list[NormalizedFieldValueV1]
    interpretation: Literal["exploratory-simulated-hypothesis"] = (
        "exploratory-simulated-hypothesis"
    )


class FebioFlexionSweepResultV1(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    experiment_definition_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    adapter_id: Literal["febio-4.12"] = "febio-4.12"
    solver_version: str
    solver_executable_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    interpretation: Literal["exploratory-simulated-hypothesis"] = (
        "exploratory-simulated-hypothesis"
    )
    poses: list[FlexionPoseResultV1] = Field(min_length=1)
    included_structures: list[str]
    excluded_structures: list[str]
    assumptions_complete: Literal[True] = True
    validation_tier: Literal["synthetic", "integration", "research", "independent"]


class SimulationAdapterCapabilityV1(BaseModel):
    adapter_id: Literal["febio-4.12"] = "febio-4.12"
    display_name: Literal["FEBio 4.12 tibiofemoral flexion sweep"] = (
        "FEBio 4.12 tibiofemoral flexion sweep"
    )
    available: bool
    executable_path: str | None
    executable_sha256: str | None
    detected_version: str | None
    supported_version: Literal["4.12"] = "4.12"
    required_modules: list[str] = ["solid"]
    capabilities: list[str] = ["independent-flexion-poses", "partial-results"]
    unavailable_reasons: list[str]


class SimulationAdapterListV1(BaseModel):
    adapters: list[SimulationAdapterCapabilityV1]
