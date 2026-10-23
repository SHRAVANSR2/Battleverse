import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests drive the real app: Vite dev server + FastAPI backend with
 * real Piper audio. Installed Chrome is used via `channel: "chrome"` so no
 * browser download is required. Start the backend first (see README).
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  outputDir: "./e2e-artifacts",
  // Keep screenshots from passing runs too — they are the visual review record.
  preserveOutput: "always",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    // `localhost` (not 127.0.0.1): Vite binds IPv6 ::1 by default on Windows.
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    // Audio autoplay needs a gesture; Playwright's flag makes playback reliable.
    launchOptions: { args: ["--autoplay-policy=no-user-gesture-required"] },
  },
  projects: [
    {
      name: "chrome",
      use: { ...devices["Desktop Chrome"], channel: "chrome" },
    },
  ],
  webServer: {
    command: "npm run dev -- --port 5173 --strictPort",
    url: "http://localhost:5173",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
