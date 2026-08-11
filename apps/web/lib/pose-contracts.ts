export type Recording = {
  schema_version: "1.0.0";
  id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  duration_ms: number;
  fps: number;
  width: number;
  height: number;
  storage_reference: string;
};

export type CoordinateConvention = {
  image: "mediapipe-normalized-image-v1";
  image_axes: string;
  image_depth: string;
  world: "mediapipe-pose-world-v1";
  world_units: "meter";
  world_origin: string;
};

export type PoseSequenceSummary = {
  schema_version: "1.0.0";
  id: string;
  recording_id: string;
  pose_model: string;
  pose_model_version: string;
  coordinate_convention: CoordinateConvention;
  frame_count: number;
  detected_frame_count: number;
  raw_landmarks_reference: string;
  annotated_video_reference: string;
};

export type PoseAnalysisResponse = {
  recording: Recording;
  pose_sequence: PoseSequenceSummary;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function parsePoseAnalysisResponse(value: unknown): PoseAnalysisResponse | null {
  if (!isRecord(value) || !isRecord(value.recording) || !isRecord(value.pose_sequence)) {
    return null;
  }

  const recording = value.recording;
  const sequence = value.pose_sequence;
  if (
    recording.schema_version !== "1.0.0" ||
    typeof recording.id !== "string" ||
    typeof recording.original_filename !== "string" ||
    typeof recording.content_type !== "string" ||
    typeof recording.size_bytes !== "number" ||
    typeof recording.duration_ms !== "number" ||
    typeof recording.fps !== "number" ||
    typeof recording.width !== "number" ||
    typeof recording.height !== "number" ||
    typeof recording.storage_reference !== "string" ||
    sequence.schema_version !== "1.0.0" ||
    typeof sequence.id !== "string" ||
    typeof sequence.recording_id !== "string" ||
    typeof sequence.pose_model !== "string" ||
    typeof sequence.pose_model_version !== "string" ||
    typeof sequence.frame_count !== "number" ||
    typeof sequence.detected_frame_count !== "number" ||
    typeof sequence.raw_landmarks_reference !== "string" ||
    typeof sequence.annotated_video_reference !== "string" ||
    !isRecord(sequence.coordinate_convention)
  ) {
    return null;
  }

  return value as PoseAnalysisResponse;
}

export function artifactProxyUrl(reference: string): string {
  return `/api${reference}`;
}
