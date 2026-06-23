import { expect, test } from "@playwright/test";

// Phase 6 smoke: Playbooks page renders the DAG builder + create button.
test("playbooks page renders the DAG builder", async ({ page }) => {
  await page.goto("/playbooks");
  await expect(page.getByRole("heading", { name: "Playbooks" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "New playbook (JSON DAG)" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create playbook" })).toBeVisible();
});
