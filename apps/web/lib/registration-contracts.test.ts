import { expect, it } from "vitest";

import { registrationEvidenceLabel } from "./registration-contracts";

it("keeps synthetic and independently validated registration visibly distinct", () => {
  expect(registrationEvidenceLabel("synthetic")).not.toBe(
    registrationEvidenceLabel("independent"),
  );
});
