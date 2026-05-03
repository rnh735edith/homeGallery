const { test: baseTest, expect } = require("@playwright/test");

const test = baseTest.extend({
  page: async ({ page }, use) => {
    await use(page);
  },
});

/**
 * Helper to login as admin user
 * @param {import('@playwright/test').Page} page
 */
async function loginAsAdmin(page) {
  await page.goto("/login");
  await page.fill('[name="username"]', "testadmin");
  await page.fill('[name="password"]', "TestPass123!");
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL("/");
}

module.exports = { test, expect, loginAsAdmin };
