import type { JsonObject, Reconstruction } from "./evidence-contracts";

export type SimulationModelV1 = {
  id: string;
  reconstruction_id: string;
  version: string;
  adapter_id: string;
  model_sha256: string;
  model_manifest: JsonObject;
  artifact_references: JsonObject;
  mesh_quality: JsonObject;
  included_structures: string[];
  excluded_structures: string[];
  validation_state: "structurally-valid" | "invalid";
  created_at: string;
};

export type SimulationAdapterV1 = {
  adapter_id: "febio-4.12";
  display_name: string;
  available: boolean;
  executable_path: string | null;
  executable_sha256: string | null;
  detected_version: string | null;
  supported_version: "4.12";
  required_modules: string[];
  capabilities: string[];
  unavailable_reasons: string[];
};

export type FiniteElementModelImportJobRequestV1 = {
  upload_bundle_id: string;
};

export type FiniteElementModelPackageV1 = {
  schema_version: "1.0.0";
  reconstruction_id: string;
  version: string;
  adapter_id: "febio-4.12";
  coordinate_system: {
    name: string;
    unit: "mm";
    handedness: "right-handed";
    laterality: "left" | "right";
  };
  nodes: { id: number; position_mm: [number, number, number] }[];
  elements: {
    id: number;
    structure: string;
    node_ids: [number, number, number, number];
  }[];
  surfaces: { name: string; facets: { node_ids: [number, number, number] }[] }[];
  node_sets: { name: string; node_ids: number[] }[];
  ligament_attachments: {
    name: "acl" | "pcl" | "mcl" | "lcl";
    origin_node_id: number;
    insertion_node_id: number;
  }[];
  included_structures: string[];
  excluded_structures: string[];
  source: string;
  license: string;
};

export type SourcedScalarV2 = {
  value: number;
  unit: string;
  source: string;
  range: [number, number];
  rationale: string;
  individual_measurement: boolean;
  evidence_class: "observed" | "reconstructed" | "expert-assumption";
};

export type ExperimentDefinitionV2 = {
  schema_version: "2.0.0";
  experiment_type: "febio-tibiofemoral-flexion-sweep";
  simulation_model_id: string;
  simulation_model_sha256: string;
  scientific_question: string;
  flexion_angles_degrees: number[];
  materials: {
    structure: string;
    model: "neo-Hookean";
    young_modulus: SourcedScalarV2;
    poisson_ratio: SourcedScalarV2;
  }[];
  ligaments: {
    structure: "acl" | "pcl" | "mcl" | "lcl";
    stiffness: SourcedScalarV2;
    slack_length: SourcedScalarV2;
  }[];
  contacts: {
    name: string;
    primary_surface: string;
    secondary_surface: string;
    penalty: SourcedScalarV2;
    friction_coefficient: SourcedScalarV2;
  }[];
  boundary: {
    tibia_fixed_node_set: "tibia_fixed";
    femur_control_node_set: "femur_control";
    compressive_load: SourcedScalarV2;
    rotation_axis: "x" | "y" | "z";
  };
  convergence: {
    displacement_tolerance: SourcedScalarV2;
    energy_tolerance: SourcedScalarV2;
    maximum_reformations: SourcedScalarV2;
    timeout_seconds_per_pose: SourcedScalarV2;
  };
  requested_outputs: NormalizedFieldValueV1["name"][];
  software_versions: Record<string, string>;
  validation_tier: "synthetic" | "integration" | "research" | "independent";
  interpretation: "exploratory-simulated-hypothesis";
};

export type NormalizedFieldValueV1 = {
  name:
    | "contact-pressure"
    | "contact-area"
    | "displacement"
    | "cartilage-meniscus-strain"
    | "ligament-strain"
    | "reaction-force"
    | "convergence-residual";
  value: number | null;
  unit: "MPa" | "mm2" | "mm" | "1" | "N";
  available: boolean;
  evidence_class: "simulated";
};

export type NormalizedFieldManifestV1 = {
  schema_version: "1.0.0";
  flexion_angle_degrees: number;
  pose_status: "converged" | "nonconverged" | "failed" | "cancelled";
  source_field_artifact: string | null;
  fields: NormalizedFieldValueV1[];
  interpretation: "exploratory-simulated-hypothesis";
};

export type FlexionPoseResultV1 = {
  flexion_angle_degrees: number;
  status: "converged" | "nonconverged" | "failed" | "cancelled";
  contact_pressure_mpa: number | null;
  contact_area_mm2: number | null;
  maximum_displacement_mm: number | null;
  maximum_cartilage_meniscus_strain: number | null;
  maximum_ligament_strain: number | null;
  reaction_force_n: number | null;
  convergence_residual: number | null;
  diagnostic: string | null;
  field_artifact_reference: string | null;
  normalized_field_manifest_reference: string | null;
};

export type FebioFlexionSweepResultV1 = {
  schema_version: "1.0.0";
  experiment_definition_sha256: string;
  adapter_id: "febio-4.12";
  solver_version: string;
  solver_executable_sha256: string;
  interpretation: "exploratory-simulated-hypothesis";
  poses: FlexionPoseResultV1[];
  included_structures: string[];
  excluded_structures: string[];
  assumptions_complete: true;
  validation_tier: "synthetic" | "integration" | "research" | "independent";
};

function record(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseSimulationModels(value: unknown): SimulationModelV1[] | null {
  if (!record(value) || !Array.isArray(value.simulation_models)) return null;
  return value.simulation_models.every(
    (item) =>
      record(item) &&
      typeof item.id === "string" &&
      typeof item.reconstruction_id === "string" &&
      typeof item.version === "string" &&
      typeof item.adapter_id === "string" &&
      typeof item.model_sha256 === "string" &&
      Array.isArray(item.included_structures) &&
      Array.isArray(item.excluded_structures),
  )
    ? (value.simulation_models as SimulationModelV1[])
    : null;
}

export function parseSimulationAdapters(value: unknown): SimulationAdapterV1[] | null {
  if (!record(value) || !Array.isArray(value.adapters)) return null;
  return value.adapters.every(
    (item) =>
      record(item) &&
      item.adapter_id === "febio-4.12" &&
      typeof item.available === "boolean" &&
      Array.isArray(item.unavailable_reasons),
  )
    ? (value.adapters as SimulationAdapterV1[])
    : null;
}

export function parseFlexionResult(value: unknown): FebioFlexionSweepResultV1 | null {
  if (
    !record(value) ||
    value.schema_version !== "1.0.0" ||
    value.interpretation !== "exploratory-simulated-hypothesis" ||
    !Array.isArray(value.poses)
  ) {
    return null;
  }
  return value.poses.every(
    (pose) =>
      record(pose) &&
      typeof pose.flexion_angle_degrees === "number" &&
      ["converged", "nonconverged", "failed", "cancelled"].includes(String(pose.status)),
  )
    ? (value as FebioFlexionSweepResultV1)
    : null;
}

const sourced = (value: number, unit: string): SourcedScalarV2 => ({
  value,
  unit,
  source: "Knee Twin CC0 synthetic fixture manifest",
  range: [value, value],
  rationale: "Explicit fixture-only assumption; not a patient measurement.",
  individual_measurement: false,
  evidence_class: "expert-assumption",
});

export function syntheticExperimentTemplate(model: SimulationModelV1): ExperimentDefinitionV2 {
  const deformable = [
    "femoral_cartilage",
    "medial_tibial_cartilage",
    "lateral_tibial_cartilage",
    "medial_meniscus",
    "lateral_meniscus",
  ];
  return {
    schema_version: "2.0.0",
    experiment_type: "febio-tibiofemoral-flexion-sweep",
    simulation_model_id: model.id,
    simulation_model_sha256: model.model_sha256,
    scientific_question:
      "Under a manually specified compressive load, how do simulated tibiofemoral contact and strain fields change from 0 to 90 degrees of prescribed flexion?",
    flexion_angles_degrees: [0, 15, 30, 45, 60, 75, 90],
    materials: deformable.map((structure) => ({
      structure,
      model: "neo-Hookean",
      young_modulus: sourced(5, "MPa"),
      poisson_ratio: sourced(0.45, "1"),
    })),
    ligaments: (["acl", "pcl", "mcl", "lcl"] as const).map((structure) => ({
      structure,
      stiffness: sourced(50, "N/mm"),
      slack_length: sourced(4, "mm"),
    })),
    contacts: [
      {
        name: "tibiofemoral-contact",
        primary_surface: "femoral_contact",
        secondary_surface: "tibial_contact",
        penalty: sourced(1, "1"),
        friction_coefficient: sourced(0, "1"),
      },
    ],
    boundary: {
      tibia_fixed_node_set: "tibia_fixed",
      femur_control_node_set: "femur_control",
      compressive_load: sourced(500, "N"),
      rotation_axis: "x",
    },
    convergence: {
      displacement_tolerance: sourced(0.001, "mm"),
      energy_tolerance: sourced(0.01, "1"),
      maximum_reformations: sourced(25, "count"),
      timeout_seconds_per_pose: sourced(30, "s"),
    },
    requested_outputs: [
      "contact-pressure",
      "contact-area",
      "displacement",
      "cartilage-meniscus-strain",
      "ligament-strain",
      "reaction-force",
      "convergence-residual",
    ],
    software_versions: { "knee-twin": "milestone-14", febio: "4.12" },
    validation_tier: "synthetic",
    interpretation: "exploratory-simulated-hypothesis",
  };
}

export function reconstructionForModel(
  model: SimulationModelV1,
  reconstructions: Reconstruction[],
): Reconstruction | null {
  return reconstructions.find((item) => item.id === model.reconstruction_id) ?? null;
}
