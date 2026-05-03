const { test, expect } = require("./fixtures");

test.describe("Agents Management", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="username"]', "testadmin");
    await page.fill('[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
    await page.goto("/settings");
    await page.waitForSelector(".settings-page");
  });

  test("agents tab is visible", async ({ page }) => {
    const agentsTab = page.locator(".tab-btn", { hasText: "Agents" });
    await expect(agentsTab).toBeVisible();
    await agentsTab.click();
    await expect(page.locator("text=Image Analysis Agents")).toBeVisible();
  });

  test("agents tab shows content after loading", async ({ page }) => {
    const agentsTab = page.locator(".tab-btn", { hasText: "Agents" });
    await agentsTab.click();

    await page.waitForTimeout(1000);

    const hasAgents = await page
      .locator(".agent-card")
      .count()
      .then((c) => c > 0);
    const hasEmpty = await page
      .locator(".empty-agents")
      .isVisible()
      .catch(() => false);
    expect(hasAgents || hasEmpty).toBe(true);
  });

  test("agent cards display correctly when agents exist", async ({ page }) => {
    const agentsTab = page.locator(".tab-btn", { hasText: "Agents" });
    await agentsTab.click();
    await page.waitForTimeout(1000);

    const agentCards = page.locator(".agent-card");
    const count = await agentCards.count();

    if (count > 0) {
      const firstCard = agentCards.first();
      await expect(firstCard.locator(".agent-name")).toBeVisible();
      await expect(firstCard.locator(".agent-icon")).toBeVisible();
      await expect(firstCard.locator(".agent-actions")).toBeVisible();
    }
  });

  test("agent status API endpoint is accessible", async ({ request }) => {
    const loginRes = await request.post("/api/auth/login", {
      data: { username: "testadmin", password: "TestPass123!" },
    });
    expect(loginRes.ok()).toBeTruthy();
    const token = (await loginRes.json()).access_token;

    const agentsRes = await request.get("/api/agents/status", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(agentsRes.ok()).toBeTruthy();
  });

  test("non-existent agent returns 404", async ({ request }) => {
    const loginRes = await request.post("/api/auth/login", {
      data: { username: "testadmin", password: "TestPass123!" },
    });
    expect(loginRes.ok()).toBeTruthy();
    const token = (await loginRes.json()).access_token;

    const agentsRes = await request.get("/api/agents/nonexistent/status", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(agentsRes.status()).toBe(404);
  });
});
