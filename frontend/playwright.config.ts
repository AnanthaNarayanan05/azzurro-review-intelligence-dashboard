import { defineConfig } from "@playwright/test";

/**
 * Browser end-to-end tests. They start their own API (on a brand-new throwaway database, see
 * backend/scripts/e2e_server.py) and a production build of the frontend, on ports that differ from the
 * development servers, so they never touch real data. They drive the installed Google Chrome, so no
 * browser download is needed.
 *
 * Run from frontend/:  npm run e2e
 */
const API_PORT = 8100;
const WEB_PORT = 3100;
const python =
  process.platform === "win32" ? "..\\backend\\.venv\\Scripts\\python.exe" : "../backend/.venv/bin/python";

export default defineConfig({
  testDir: "./e2e",
  // One worker: the tests share one database and follow one story (import, then look at the results).
  workers: 1,
  fullyParallel: false,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    channel: "chrome",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `${python} -m scripts.e2e_server --port ${API_PORT} --origin http://localhost:${WEB_PORT}`,
      cwd: "../backend",
      url: `http://localhost:${API_PORT}/api/health`,
      env: { DISABLE_SQLALCHEMY_CEXT: "1" },
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npm run build && npm run start -- -p ${WEB_PORT}`,
      url: `http://localhost:${WEB_PORT}`,
      env: { NEXT_PUBLIC_API_BASE_URL: `http://localhost:${API_PORT}` },
      reuseExistingServer: false,
      timeout: 240_000,
    },
  ],
});
