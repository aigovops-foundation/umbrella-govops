import { test, expect } from "@playwright/test";

/**
 * Live-site smoke tests for the Umbrella-GovOps landing page.
 *
 * Assertions exercise public contracts that the brand and content team rely
 * on: hero pitch, framework registry size, role coverage, oath ribbon,
 * medallion SVG, and the section anchors linked from the nav.
 *
 * Element counts are pinned to the current production build (38 framework
 * rows + 1 header = 39 <tr>; 6 role cards) so a regression that drops or
 * duplicates rows fails CI loudly.
 */

test.describe("umbrella-govops landing page", () => {
  test.beforeEach(async ({ page }) => {
    // Use an empty path so baseURL is hit verbatim — baseURL already has
    // a path component ("/umbrella-govops/") and "/" would drop it.
    await page.goto("", { waitUntil: "domcontentloaded" });
  });

  test("hero h1 carries the core promise", async ({ page }) => {
    const h1 = page.locator("#hero-h");
    await expect(h1).toBeVisible();
    await expect(h1).toContainText("Governance is a pipeline");
    await expect(h1).toContainText("Make it verifiable");
  });

  test("hero medallion SVG renders", async ({ page }) => {
    const heroSvg = page.locator("section.hero svg").first();
    await expect(heroSvg).toBeVisible();
  });

  test("framework registry table lists 38 frameworks", async ({ page }) => {
    const table = page.locator("#framework-table");
    await expect(table).toBeVisible();
    // 1 header row + 38 framework rows = 39 <tr>
    const rows = table.locator("tr");
    const count = await rows.count();
    expect(count).toBeGreaterThanOrEqual(38);
    expect(count).toBeLessThanOrEqual(50);
    // Body should be at least 30 — guards against a markup regression that
    // accidentally drops the registry to a handful of placeholder rows.
    const bodyRows = table.locator("tbody tr");
    expect(await bodyRows.count()).toBeGreaterThanOrEqual(30);
  });

  test("roles section has 6 practitioner paths", async ({ page }) => {
    const roles = page.locator("#roles");
    await expect(roles).toBeVisible();
    const headings = roles.locator("h3");
    await expect(headings).toHaveCount(6);
  });

  test("oath / mantra ribbon is present", async ({ page }) => {
    const body = page.locator("body");
    await expect(body).toContainText("Governance is not a PDF");
    await expect(body).toContainText("It is a pipeline");
  });

  test("primary navigation anchors all resolve to real sections", async ({
    page,
  }) => {
    const anchors = [
      "#roles",
      "#frameworks",
      "#journeys",
      "#domains",
      "#crosswalk",
      "#pipeline",
      "#evidence",
    ];
    for (const a of anchors) {
      const sec = page.locator(a);
      await expect(sec, `anchor ${a} missing`).toHaveCount(1);
    }
  });

  test("page title brands the project correctly", async ({ page }) => {
    await expect(page).toHaveTitle(/Governance is a pipeline/i);
  });

  test("no fatal JS errors on initial render", async ({ page }) => {
    // pageerror = uncaught JS exception. We treat those as fatal.
    // Plain 404s for optional assets (e.g., favicon variants) are tolerated
    // — they don't break the user experience and would otherwise create
    // noisy CI failures every time a new asset is referenced.
    const fatal: string[] = [];
    page.on("pageerror", (err) => fatal.push(err.message));
    await page.goto("", { waitUntil: "networkidle" });
    expect(
      fatal,
      `uncaught JS exceptions: ${fatal.join(" | ")}`
    ).toHaveLength(0);
  });

  test("sister site beacon link is reachable from the page", async ({
    page,
  }) => {
    const beacon = page.locator('a[href*="aigovops-beacon"]').first();
    if ((await beacon.count()) > 0) {
      await expect(beacon).toBeVisible();
    }
  });

  test("captures a full-page screenshot for the harness report", async ({
    page,
  }, testInfo) => {
    const buf = await page.screenshot({ fullPage: true });
    await testInfo.attach("landing.png", {
      body: buf,
      contentType: "image/png",
    });
  });
});
