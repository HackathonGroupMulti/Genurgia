export type JsonObject = Record<string, unknown>;

export type Subject = { id: string; research_code: string; created_at: string };
export type Knee = {
  id: string;
  subject_id: string;
  laterality: "left" | "right";
  created_at: string;
};
export type Episode = {
  id: string;
  subject_id: string;
  episode_type: "injury" | "procedure" | "study" | "recovery" | "other";
  label: string;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
};
export type Timepoint = {
  id: string;
  subject_id: string;
  episode_id: string | null;
  observed_at: string;
  label: string;
  legacy_session_id: string | null;
  created_at: string;
};
export type Observation = {
  id: string;
  timepoint_id: string;
  modality: "video" | "mri" | "arthroscopy" | "sensor" | "other";
  source_artifact_reference: string;
  source_sha256: string | null;
  acquisition_manifest: JsonObject;
  authorization: JsonObject;
  quality: JsonObject;
  knee_target_ids: string[];
  immutable: true;
  created_at: string;
};
export type Annotation = {
  id: string;
  observation_id: string;
  annotation_type: string;
  version: string;
  author_type: "machine" | "expert" | "adjudicated";
  payload: JsonObject;
  review_state: "draft" | "in_review" | "approved" | "rejected";
  supersedes_id: string | null;
  created_at: string;
};
export type Reconstruction = {
  id: string;
  knee_id: string;
  timepoint_id: string;
  version: string;
  geometry_class:
    | "generic"
    | "fitted"
    | "machine-segmented"
    | "expert-reviewed"
    | "patient-specific";
  structures: string[];
  artifact_references: JsonObject;
  coordinate_system: JsonObject;
  review_state: "draft" | "in_review" | "approved" | "rejected";
  created_at: string;
};
export type Registration = {
  id: string;
  source_reference: string;
  target_reference: string;
  source_coordinate_system: JsonObject;
  target_coordinate_system: JsonObject;
  transform: number[][];
  method: string;
  coverage: JsonObject;
  error: JsonObject;
  uncertainty: JsonObject;
  created_at: string;
};
export type Derivation = {
  id: string;
  derivation_type: string;
  inputs: string[];
  outputs: string[];
  algorithm: string;
  algorithm_version: string;
  configuration: JsonObject;
  code_revision: string;
  environment: JsonObject;
  created_at: string;
};
export type VirtualExperiment = {
  id: string;
  knee_id: string;
  timepoint_id: string;
  definition_version: string;
  definition: JsonObject;
  validation_tier: "synthetic" | "integration" | "research" | "independent";
  created_at: string;
};
export type SimulationResult = {
  id: string;
  experiment_id: string;
  status: "complete" | "failed" | "cancelled";
  outputs: JsonObject;
  sensitivity: JsonObject;
  validation_evidence: JsonObject;
  artifact_references: JsonObject;
  created_at: string;
};

export type SubjectList = { subjects: Subject[] };
export type KneeList = { knees: Knee[] };
export type TimepointList = { timepoints: Timepoint[] };
export type ObservationList = { observations: Observation[] };

function record(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function nullableString(value: unknown): boolean {
  return value === null || typeof value === "string";
}

export function parseSubjectList(value: unknown): SubjectList | null {
  if (!record(value) || !Array.isArray(value.subjects)) return null;
  return value.subjects.every(
    (item) =>
      record(item) &&
      typeof item.id === "string" &&
      typeof item.research_code === "string" &&
      typeof item.created_at === "string",
  )
    ? (value as SubjectList)
    : null;
}

export function parseKneeList(value: unknown): KneeList | null {
  if (!record(value) || !Array.isArray(value.knees)) return null;
  return value.knees.every(
    (item) =>
      record(item) &&
      typeof item.id === "string" &&
      typeof item.subject_id === "string" &&
      ["left", "right"].includes(String(item.laterality)) &&
      typeof item.created_at === "string",
  )
    ? (value as KneeList)
    : null;
}

export function parseTimepointList(value: unknown): TimepointList | null {
  if (!record(value) || !Array.isArray(value.timepoints)) return null;
  return value.timepoints.every(
    (item) =>
      record(item) &&
      typeof item.id === "string" &&
      typeof item.subject_id === "string" &&
      nullableString(item.episode_id) &&
      typeof item.observed_at === "string" &&
      typeof item.label === "string" &&
      nullableString(item.legacy_session_id) &&
      typeof item.created_at === "string",
  )
    ? (value as TimepointList)
    : null;
}

export function parseObservationList(value: unknown): ObservationList | null {
  if (!record(value) || !Array.isArray(value.observations)) return null;
  return value.observations.every(
    (item) =>
      record(item) &&
      typeof item.id === "string" &&
      typeof item.timepoint_id === "string" &&
      ["video", "mri", "arthroscopy", "sensor", "other"].includes(String(item.modality)) &&
      typeof item.source_artifact_reference === "string" &&
      nullableString(item.source_sha256) &&
      record(item.acquisition_manifest) &&
      record(item.authorization) &&
      record(item.quality) &&
      Array.isArray(item.knee_target_ids) &&
      item.knee_target_ids.every((id) => typeof id === "string") &&
      item.immutable === true &&
      typeof item.created_at === "string",
  )
    ? (value as ObservationList)
    : null;
}
