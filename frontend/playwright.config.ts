import { defineConfig } from "@playwright/test";

// Smoke e2e runs against the compose stack (or a locally started dev server).
export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  use: {
    baseURL: process.env.FRONTEND_URL ?? "http://localhost:3000",
  },
});
