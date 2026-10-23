import { defineConfig, devices } from "@playwright/test";

// Browser journeys run in the `checks-e2e` container (docs/engineering/E2E.md):
// the compiled standalone server is started here, without preview access control,
// against the local API. Failure traces and screenshots go to E2E_ARTIFACTS.
const port = 3101;
const artifacts = process.env.E2E_ARTIFACTS ?? "../../.cache/e2e";

export default defineConfig({
  testDir: "e2e",
  outputDir: `${artifacts}/results`,
  // Software WebGL is slow; one map at a time keeps timings honest on a laptop.
  workers: 1,
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 20_000 },
  reporter: [
    ["list"],
    ["html", { outputFolder: `${artifacts}/report`, open: "never" }],
  ],
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: [
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"] },
      grepInvert: /@mobile/,
    },
    {
      name: "mobile",
      use: { ...devices["Pixel 7"] },
      grep: /@mobile/,
    },
  ],
  webServer: {
    command: "node .next/standalone/apps/web/server.js",
    url: `http://127.0.0.1:${port}/en`,
    timeout: 60_000,
    reuseExistingServer: false,
    env: {
      PORT: String(port),
      HOSTNAME: "127.0.0.1",
      NODE_ENV: "production",
      NEXT_TELEMETRY_DISABLED: "1",
      PROPERTY_PLATFORM_API_ORIGIN:
        process.env.E2E_API_ORIGIN ?? "http://127.0.0.1:8000",
      PROPERTY_PLATFORM_ENABLE_LOCAL_PREVIEW: "1",
      // Never the preview password: these journeys need an open local server.
      PROPERTY_PLATFORM_PREVIEW_ACCESS_REQUIRED: "0",
    },
  },
});
