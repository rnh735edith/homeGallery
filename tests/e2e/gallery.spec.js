const { test, expect } = require("./fixtures");

test.describe("Gallery Features", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
  });

  test("gallery page loads with toolbar", async ({ page }) => {
    await expect(page.locator(".sidebar")).toBeVisible();
    await expect(page.locator(".gallery-toolbar")).toBeVisible();
    await expect(page.locator(".search-input")).toBeVisible();
  });

  test("sidebar navigation works", async ({ page }) => {
    await expect(page.locator(".sidebar")).toBeVisible();
    await page.locator(".sidebar-link", { hasText: "Dashboard" }).click();
    await page.waitForURL("/dashboard");
    await page.locator(".sidebar-link", { hasText: "Gallery" }).click();
    await page.waitForURL("/");
    await expect(page.locator(".gallery-toolbar")).toBeVisible();
  });

  test("search input is functional", async ({ page }) => {
    await expect(page.locator(".sidebar")).toBeVisible();
    const searchInput = page.locator(".search-input");
    await expect(searchInput).toBeVisible();
    await searchInput.click();
    await searchInput.fill("test");
    await expect(searchInput).toHaveValue("test");
  });
});
