import type { JsonObject, Observation } from "./evidence-contracts";

export type ImportStatus = "pass" | "warning" | "fail";

export type ImportQualitySignal = {
  name: string;
  status: ImportStatus;
  value: number | string | boolean | null;
  unit: string | null;
  explanation: string;
};

export type DicomSeriesManifestV1 = {
  schema_version: "1.0.0";
  modality: "MRI";
  instance_count: number;
  pixel_spacing_mm: [number, number];
  slice_spacing_mm: number | null;
  coordinate_system: "dicom-patient-lps-mm";
  deidentification: {
    profile: "knee-twin-research-screen-v1";
    dicom_ps3_15_conformance_claimed: false;
    populated_direct_identifier_tags: string[];
    status: "pass" | "fail";
  } & JsonObject;
  quality_signals: ImportQualitySignal[];
  status: ImportStatus;
} & JsonObject;

export type ArthroscopyManifestV1 = {
  schema_version: "1.0.0";
  procedure_at: string;
  calibration_artifact_reference: string;
  calibration_error_px: number;
  frame_count: number;
  duration_ms: number;
  timestamp_basis: "decoded-frame-index-and-container-fps";
  coordinate_system: "arthroscope-image-pixels";
  quality_signals: ImportQualitySignal[];
  status: ImportStatus;
} & JsonObject;

export type MultiViewCaptureManifestV1 = {
  schema_version: "1.0.0";
  protocol: "calibrated-four-camera-rgb-v1";
  coordinate_system: "capture-volume-right-handed-mm";
  cameras: JsonObject[];
  source_artifacts: Record<string, string>;
  quality_signals: ImportQualitySignal[];
  status: ImportStatus;
} & JsonObject;

export type AcquisitionManifestV1 =
  | DicomSeriesManifestV1
  | ArthroscopyManifestV1
  | MultiViewCaptureManifestV1;

export type ObservationImportResultV1 = {
  schema_version: "1.0.0";
  observation: Observation;
  acquisition_manifest: AcquisitionManifestV1;
  artifact_integrity: JsonObject[];
  execution: "synchronous-local-import";
  job_runner_status: "deferred-to-milestone-13";
};

function record(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseAcquisitionManifest(value: unknown): AcquisitionManifestV1 | null {
  if (
    !record(value) ||
    value.schema_version !== "1.0.0" ||
    !["pass", "warning", "fail"].includes(String(value.status)) ||
    !Array.isArray(value.quality_signals)
  ) {
    return null;
  }
  if (value.coordinate_system === "dicom-patient-lps-mm" && value.modality === "MRI") {
    return value as DicomSeriesManifestV1;
  }
  if (value.coordinate_system === "arthroscope-image-pixels") {
    return value as ArthroscopyManifestV1;
  }
  if (
    value.coordinate_system === "capture-volume-right-handed-mm" &&
    value.protocol === "calibrated-four-camera-rgb-v1"
  ) {
    return value as MultiViewCaptureManifestV1;
  }
  return null;
}
