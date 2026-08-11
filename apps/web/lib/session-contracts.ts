export type SessionStatus = "pose_extracted" | "knee_flexion_complete" | "complete";

export type SessionMetric = {
  name: string;
  value: number;
  unit: "count" | "degree" | "millisecond" | "ratio";
  source_analysis_version: string;
};

export type SessionSummary = {
  id: string;
  exercise_type: "squat";
  recorded_at: string;
  created_at: string;
  status: SessionStatus;
  recording: {
    schema_version: string;
    id: string;
    original_filename: string;
    content_type: string;
    storage_reference: string;
    size_bytes: number;
    duration_ms: number;
    fps: number;
    width: number;
    height: number;
  };
  pose_sequence: {
    schema_version: string;
    id: string;
    recording_id: string;
    pose_model: string;
    pose_model_version: string;
    raw_landmarks_reference: string;
    annotated_video_reference: string;
    frame_count: number;
    detected_frame_count: number;
  };
  analyses: {
    id: number;
    analysis_type: "knee_flexion" | "squat_repetitions";
    analysis_version: string;
    artifact_reference: string;
    created_at: string;
  }[];
  metrics: SessionMetric[];
};

export type SessionListResponse = { sessions: SessionSummary[] };

export type SessionComparison = {
  session_id: string;
  recorded_at: string;
  repetition_count: number;
  mean_left_rom_degrees: number | null;
  mean_right_rom_degrees: number | null;
  mean_rom_degrees: number | null;
  mean_duration_ms: number | null;
  mean_confidence: number | null;
  mean_rom_change_from_previous_degrees: number | null;
};

export type SessionComparisonResponse = {
  exercise_type: "squat";
  sessions: SessionComparison[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isNullableNumber(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function isSession(value: unknown): value is SessionSummary {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    value.exercise_type === "squat" &&
    typeof value.recorded_at === "string" &&
    typeof value.created_at === "string" &&
    ["pose_extracted", "knee_flexion_complete", "complete"].includes(String(value.status)) &&
    isRecord(value.recording) &&
    typeof value.recording.original_filename === "string" &&
    isRecord(value.pose_sequence) &&
    typeof value.pose_sequence.id === "string" &&
    Array.isArray(value.analyses) &&
    Array.isArray(value.metrics) &&
    value.metrics.every(
      (metric) =>
        isRecord(metric) &&
        typeof metric.name === "string" &&
        typeof metric.value === "number" &&
        typeof metric.unit === "string" &&
        typeof metric.source_analysis_version === "string",
    )
  );
}

function isComparison(value: unknown): value is SessionComparison {
  return (
    isRecord(value) &&
    typeof value.session_id === "string" &&
    typeof value.recorded_at === "string" &&
    typeof value.repetition_count === "number" &&
    isNullableNumber(value.mean_left_rom_degrees) &&
    isNullableNumber(value.mean_right_rom_degrees) &&
    isNullableNumber(value.mean_rom_degrees) &&
    isNullableNumber(value.mean_duration_ms) &&
    isNullableNumber(value.mean_confidence) &&
    isNullableNumber(value.mean_rom_change_from_previous_degrees)
  );
}

export function parseSessionList(value: unknown): SessionListResponse | null {
  if (!isRecord(value) || !Array.isArray(value.sessions) || !value.sessions.every(isSession)) {
    return null;
  }
  return value as SessionListResponse;
}

export function parseSessionComparison(value: unknown): SessionComparisonResponse | null {
  if (
    !isRecord(value) ||
    value.exercise_type !== "squat" ||
    !Array.isArray(value.sessions) ||
    !value.sessions.every(isComparison)
  ) {
    return null;
  }
  return value as SessionComparisonResponse;
}

export function metricValue(session: SessionSummary, name: string): number | null {
  return session.metrics.find((metric) => metric.name === name)?.value ?? null;
}
