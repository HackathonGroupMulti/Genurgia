import { describe, expect, it } from "vitest";
import { parseProcessingOperationList } from "./operation-contracts";

describe("processing operation contracts", () => {
  it("preserves explicit failed-stage provenance", () => {
    const parsed = parseProcessingOperationList({
      operations: [
        {
          id: "operation-id",
          operation_type: "pose_extraction",
          status: "failed",
          stage: "pose_extraction",
          input_bytes: 100,
          pose_sequence_id: null,
          started_at: "2026-08-12T00:00:00Z",
          completed_at: "2026-08-12T00:00:01Z",
          duration_ms: 1000,
          error_code: "PoseExtractionError",
          error_detail: "Decode failed.",
        },
      ],
    });

    expect(parsed?.operations[0].stage).toBe("pose_extraction");
    expect(parsed?.operations[0].error_code).toBe("PoseExtractionError");
  });

  it("rejects an implicit failure without a stage", () => {
    expect(parseProcessingOperationList({ operations: [{ status: "failed" }] })).toBeNull();
  });
});
