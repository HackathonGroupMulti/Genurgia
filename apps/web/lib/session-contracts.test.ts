import { describe, expect, it } from "vitest";
import {
  metricValue,
  parseSessionComparison,
  parseSessionList,
  parseSelectedSessionComparison,
  type SessionSummary,
} from "./session-contracts";

const session: SessionSummary = {
  id: "session-id",
  exercise_type: "squat",
  recorded_at: "2026-08-10T12:00:00Z",
  created_at: "2026-08-10T12:00:00Z",
  status: "complete",
  recording: {
    schema_version: "1.0.0",
    id: "recording-id",
    original_filename: "squat.mp4",
    content_type: "video/mp4",
    storage_reference: "/artifacts/id/recording.mp4",
    size_bytes: 100,
    duration_ms: 2000,
    fps: 30,
    width: 640,
    height: 480,
  },
  pose_sequence: {
    schema_version: "1.0.0",
    id: "pose-id",
    recording_id: "recording-id",
    pose_model: "model",
    pose_model_version: "v1",
    coordinate_convention: "mediapipe-pose-world-v1",
    raw_landmarks_reference: "/artifacts/id/pose_sequence.json",
    annotated_video_reference: "/artifacts/id/annotated.mp4",
    frame_count: 60,
    detected_frame_count: 58,
  },
  analyses: [],
  metrics: [
    {
      name: "mean_rom_degrees",
      value: 70,
      unit: "degree",
      source_analysis_version: "squat-repetition-analysis-v1",
    },
  ],
};

describe("session contracts", () => {
  it("parses session history and reads named metrics", () => {
    const parsed = parseSessionList({ sessions: [session] });
    expect(parsed?.sessions[0]).toEqual(session);
    expect(metricValue(session, "mean_rom_degrees")).toBe(70);
    expect(metricValue(session, "missing")).toBeNull();
  });

  it("parses nullable comparison metrics", () => {
    expect(
      parseSessionComparison({
        exercise_type: "squat",
        sessions: [
          {
            session_id: "session-id",
            recorded_at: "2026-08-10T12:00:00Z",
            repetition_count: 0,
            mean_left_rom_degrees: null,
            mean_right_rom_degrees: null,
            mean_rom_degrees: null,
            mean_duration_ms: null,
            mean_confidence: null,
            mean_rom_change_from_previous_degrees: null,
          },
        ],
      }),
    ).not.toBeNull();
  });

  it("rejects malformed history", () => {
    expect(parseSessionList({ sessions: [{ id: "incomplete" }] })).toBeNull();
  });

  it("parses an explicit compatible session comparison", () => {
    expect(
      parseSelectedSessionComparison({
        schema_version: "2.0.0",
        baseline_session_id: "baseline-id",
        current_session_id: "current-id",
        compatible: true,
        compatibility_basis: "canonical-evidence-v1",
        incompatibilities: [],
        analysis_version: "squat-repetition-analysis-v2",
        metrics: [
          {
            name: "mean_rom_degrees",
            baseline_value: 65,
            current_value: 70,
            change: 5,
            unit: "degree",
          },
        ],
      }),
    ).not.toBeNull();
  });
});
