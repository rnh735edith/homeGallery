const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const SCREENSHOT_DIR = path.join(__dirname, "tests/e2e/setup-screenshots");
const BASE_URL = "http://localhost:8080";

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}
fs.readdirSync(SCREENSHOT_DIR).forEach((f) =>
  fs.unlinkSync(path.join(SCREENSHOT_DIR, f)),
);

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
  console.log("🎬 Capturing HomeGallery screenshots...\n");

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
  });
  const page = await context.newPage();

  // ========== SETUP WIZARD (6 steps) ==========
  console.log("📋 Setup Wizard Screenshots:");
  await page.goto(`${BASE_URL}/setup`, { waitUntil: "networkidle" });
  await wait(500);

  // Step 1: Photo Library
  await screenshot(page, "01-setup-step1-library");
  await page.locator('input[name="photo_dir"]').first().fill("D:/Photos");
  await wait(300);
  await screenshot(page, "02-setup-step1-library-filled");
  await page.getByRole("button", { name: "Next" }).click();
  await wait(800);

  // Step 2: Admin Account
  await screenshot(page, "03-setup-step2-admin");
  await page.locator('input[name="username"]').fill("testadmin");
  await page.locator('input[name="password"]').fill("TestPass123!");
  await page.locator('input[name="confirmPassword"]').fill("TestPass123!");
  await wait(300);
  await screenshot(page, "04-setup-step2-admin-filled");
  await page.getByRole("button", { name: "Next" }).click();
  await wait(800);

  // Step 3: Server
  await screenshot(page, "05-setup-step3-server");
  await page.getByRole("button", { name: "Next" }).click();
  await wait(800);

  // Step 4: Database
  await screenshot(page, "06-setup-step4-database");
  await page.getByRole("button", { name: "Next" }).click();
  await wait(800);

  // Step 5: Processing
  await screenshot(page, "07-setup-step5-processing");
  await page.getByRole("button", { name: "Next" }).click();
  await wait(800);

  // Step 6: Review/Summary
  await screenshot(page, "08-setup-step6-review");
  await page.getByRole("button", { name: "Save & Start" }).click();
  await wait(3000);

  // ========== LOGIN ==========
  console.log("\n🔐 Login Screenshots:");
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
  await wait(500);
  await screenshot(page, "09-login-page");

  await page.locator('input[name="username"]').fill("testadmin");
  await page.locator('input[name="password"]').fill("TestPass123!");
  await wait(300);
  await screenshot(page, "10-login-filled");

  await page.getByRole("button", { name: /sign in|login/i }).click();
  await wait(2000);

  // ========== AUTHENTICATED VIEWS ==========
  console.log("\n📸 Authenticated View Screenshots:");

  await page.goto(`${BASE_URL}/`, { waitUntil: "networkidle" });
  await wait(1000);
  await screenshot(page, "11-gallery");

  await page.goto(`${BASE_URL}/albums`, { waitUntil: "networkidle" });
  await wait(500);
  await screenshot(page, "12-albums");

  await page.goto(`${BASE_URL}/duplicates`, { waitUntil: "networkidle" });
  await wait(500);
  await screenshot(page, "13-duplicates");

  await page.goto(`${BASE_URL}/dashboard`, { waitUntil: "networkidle" });
  await wait(500);
  await screenshot(page, "14-dashboard");

  await page.goto(`${BASE_URL}/settings`, { waitUntil: "networkidle" });
  await wait(1000);
  await screenshot(page, "15-settings-general");

  // API Keys tab
  await page.getByRole("tab", { name: /api key/i }).click();
  await wait(500);
  await screenshot(page, "16-settings-api-keys");

  // Agents tab
  await page.getByRole("tab", { name: /agent/i }).click();
  await wait(500);
  await screenshot(page, "17-settings-agents");

  // Mobile view
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(`${BASE_URL}/`, { waitUntil: "networkidle" });
  await wait(1000);
  await screenshot(page, "18-mobile-gallery");

  await browser.close();

  console.log("\n📊 Screenshots captured:");
  const files = fs.readdirSync(SCREENSHOT_DIR);
  files.forEach((f) => {
    const stats = fs.statSync(path.join(SCREENSHOT_DIR, f));
    console.log(`  ${f} (${(stats.size / 1024).toFixed(1)} KB)`);
  });
  console.log(
    `\n✅ Total: ${files.length} screenshots saved to ${SCREENSHOT_DIR}`,
  );
}

main().catch((err) => {
  console.error("Error:", err.message);
  process.exit(1);
});
