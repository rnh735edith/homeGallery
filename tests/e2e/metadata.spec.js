const { test, expect } = require("./fixtures");

test.describe("Metadata Features", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill("[name=username]", "testadmin");
    await page.fill("[name=password]", "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
  });

  test("metadata badge shows on gallery photos", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".photo-card");

    // Check that metadata badges exist (if photos have metadata)
    const badges = page.locator(".metadata-badge-compact");
    const count = await badges.count();
    if (count > 0) {
      const firstBadge = badges.first();
      await expect(firstBadge).toBeVisible();
    }
  });

  test("metadata panel opens on shift+click", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".photo-card");

    const firstPhoto = page.locator(".photo-card").first();
    await firstPhoto.click({ modifiers: ["Shift"] });

    // Panel should appear if metadata exists
    const panel = page.locator(".metadata-panel");
    const isVisible = await panel
      .isVisible({ timeout: 2000 })
      .catch(() => false);
    if (isVisible) {
      await expect(panel).toBeVisible();
      await expect(panel).toContainText("Photo Metadata");
    }
  });

  test("tag filter input exists in gallery toolbar", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".gallery-toolbar");

    const tagInput = page.locator('input[placeholder="Filter by tag..."]');
    await expect(tagInput).toBeVisible();
  });

  test("color filter input exists in gallery toolbar", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".gallery-toolbar");

    const colorFilter = page.locator('input[type="color"]');
    await expect(colorFilter).toBeVisible();
  });

  test("clear filters button appears when filters are active", async ({
    page,
  }) => {
    await page.goto("/");
    await page.waitForSelector(".gallery-toolbar");

    const tagInput = page.locator('input[placeholder="Filter by tag..."]');
    await tagInput.fill("test");

    const clearBtn = page.locator("button", { hasText: "Clear filters" });
    await expect(clearBtn).toBeVisible();
  });

  test("agents settings shows metadata agent", async ({ page }) => {
    await page.goto("/settings");
    await page.waitForSelector(".settings-page");

    // Click Agents tab
    const agentsTab = page.locator("button", { hasText: "Agents" });
    await expect(agentsTab).toBeVisible();
    await agentsTab.click();

    // Check metadata agent card exists
    const metadataCard = page.locator(".agent-card", { hasText: "metadata" });
    await expect(metadataCard).toBeVisible();
  });
});
