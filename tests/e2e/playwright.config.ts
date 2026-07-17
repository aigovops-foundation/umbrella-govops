import { defineConfig, devices } from "@playwright/test";

/**
 * Umbrella-GovOps live-site smoke tests.
 *
 * BASE_URL defaults to the production GitHub Pages deployment.
 * Override to point at a preview build:
 *   BASE_URL=http://localhost:8080 npx playwright test
 */
const BASE_URL = process.env.BASE_URL || "https://aigovops-foundation.github.io/umbrella-govops/";

export default defineConfig({
  testDir: ".",
  testMatch: /.*\.spec\.ts$/,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [
    ["list"],
    ["html", { outputFolder: "../../reports/harness/playwright-html", open: "never" }],
    ["json", { outputFile: "../../reports/harness/playwright.json" }],
  ],
  outputDir: "../../reports/harness/playwright-artifacts",
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
