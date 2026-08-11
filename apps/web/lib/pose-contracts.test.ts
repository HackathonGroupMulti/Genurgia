import { describe, expect, it } from "vitest";
import {
  artifactProxyUrl,
  nearestPoseFrame,
  parsePoseAnalysisResponse,
  parsePoseSequenceArtifact,
} from "./pose-contracts";

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

  it("parses raw frames and selects the nearest synchronized frame", () => {
    const artifact = {
      recording: validResponse.recording,
      pose_sequence: {
        ...validResponse.pose_sequence,
        frames: [
          { frame_index: 0, timestamp_ms: 0, poses: [] },
          { frame_index: 1, timestamp_ms: 100, poses: [] },
        ],
      },
    };
    delete (artifact.pose_sequence as Record<string, unknown>).raw_landmarks_reference;
    delete (artifact.pose_sequence as Record<string, unknown>).annotated_video_reference;

    const parsed = parsePoseSequenceArtifact(artifact);

    expect(parsed).not.toBeNull();
    expect(parsed && nearestPoseFrame(parsed, 80)?.frame_index).toBe(1);
  });
});
