import { expect, test } from "@playwright/test";

test("keeps the research boundary and capture guidance visible when the API is offline", async ({
  page,
}) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Movement, made comparable." })).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Unavailable");
  await expect(page.getByText("not a medical diagnostic device")).toBeVisible();
  await expect(page.getByLabel("Movement video")).toBeVisible();
  await expect(page.getByRole("button", { name: "Analyze video" })).toBeEnabled();
  await expect(page.getByText("Session history is currently unavailable.")).toBeVisible();
});
