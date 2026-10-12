import { defineConfig, devices } from "@playwright/test";

// First browser framework in this repo (@playwright/test was already a
// devDependency; no new packages). Static marketing + mock-preview routes
// need no backend; live-data routes proxy /api/* to localhost:8001.
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "off",
  },
  projects: [
    { name: "chromium-light", use: { ...devices["Desktop Chrome"] } },
    {
      name: "chromium-dark-narrow",
      use: {
        ...devices["Desktop Chrome"],
        colorScheme: "dark",
        viewport: { width: 390, height: 844 },
      },
    },
  ],
});
