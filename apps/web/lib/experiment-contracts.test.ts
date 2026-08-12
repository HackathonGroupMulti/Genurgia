import { expect, it } from "vitest";

import { replayEvidenceLabel } from "./experiment-contracts";

it("keeps synthetic replay distinct from independently validated replay", () => {
  expect(replayEvidenceLabel("synthetic")).not.toBe(replayEvidenceLabel("independent"));
});
