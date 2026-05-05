const { test, expect } = require("./fixtures");

test.describe("Setup Flow", () => {
  test.beforeEach(async ({ page }) => {
    // Reset config via API to trigger setup wizard
    await page.request.post("/api/setup/reset");
    await page.goto("/");
  });

  test.afterAll(async ({ request }) => {
    // Re-create config so other tests can run
    await request.post("/api/setup/configure", {
      data: {
        server: { host: "0.0.0.0", port: 8080 },
        database: { type: "sqlite", url: "sqlite:///./data/test_gallery.db" },
        storage: {
          photo_dir: "./data/test_photos",
          thumbnail_dir: "./data/test_thumbnails",
          face_encoding_dir: "./data/test_face_encodings",
        },
        admin: { username: "testadmin", password: "TestPass123!" },
        processing: {
          thumbnail_sizes: { small: 200, medium: 800, large: 1920 },
          auto_thumbnails: true,
          face_detection: false,
          face_processing_max_memory_mb: 512,
          max_concurrent_tasks: 2,
        },
      },
    });
  });

  test("redirects to setup when not configured", async ({ page }) => {
    await expect(page.locator(".setup-page")).toBeVisible();
    await expect(page.locator("h1")).toContainText("HomeGallery Setup");
  });

  test("setup wizard has all 6 steps", async ({ page }) => {
    await expect(page.locator(".setup-step-label")).toContainText(
      "Step 1 of 6",
    );

    await page.click('button:has-text("Next")');
    await expect(page.locator(".setup-step-label")).toContainText(
      "Step 2 of 6",
    );

    // Admin step requires filling form to advance
    await page.fill("#admin-username", "testadmin");
    await page.fill("#admin-password", "TestPass123!");
    await page.fill("#admin-confirm", "TestPass123!");
    await page.click('button:has-text("Next")');
    await expect(page.locator(".setup-step-label")).toContainText(
      "Step 3 of 6",
    );

    await page.click('button:has-text("Next")');
    await expect(page.locator(".setup-step-label")).toContainText(
      "Step 4 of 6",
    );

    await page.click('button:has-text("Next")');
    await expect(page.locator(".setup-step-label")).toContainText(
      "Step 5 of 6",
    );

    await page.click('button:has-text("Next")');
    await expect(page.locator(".setup-step-label")).toContainText(
      "Step 6 of 6",
    );
  });

  test("admin step validates username length", async ({ page }) => {
    await page.click('button:has-text("Next")');
    await page.fill("#admin-username", "ab");
    await page.click('button:has-text("Next")');
    await expect(page.locator(".setup-error")).toContainText(
      "at least 3 characters",
    );
  });

  test("admin step validates password match", async ({ page }) => {
    await page.click('button:has-text("Next")');
    await page.fill("#admin-username", "testadmin");
    await page.fill("#admin-password", "password123");
    await page.fill("#admin-confirm", "different123");
    await page.click('button:has-text("Next")');
    await expect(page.locator(".setup-error")).toContainText("do not match");
  });

  test("completes full setup and redirects to login", async ({ page }) => {
    await page.fill("#photo-dir", "./data/photos");
    await page.click('button:has-text("Next")');
    await page.fill("#admin-username", "testadmin");
    await page.fill("#admin-password", "TestPass123!");
    await page.fill("#admin-confirm", "TestPass123!");
    await page.click('button:has-text("Next")');
    await page.fill("#server-port", "8080");
    await page.click('button:has-text("Next")');
    await page.click('button:has-text("Next")');
    await page.click('button:has-text("Next")');
    await page.click('button:has-text("Save & Start")');
    await expect(page).toHaveURL("/login");
  });
});
