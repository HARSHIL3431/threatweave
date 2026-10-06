const BASE = process.env.API_BASE || "http://localhost:8001";
const fs = require("fs");
const path = require("path");
const flows = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "..", "backend", "tests", "fixtures", "sample_flows.json"), "utf8"));

async function post(path, body) {
  const r = await fetch(`${BASE}/api/v1${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return { status: r.status, json: await r.json() };
}

(async () => {
  let fail = 0;
  const h = await fetch(`${BASE}/api/v1/health`).then((r) => r.json());
  console.log("health:", h.status === "healthy" ? "PASS" : "FAIL", h.status, h.model_status);
  if (h.status !== "healthy") fail = 1;

  for (const key of ["benign_flow", "anomalous_flow", "zero_duration_flow"]) {
    const { status, json } = await post("/detect", flows[key].input);
    const ok = status === 200 && typeof json.detection?.anomaly_score === "number" && typeof json.severity?.level === "string";
    console.log(`detect ${key}:`, ok ? "PASS" : "FAIL", status, json.detection?.anomaly_score, json.severity?.level);
    if (!ok) fail = 1;
  }

  const b = await post("/detect/batch", { flows: [flows.benign_flow.input, flows.anomalous_flow.input] });
  const okB = b.status === 200 && b.json.count === 2 && Array.isArray(b.json.results);
  console.log("detect/batch:", okB ? "PASS" : "FAIL", b.status, b.json.count);
  if (!okB) fail = 1;

  const e = await post("/detect", { "Destination Port": 80 });
  const okE = e.status === 422;
  console.log("invalid input -> 422:", okE ? "PASS" : "FAIL", e.status);
  if (!okE) fail = 1;

  process.exit(fail);
})();
