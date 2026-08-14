import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";

import { KneeLab } from "./knee-lab";

it("keeps evidence classes and unavailable solver state explicit", () => {
  const markup = renderToStaticMarkup(
    <KneeLab
      adapters={[
        {
          adapter_id: "febio-4.12",
          display_name: "FEBio 4.12 tibiofemoral flexion sweep",
          available: false,
          executable_path: null,
          executable_sha256: null,
          detected_version: null,
          supported_version: "4.12",
          required_modules: ["solid"],
          capabilities: ["partial-results"],
          unavailable_reasons: ["FEBio is not installed."],
        },
      ]}
      models={[]}
      reconstructions={[]}
    />,
  );

  expect(markup).toContain("Observed");
  expect(markup).toContain("Expert assumption");
  expect(markup).toContain("Simulated");
  expect(markup).toContain("FEBio is not installed.");
  expect(markup).toContain("disabled");
});
