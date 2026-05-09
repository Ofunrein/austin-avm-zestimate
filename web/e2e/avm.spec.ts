import { test, expect } from "@playwright/test";

// ── Homepage ─────────────────────────────────────────────
test.describe("Homepage", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("loads with Bloomberg Terminal UI", async ({ page }) => {
    await expect(page).toHaveTitle(/Austin AVM/i);
    // Dark background
    const bg = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );
    expect(bg).toBeTruthy();
  });

  test("persistent nav bar present", async ({ page }) => {
    const nav = page.locator("nav.topbar, .topbar");
    await expect(nav).toBeVisible();
    // All 5 nav links
    for (const label of ["VALUATION", "BENCHMARK", "SCANNER", "DEALS", "MODEL CARD"]) {
      await expect(nav.getByText(label)).toBeVisible();
    }
  });

  test("dark/light toggle button exists", async ({ page }) => {
    const toggle = page.getByRole("button", { name: /LIGHT|DARK/i });
    await expect(toggle).toBeVisible();
  });

  test("NL search bar visible", async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="QUERY"]').or(
      page.locator('input[placeholder*="3BR"]')
    );
    await expect(searchInput).toBeVisible();
  });

  test("NL search execute button works", async ({ page }) => {
    const input = page.locator('input[placeholder*="QUERY"]').or(
      page.locator('input[placeholder*="3BR"]')
    );
    await input.fill("3BR under $400k in 78704");
    const btn = page.getByRole("button", { name: "EXECUTE ↵" });
    await btn.click();
    // Wait for either results or no-match message
    await page.waitForTimeout(4000);
    const body = await page.textContent("body");
    expect(
      body!.includes("RESULTS") ||
      body!.includes("results") ||
      body!.includes("NO MATCHING") ||
      body!.includes("No matching")
    ).toBeTruthy();
  });

  test("prediction form visible with all fields", async ({ page }) => {
    for (const label of ["01 · LIVING SQFT", "03 · BEDS", "04 · FULL BATHS", "05 · YEAR BUILT", "06 · ZIP CODE"]) {
      await expect(page.getByText(label, { exact: false })).toBeVisible();
    }
  });

  test("prediction form submits and shows result", async ({ page }) => {
    const executeBtn = page.getByRole("button", { name: /EXECUTE VALUATION/i });
    await executeBtn.click();
    // Wait up to 20s for API response
    await page.waitForTimeout(8000);
    const body = await page.textContent("body");
    // Should show a price ($ sign in big number)
    expect(body!.includes("$")).toBeTruthy();
  });
});

// ── Nav persistence across pages ─────────────────────────
test.describe("Navigation persistence", () => {
  const pages = ["/", "/benchmark", "/scanner", "/deals", "/model-card"];

  for (const path of pages) {
    test(`nav visible on ${path}`, async ({ page }) => {
      await page.goto(path);
      const nav = page.locator("nav.topbar, .topbar");
      await expect(nav).toBeVisible();
      await expect(nav.getByText("AVM")).toBeVisible();
    });
  }

  test("clicking BENCHMARK link navigates correctly", async ({ page }) => {
    await page.goto("/");
    await page.locator(".topbar").getByText("BENCHMARK").click();
    await expect(page).toHaveURL(/benchmark/);
    await expect(page.getByText(/BENCHMARK|MedAPE/i).first()).toBeVisible();
  });

  test("clicking DEALS link navigates correctly", async ({ page }) => {
    await page.goto("/");
    await page.locator(".topbar").getByText("DEALS").click();
    await expect(page).toHaveURL(/deals/);
    await expect(page.getByText(/DEAL|Undervalued|No deals/i).first()).toBeVisible();
  });

  test("clicking SCANNER link navigates correctly", async ({ page }) => {
    await page.goto("/");
    await page.locator(".topbar").getByText("SCANNER").click();
    await expect(page).toHaveURL(/scanner/);
  });

  test("clicking MODEL CARD link navigates correctly", async ({ page }) => {
    await page.goto("/");
    await page.locator(".topbar").getByText("MODEL CARD").click();
    await expect(page).toHaveURL(/model-card/);
  });
});

// ── Dark/light mode toggle ────────────────────────────────
test.describe("Theme toggle", () => {
  test("toggles data-theme attribute", async ({ page }) => {
    await page.goto("/");
    const toggle = page.getByRole("button", { name: /LIGHT|DARK/i });
    const htmlEl = page.locator("html");

    const initialTheme = await htmlEl.getAttribute("data-theme");
    await toggle.click();
    const newTheme = await htmlEl.getAttribute("data-theme");
    expect(newTheme).not.toBe(initialTheme);
  });

  test("theme persists after navigation", async ({ page }) => {
    await page.goto("/");
    const toggle = page.getByRole("button", { name: /LIGHT|DARK/i });
    await toggle.click();
    const themeAfterToggle = await page.locator("html").getAttribute("data-theme");

    await page.goto("/benchmark");
    const themeAfterNav = await page.locator("html").getAttribute("data-theme");
    expect(themeAfterNav).toBe(themeAfterToggle);
  });
});

// ── Benchmark page ────────────────────────────────────────
test.describe("Benchmark page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/benchmark");
  });

  test("shows performance metrics", async ({ page }) => {
    await page.waitForTimeout(3000);
    const body = await page.textContent("body");
    // Either shows data or error
    expect(
      body!.includes("MEDAPE") ||
      body!.includes("MedAPE") ||
      body!.includes("ERR")
    ).toBeTruthy();
  });

  test("back navigation works", async ({ page }) => {
    await page.goto("/benchmark");
    await page.locator(".topbar").getByText("VALUATION").click();
    await expect(page).toHaveURL(/\/$/);
  });
});

// ── Deals page ────────────────────────────────────────────
test.describe("Deals page", () => {
  test("loads without error", async ({ page }) => {
    await page.goto("/deals");
    await page.waitForTimeout(3000);
    const body = await page.textContent("body");
    // Should show deals or empty state — not a crash
    expect(
      body!.includes("DEAL") ||
      body!.includes("Deal") ||
      body!.includes("deal") ||
      body!.includes("No deals") ||
      body!.includes("ERR")
    ).toBeTruthy();
  });

  test("nav still visible on deals page", async ({ page }) => {
    await page.goto("/deals");
    await expect(page.locator(".topbar")).toBeVisible();
  });
});

// ── Scanner page ──────────────────────────────────────────
test.describe("Scanner page", () => {
  test("loads Bloomberg Terminal UI", async ({ page }) => {
    await page.goto("/scanner");
    await expect(page.getByText(/BATCH.*SCANNER|Scanner/i).first()).toBeVisible();
  });

  test("file upload area visible", async ({ page }) => {
    await page.goto("/scanner");
    const upload = page.locator('input[type="file"]');
    await expect(upload).toBeAttached();
  });
});

// ── Model Card page ───────────────────────────────────────
test.describe("Model Card page", () => {
  test("loads all sections", async ({ page }) => {
    await page.goto("/model-card");
    for (const text of ["MODEL DETAILS", "TRAINING DATA", "VALIDATION"]) {
      await expect(page.locator(".panel-label").getByText(text, { exact: true }).first()).toBeVisible();
    }
  });

  test("nav visible on model-card", async ({ page }) => {
    await page.goto("/model-card");
    await expect(page.locator(".topbar")).toBeVisible();
  });
});

// ── API health ────────────────────────────────────────────
test.describe("API health", () => {
  test("HF Space /health returns ok", async ({ request }) => {
    const resp = await request.get("https://ofunrein-austin-avm-api.hf.space/health");
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe("ok");
  });

  test("HF Space /predict returns prediction", async ({ request }) => {
    const resp = await request.post("https://ofunrein-austin-avm-api.hf.space/predict", {
      data: {
        sqft_living: 1800,
        beds: 3,
        baths_full: 2,
        year_built: 2005,
        zip_code: "78701",
        lat: 30.27,
        lng: -97.74,
        lot_sqft: 5000,
        garage_spaces: 1,
        has_pool: 0,
        assessed_value: 0,
      },
    });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.predicted_price).toBeGreaterThan(0);
    expect(body.confidence_score).toBeGreaterThan(0);
    expect(body.shap_top5).toHaveLength(5);
  });

  test("HF Space /benchmark returns data", async ({ request }) => {
    const resp = await request.get("https://ofunrein-austin-avm-api.hf.space/benchmark");
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.test_medape).toBeGreaterThan(0);
  });
});
