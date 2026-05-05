const { test, expect } = require("./fixtures");

/**
 * HomeGallery Feature Demo - Comprehensive E2E walkthrough
 * Documents every feature by navigating through the application
 * Run with: npx playwright test feature-demo.spec.js --reporter=line --headed
 */
test.describe("HomeGallery Feature Demo", () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL("/", { timeout: 15000 });
  });

  test("1. Gallery - Browse Photos", async ({ page }) => {
    console.log("=== FEATURE 1: Gallery - Browse Photos ===");
    await page.goto("/");
    await page.waitForSelector(".photo-grid, .empty-gallery", {
      timeout: 10000,
    });

    // Toolbar with search, favorites filter, upload
    await expect(page.locator(".gallery-toolbar")).toBeVisible();
    await expect(page.locator('input[type="search"]')).toBeVisible();

    // Photos displayed in grid
    const photoCount = await page.locator(".photo-card").count();
    console.log(`Gallery shows ${photoCount} photos`);

    await page.screenshot({ path: "test-results/demo-01-gallery.png" });
  });

  test("2. Gallery - Search Photos", async ({ page }) => {
    console.log("=== FEATURE 2: Gallery - Search Photos ===");
    await page.goto("/");
    await page.waitForSelector('input[type="search"]', { timeout: 10000 });

    const searchInput = page.locator('input[type="search"]');
    await searchInput.fill("test");
    await page.waitForTimeout(1000);

    // Search results displayed
    const results = await page.locator(".photo-card").count();
    console.log(`Search 'test' returned ${results} results`);

    await searchInput.fill("");
    await page.waitForTimeout(500);

    await page.screenshot({ path: "test-results/demo-02-search.png" });
  });

  test("3. Gallery - Favorites Filter", async ({ page }) => {
    console.log("=== FEATURE 3: Gallery - Favorites Filter ===");
    await page.goto("/");
    await page.waitForSelector(".gallery-toolbar", { timeout: 10000 });

    // Toggle favorites filter
    const favBtn = page.locator("button:has-text('Favorites')");
    await expect(favBtn).toBeVisible();
    await favBtn.click();

    await page.screenshot({ path: "test-results/demo-03-favorites.png" });
  });

  test("4. Gallery - Upload Photo", async ({ page }) => {
    console.log("=== FEATURE 4: Gallery - Upload Photo ===");
    await page.goto("/");
    await page.waitForSelector(".gallery-toolbar", { timeout: 10000 });

    // Upload button visible (use exact match to avoid strict violation)
    const uploadBtn = page.getByRole("button", { name: "Upload", exact: true });
    await expect(uploadBtn).toBeVisible();
    console.log("Upload button is accessible");

    await page.screenshot({ path: "test-results/demo-04-upload.png" });
  });

  test("5. Albums - Browse & Create", async ({ page }) => {
    console.log("=== FEATURE 5: Albums - Browse & Create ===");
    await page.goto("/albums");
    await page.waitForSelector(".albums-page", { timeout: 10000 });

    // New Album button
    await expect(page.locator('[data-testid="create-album"]')).toBeVisible();

    // Album cards visible
    const albumCount = await page.locator(".album-card").count();
    console.log(`Albums page shows ${albumCount} albums`);

    await page.screenshot({ path: "test-results/demo-05-albums.png" });
  });

  test("6. Albums - Album Detail View", async ({ page }) => {
    console.log("=== FEATURE 6: Albums - Album Detail ===");

    // Get first album ID from API and navigate directly
    const albums = await page.evaluate(async () => {
      const response = await fetch("/api/albums");
      const data = await response.json();
      return data;
    });

    if (albums.length > 0) {
      await page.goto(`/albums/${albums[0].id}`);
      await page.waitForTimeout(1000);
      await expect(page.locator(".album-detail-page")).toBeVisible({
        timeout: 5000,
      });
      await expect(page.locator(".back-link")).toBeVisible();
      console.log(`Viewing album: ${albums[0].name}`);
    } else {
      console.log("No albums available to view");
    }

    await page.screenshot({ path: "test-results/demo-06-album-detail.png" });
  });

  test("7. Photo Editor - Edit Photo", async ({ page }) => {
    console.log("=== FEATURE 7: Photo Editor ===");
    await page.goto("/editor/1");
    await page.waitForSelector(".editor-page, .error-screen", {
      timeout: 10000,
    });

    const editorVisible = await page.locator(".editor-page").isVisible();
    if (editorVisible) {
      // Editor controls
      await expect(page.locator(".editor-header")).toBeVisible();
      await expect(page.locator(".editor-controls")).toBeVisible();

      // Transform buttons
      await expect(page.locator('button:has-text("Rotate 90")')).toBeVisible();
      await expect(page.locator('button:has-text("Flip H")')).toBeVisible();

      // Adjustment sliders
      const sliders = await page.locator('input[type="range"]').count();
      console.log(`Editor has ${sliders} adjustment sliders`);

      await page.screenshot({ path: "test-results/demo-07-editor.png" });
    } else {
      console.log("Editor not available (photo not found)");
    }
  });

  test("8. Face Recognition", async ({ page }) => {
    console.log("=== FEATURE 8: Face Recognition ===");
    await page.goto("/faces");
    await page.waitForSelector(".faces-page", { timeout: 10000 });

    // Faces page loads
    await expect(page.locator(".faces-page")).toBeVisible();

    const personCount = await page.locator(".person-card, .face-item").count();
    console.log(`Faces page shows ${personCount} persons/faces`);

    await page.screenshot({ path: "test-results/demo-08-faces.png" });
  });

  test("9. Dashboard - Metrics & Analytics", async ({ page }) => {
    console.log("=== FEATURE 9: Dashboard ===");
    await page.goto("/dashboard");
    await page.waitForSelector(".dashboard-page", { timeout: 10000 });

    // Dashboard metrics
    await expect(page.locator(".dashboard-page")).toBeVisible();

    // Performance metrics
    const metrics = await page.locator(".metric-card, .stat-card").count();
    console.log(`Dashboard has ${metrics} metric cards`);

    // Task queue
    const queueVisible = await page
      .locator(".task-queue, .queue-list")
      .isVisible()
      .catch(() => false);
    console.log(`Task queue visible: ${queueVisible}`);

    // Log viewer
    const logViewer = await page
      .locator(".log-viewer, .logs-panel")
      .isVisible()
      .catch(() => false);
    console.log(`Log viewer visible: ${logViewer}`);

    await page.screenshot({ path: "test-results/demo-09-dashboard.png" });
  });

  test("10. Settings - Configuration", async ({ page }) => {
    console.log("=== FEATURE 10: Settings ===");
    await page.goto("/settings");
    await page.waitForSelector(".settings-page", { timeout: 10000 });

    // Settings sections
    await expect(page.locator(".settings-page")).toBeVisible();

    // Server settings
    const serverInputs = await page
      .locator('input[id*="port"], input[id*="host"]')
      .count();
    console.log(`Server settings: ${serverInputs} inputs`);

    // Processing toggles
    const toggles = await page.locator('input[type="checkbox"]').count();
    console.log(`Processing toggles: ${toggles}`);

    // Danger zone
    const dangerVisible = await page
      .locator(".danger-zone, .danger-section")
      .isVisible()
      .catch(() => false);
    console.log(`Danger zone visible: ${dangerVisible}`);

    await page.screenshot({ path: "test-results/demo-10-settings.png" });
  });

  test("11. Task Queue Management", async ({ page }) => {
    console.log("=== FEATURE 11: Task Queue ===");
    await page.goto("/dashboard");
    await page.waitForSelector(".dashboard-page", { timeout: 10000 });

    // Task queue section
    const queueSection = page.locator(
      ".task-queue, .queue-section, [data-testid='task-queue']",
    );
    const isVisible = await queueSection.isVisible().catch(() => false);
    console.log(`Task queue section visible: ${isVisible}`);

    await page.screenshot({ path: "test-results/demo-11-queue.png" });
  });

  test("12. User Authentication Flow", async ({ page }) => {
    console.log("=== FEATURE 12: Authentication ===");

    // Register page
    await page.goto("/register");
    await expect(page.locator(".auth-page")).toBeVisible();
    await expect(page.locator('[name="username"]')).toBeVisible();
    await expect(page.locator('[name="password"]')).toBeVisible();
    console.log("Registration page loads with username/password fields");

    await page.screenshot({ path: "test-results/demo-12-register.png" });

    // Login page
    await page.goto("/login");
    await expect(page.locator(".auth-page")).toBeVisible();
    console.log("Login page loads");

    await page.screenshot({ path: "test-results/demo-12-login.png" });

    // Logout
    await page.goto("/");
    await page.waitForSelector(".gallery-toolbar", { timeout: 10000 });

    // Look for logout button in header/sidebar
    const logoutBtn = page.locator(
      "button:has-text('Logout'), a:has-text('Logout'), [data-testid='logout']",
    );
    const logoutVisible = await logoutBtn.isVisible().catch(() => false);
    console.log(`Logout button visible: ${logoutVisible}`);
  });

  test("13. Responsive Layout - Sidebar Navigation", async ({ page }) => {
    console.log("=== FEATURE 13: Navigation ===");
    await page.goto("/");
    await page.waitForSelector(".app-layout", { timeout: 10000 });

    // Sidebar links
    const sidebarLinks = await page
      .locator(".sidebar a, .sidebar-nav a, nav a")
      .count();
    console.log(`Sidebar has ${sidebarLinks} navigation links`);

    // Test each nav link
    const navItems = [
      { name: "Gallery", url: "/" },
      { name: "Dashboard", url: "/dashboard" },
      { name: "Albums", url: "/albums" },
      { name: "Faces", url: "/faces" },
      { name: "Settings", url: "/settings" },
    ];

    for (const item of navItems) {
      const link = page.locator(
        `a[href="${item.url}"], a:has-text("${item.name}")`,
      );
      const visible = await link.isVisible().catch(() => false);
      console.log(`  ${item.name} link visible: ${visible}`);
    }

    await page.screenshot({ path: "test-results/demo-13-navigation.png" });
  });
});
