import { describe, expect, it } from "vitest";
import { parseSquatRepetitionAnalysis } from "./repetition-contracts";

const validAnalysis = {
  schema_version: "1.0.0",
  analysis_version: "squat-repetition-analysis-v1",
  source_pose_sequence_id: "sequence-id",
  source_knee_flexion_analysis_version: "knee-flexion-analysis-v1",
  exercise: "squat",
  angle_unit: "degree",
  phase_model: {
    algorithm_version: "bilateral-squat-state-machine-v1",
    phase_states: ["standing", "descending", "bottom", "ascending"],
    standing_max_degrees: 25,
    descent_start_min_degrees: 35,
    bottom_min_degrees: 70,
    bottom_exit_max_degrees: 60,
    minimum_duration_ms: 800,
    maximum_duration_ms: 10000,
    maximum_gap_ms: 500,
    minimum_side_rom_degrees: 35,
    behavior: "test",
  },
  repetitions: [
    {
      repetition_index: 1,
      start_timestamp_ms: 100,
      bottom_timestamp_ms: 700,
      end_timestamp_ms: 1400,
      duration_ms: 1300,
      left_max_flexion_degrees: 90,
      right_max_flexion_degrees: 92,
      left_rom_degrees: 80,
      right_rom_degrees: 81,
      mean_rom_degrees: 80.5,
      confidence: 0.8,
    },
  ],
  artifact_reference: "/artifacts/id/squat_repetitions.json",
};

describe("squat repetition contract", () => {
  it("accepts a versioned repetition analysis", () => {
    expect(parseSquatRepetitionAnalysis(validAnalysis)).toEqual(validAnalysis);
  });

  it("accepts a valid analysis with no detected repetitions", () => {
    expect(parseSquatRepetitionAnalysis({ ...validAnalysis, repetitions: [] })).not.toBeNull();
  });

  it("rejects incomplete metrics", () => {
    expect(
      parseSquatRepetitionAnalysis({
        ...validAnalysis,
        repetitions: [{ repetition_index: 1 }],
      }),
    ).toBeNull();
  });
});
