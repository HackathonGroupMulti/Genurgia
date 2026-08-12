import { describe, expect, it } from "vitest";
import {
  parseKneeList,
  parseObservationList,
  parseSubjectList,
  parseTimepointList,
} from "./evidence-contracts";

describe("canonical evidence contracts", () => {
  it("parses migrated immutable bilateral evidence", () => {
    expect(
      parseSubjectList({
        subjects: [{ id: "subject", research_code: "LOCAL-RESEARCH-SUBJECT", created_at: "now" }],
      }),
    ).not.toBeNull();
    expect(
      parseKneeList({
        knees: [
          { id: "left", subject_id: "subject", laterality: "left", created_at: "now" },
          { id: "right", subject_id: "subject", laterality: "right", created_at: "now" },
        ],
      }),
    ).not.toBeNull();
    expect(
      parseTimepointList({
        timepoints: [
          {
            id: "session",
            subject_id: "subject",
            episode_id: null,
            observed_at: "2026-08-12T00:00:00Z",
            label: "Migrated squat session",
            legacy_session_id: "session",
            created_at: "2026-08-12T00:00:00Z",
          },
        ],
      }),
    ).not.toBeNull();
    expect(
      parseObservationList({
        observations: [
          {
            id: "recording",
            timepoint_id: "session",
            modality: "video",
            source_artifact_reference: "/artifacts/id/recording.mp4",
            source_sha256: null,
            acquisition_manifest: { migration: "legacy-session-v1" },
            authorization: { status: "not-recorded" },
            quality: { status: "legacy-or-derived" },
            knee_target_ids: ["left", "right"],
            immutable: true,
            created_at: "2026-08-12T00:00:00Z",
          },
        ],
      }),
    ).not.toBeNull();
  });

  it("rejects an observation without explicit knee targets", () => {
    expect(parseObservationList({ observations: [{ immutable: true }] })).toBeNull();
  });
});
