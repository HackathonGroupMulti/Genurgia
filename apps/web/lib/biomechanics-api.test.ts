import { describe, expect, it } from "vitest";
import { parseHealthResponse } from "./biomechanics-api";

describe("parseHealthResponse", () => {
  it("accepts the biomechanics health contract", () => {
    expect(parseHealthResponse({ status: "ok", service: "biomechanics" })).toEqual({
      status: "ok",
      service: "biomechanics",
    });
  });

  it.each([
    null,
    {},
    { status: "degraded", service: "biomechanics" },
    { status: "ok", service: "unknown" },
  ])("rejects an invalid response: %j", (response) => {
    expect(parseHealthResponse(response)).toBeNull();
  });
});
