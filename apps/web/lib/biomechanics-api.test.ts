import { describe, expect, it } from "vitest";
import { getBackendBaseUrl, parseHealthResponse } from "./biomechanics-api";

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

  it("rejects a non-loopback backend", () => {
    const original = process.env.BIOMECHANICS_API_URL;
    process.env.BIOMECHANICS_API_URL = "https://example.test";
    try {
      expect(() => getBackendBaseUrl()).toThrow("loopback");
    } finally {
      if (original === undefined) delete process.env.BIOMECHANICS_API_URL;
      else process.env.BIOMECHANICS_API_URL = original;
    }
  });
});
