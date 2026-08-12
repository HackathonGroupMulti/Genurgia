import type { JsonObject } from "./evidence-contracts";

export type JobV1 = {
  id: string;
  job_type: string;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  progress: number;
  request: JsonObject;
  result_artifact_reference: string | null;
  attempts: number;
  cancel_requested: boolean;
  error_detail: string | null;
};

export type MotionReplayResultV1 = {
  schema_version: "1.0.0";
  experiment_definition_sha256: string;
  frame_count: number;
  included_frame_count: number;
  excluded_intervals: JsonObject[];
  residual_rms_mm: number | null;
  maximum_transform_uncertainty_mm: number;
  anatomical_constraint_violations: JsonObject[];
  registration_sensitivity: JsonObject;
  validation_tier: "synthetic" | "integration" | "research" | "independent";
};

export function replayEvidenceLabel(tier: MotionReplayResultV1["validation_tier"]): string {
  return {
    synthetic: "Synthetic motion replay",
    integration: "Integrated research fixture replay",
    research: "Research-case replay",
    independent: "Independently validated replay",
  }[tier];
}
