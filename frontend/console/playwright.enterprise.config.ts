import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e-enterprise",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 2,
  reporter: [["list"], ["html", { outputFolder: "playwright-enterprise-report", open: "never" }]],
  outputDir: "test-results-enterprise",
  use: { baseURL: "http://127.0.0.1:4180", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run build:enterprise && npx vite preview --outDir dist/enterprise --host 127.0.0.1 --port 4180 --strictPort",
    env: { VITE_OIDC_AUTHORITY: "https://identity.invalid", VITE_OIDC_CLIENT_ID: "cris-console", VITE_OIDC_SCOPE: "openid cris.api" },
    url: "http://127.0.0.1:4180", reuseExistingServer: false, timeout: 120_000,
  },
});
