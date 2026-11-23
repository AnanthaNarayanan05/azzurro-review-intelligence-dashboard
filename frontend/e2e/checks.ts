import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

/** Every page of the app. The data pages are opened with the synthetic scope so they show real content. */
export const PAGES = [
  "/overview?scope=synthetic",
  "/properties?scope=synthetic",
  "/comparison?scope=synthetic",
  "/reviews?scope=synthetic",
  "/insights?scope=synthetic",
  "/import",
  "/settings",
];

async function settle(page: Page) {
  await page.waitForLoadState("networkidle");
  // Charts and tables render after the data arrives; give the page a moment to finish drawing.
  await page.waitForTimeout(400);
}

/** The page must not scroll sideways: that is what "doesn't fit the screen" means on a phone. */
export async function expectNoHorizontalOverflow(page: Page, url: string, width: number) {
  await page.setViewportSize({ width, height: 812 });
  await page.goto(url);
  await settle(page);
  const { scrollWidth, clientWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(scrollWidth, `${url} at ${width}px is ${scrollWidth}px wide`).toBeLessThanOrEqual(clientWidth);
}

/** Automated WCAG 2.1 A/AA checks (axe). Returns the violations so the caller can describe them. */
export async function axeViolations(page: Page, url: string) {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(url);
  await settle(page);
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  return result.violations.map((v) => ({
    page: url,
    rule: v.id,
    impact: v.impact,
    help: v.help,
    count: v.nodes.length,
    example: v.nodes[0]?.target.join(" "),
  }));
}
