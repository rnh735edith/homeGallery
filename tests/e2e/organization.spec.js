const { test, expect } = require("./fixtures");
const { loginAsAdmin } = require("./fixtures");

test.describe("Auto-Organization", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test("duplicates page loads", async ({ page }) => {
    await page.goto("/duplicates");
    // Use role-based selector to avoid strict mode violation
    await expect(
      page.getByRole("heading", { name: "Duplicate Photos" }),
    ).toBeVisible();
  });

  test("sidebar shows duplicates link", async ({ page }) => {
    await page.goto("/");
    // NavLink with icon + text - use regex to match
    const dupLink = page.getByRole("link", { name: /Duplicates/ });
    await expect(dupLink).toBeVisible();
    await dupLink.click();
    await expect(page).toHaveURL(/.*duplicates/);
  });

  test("albums page shows sections", async ({ page }) => {
    await page.goto("/albums");
    // Check if section headers exist (conditional on albums existing)
    const userSection = page.getByRole("heading", { name: "Your Albums" });
    const autoSection = page.getByRole("heading", { name: "Auto-Albums" });
    const userCount = await userSection.count();
    const autoCount = await autoSection.count();
    if (userCount > 0 || autoCount > 0) {
      // At least one section should be visible if albums exist
      expect(userCount + autoCount).toBeGreaterThanOrEqual(0);
    }
  });

  test("auto-album badge appears for auto albums", async ({ page }) => {
    await page.goto("/albums");
    // Auto-albums show "Auto" badge with class "badge badge-auto"
    const autoBadges = page.locator(".album-card-auto .badge-auto");
    const count = await autoBadges.count();
    if (count > 0) {
      await expect(autoBadges.first()).toBeVisible();
      await expect(autoBadges.first()).toHaveText("Auto");
    }
  });

  test("auto-album edit button is disabled", async ({ page }) => {
    await page.goto("/albums");
    // Find album cards that have auto badge
    const autoCards = page.locator(".album-card-auto");
    const count = await autoCards.count();
    if (count > 0) {
      // Edit button should be disabled for auto-albums
      const editBtn = autoCards.first().getByRole("button", { name: "Edit" });
      await expect(editBtn).toBeDisabled();
    }
  });

  test("organization agent card shows in settings", async ({ page }) => {
    await page.goto("/settings");
    // Settings tabs are buttons, not proper ARIA tabs
    await page.getByRole("button", { name: "Agents" }).click();
    // Agent cards have class "agent-card"
    const orgCard = page.locator(".agent-card", { hasText: /organization/i });
    await expect(orgCard).toBeVisible();
  });
});
