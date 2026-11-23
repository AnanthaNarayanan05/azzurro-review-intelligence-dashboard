// Takes the screenshots used in docs/HANDOVER.md from a RUNNING app (see docs/DEPLOYMENT.md).
// Every page is opened with the synthetic data scope, so the pictures show the clearly labelled demo data,
// never genuine reviews.
//
// From frontend/:  node scripts/screenshots.mjs [baseUrl] [outputDir]
//   baseUrl   default http://localhost:3000
//   outputDir default ../docs/screenshots
import { mkdirSync } from "node:fs";
import path from "node:path";
import { chromium } from "@playwright/test";

const base = process.argv[2] ?? "http://localhost:3000";
const outDir = path.resolve(process.argv[3] ?? "../docs/screenshots");
mkdirSync(outDir, { recursive: true });

const pages = [
  ["overview", "/overview?scope=synthetic"],
  ["properties", "/properties?scope=synthetic"],
  ["comparison", "/comparison?scope=synthetic"],
  ["reviews", "/reviews?scope=synthetic"],
  ["insights", "/insights?scope=synthetic"],
  ["import", "/import"],
  ["settings", "/settings"],
];

const browser = await chromium.launch({ channel: "chrome" });
try {
  for (const [name, url, width = 1280, height = 900] of pages) {
    const page = await browser.newPage({ viewport: { width, height } });
    await page.goto(base + url);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(800); // charts draw after the data arrives
    await page.screenshot({ path: path.join(outDir, `${name}.png`) });
    await page.close();
    console.log(`saved ${name}.png`);
  }
  // One narrow-screen view to show the responsive layout.
  const phone = await browser.newPage({ viewport: { width: 375, height: 812 } });
  await phone.goto(`${base}/overview?scope=synthetic`);
  await phone.waitForLoadState("networkidle");
  await phone.waitForTimeout(800);
  await phone.screenshot({ path: path.join(outDir, "overview-375px.png") });
  console.log("saved overview-375px.png");
} finally {
  await browser.close();
}
