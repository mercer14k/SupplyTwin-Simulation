import { defineConfig } from "@playwright/test";
import path from "node:path";
export default defineConfig({
  testDir: "../../tests/e2e",
  timeout: 60000,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:5181",
    channel: process.env.PLAYWRIGHT_CHANNEL,
    viewport: { width: 1512, height: 1050 },
    trace: "retain-on-failure",
  },
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : [
        {
          command: `${process.env.SUPPLYTWIN_PYTHON || ".venv/bin/python"} -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8011`,
          cwd: path.resolve("../.."),
          url: "http://127.0.0.1:8011/ready",
          reuseExistingServer: !process.env.CI,
          env: {
            ALLOWED_ORIGINS: "http://127.0.0.1:5181",
            DATABASE_PATH: ".local/e2e.db",
          },
        },
        {
          command:
            "node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5181 --strictPort",
          url: "http://127.0.0.1:5181",
          reuseExistingServer: !process.env.CI,
          env: { SUPPLYTWIN_API_TARGET: "http://127.0.0.1:8011" },
        },
      ],
});
