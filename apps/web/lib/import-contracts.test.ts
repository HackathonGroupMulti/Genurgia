import { describe, expect, it } from "vitest";

import { parseAcquisitionManifest } from "./import-contracts";

describe("multimodal import contracts", () => {
  it("distinguishes MRI acquisition evidence from estimates", () => {
    const manifest = parseAcquisitionManifest({
      schema_version: "1.0.0",
      modality: "MRI",
      coordinate_system: "dicom-patient-lps-mm",
      status: "pass",
      quality_signals: [],
    });
    expect(manifest?.coordinate_system).toBe("dicom-patient-lps-mm");
  });

  it("refuses an unversioned or unknown coordinate convention", () => {
    expect(
      parseAcquisitionManifest({
        schema_version: "1.0.0",
        coordinate_system: "unknown",
        status: "pass",
        quality_signals: [],
      }),
    ).toBeNull();
  });
});
