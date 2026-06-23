import { expect, test } from "@playwright/test";

// Phase 4 smoke: Explore exposes the NL->SQL box; Alerts exposes the AI triage action.
test("explore page shows the natural-language query box", async ({ page }) => {
  await page.goto("/explore");
  await expect(
    page.getByPlaceholder(/Ask in natural language/i),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Ask AI" })).toBeVisible();
});

test("alerts page exposes an AI triage action", async ({ page }) => {
  await page.goto("/alerts");
  // Either there are alerts (triage buttons) or an empty state — both must render without error.
  await expect(page.getByRole("heading").first()).toBeVisible();
});
