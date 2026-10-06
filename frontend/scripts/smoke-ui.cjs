const { chromium } = require("playwright-core");

const BASE = process.env.UI_BASE || "http://localhost:3000";
const routes = ["/", "/dashboard", "/detections/d1", "/analytics", "/mitre", "/reports", "/explorer", "/settings", "/dev/components"];
const expectText = { "/": "Detection Engine Operational", "/dashboard": "Anomaly Activity", "/detections/d1": "Detection Details", "/analytics": "Incident Report" };

(async () => {
  const b = await chromium.launch();
  let fail = 0;
  for (const theme of ["dark", "light"]) {
    for (const route of routes) {
      const page = await b.newPage({ viewport: { width: 1536, height: 960 } });
      const errors = [];
      page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
      page.on("pageerror", (e) => errors.push(String(e)));
      const resp = await page.goto(`${BASE}${route}`, { waitUntil: "networkidle" });
      await page.evaluate((t) => localStorage.setItem("theme", t), theme);
      await page.reload({ waitUntil: "networkidle" });
      await page.waitForTimeout(500);
      const status = resp && resp.status();
      const text = expectText[route];
      const hasText = text ? (await page.locator(`text=${text}`).count()) > 0 : true;
      const ok = status === 200 && errors.length === 0 && hasText;
      console.log(`${theme} ${route}:`, ok ? "PASS" : "FAIL", `status=${status}`, `errors=${errors.length}`, text ? `hasText=${hasText}` : "");
      if (errors.length) console.log("  ", errors.join(" | "));
      if (!ok) fail = 1;
      await page.screenshot({ path: `docs/screenshots/smoke/${theme}${route.replace(/\//g, "_") || "_home"}.png`, fullPage: false });
      await page.close();
    }
  }
  await b.close();
  process.exit(fail);
})();
