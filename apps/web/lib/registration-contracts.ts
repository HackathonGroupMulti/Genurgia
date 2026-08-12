import type { JsonObject } from "./evidence-contracts";

export type RegistrationUncertaintyV1 = {
  method: "synthetic-perturbation" | "bootstrap" | "not-evaluated";
  translation_95_mm: number | null;
  rotation_95_degrees: number | null;
  explanation: string;
};

export type FunctionalRegistrationResultV1 = {
  schema_version: "1.0.0";
  method: "calibrated-dlt-kabsch-v1";
  source_coordinate_system: "capture-volume-right-handed-mm";
  target_coordinate_system: "dicom-patient-lps-mm";
  frames: JsonObject[];
  projected_landmark_residual_rms_mm: number;
  coverage_ratio: number;
  uncertainty: RegistrationUncertaintyV1;
  validation_tier: "synthetic" | "paired-laboratory" | "independent";
};

export type ArthroscopyOverlayResultV1 = {
  schema_version: "1.0.0";
  method: "expert-seed-pnp-v1";
  rms_reprojection_error_px: number;
  visible_coverage_ratio: number;
  uncertainty: RegistrationUncertaintyV1;
  gate_status: "pass" | "fail";
} & JsonObject;

export function registrationEvidenceLabel(
  tier: FunctionalRegistrationResultV1["validation_tier"],
): string {
  return {
    synthetic: "Synthetic known-transform registration",
    "paired-laboratory": "Registration compared with a paired laboratory reference",
    independent: "Independently validated registration",
  }[tier];
}
