import { expect, test } from "@playwright/test";

// Phase 1 smoke: Explore page renders filters + live-tail control.
test("explore page renders search and live tail controls", async ({ page }) => {
  await page.goto("/explore");
  await expect(page.getByRole("heading", { name: "Explore" })).toBeVisible();
  await expect(page.getByPlaceholder("host.name")).toBeVisible();
  await expect(page.getByRole("button", { name: "Search" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Live tail" })).toBeVisible();
});
