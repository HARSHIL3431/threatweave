const { chromium } = require("playwright-core");
const path = require("path");

const [url, outPrefix, full] = process.argv.slice(2);

(async () => {
  const b = await chromium.launch();
  const page = await b.newPage({ viewport: { width: 1536, height: 960 } });
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(url, { waitUntil: "networkidle" });
  await page.evaluate((t) => localStorage.setItem("theme", t), "dark");
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${outPrefix}-dark.png`, fullPage: full === "full" });
  await page.evaluate((t) => localStorage.setItem("theme", t), "light");
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${outPrefix}-light.png`, fullPage: full === "full" });
  console.log("console errors:", JSON.stringify(errors));
  await b.close();
})();
