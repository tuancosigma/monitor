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
  // Time-window selector drives the live widget queries.
  await expect(page.getByLabel("time window")).toBeVisible();
});

test("adding a widget renders a widget card", async ({ page }) => {
  await page.goto("/dashboard");
  await page.getByPlaceholder("Widget title").fill("Events over time");
  await page.getByRole("button", { name: "Add widget" }).click();
  // Card header shows the title and a remove control (chart loads against live data).
  await expect(page.getByRole("heading", { name: "Events over time" })).toBeVisible();
  await expect(page.getByRole("button", { name: "remove" })).toBeVisible();
});
