const { test, expect } = require('./fixtures');

test.describe('Face Recognition', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', 'testadmin');
    await page.fill('[name="password"]', 'TestPass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('/');
  });

  test('faces page loads', async ({ page }) => {
    await page.goto('/faces');
    await expect(page.locator('.faces-page')).toBeVisible();
    await expect(page.locator('.person-grid, .empty-faces, .loading-screen')).toBeVisible();
    // Wait for loading to finish
    await page.waitForFunction(() => !document.querySelector('.loading-screen'), { timeout: 10000 });
    await expect(page.locator('.person-grid, .empty-faces')).toBeVisible();
  });

  test('can view photos of a person', async ({ page }) => {
    await page.goto('/faces');
    const personCard = page.locator('.person-card').first();
    if (await personCard.isVisible()) {
      await personCard.click();
      await expect(page.locator('.person-photos')).toBeVisible();
    }
  });
});
