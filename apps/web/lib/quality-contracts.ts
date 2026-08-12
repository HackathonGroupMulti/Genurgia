export type QualityStatus = "pass" | "warning" | "fail" | "unavailable";

export type CaptureQualitySignal = {
  name: string;
  value: number | boolean | null;
  unit: "ratio" | "millisecond" | "count" | "boolean";
  status: QualityStatus;
  criteria: string;
  explanation: string;
};

export type CaptureQualityReport = {
  schema_version: "1.0.0";
  analysis_version: "capture-quality-v1";
  source_pose_sequence_id: string;
  source_knee_flexion_analysis_version: "knee-flexion-analysis-v1";
  source_repetition_analysis_version: "squat-repetition-analysis-v2";
  protocol: "squat";
  status: "pass" | "warning" | "fail";
  signals: CaptureQualitySignal[];
  guidance: string[];
  interpretation: string;
  artifact_reference: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isSignal(value: unknown): value is CaptureQualitySignal {
  return (
    isRecord(value) &&
    typeof value.name === "string" &&
    (value.value === null || typeof value.value === "number" || typeof value.value === "boolean") &&
    ["ratio", "millisecond", "count", "boolean"].includes(String(value.unit)) &&
    ["pass", "warning", "fail", "unavailable"].includes(String(value.status)) &&
    typeof value.criteria === "string" &&
    typeof value.explanation === "string"
  );
}

export function parseCaptureQualityReport(value: unknown): CaptureQualityReport | null {
  if (
    !isRecord(value) ||
    value.schema_version !== "1.0.0" ||
    value.analysis_version !== "capture-quality-v1" ||
    typeof value.source_pose_sequence_id !== "string" ||
    value.source_knee_flexion_analysis_version !== "knee-flexion-analysis-v1" ||
    value.source_repetition_analysis_version !== "squat-repetition-analysis-v2" ||
    value.protocol !== "squat" ||
    !["pass", "warning", "fail"].includes(String(value.status)) ||
    !Array.isArray(value.signals) ||
    !value.signals.every(isSignal) ||
    !Array.isArray(value.guidance) ||
    !value.guidance.every((item) => typeof item === "string") ||
    typeof value.interpretation !== "string" ||
    typeof value.artifact_reference !== "string"
  ) {
    return null;
  }
  return value as CaptureQualityReport;
}
