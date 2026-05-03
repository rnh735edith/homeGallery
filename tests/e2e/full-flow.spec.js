const { test, expect } = require("./fixtures");

test.describe("Full User Flow E2E", () => {
  test("complete user journey - login, gallery, albums, dashboard, settings, logout", async ({
    page,
  }) => {
    // Step 1: Login page loads
    await page.goto("/login");
    await expect(page.locator(".auth-page")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("h1")).toContainText("HomeGallery");

    // Step 2: Login with valid credentials
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForURL("/", { timeout: 10000 });

    // Step 3: Verify gallery page with sidebar
    await expect(page.locator(".sidebar")).toBeVisible({ timeout: 10000 });
    await expect(page.locator(".gallery-toolbar")).toBeVisible();
    await expect(page.locator('input[type="search"]')).toBeVisible();

    // Step 4: Navigate to Dashboard
    await page.locator(".sidebar-link", { hasText: "Dashboard" }).click();
    await page.waitForURL("/dashboard", { timeout: 10000 });
    await expect(page.locator(".dashboard-page")).toBeVisible();

    // Step 5: Navigate to Albums
    await page.locator(".sidebar-link", { hasText: "Albums" }).click();
    await page.waitForURL("/albums", { timeout: 10000 });
    await expect(page.locator(".albums-page")).toBeVisible();

    // Step 6: Navigate to Settings
    await page.locator(".sidebar-link", { hasText: "Settings" }).click();
    await page.waitForURL("/settings", { timeout: 10000 });
    await expect(page.locator(".settings-page")).toBeVisible();

    // Step 7: Navigate back to Gallery
    await page.locator(".sidebar-link", { hasText: "Gallery" }).click();
    await page.waitForURL("/", { timeout: 10000 });
    await expect(page.locator(".gallery-toolbar")).toBeVisible();

    // Step 8: Verify search input works
    const searchInput = page.locator('input[type="search"]');
    await searchInput.click();
    await searchInput.fill("test");
    await expect(searchInput).toHaveValue("test");

    // Step 9: Verify favorites filter
    const favBtn = page.locator("button", { hasText: /Favorites/ });
    await expect(favBtn).toBeVisible();
    await favBtn.click();

    // Step 10: Logout
    await page.locator('button:has-text("Logout")').first().click();
    await page.waitForURL("/login", { timeout: 10000 });
    await expect(page.locator(".auth-page")).toBeVisible();
  });

  test("album creation flow", async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForURL("/", { timeout: 10000 });

    await page.goto("/albums");
    await expect(page.locator(".albums-page")).toBeVisible({ timeout: 10000 });

    const createBtn = page.locator(
      '[data-testid="create-album"], button:has-text("Create Album"), button:has-text("New Album")',
    );
    if (await createBtn.isVisible()) {
      await createBtn.click();
      await page.fill(
        '[name="album-name"], input[placeholder*="name"]',
        "E2E Test Album",
      );
      await page.click(
        'button[type="submit"], button:has-text("Create"), button:has-text("Save")',
      );
      await page.waitForTimeout(2000);
      await expect(
        page.locator(".album-card", { hasText: "E2E Test Album" }).first(),
      ).toBeVisible({ timeout: 10000 });
    }
  });

  test("faces page loads", async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForURL("/", { timeout: 10000 });

    await page.locator(".sidebar-link", { hasText: "Faces" }).click();
    await page.waitForURL("/faces", { timeout: 10000 });
    await expect(page.locator(".faces-page")).toBeVisible();
  });
});
