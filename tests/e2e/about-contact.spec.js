const { test, expect, loginAsAdmin } = require("./fixtures");

test.describe("About Page", () => {
  test("about page loads without auth", async ({ page }) => {
    await page.goto("/about");
    await expect(page.locator(".about-page")).toBeVisible();
    await expect(page.locator("h1")).toContainText("HomeGallery");
  });

  test("about page shows features section", async ({ page }) => {
    await page.goto("/about");
    await expect(page.getByRole("heading", { name: "Features" })).toBeVisible();
    await expect(page.locator(".feature-list")).toBeVisible();
  });

  test("about page shows tech stack", async ({ page }) => {
    await page.goto("/about");
    await expect(
      page.getByRole("heading", { name: "Tech Stack" }),
    ).toBeVisible();
    await expect(page.locator(".tech-grid")).toBeVisible();
  });

  test("about page shows agents section", async ({ page }) => {
    await page.goto("/about");
    await expect(
      page.getByRole("heading", { name: "AI Agents" }),
    ).toBeVisible();
  });

  test("about page links to contact", async ({ page }) => {
    await page.goto("/about");
    const contactLink = page.locator("a.about-link");
    await expect(contactLink).toBeVisible();
    await expect(contactLink).toHaveAttribute("href", "/contact");
  });

  test("about page is accessible from sidebar", async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
    await page.getByRole("link", { name: "About" }).click();
    await expect(page).toHaveURL("/about");
  });
});

test.describe("Contact Page", () => {
  test("contact page loads without auth", async ({ page }) => {
    await page.goto("/contact");
    await expect(page.locator(".contact-page")).toBeVisible();
    await expect(page.locator("h1")).toContainText("Contact");
  });

  test("contact form has required fields", async ({ page }) => {
    await page.goto("/contact");
    await expect(page.locator("#name")).toBeVisible();
    await expect(page.locator("#email")).toBeVisible();
    await expect(page.locator("#subject")).toBeVisible();
    await expect(page.locator("#message")).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test("contact form validates required fields", async ({ page }) => {
    await page.goto("/contact");
    await page.click('button[type="submit"]');
    await expect(page.locator(".field-error").first()).toBeVisible();
  });

  test("contact form validates email format", async ({ page }) => {
    await page.goto("/contact");
    await page.fill("#name", "Test User");
    await page.fill("#email", "invalid-email");
    await page.fill("#message", "Test message");
    await page.click('button[type="submit"]');
    await expect(page.locator(".field-error")).toContainText("Invalid email");
  });

  test("contact form submits successfully", async ({ page }) => {
    await page.goto("/contact");
    await page.fill("#name", "E2E Tester");
    await page.fill("#email", "e2e@test.com");
    await page.fill("#subject", "E2E Test");
    await page.fill("#message", "This is an E2E test message");
    await page.click('button[type="submit"]');
    await expect(page.locator(".contact-success")).toBeVisible();
    await expect(page.locator(".contact-success h2")).toContainText(
      "Message Sent",
    );
  });

  test("contact page links to about", async ({ page }) => {
    await page.goto("/contact");
    const aboutLink = page.locator("a.contact-link");
    await expect(aboutLink).toBeVisible();
    await expect(aboutLink).toHaveAttribute("href", "/about");
  });

  test("contact is accessible from sidebar", async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
    await page.getByRole("link", { name: "Contact" }).click();
    await expect(page).toHaveURL("/contact");
  });
});

test.describe("Contact Messages (Admin Inbox)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
    await page.goto("/settings");
    await page.getByRole("button", { name: "Messages" }).click();
  });

  test("messages tab is visible in settings", async ({ page }) => {
    await expect(page.getByRole("button", { name: "Messages" })).toBeVisible();
  });

  test("messages section loads", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Contact Messages" }),
    ).toBeVisible();
  });

  test("shows submitted messages", async ({ page }) => {
    await page.goto("/contact");
    await page.fill("#name", "Unique Sender ABC");
    await page.fill("#email", "unique-abc@test.com");
    await page.fill("#subject", "Unique Subject XYZ");
    await page.fill("#message", "Unique message content 123");
    await page.click('button[type="submit"]');
    await expect(page.locator(".contact-success")).toBeVisible();

    await page.goto("/settings");
    await page.getByRole("button", { name: "Messages" }).click();

    await expect(page.getByText("Unique Sender ABC")).toBeVisible();
    await expect(page.getByText("Unique Subject XYZ")).toBeVisible();
    await expect(page.getByText("Unique message content 123")).toBeVisible();
  });

  test("unread messages show badge", async ({ page }) => {
    await page.goto("/contact");
    await page.fill("#name", "Badge Unique");
    await page.fill("#email", "badge-unique@test.com");
    await page.fill("#message", "Badge unique test");
    await page.click('button[type="submit"]');
    await expect(page.locator(".contact-success")).toBeVisible();

    await page.goto("/settings");
    await page.getByRole("button", { name: "Messages" }).click();
    await expect(page.locator(".message-badge").first()).toContainText("New");
  });

  test("mark message as read removes badge", async ({ page }) => {
    await page.goto("/settings");
    await page.getByRole("button", { name: "Messages" }).click();

    const badgeLocator = page.locator(".message-badge").first();
    const hasBadge = await badgeLocator.isVisible().catch(() => false);
    if (hasBadge) {
      await page.getByRole("button", { name: "Mark Read" }).first().click();
      await page.waitForTimeout(500);
      await expect(badgeLocator).not.toBeVisible();
    }
  });
  });
});
