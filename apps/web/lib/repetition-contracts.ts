export type SquatRepetition = {
  repetition_index: number;
  start_timestamp_ms: number;
  bottom_timestamp_ms: number;
  end_timestamp_ms: number;
  duration_ms: number;
  left_max_flexion_degrees: number;
  right_max_flexion_degrees: number;
  left_rom_degrees: number;
  right_rom_degrees: number;
  mean_rom_degrees: number;
  signed_rom_difference_degrees: number;
  absolute_rom_difference_degrees: number;
  signed_max_flexion_difference_degrees: number;
  absolute_max_flexion_difference_degrees: number;
  confidence: number;
};

export type SquatRepetitionAnalysis = {
  schema_version: "1.1.0";
  analysis_version: "squat-repetition-analysis-v2";
  source_pose_sequence_id: string;
  source_knee_flexion_analysis_version: "knee-flexion-analysis-v1";
  exercise: "squat";
  angle_unit: "degree";
  bilateral_difference_convention: "left-minus-right-v1";
  phase_model: {
    algorithm_version: "bilateral-squat-state-machine-v1";
    phase_states: ["standing", "descending", "bottom", "ascending"];
    standing_max_degrees: number;
    descent_start_min_degrees: number;
    bottom_min_degrees: number;
    bottom_exit_max_degrees: number;
    minimum_duration_ms: number;
    maximum_duration_ms: number;
    maximum_gap_ms: number;
    minimum_side_rom_degrees: number;
    behavior: string;
  };
  repetitions: SquatRepetition[];
  artifact_reference: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isRepetition(value: unknown): value is SquatRepetition {
  return (
    isRecord(value) &&
    isNumber(value.repetition_index) &&
    isNumber(value.start_timestamp_ms) &&
    isNumber(value.bottom_timestamp_ms) &&
    isNumber(value.end_timestamp_ms) &&
    isNumber(value.duration_ms) &&
    isNumber(value.left_max_flexion_degrees) &&
    isNumber(value.right_max_flexion_degrees) &&
    isNumber(value.left_rom_degrees) &&
    isNumber(value.right_rom_degrees) &&
    isNumber(value.mean_rom_degrees) &&
    isNumber(value.signed_rom_difference_degrees) &&
    isNumber(value.absolute_rom_difference_degrees) &&
    isNumber(value.signed_max_flexion_difference_degrees) &&
    isNumber(value.absolute_max_flexion_difference_degrees) &&
    isNumber(value.confidence)
  );
}

export function parseSquatRepetitionAnalysis(
  value: unknown,
): SquatRepetitionAnalysis | null {
  if (
    !isRecord(value) ||
    value.schema_version !== "1.1.0" ||
    value.analysis_version !== "squat-repetition-analysis-v2" ||
    typeof value.source_pose_sequence_id !== "string" ||
    value.source_knee_flexion_analysis_version !== "knee-flexion-analysis-v1" ||
    value.exercise !== "squat" ||
    value.angle_unit !== "degree" ||
    value.bilateral_difference_convention !== "left-minus-right-v1" ||
    !isRecord(value.phase_model) ||
    value.phase_model.algorithm_version !== "bilateral-squat-state-machine-v1" ||
    !Array.isArray(value.phase_model.phase_states) ||
    value.phase_model.phase_states.join(",") !== "standing,descending,bottom,ascending" ||
    !isNumber(value.phase_model.standing_max_degrees) ||
    !isNumber(value.phase_model.descent_start_min_degrees) ||
    !isNumber(value.phase_model.bottom_min_degrees) ||
    !isNumber(value.phase_model.bottom_exit_max_degrees) ||
    !isNumber(value.phase_model.minimum_duration_ms) ||
    !isNumber(value.phase_model.maximum_duration_ms) ||
    !isNumber(value.phase_model.maximum_gap_ms) ||
    !isNumber(value.phase_model.minimum_side_rom_degrees) ||
    typeof value.phase_model.behavior !== "string" ||
    !Array.isArray(value.repetitions) ||
    !value.repetitions.every(isRepetition) ||
    typeof value.artifact_reference !== "string"
  ) {
    return null;
  }

  return value as SquatRepetitionAnalysis;
}
