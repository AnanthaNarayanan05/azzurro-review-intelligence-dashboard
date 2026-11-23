import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { PAGES, axeViolations, expectNoHorizontalOverflow } from "./checks";

/**
 * The whole story in a real browser against a real API and a fresh database:
 * upload a file, import it, see matching totals on the dashboard, filter reviews, generate insights, and
 * follow an insight to the exact reviews behind it. The file is the committed SYNTHETIC sample, so the
 * data is imported as synthetic and viewed with the "synthetic" data scope.
 */
const SAMPLE = path.resolve(__dirname, "../../data/sample/synthetic_reviews_sample.csv");
const PROPERTY_NAMES = [
  "Olympic Hotel Paddington",
  "Potts Point",
  "Central Sydney",
  "Darling Harbour",
];

// Filled by the first test, used by the later ones.
const state = { imported: 0, firstProperty: "" };

test.describe.serial("upload to insight", () => {
  test("starts empty: nothing is shown as real data", async ({ page }) => {
    await page.goto("/overview");
    await expect(page.getByRole("heading", { name: "No reviews to show" })).toBeVisible();
  });

  test("imports the sample file through the wizard and reconciles the counts", async ({ page }) => {
    await page.goto("/import");
    await page.locator("#import-file").setInputFiles(SAMPLE);

    // Step 2: columns are suggested from the headers; continue without changing anything.
    await expect(page.getByRole("button", { name: "Continue" })).toBeEnabled();
    await page.getByRole("button", { name: "Continue" }).click();

    // Step 3: create each property found in the file, mark it synthetic and import.
    for (const name of PROPERTY_NAMES) {
      await page.getByRole("button", { name: `Create property "${name}"` }).click();
      await expect(page.getByRole("button", { name: `Create property "${name}"` })).toHaveCount(0);
    }
    await page.getByLabel("This file contains synthetic (demo) data").check();
    await page.getByRole("button", { name: /^Import [\d,]+ rows$/ }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Import reviews" }).click();

    // Report: the counts add up, and nothing was rejected.
    const report = page.getByTestId("import-report");
    await expect(report).toBeVisible();
    const text = (await page.getByTestId("reconciliation").textContent()) ?? "";
    const m = text.match(/([\d,]+) rows in the file = ([\d,]+) imported \+ ([\d,]+) updated \+ ([\d,]+) duplicates \+ ([\d,]+) rejected/);
    expect(m, text).not.toBeNull();
    const [total, imported, updated, duplicates, rejected] = m!.slice(1).map((v) => Number(v.replace(/,/g, "")));
    expect(imported + updated + duplicates + rejected).toBe(total);
    expect(rejected).toBe(0);
    expect(imported).toBeGreaterThan(400);
    await expect(report.getByText("Synthetic demo data")).toBeVisible();
    state.imported = imported;
  });

  test("the overview shows the same total, labelled as synthetic, and nothing as genuine", async ({ page }) => {
    await page.goto("/overview?scope=synthetic");
    await expect(page.getByText("Synthetic demo data").first()).toBeVisible();
    const tile = page.locator('[data-slot="card"]', { hasText: /^Reviews/ }).first();
    await expect(tile).toContainText(state.imported.toLocaleString("en-US"));

    // Default scope is genuine: the imported synthetic reviews must not appear there.
    await page.goto("/overview");
    await expect(page.getByText("No genuine reviews imported yet")).toBeVisible();
    await expect(page.getByRole("heading", { name: "No reviews to show" })).toBeVisible();
  });

  test("filtering reviews by property and by aspect changes the list and the URL", async ({ page }) => {
    await page.goto("/reviews?scope=synthetic");
    const summary = page.getByText(/^[\d,]+ reviews?\. Page 1 of/);
    await expect(summary).toContainText(state.imported.toLocaleString("en-US"));

    state.firstProperty = PROPERTY_NAMES[0];
    await page.getByRole("button", { name: state.firstProperty, exact: true }).click();
    await expect(page).toHaveURL(/properties=\d+/);
    await expect(summary).not.toContainText(state.imported.toLocaleString("en-US"));
    const filtered = Number(((await summary.textContent()) ?? "").match(/^([\d,]+)/)![1].replace(/,/g, ""));
    expect(filtered).toBeGreaterThan(0);
    expect(filtered).toBeLessThan(state.imported);

    // A search that matches nothing explains itself instead of showing a blank page.
    await page.getByLabel("Search review text").fill("zzzzqqqq");
    await expect(page.getByRole("heading", { name: "No reviews match" })).toBeVisible();
    await page.getByRole("region", { name: "Search and filter reviews" }).getByRole("button", { name: "Clear search and filters" }).click();
    await expect(summary).toBeVisible();
  });

  test("generates insights and follows one to exactly the reviews it cites", async ({ page }) => {
    await page.goto("/insights?scope=synthetic");
    await expect(page.getByText("No insights generated yet")).toBeVisible();
    await page.getByRole("button", { name: "Generate insights" }).first().click();
    const count = page.getByText(/^\d+ insights?\. Page 1 of/);
    await expect(count).toBeVisible();

    // Every card is labelled as synthetic and offers its evidence.
    const first = page.locator("li", { has: page.getByRole("link", { name: /^See all \d+ reviews/ }) }).first();
    await expect(first.getByText("Synthetic demo data")).toBeVisible();
    const link = first.getByRole("link", { name: /^See all \d+ reviews/ });
    const claimed = Number(((await link.textContent()) ?? "").match(/See all (\d+)/)![1]);

    // The explorer, opened from that link, lists exactly that many reviews.
    await link.click();
    await expect(page).toHaveURL(/\/reviews\?/);
    await expect(page.getByText(new RegExp(`^${claimed} reviews?\\. Page 1 of`))).toBeVisible();

    // An example sentence opens the full review with its evidence.
    await page.goBack();
    await first.getByRole("button", { name: /example sentence/ }).click();
    await first.getByRole("link", { name: "Open full review" }).first().click();
    await expect(page.getByRole("dialog")).toBeVisible();
  });

  for (const width of [375, 768]) {
    test(`no page scrolls sideways at ${width}px wide`, async ({ page }) => {
      for (const url of PAGES) await expectNoHorizontalOverflow(page, url, width);
    });
  }

  test("no page has an automated accessibility violation (WCAG 2.1 A and AA)", async ({ page }) => {
    const found = [];
    for (const url of PAGES) found.push(...(await axeViolations(page, url)));
    expect(found, JSON.stringify(found, null, 2)).toEqual([]);
  });

  test("removing the import leaves insights that the page flags as out of date", async ({ page, request }) => {
    const imports = await (await request.get("http://localhost:8100/api/imports")).json();
    const removed = await request.delete(`http://localhost:8100/api/imports/${imports.data[0].id}`);
    expect(removed.ok()).toBeTruthy();
    await page.goto("/insights?scope=synthetic");
    await expect(page.getByText("These insights are out of date")).toBeVisible();
    await expectNoErrorBanner(page);
  });
});

async function expectNoErrorBanner(page: Page) {
  await expect(page.getByText("Could not load")).toHaveCount(0);
}
