import { describe, expect, it } from "vitest";
import { artifactProxyUrl, parsePoseAnalysisResponse } from "./pose-contracts";

const validResponse = {
  recording: {
    schema_version: "1.0.0",
    id: "recording-id",
    original_filename: "squat.mp4",
    content_type: "video/mp4",
    size_bytes: 100,
    duration_ms: 1000,
    fps: 30,
    width: 1920,
    height: 1080,
    storage_reference: "/artifacts/id/recording.mp4",
  },
  pose_sequence: {
    schema_version: "1.0.0",
    id: "sequence-id",
    recording_id: "recording-id",
    pose_model: "mediapipe-pose-landmarker",
    pose_model_version: "test",
    coordinate_convention: {},
    frame_count: 30,
    detected_frame_count: 28,
    raw_landmarks_reference: "/artifacts/id/pose_sequence.json",
    annotated_video_reference: "/artifacts/id/annotated.mp4",
  },
};

describe("pose analysis contract", () => {
  it("accepts a valid summary response", () => {
    expect(parsePoseAnalysisResponse(validResponse)).toEqual(validResponse);
  });

  it("rejects an incomplete response", () => {
    expect(parsePoseAnalysisResponse({ recording: {} })).toBeNull();
  });

  it("routes backend artifact references through Next.js", () => {
    expect(artifactProxyUrl("/artifacts/id/annotated.mp4")).toBe(
      "/api/artifacts/id/annotated.mp4",
    );
  });
});
