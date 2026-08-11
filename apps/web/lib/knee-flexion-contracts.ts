import type { CoordinateConvention } from "./pose-contracts";

export type MeasurementQuality =
  | "valid"
  | "low_confidence"
  | "missing_pose"
  | "missing_landmark"
  | "invalid_coordinate"
  | "degenerate_geometry";

export type KneeFlexionSample = {
  timestamp_ms: number;
  value_degrees: number | null;
  filtered_value_degrees: number | null;
  confidence: number | null;
  quality: MeasurementQuality;
};

export type KneeFlexionSeries = {
  joint: "knee";
  side: "left" | "right";
  metric: "flexion";
  unit: "degree";
  samples: KneeFlexionSample[];
};

export type KneeFlexionAnalysis = {
  schema_version: "1.0.0";
  analysis_version: "knee-flexion-analysis-v1";
  calculation_version: "knee-flexion-world-3d-v1";
  source_pose_sequence_id: string;
  source_pose_model: string;
  source_pose_model_version: string;
  coordinate_convention: CoordinateConvention;
  minimum_measurement_confidence: number;
  filtering: {
    name: "centered-moving-average-v1";
    window_size: number;
    minimum_valid_values: number;
    behavior: string;
  };
  series: KneeFlexionSeries[];
  artifact_reference: string;
};

const MEASUREMENT_QUALITIES = new Set<MeasurementQuality>([
  "valid",
  "low_confidence",
  "missing_pose",
  "missing_landmark",
  "invalid_coordinate",
  "degenerate_geometry",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isSample(value: unknown): value is KneeFlexionSample {
  return (
    isRecord(value) &&
    typeof value.timestamp_ms === "number" &&
    (typeof value.value_degrees === "number" || value.value_degrees === null) &&
    (typeof value.filtered_value_degrees === "number" ||
      value.filtered_value_degrees === null) &&
    (typeof value.confidence === "number" || value.confidence === null) &&
    typeof value.quality === "string" &&
    MEASUREMENT_QUALITIES.has(value.quality as MeasurementQuality)
  );
}

export function parseKneeFlexionAnalysis(value: unknown): KneeFlexionAnalysis | null {
  if (
    !isRecord(value) ||
    value.schema_version !== "1.0.0" ||
    value.analysis_version !== "knee-flexion-analysis-v1" ||
    value.calculation_version !== "knee-flexion-world-3d-v1" ||
    typeof value.source_pose_sequence_id !== "string" ||
    typeof value.source_pose_model !== "string" ||
    typeof value.source_pose_model_version !== "string" ||
    !isRecord(value.coordinate_convention) ||
    typeof value.minimum_measurement_confidence !== "number" ||
    !isRecord(value.filtering) ||
    value.filtering.name !== "centered-moving-average-v1" ||
    typeof value.filtering.window_size !== "number" ||
    typeof value.filtering.minimum_valid_values !== "number" ||
    typeof value.filtering.behavior !== "string" ||
    typeof value.artifact_reference !== "string" ||
    !Array.isArray(value.series) ||
    value.series.length !== 2
  ) {
    return null;
  }

  for (const series of value.series) {
    if (
      !isRecord(series) ||
      series.joint !== "knee" ||
      (series.side !== "left" && series.side !== "right") ||
      series.metric !== "flexion" ||
      series.unit !== "degree" ||
      !Array.isArray(series.samples) ||
      !series.samples.every(isSample)
    ) {
      return null;
    }
  }

  return value as KneeFlexionAnalysis;
}

export function sampleDisplayValue(sample: KneeFlexionSample): number | null {
  if (sample.quality !== "valid") return null;
  return sample.filtered_value_degrees ?? sample.value_degrees;
}

export function sampleAtTimestamp(
  series: KneeFlexionSeries,
  timestampMs: number,
): KneeFlexionSample | null {
  if (series.samples.length === 0) return null;
  return series.samples.reduce((nearest, sample) =>
    Math.abs(sample.timestamp_ms - timestampMs) <
    Math.abs(nearest.timestamp_ms - timestampMs)
      ? sample
      : nearest,
  );
}
