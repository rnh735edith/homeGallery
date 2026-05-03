const { test, expect } = require("./fixtures");

test.describe("Settings", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
    await page.goto("/settings");
  });

  test("settings page loads", async ({ page }) => {
    await expect(page.locator(".settings-page")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  });

  test("all settings sections display", async ({ page }) => {
    await expect(page.getByRole("button", { name: "General" })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Storage & Folders" }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Database" })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Backup & Restore" }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Wipe Data" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Agents" })).toBeVisible();
  });

  test("server settings are editable", async ({ page }) => {
    const portInput = page.locator('input[type="number"]').first();
    await expect(portInput).toBeVisible();
    await portInput.fill("9090");
    await expect(portInput).toHaveValue("9090");
  });

  test("processing toggles work", async ({ page }) => {
    const checkboxes = page.locator('.setting-section input[type="checkbox"]');
    await expect(checkboxes).toHaveCount(2);
  });

  test("danger zone is visible", async ({ page }) => {
    await page.getByRole("button", { name: "Wipe Data" }).click();
    await expect(page.locator(".settings-danger-zone")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Reset to Factory Defaults" }),
    ).toBeVisible();
  });
});
