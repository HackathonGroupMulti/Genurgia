export type Recording = {
  schema_version: "1.0.0" | "1.1.0";
  id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  duration_ms: number;
  fps: number;
  width: number;
  height: number;
  storage_reference: string;
  captured_at?: string | null;
  protocol?: "squat";
  camera_view?: "front" | "rear" | "left_side" | "right_side" | "oblique" | "unknown";
  orientation?: "portrait" | "landscape" | "unknown";
  laterality_context?: "bilateral" | "left" | "right" | "unknown";
  capture_notes?: string | null;
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
  processing: {
    operation_id: string;
    upload_bytes: number;
    processing_duration_ms: number;
    processed_frames: number;
    average_frames_per_second: number | null;
  };
};

export type Landmark = {
  index: number;
  name: string;
  x: number | null;
  y: number | null;
  z: number | null;
  visibility: number | null;
  presence: number | null;
};

export type PoseFrame = {
  frame_index: number;
  timestamp_ms: number;
  poses: {
    pose_index: number;
    image_landmarks: Landmark[];
    world_landmarks: Landmark[];
  }[];
};

export type PoseSequenceArtifact = {
  recording: Recording;
  pose_sequence: {
    schema_version: "1.0.0";
    id: string;
    recording_id: string;
    pose_model: string;
    pose_model_version: string;
    coordinate_convention: CoordinateConvention;
    frame_count: number;
    detected_frame_count: number;
    frames: PoseFrame[];
  };
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isNullableNumber(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function isLandmark(value: unknown): value is Landmark {
  return (
    isRecord(value) &&
    typeof value.index === "number" &&
    typeof value.name === "string" &&
    isNullableNumber(value.x) &&
    isNullableNumber(value.y) &&
    isNullableNumber(value.z) &&
    isNullableNumber(value.visibility) &&
    isNullableNumber(value.presence)
  );
}

function isPoseFrame(value: unknown): value is PoseFrame {
  return (
    isRecord(value) &&
    typeof value.frame_index === "number" &&
    typeof value.timestamp_ms === "number" &&
    Array.isArray(value.poses) &&
    value.poses.every(
      (pose) =>
        isRecord(pose) &&
        typeof pose.pose_index === "number" &&
        Array.isArray(pose.image_landmarks) &&
        pose.image_landmarks.every(isLandmark) &&
        Array.isArray(pose.world_landmarks) &&
        pose.world_landmarks.every(isLandmark),
    )
  );
}

export function parsePoseAnalysisResponse(value: unknown): PoseAnalysisResponse | null {
  if (
    !isRecord(value) ||
    !isRecord(value.recording) ||
    !isRecord(value.pose_sequence) ||
    !isRecord(value.processing)
  ) {
    return null;
  }

  const recording = value.recording;
  const sequence = value.pose_sequence;
  const processing = value.processing;
  if (
    !["1.0.0", "1.1.0"].includes(String(recording.schema_version)) ||
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
    !isRecord(sequence.coordinate_convention) ||
    typeof processing.operation_id !== "string" ||
    typeof processing.upload_bytes !== "number" ||
    typeof processing.processing_duration_ms !== "number" ||
    typeof processing.processed_frames !== "number" ||
    !isNullableNumber(processing.average_frames_per_second)
  ) {
    return null;
  }

  return value as PoseAnalysisResponse;
}

export function parsePoseSequenceArtifact(value: unknown): PoseSequenceArtifact | null {
  if (!isRecord(value) || !isRecord(value.recording) || !isRecord(value.pose_sequence)) {
    return null;
  }
  const recording = value.recording;
  const sequence = value.pose_sequence;
  if (
    !["1.0.0", "1.1.0"].includes(String(recording.schema_version)) ||
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
    !isRecord(sequence.coordinate_convention) ||
    typeof sequence.frame_count !== "number" ||
    typeof sequence.detected_frame_count !== "number" ||
    !Array.isArray(sequence.frames) ||
    !sequence.frames.every(isPoseFrame)
  ) {
    return null;
  }
  return value as PoseSequenceArtifact;
}

export function nearestPoseFrame(
  artifact: PoseSequenceArtifact,
  timestampMs: number,
): PoseFrame | null {
  const frames = artifact.pose_sequence.frames;
  if (frames.length === 0) return null;
  return frames.reduce((nearest, frame) =>
    Math.abs(frame.timestamp_ms - timestampMs) < Math.abs(nearest.timestamp_ms - timestampMs)
      ? frame
      : nearest,
  );
}

export function artifactProxyUrl(reference: string): string {
  return `/api${reference}`;
}
