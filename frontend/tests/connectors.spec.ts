import { expect, test } from "@playwright/test";

// Phase 5 smoke: Connectors page renders the add-connector form and table.
test("connectors page renders form and table", async ({ page }) => {
  await page.goto("/connectors");
  await expect(page.getByRole("heading", { name: "Connectors" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Add connector" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create" })).toBeVisible();
});
