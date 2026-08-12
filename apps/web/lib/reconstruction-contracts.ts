import type { JsonObject, Reconstruction } from "./evidence-contracts";

export const requiredKneeStructures = [
  "femur",
  "tibia",
  "fibula",
  "patella",
  "femoral_cartilage",
  "medial_tibial_cartilage",
  "lateral_tibial_cartilage",
  "patellar_cartilage",
  "medial_meniscus",
  "lateral_meniscus",
  "acl",
  "pcl",
  "mcl",
  "lcl",
  "quadriceps_tendon",
  "patellar_tendon",
  "quadriceps_musculotendon",
  "medial_hamstrings_musculotendon",
  "lateral_hamstrings_musculotendon",
  "medial_gastrocnemius_musculotendon",
  "lateral_gastrocnemius_musculotendon",
  "popliteus_musculotendon",
] as const;

export type KneeStructure = (typeof requiredKneeStructures)[number];

export type ReconstructionImportResultV1 = {
  schema_version: "1.0.0";
  reconstruction: Reconstruction;
  package: JsonObject;
  quality: {
    schema_version: "1.0.0";
    threshold_approval_state: "draft" | "approved";
    validation_status: "accepted" | "rejected" | "thresholds-unapproved";
    structures: JsonObject[];
  };
  artifact_integrity: JsonObject[];
  evidence_class: "expert-reviewed-reconstruction";
};

export function reconstructionEvidenceLabel(
  geometryClass: Reconstruction["geometry_class"],
): string {
  const labels: Record<Reconstruction["geometry_class"], string> = {
    generic: "Generic reference geometry",
    fitted: "Generic geometry fitted to evidence",
    "machine-segmented": "Machine-segmented geometry awaiting expert authority",
    "expert-reviewed": "Expert-reviewed reconstructed geometry",
    "patient-specific": "Validated patient-specific geometry",
  };
  return labels[geometryClass];
}
