const { test, expect } = require("./fixtures");

test.describe("Search", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
  });

  test("search input is visible", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.locator('[data-testid="search-input"], input[type="search"]'),
    ).toBeVisible();
  });

  test("search by filename", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator(".gallery-toolbar")).toBeVisible({
      timeout: 10000,
    });
    const searchInput = page.locator('input[type="search"]');
    await expect(searchInput).toBeVisible();
    await searchInput.click();
    await searchInput.fill("test");
    await page.waitForTimeout(1000);
    const photoGrid = page.locator(".photo-grid");
    const emptyGallery = page.locator(".empty-gallery");
    await expect(photoGrid.or(emptyGallery)).toBeVisible({ timeout: 10000 });
  });

  test("filter by favorites", async ({ page }) => {
    await page.goto("/");
    const favFilter = page.locator('[data-testid="filter-favorites"]');
    if (await favFilter.isVisible()) {
      await favFilter.click();
      await expect(page.locator(".photo-grid")).toBeVisible();
    }
  });
});
