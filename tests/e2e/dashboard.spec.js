const { test, expect } = require('./fixtures');

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', 'testadmin');
    await page.fill('[name="password"]', 'TestPass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('/');
    await page.goto('/dashboard');
  });

  test('dashboard loads with metrics', async ({ page }) => {
    await expect(page.locator('.dashboard-page')).toBeVisible();
    await expect(page.locator('.metrics-grid')).toBeVisible();
  });

  test('performance metrics display', async ({ page }) => {
    await expect(page.locator('.metric-card')).toHaveCount(6);
    await expect(page.getByText('App CPU', { exact: true })).toBeVisible();
    await expect(page.getByText('App Memory', { exact: true })).toBeVisible();
    await expect(page.locator('.metric-card', { hasText: 'Photos' }).first()).toBeVisible();
    await expect(page.locator('.metric-card', { hasText: 'Thumbnails' }).first()).toBeVisible();
    await expect(page.locator('.metric-card', { hasText: 'Disk Usage' }).first()).toBeVisible();
    await expect(page.locator('.metric-card', { hasText: 'Database' }).first()).toBeVisible();
  });

  test('storage chart renders', async ({ page }) => {
    await expect(page.locator('.storage-chart')).toBeVisible();
    await expect(page.locator('.chart-bar')).toBeVisible();
  });

  test('task queue displays', async ({ page }) => {
    await expect(page.locator('.task-list, .empty-tasks')).toBeVisible();
  });

  test('log viewer displays', async ({ page }) => {
    await expect(page.locator('.log-viewer')).toBeVisible();
  });
});
