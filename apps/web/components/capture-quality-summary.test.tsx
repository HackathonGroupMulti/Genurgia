import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { CaptureQualityReport } from "@/lib/quality-contracts";
import { CaptureQualitySummary } from "./capture-quality-summary";

describe("CaptureQualitySummary", () => {
  it("renders failure, missing evidence, units, and guidance explicitly", () => {
    const report: CaptureQualityReport = {
      schema_version: "1.0.0",
      analysis_version: "capture-quality-v1",
      source_pose_sequence_id: "sequence-id",
      source_knee_flexion_analysis_version: "knee-flexion-analysis-v1",
      source_repetition_analysis_version: "squat-repetition-analysis-v2",
      protocol: "squat",
      status: "fail",
      signals: [
        {
          name: "maximum_unavailable_interval",
          value: null,
          unit: "millisecond",
          status: "unavailable",
          criteria: "pass ≤250 ms",
          explanation: "No bilateral interval was measurable.",
        },
      ],
      guidance: ["Keep both knees visible."],
      interpretation: "Input quality only; not clinical accuracy.",
      artifact_reference: "/artifacts/id/capture_quality.json",
    };

    const markup = renderToStaticMarkup(<CaptureQualitySummary report={report} />);

    expect(markup).toContain("quality-fail");
    expect(markup).toContain("FAIL");
    expect(markup).toContain("Unavailable");
    expect(markup).toContain("Keep both knees visible.");
    expect(markup).toContain("not clinical accuracy");
  });
});
