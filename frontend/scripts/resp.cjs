const { chromium } = require("playwright-core");
(async () => {
  const b = await chromium.launch();
  for (const [w, h] of [[1280, 960], [768, 1024]]) {
    const p = await b.newPage({ viewport: { width: w, height: h } });
    await p.goto("http://localhost:3000/dashboard", { waitUntil: "networkidle" });
    await p.evaluate(() => localStorage.setItem("theme", "dark"));
    await p.reload({ waitUntil: "networkidle" });
    await p.screenshot({ path: `docs/screenshots/p5/dashboard-${w}-dark.png`, fullPage: true });
    await p.close();
  }
  await b.close();
  console.log("ok");
})();
