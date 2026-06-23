import { expect, test } from "@playwright/test";

test("alerts page renders SIEM Alerts heading and filter selectors", async ({ page }) => {
  await page.goto("/alerts");
  await expect(page.getByRole("heading", { name: "SIEM Alerts" })).toBeVisible();
  
  // Verify filter select elements are visible
  const selectElements = await page.locator("select");
  await expect(selectElements.first()).toBeVisible();
});

test("incidents page renders board workbench with split-pane columns", async ({ page }) => {
  await page.goto("/incidents");
  await expect(page.getByRole("heading", { name: "Incidents Board" })).toBeVisible();
  
  // Verify split pane sidebar button refresh
  await expect(page.getByRole("button", { name: "Refresh" })).toBeVisible();
});
