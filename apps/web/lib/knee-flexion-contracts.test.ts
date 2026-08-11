import { describe, expect, it } from "vitest";
import {
  parseKneeFlexionAnalysis,
  sampleAtTimestamp,
  sampleDisplayValue,
  type KneeFlexionSeries,
  type KneeFlexionSample,
} from "./knee-flexion-contracts";

const sample: KneeFlexionSample = {
  timestamp_ms: 0,
  value_degrees: 90,
  filtered_value_degrees: 88,
  confidence: 0.9,
  quality: "valid",
};

const validAnalysis = {
  schema_version: "1.0.0",
  analysis_version: "knee-flexion-analysis-v1",
  calculation_version: "knee-flexion-world-3d-v1",
  source_pose_sequence_id: "sequence-id",
  source_pose_model: "mediapipe-pose-landmarker",
  source_pose_model_version: "test",
  coordinate_convention: {},
  minimum_measurement_confidence: 0.5,
  filtering: {
    name: "centered-moving-average-v1",
    window_size: 5,
    minimum_valid_values: 3,
    behavior: "test",
  },
  artifact_reference: "/artifacts/id/knee_flexion.json",
  series: [
    { joint: "knee", side: "left", metric: "flexion", unit: "degree", samples: [sample] },
    { joint: "knee", side: "right", metric: "flexion", unit: "degree", samples: [sample] },
  ],
};

describe("knee-flexion contract", () => {
  it("accepts a versioned left/right analysis", () => {
    expect(parseKneeFlexionAnalysis(validAnalysis)).toEqual(validAnalysis);
  });

  it("rejects incomplete analysis", () => {
    expect(parseKneeFlexionAnalysis({ series: [] })).toBeNull();
  });

  it("prefers filtered values only for valid samples", () => {
    expect(sampleDisplayValue(sample)).toBe(88);
    expect(sampleDisplayValue({ ...sample, quality: "low_confidence" })).toBeNull();
  });

  it("selects the closest source sample for synchronized playback", () => {
    const series: KneeFlexionSeries = {
      joint: "knee",
      side: "left",
      metric: "flexion",
      unit: "degree",
      samples: [sample, { ...sample, timestamp_ms: 100, value_degrees: 80 }],
    };

    expect(sampleAtTimestamp(series, 80)?.timestamp_ms).toBe(100);
  });
});
