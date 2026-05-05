const { test, expect } = require("./fixtures");

test.describe("Authentication", () => {
  test("login page loads", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator(".auth-page")).toBeVisible();
    await expect(page.locator("h1")).toContainText("HomeGallery");
  });

  test("login with valid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL("/");
  });

  test("login fails with invalid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "wronguser");
    await page.fill('[name="password"]', "wrongpass");
    await page.click('button[type="submit"]');
    await expect(page.locator(".auth-error")).toBeVisible();
  });

  test("register page loads", async ({ page }) => {
    await page.goto("/register");
    await expect(page.locator(".auth-card")).toBeVisible();
    await expect(page.locator("h1")).toContainText("Create Account");
  });

  test("logout works", async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL("/");
    await page.waitForSelector(".header", { timeout: 5000 });
    await page.waitForTimeout(500);
    await page.locator('button:has-text("Logout")').first().click();
    await expect(page).toHaveURL("/login");
  });
});
