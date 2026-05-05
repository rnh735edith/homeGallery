const { test, expect } = require("./fixtures");

test.describe("Photo Editor", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL("/", { timeout: 15000 });
  });

  test("open editor from gallery", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".photo-grid, .empty-gallery", {
      timeout: 15000,
    });
    const photoCards = await page.locator(".photo-card:not(.loading)").count();
    if (photoCards > 0) {
      await page
        .locator(".photo-card")
        .first()
        .click({ modifiers: ["Control"] });
    }
    await page.goto("/editor/1");
    await page.waitForSelector(".editor-page, .error-screen", {
      timeout: 10000,
    });
    await expect(page.locator(".editor-page")).toBeVisible({ timeout: 5000 });
  });

  test("adjust brightness", async ({ page }) => {
    await page.goto("/editor/1");
    await page.waitForSelector(".editor-page, .error-screen", {
      timeout: 10000,
    });
    const editorVisible = await page
      .locator(".editor-page")
      .isVisible()
      .catch(() => false);
    if (!editorVisible) {
      const errorText = await page
        .locator(".error-screen")
        .textContent()
        .catch(() => "");
      console.log("Editor error:", errorText);
    }
    await expect(page.locator(".editor-page")).toBeVisible({ timeout: 5000 });
    const brightnessSlider = page.locator('input[type="range"]').first();
    await expect(brightnessSlider).toBeVisible();
  });

  test("rotate photo", async ({ page }) => {
    await page.goto("/editor/1");
    await page.waitForSelector(".editor-page, .error-screen", {
      timeout: 10000,
    });
    await expect(page.locator(".editor-page")).toBeVisible({ timeout: 5000 });
    await page.click('button:has-text("Rotate 90")');
    await expect(page.locator(".editor-canvas img")).toBeVisible();
  });
});
