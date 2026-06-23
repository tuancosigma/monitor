import { expect, test } from "@playwright/test";

// Phase 7 smoke: Posture, Benchmark, and Dashboard pages render their controls.
test("posture page renders score controls", async ({ page }) => {
  await page.goto("/posture");
  await expect(page.getByRole("heading", { name: "Security Posture" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Run Trivy" })).toBeVisible();
});

test("benchmark page renders run controls", async ({ page }) => {
  await page.goto("/benchmark");
  await expect(page.getByRole("heading", { name: "Benchmarks" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Run ingest" })).toBeVisible();
});

test("dashboard page allows adding and saving widgets", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Add widget" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save layout" })).toBeVisible();
});
