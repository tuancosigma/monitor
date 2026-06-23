import { expect, test } from "@playwright/test";

// Phase 0 smoke: the home page renders the Sentinel heading and a health badge
// reflecting the backend /healthz call.
test("home page shows backend health badge", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sentinel" })).toBeVisible();
  await expect(page.getByTestId("health-badge")).toBeVisible();
});
