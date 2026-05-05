const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const SCREENSHOT_DIR =
  "D:\\Service\\homeGallery\\tests\\e2e\\setup-screenshots";
const BASE_URL = "http://localhost:8080";
const TEST_USER = { username: "testadmin", password: "TestPass123!" };

async function captureScreenshots() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 1024 },
  });
  const page = await context.newPage();

  const screenshots = [];

  try {
    // 1. Setup step 1 (Photo Library) - http://localhost:8080/setup
    console.log("Capturing setup step 1...");
    await page.goto(`${BASE_URL}/setup`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1000);
    const setup1Path = path.join(
      SCREENSHOT_DIR,
      "01-setup-step1-photo-library.png",
    );
    await page.screenshot({ path: setup1Path, fullPage: true });
    screenshots.push({
      name: "01-setup-step1-photo-library.png",
      path: setup1Path,
    });

    // 2. Setup step 2 (Admin Account) - click Next
    console.log("Capturing setup step 2...");
    const nextButtons = await page.$$('button:has-text("Next")');
    if (nextButtons.length > 0) {
      await nextButtons[0].click();
      await page.waitForTimeout(1000);
    }
    const setup2Path = path.join(
      SCREENSHOT_DIR,
      "02-setup-step2-admin-account.png",
    );
    await page.screenshot({ path: setup2Path, fullPage: true });
    screenshots.push({
      name: "02-setup-step2-admin-account.png",
      path: setup2Path,
    });

    // 3. Setup step 3 (Agents) - click Next
    console.log("Capturing setup step 3...");
    const nextButtons2 = await page.$$('button:has-text("Next")');
    if (nextButtons2.length > 0) {
      await nextButtons2[0].click();
      await page.waitForTimeout(1000);
    }
    const setup3Path = path.join(SCREENSHOT_DIR, "03-setup-step3-agents.png");
    await page.screenshot({ path: setup3Path, fullPage: true });
    screenshots.push({ name: "03-setup-step3-agents.png", path: setup3Path });

    // 4. Setup step 4 (Database) - click Next
    console.log("Capturing setup step 4...");
    const nextButtons3 = await page.$$('button:has-text("Next")');
    if (nextButtons3.length > 0) {
      await nextButtons3[0].click();
      await page.waitForTimeout(1000);
    }
    const setup4Path = path.join(SCREENSHOT_DIR, "04-setup-step4-database.png");
    await page.screenshot({ path: setup4Path, fullPage: true });
    screenshots.push({ name: "04-setup-step4-database.png", path: setup4Path });

    // 5. Setup step 5 (Review/Finish) - click Next
    console.log("Capturing setup step 5...");
    const nextButtons4 = await page.$$('button:has-text("Next")');
    if (nextButtons4.length > 0) {
      await nextButtons4[0].click();
      await page.waitForTimeout(1000);
    }
    const setup5Path = path.join(SCREENSHOT_DIR, "05-setup-step5-review.png");
    await page.screenshot({ path: setup5Path, fullPage: true });
    screenshots.push({ name: "05-setup-step5-review.png", path: setup5Path });

    // Since config.json exists, setup will redirect to login
    // Let's login and capture authenticated views

    // 6. Login page - http://localhost:8080/login
    console.log("Capturing login page...");
    await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1000);
    const loginPath = path.join(SCREENSHOT_DIR, "06-login-page.png");
    await page.screenshot({ path: loginPath, fullPage: true });
    screenshots.push({ name: "06-login-page.png", path: loginPath });

    // Login
    console.log("Logging in...");
    await page.fill('input[name="username"]', TEST_USER.username);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: "networkidle" });
    await page.waitForTimeout(2000);

    // 7. Gallery after login - http://localhost:8080/
    console.log("Capturing gallery page...");
    await page.goto(`${BASE_URL}/`, { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);
    const galleryPath = path.join(SCREENSHOT_DIR, "07-gallery-page.png");
    await page.screenshot({ path: galleryPath, fullPage: true });
    screenshots.push({ name: "07-gallery-page.png", path: galleryPath });

    // 8. Albums page - http://localhost:8080/albums
    console.log("Capturing albums page...");
    await page.goto(`${BASE_URL}/albums`, { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);
    const albumsPath = path.join(SCREENSHOT_DIR, "08-albums-page.png");
    await page.screenshot({ path: albumsPath, fullPage: true });
    screenshots.push({ name: "08-albums-page.png", path: albumsPath });

    // 9. Duplicates page - http://localhost:8080/duplicates
    console.log("Capturing duplicates page...");
    await page.goto(`${BASE_URL}/duplicates`, { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);
    const duplicatesPath = path.join(SCREENSHOT_DIR, "09-duplicates-page.png");
    await page.screenshot({ path: duplicatesPath, fullPage: true });
    screenshots.push({ name: "09-duplicates-page.png", path: duplicatesPath });

    // 10. Dashboard - http://localhost:8080/dashboard
    console.log("Capturing dashboard page...");
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);
    const dashboardPath = path.join(SCREENSHOT_DIR, "10-dashboard-page.png");
    await page.screenshot({ path: dashboardPath, fullPage: true });
    screenshots.push({ name: "10-dashboard-page.png", path: dashboardPath });

    // 11. Settings > General tab
    console.log("Capturing settings general tab...");
    await page.goto(`${BASE_URL}/settings`, { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);
    const settingsGeneralPath = path.join(
      SCREENSHOT_DIR,
      "11-settings-general.png",
    );
    await page.screenshot({ path: settingsGeneralPath, fullPage: true });
    screenshots.push({
      name: "11-settings-general.png",
      path: settingsGeneralPath,
    });

    // 12. Settings > API Keys tab
    console.log("Capturing settings API keys tab...");
    await page.click(
      'button:has-text("API Keys"), [role="tab"]:has-text("API Keys")',
    );
    await page.waitForTimeout(1500);
    const settingsApiKeysPath = path.join(
      SCREENSHOT_DIR,
      "12-settings-api-keys.png",
    );
    await page.screenshot({ path: settingsApiKeysPath, fullPage: true });
    screenshots.push({
      name: "12-settings-api-keys.png",
      path: settingsApiKeysPath,
    });

    // 13. Settings > Agents tab
    console.log("Capturing settings agents tab...");
    await page.click(
      'button:has-text("Agents"), [role="tab"]:has-text("Agents")',
    );
    await page.waitForTimeout(1500);
    const settingsAgentsPath = path.join(
      SCREENSHOT_DIR,
      "13-settings-agents.png",
    );
    await page.screenshot({ path: settingsAgentsPath, fullPage: true });
    screenshots.push({
      name: "13-settings-agents.png",
      path: settingsAgentsPath,
    });

    // 14. Mobile view (375px width) of gallery
    console.log("Capturing mobile view...");
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`${BASE_URL}/`, { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);
    const mobilePath = path.join(SCREENSHOT_DIR, "14-mobile-gallery-view.png");
    await page.screenshot({ path: mobilePath, fullPage: true });
    screenshots.push({ name: "14-mobile-gallery-view.png", path: mobilePath });

    console.log("\n=== SCREENSHOTS CAPTURED ===");
    for (const screenshot of screenshots) {
      const stats = fs.statSync(screenshot.path);
      console.log(`${screenshot.name} - ${stats.size} bytes`);
    }
  } catch (error) {
    console.error("Error capturing screenshots:", error.message);
  } finally {
    await browser.close();
  }
}

captureScreenshots();
