import { expect, it } from "vitest";

import {
  parseFlexionResult,
  syntheticExperimentTemplate,
  type SimulationModelV1,
} from "./simulation-contracts";

const model: SimulationModelV1 = {
  id: "model-1",
  reconstruction_id: "reconstruction-1",
  version: "cc0-synthetic-flexion-v1",
  adapter_id: "febio-4.12",
  model_sha256: "a".repeat(64),
  model_manifest: {},
  artifact_references: {},
  mesh_quality: {},
  included_structures: ["femur", "tibia"],
  excluded_structures: ["patella"],
  validation_state: "structurally-valid",
  created_at: "2026-08-14T00:00:00Z",
};

it("builds fixture assumptions explicitly without calling them measurements", () => {
  const template = syntheticExperimentTemplate(model);
  expect(template.interpretation).toBe("exploratory-simulated-hypothesis");
  expect(JSON.stringify(template)).toContain('"individual_measurement":false');
});

it("preserves nonconverged pose evidence", () => {
  const parsed = parseFlexionResult({
    schema_version: "1.0.0",
    interpretation: "exploratory-simulated-hypothesis",
    poses: [{ flexion_angle_degrees: 45, status: "nonconverged" }],
  });
  expect(parsed?.poses[0].status).toBe("nonconverged");
});
