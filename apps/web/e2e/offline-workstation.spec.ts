import { expect, test } from "@playwright/test";

test("keeps the research boundary and capture guidance visible when the API is offline", async ({
  page,
}) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Movement, made comparable." })).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Unavailable");
  await expect(page.getByText("not medical diagnosis")).toBeVisible();
  await expect(page.getByLabel("Movement video")).toBeVisible();
  await expect(page.getByRole("button", { name: "Analyze video" })).toBeEnabled();
  await expect(page.getByText("Session history is currently unavailable.")).toBeVisible();
});

test("keeps exploratory simulation provenance visible when the API is offline", async ({
  page,
}) => {
  await page.goto("/lab");

  await expect(page.getByRole("heading", { name: "Try the knee." })).toBeVisible();
  await expect(page.getByText("Observed", { exact: true })).toBeVisible();
  await expect(page.getByText("Reconstructed", { exact: true })).toBeVisible();
  await expect(page.getByText("Expert assumption", { exact: true })).toBeVisible();
  await expect(page.getByText("Simulated", { exact: true })).toBeVisible();
  await expect(page.getByText("FEBio adapter unavailable")).toBeVisible();
  await expect(page.getByRole("button", { name: "Run independent flexion poses" })).toBeDisabled();
});
