const { test, expect } = require("./fixtures");

test.describe("Albums", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL("/");
  });

  test("create new album", async ({ page }) => {
    await page.goto("/albums");
    await page.click('[data-testid="create-album"]');
    await page.fill('[name="album-name"]', "Test Album");
    await page.fill('[name="album-description"]', "Test description");
    await page.click('button[type="submit"]');
    // Wait for modal to close and album to appear
    await page.waitForSelector(".modal", { state: "hidden", timeout: 10000 });
    await expect(
      page.locator(".album-card", { hasText: "Test Album" }).first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test("open album and view photos", async ({ page }) => {
    await page.goto("/albums");
    await page.waitForSelector(".album-card", { timeout: 10000 });
    await page.locator(".album-card").first().click();
    await expect(page).toHaveURL(/\/albums\//);
    await expect(page.locator(".photo-grid")).toBeVisible();
  });
});
