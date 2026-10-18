import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  outputDir: "./test-results",
  use: {
    baseURL: process.env.BASE_URL || "https://orang2-bu.github.io/SOPia/",
    ...devices["Desktop Chrome"],
    video: "on",
    screenshot: "on",
    trace: "on-first-retry",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
});
