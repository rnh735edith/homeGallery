const { test, expect } = require("./fixtures");
const fs = require("fs");
const path = require("path");

test.describe("Management - Backup & Restore", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
    await page.goto("/settings");
    await page.waitForSelector(".settings-page");
  });

  test("backup tab is visible", async ({ page }) => {
    const backupTab = page.locator(".tab-btn", { hasText: "Backup & Restore" });
    await expect(backupTab).toBeVisible();
    await backupTab.click();
    await expect(page.locator("text=Export Config")).toBeVisible();
    await expect(page.locator("text=Import Config")).toBeVisible();
    await expect(page.locator("text=Full Backup")).toBeVisible();
    await expect(page.locator("text=Restore from Backup")).toBeVisible();
  });

  test("export config downloads file", async ({ page }) => {
    const backupTab = page.locator(".tab-btn", { hasText: "Backup & Restore" });
    await backupTab.click();

    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.locator("button", { hasText: "Export Config" }).click(),
    ]);

    expect(download.suggestedFilename()).toContain("homegallery-config.json");
  });

  test("import config accepts JSON file", async ({ page }) => {
    const backupTab = page.locator(".tab-btn", { hasText: "Backup & Restore" });
    await backupTab.click();

    // Import config file input is hidden but present
    const importInput = page.locator('input[type="file"][accept=".json"]');
    await expect(importInput).toHaveCount(1);
    // The label button should be visible
    await expect(
      page.locator("label", { hasText: "Import Config" }),
    ).toBeVisible();
  });

  test("create backup downloads ZIP file", async ({ page }) => {
    const backupTab = page.locator(".tab-btn", { hasText: "Backup & Restore" });
    await backupTab.click();

    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.locator("button", { hasText: "Backup (No Photos)" }).click(),
    ]);

    expect(download.suggestedFilename()).toContain("homegallery-backup-");
    expect(download.suggestedFilename()).toContain(".zip");
  });

  test("restore backup accepts ZIP file", async ({ page }) => {
    const backupTab = page.locator(".tab-btn", { hasText: "Backup & Restore" });
    await backupTab.click();

    // Restore file input is hidden but present
    const restoreInput = page.locator('input[type="file"][accept=".zip"]');
    await expect(restoreInput).toHaveCount(1);
    // The label button should be visible
    await expect(
      page.locator("label", { hasText: "Select Backup File" }),
    ).toBeVisible();
  });
});

test.describe("Management - Wipe Data", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
    await page.goto("/settings");
    await page.waitForSelector(".settings-page");
  });

  test("wipe tab is visible", async ({ page }) => {
    const wipeTab = page.locator(".tab-btn", { hasText: "Wipe Data" });
    await expect(wipeTab).toBeVisible();
    await wipeTab.click();
    await expect(
      page.getByRole("heading", { name: "📋 Wipe Data" }),
    ).toBeVisible();
  });

  test("all wipe options are displayed", async ({ page }) => {
    const wipeTab = page.locator(".tab-btn", { hasText: "Wipe Data" });
    await wipeTab.click();

    await expect(
      page.getByRole("heading", { name: "Wipe All Photos" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Wipe All Albums" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Wipe Database" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Full System Wipe" }),
    ).toBeVisible();
  });

  test("wipe buttons are disabled without confirmation", async ({ page }) => {
    const wipeTab = page.locator(".tab-btn", { hasText: "Wipe Data" });
    await wipeTab.click();

    // Check specific wipe action buttons (not danger zone reset button)
    const wipeButtons = page.locator(".wipe-actions .btn-danger");
    const count = await wipeButtons.count();
    expect(count).toBeGreaterThanOrEqual(4);

    for (let i = 0; i < count; i++) {
      const btn = wipeButtons.nth(i);
      const isDisabled = await btn.isDisabled();
      expect(isDisabled).toBe(true);
    }
  });

  test("danger zone is visible in wipe tab", async ({ page }) => {
    const wipeTab = page.locator(".tab-btn", { hasText: "Wipe Data" });
    await wipeTab.click();

    await expect(page.locator(".settings-danger-zone")).toBeVisible();
    await expect(page.locator("text=Reset to Factory Defaults")).toBeVisible();
  });
});

test.describe("Management - API Endpoints", () => {
  test("export config endpoint returns JSON", async ({ request }) => {
    const loginRes = await request.post("/api/auth/login", {
      data: { username: "testadmin", password: "TestPass123!" },
    });
    expect(loginRes.ok()).toBeTruthy();
    const token = (await loginRes.json()).access_token;

    const exportRes = await request.get("/api/management/config/export", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(exportRes.ok()).toBeTruthy();
    expect(exportRes.headers()["content-type"]).toContain("application/json");
  });

  test("status endpoint returns system info", async ({ request }) => {
    const loginRes = await request.post("/api/auth/login", {
      data: { username: "testadmin", password: "TestPass123!" },
    });
    expect(loginRes.ok()).toBeTruthy();
    const token = (await loginRes.json()).access_token;

    const statusRes = await request.get("/api/management/status", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(statusRes.ok()).toBeTruthy();
    const data = await statusRes.json();
    expect(data).toHaveProperty("photo_count");
    expect(data).toHaveProperty("album_count");
    expect(data).toHaveProperty("user_count");
    expect(data).toHaveProperty("db_size_bytes");
  });

  test("db status endpoint returns database info", async ({ request }) => {
    const loginRes = await request.post("/api/auth/login", {
      data: { username: "testadmin", password: "TestPass123!" },
    });
    expect(loginRes.ok()).toBeTruthy();
    const token = (await loginRes.json()).access_token;

    const dbStatusRes = await request.get("/api/management/db/status", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(dbStatusRes.ok()).toBeTruthy();
    const data = await dbStatusRes.json();
    expect(data).toHaveProperty("type");
    expect(data).toHaveProperty("path");
    expect(data).toHaveProperty("size_bytes");
    expect(data).toHaveProperty("tables");
  });

  test("wipe endpoints require confirmation", async ({ request }) => {
    const loginRes = await request.post("/api/auth/login", {
      data: { username: "testadmin", password: "TestPass123!" },
    });
    expect(loginRes.ok()).toBeTruthy();
    const token = (await loginRes.json()).access_token;

    const wipeRes = await request.post("/api/management/wipe/photos", {
      headers: { Authorization: `Bearer ${token}` },
      params: { confirm: "" },
    });
    expect(wipeRes.status()).toBe(400);
  });
});
