import { describe, expect, it } from "vitest";

import {
  reconstructionEvidenceLabel,
  requiredKneeStructures,
} from "./reconstruction-contracts";

describe("reconstruction evidence contracts", () => {
  it("requires the complete approved structure target", () => {
    expect(requiredKneeStructures).toContain("femur");
    expect(requiredKneeStructures).toContain("patellar_cartilage");
    expect(requiredKneeStructures).toContain("acl");
    expect(requiredKneeStructures).toContain("popliteus_musculotendon");
    expect(new Set(requiredKneeStructures).size).toBe(22);
  });

  it("does not confuse generic, machine, reviewed, and validated geometry", () => {
    const classes = [
      "generic",
      "machine-segmented",
      "expert-reviewed",
      "patient-specific",
    ] as const;
    expect(new Set(classes.map(reconstructionEvidenceLabel)).size).toBe(classes.length);
  });
});
