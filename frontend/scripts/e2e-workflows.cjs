// ThreatWeave workflow E2E (Issue 5): live backend on :8001 (mock LLM), UI on :3000.
// Covers: landing nav, detection (benign+anomalous+invalid), backend PDF download,
// session history, MITRE search + empty states, unknown-id handling.
// The explanation UI is exercised with an intercepted, clearly-labeled TEST DOUBLE
// payload (never presented as a live result); the real mock-provider path is proven
// at API level. No external API calls are made by this script.
const { chromium } = require("playwright-core");
const fs = require("fs");
const path = require("path");
const os = require("os");

const BASE = process.env.UI_BASE || "http://localhost:3000";
const SHOT = process.env.SHOT_DIR || fs.mkdtempSync(path.join(os.tmpdir(), "tw-e2e-"));

const CANNED_EXPLAIN = {
  request_id: "test-double-1",
  detection: { is_anomaly: true, anomaly_score: 0.540229, threshold: 0.521919, experiment_id: "with_port", operating_point: "OP-A" },
  severity: { level: "medium", risk_score: 0.540229, calibration_note: "INITIAL PLACEHOLDER CALIBRATION" },
  attack_context: { mitre_techniques: [], retrieved_context: [] },
  explanation: {
    summary: "TEST DOUBLE summary: anomalous test flow for UI rendering checks only.",
    anomaly_assessment: "TEST DOUBLE assessment.",
    observed_indicators: ["TEST DOUBLE indicator"],
    potential_attack_context: [],
    recommended_actions: ["TEST DOUBLE action"],
    limitations: ["TEST DOUBLE: intercepted fixture, not a backend result."],
  },
  llm: { provider: "mock", model: "mock-test-double", latency_ms: 1.0, validated: true },
};

let fail = 0;
function check(name, ok, extra = "") {
  console.log(`${ok ? "PASS" : "FAIL"} ${name}${extra ? " — " + extra : ""}`);
  if (!ok) fail = 1;
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1536, height: 960 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => {
    // 4xx probes are intentional (invalid input, blank query); only unexpected errors fail.
    if (m.type() === "error" && !/status of 4\d\d/.test(m.text())) errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("response", (r) => { if (r.status() >= 500) errors.push(`${r.status()} ${r.url()}`); });

  // S1: landing renders + nav to dashboard
  let resp = await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
  check("S1 landing 200", resp && resp.status() === 200);
  await page.screenshot({ path: path.join(SHOT, "landing.png") });
  await page.getByRole("link", { name: /dashboard/i }).first().click();
  await page.waitForURL("**/dashboard");
  check("S1 nav landing->dashboard", page.url().endsWith("/dashboard"));

  // S2: dashboard live status + empty session state
  await page.goto(`${BASE}/dashboard`, { waitUntil: "networkidle" });
  check("S2 health Running", (await page.locator("text=Running").count()) > 0);
  check("S2 RAG Ready", (await page.locator("text=Ready").count()) > 0);
  check("S2 no-history empty state", (await page.locator("text=No persisted detection history is available").count()) > 0);

  // S3: reports — benign then anomalous detection shows real backend scores
  await page.goto(`${BASE}/reports`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Run live detection" }).click();
  await page.locator("text=0.451762").first().waitFor({ timeout: 60000 });
  check("S3 benign score 0.451762", true);
  await page.getByRole("button", { name: "Load anomalous sample" }).click();
  await page.getByRole("button", { name: "Run live detection" }).click();
  await page.locator("text=0.540229").first().waitFor({ timeout: 60000 });
  const anom = await page.locator("text=ANOMALOUS").count();
  check("S3 anomalous score + verdict", anom > 0);
  await page.screenshot({ path: path.join(SHOT, "reports-detect.png") });

  // S4: invalid input -> controlled error, no hang
  await page.locator("textarea").fill("{}");
  await page.getByRole("button", { name: "Run live detection" }).click();
  await page.locator("text=INVALID_INPUT").first().waitFor({ timeout: 60000 });
  check("S4 invalid input INVALID_INPUT", true);

  // S5: backend PDF download (no explanation attached -> no LLM involved)
  await page.goto(`${BASE}/reports`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Load anomalous sample" }).click();
  await page.getByRole("button", { name: "Run live detection" }).click();
  await page.locator("text=0.540229").first().waitFor({ timeout: 60000 });
  await page.getByRole("button", { name: "Generate backend PDF report" }).click();
  await page.locator("text=Download report_").first().waitFor({ timeout: 90000 });
  const [download] = await Promise.all([
    page.waitForEvent("download", { timeout: 60000 }),
    page.getByRole("button", { name: /^Download report_/ }).click(),
  ]);
  const pdfPath = await download.path();
  const header = fs.readFileSync(pdfPath).subarray(0, 5).toString();
  const size = fs.statSync(pdfPath).size;
  check("S5 backend PDF download", header === "%PDF-" && size > 0, `header=${header} size=${size}`);

  // S6: session history appears on dashboard
  await page.goto(`${BASE}/dashboard`, { waitUntil: "networkidle" });
  await page.locator("text=0.5402").first().waitFor({ timeout: 30000 });
  const live = await page.locator("text=Flows Scored (session)").count();
  check("S6 session history on dashboard", live > 0);

  // S7: explanation UI via intercepted test double (no backend call at all)
  await page.route("**/api/v1/explain", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(CANNED_EXPLAIN) })
  );
  await page.goto(`${BASE}/reports`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Run live detection" }).click();
  await page.locator("text=0.451762").first().waitFor({ timeout: 60000 });
  await page.getByRole("button", { name: "Get grounded AI explanation" }).click();
  await page.locator("text=TEST DOUBLE summary").first().waitFor({ timeout: 30000 });
  check("S7 explanation UI renders (test double)", true);
  await page.unroute("**/api/v1/explain");
  await page.screenshot({ path: path.join(SHOT, "reports-explain.png") });

  // S8: MITRE search + empty states
  await page.goto(`${BASE}/mitre`, { waitUntil: "networkidle" });
  await page.locator("text=222").first().waitFor({ timeout: 30000 });
  await page.getByRole("button", { name: "Search techniques" }).click();
  await page.locator("text=T1595").first().waitFor({ timeout: 60000 });
  check("S8 MITRE search returns T1595", true);
  await page.getByPlaceholder("e.g. data exfiltration over encrypted channel").fill("   ");
  await page.getByRole("button", { name: "Search techniques" }).click();
  await page.locator("text=INVALID_INPUT").first().waitFor({ timeout: 30000 });
  check("S8 blank query error state", true);

  // S9: unknown detection id -> not found; fixture -> SAMPLE
  await page.goto(`${BASE}/detections/does-not-exist-123`, { waitUntil: "networkidle" });
  check("S9 unknown id not-found", (await page.locator("text=Record not found").count()) > 0);
  await page.goto(`${BASE}/detections/d1`, { waitUntil: "networkidle" });
  check("S9 fixture SAMPLE label", (await page.locator("text=SAMPLE").count()) > 0);

  check("S10 zero console/page/5xx errors", errors.length === 0, errors.slice(0, 3).join(" | "));
  console.log(`screenshots: ${SHOT}`);
  await browser.close();
  process.exit(fail);
})().catch((e) => { console.error("E2E FATAL", e); process.exit(2); });
