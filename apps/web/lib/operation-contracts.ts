export type ProcessingOperation = {
  id: string;
  operation_type: "pose_extraction";
  status: "running" | "complete" | "failed";
  stage: string;
  input_bytes: number;
  pose_sequence_id: string | null;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  error_code: string | null;
  error_detail: string | null;
};

export type ProcessingOperationList = { operations: ProcessingOperation[] };

function nullable(value: unknown, type: "string" | "number"): boolean {
  return value === null || typeof value === type;
}

function isOperation(value: unknown): value is ProcessingOperation {
  if (typeof value !== "object" || value === null) return false;
  const item = value as Record<string, unknown>;
  return (
    typeof item.id === "string" &&
    item.operation_type === "pose_extraction" &&
    ["running", "complete", "failed"].includes(String(item.status)) &&
    typeof item.stage === "string" &&
    typeof item.input_bytes === "number" &&
    nullable(item.pose_sequence_id, "string") &&
    typeof item.started_at === "string" &&
    nullable(item.completed_at, "string") &&
    nullable(item.duration_ms, "number") &&
    nullable(item.error_code, "string") &&
    nullable(item.error_detail, "string")
  );
}

export function parseProcessingOperationList(value: unknown): ProcessingOperationList | null {
  if (typeof value !== "object" || value === null) return null;
  const operations = (value as Record<string, unknown>).operations;
  return Array.isArray(operations) && operations.every(isOperation)
    ? (value as ProcessingOperationList)
    : null;
}
