import { describe, expect, it } from "vitest";
import { parseCaptureQualityReport } from "./quality-contracts";

const report = {
  schema_version: "1.0.0",
  analysis_version: "capture-quality-v1",
  source_pose_sequence_id: "sequence-id",
  source_knee_flexion_analysis_version: "knee-flexion-analysis-v1",
  source_repetition_analysis_version: "squat-repetition-analysis-v2",
  protocol: "squat",
  status: "warning",
  signals: [
    {
      name: "pose_detection_coverage",
      value: 0.8,
      unit: "ratio",
      status: "warning",
      criteria: "test",
      explanation: "test",
    },
  ],
  guidance: ["Improve lighting."],
  interpretation: "Not clinical accuracy.",
  artifact_reference: "/artifacts/id/capture_quality.json",
};

describe("capture quality contract", () => {
  it("accepts a complete versioned report", () => {
    expect(parseCaptureQualityReport(report)).toEqual(report);
  });

  it("rejects an unsupported analysis version", () => {
    expect(parseCaptureQualityReport({ ...report, analysis_version: "future" })).toBeNull();
  });
});
