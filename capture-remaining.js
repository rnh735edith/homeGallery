const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const SCREENSHOT_DIR = path.join(__dirname, "tests/e2e/setup-screenshots");
const BASE_URL = "http://localhost:8080";

async function screenshot(page, name) {
  const filePath = path.join(SCREENSHOT_DIR, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  console.log(`  ✓ ${name}.png`);
  return filePath;
}

async function wait(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function main() {
  console.log("🎬 Capturing remaining screenshots...\n");

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
  });
  const page = await context.newPage();

  // Login
  console.log("🔐 Login Screenshots:");
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
  await wait(500);
  await screenshot(page, "09-login-page");

  await page.locator('input[name="username"]').fill("testadmin");
  await page.locator('input[name="password"]').fill("TestPass123!");
  await wait(300);
  await screenshot(page, "10-login-filled");

  await page.getByRole("button", { name: /sign in|login/i }).click();
  await wait(2000);

  // Authenticated views
  console.log("\n📸 Authenticated View Screenshots:");

  // Settings > API Keys tab
  console.log("  Navigating to Settings...");
  await page.goto(`${BASE_URL}/settings`, { waitUntil: "networkidle" });
  await wait(1000);

  console.log("  Clicking API Keys tab...");
  try {
    await page.getByRole("button", { name: "API Keys" }).click();
    await wait(2000);
    // Check for errors
    const hasError = await page
      .locator('.error, .empty-api-keys, text="No API keys"')
      .count();
    console.log("  Error elements found:", hasError);
  } catch (e) {
    console.log("  Click error:", e.message);
  }
  await screenshot(page, "16-settings-api-keys");

  // Settings > Agents tab
  console.log("  Clicking Agents tab...");
  try {
    await page.getByRole("button", { name: "Agents" }).click();
    await wait(1000);
  } catch (e) {
    console.log("  Click error:", e.message);
  }
  await screenshot(page, "17-settings-agents");

  // Mobile view
  console.log("  Capturing mobile view...");
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(`${BASE_URL}/`, { waitUntil: "networkidle" });
  await wait(1000);
  await screenshot(page, "18-mobile-gallery");

  await browser.close();

  console.log("\n✅ All screenshots captured!");
}

main().catch((err) => {
  console.error("Error:", err.message);
  process.exit(1);
});
