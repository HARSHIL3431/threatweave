/**
 * Offline check for src/lib/gauge-scale.ts (P1-12).
 *
 * Compiles the actual source with the repo's own typescript package and
 * asserts below-range / in-range / above-range / invalid behavior. No new
 * dependencies, no browser, no network. Run: `node scripts/check-gauge-scale.cjs`
 */
const fs = require("fs");
const path = require("path");
const ts = require("typescript");

const SRC = path.join(__dirname, "..", "src", "lib", "gauge-scale.ts");

function load() {
  const source = fs.readFileSync(SRC, "utf8");
  const out = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2019 },
  });
  const module_ = { exports: {} };
  new Function("module", "exports", out.outputText)(module_, module_.exports);
  return module_.exports;
}

let failures = 0;
function check(name, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  if (!ok) {
    failures += 1;
    console.error(`FAIL ${name}: got ${JSON.stringify(actual)}, want ${JSON.stringify(expected)}`);
  } else {
    console.log(`ok ${name}`);
  }
}

const g = load();
check("constants", [g.GAUGE_DISPLAY_MIN, g.GAUGE_DISPLAY_MAX], [0, 1]);
check("clamp below", g.clampGaugeDisplay(-0.5), 0);
check("clamp in-range", g.clampGaugeDisplay(0.54), 0.54);
check("clamp above", g.clampGaugeDisplay(1.25), 1);
check("clamp boundaries", [g.clampGaugeDisplay(0), g.clampGaugeDisplay(1)], [0, 1]);
check("range below", g.isGaugeOutOfRange(-0.01), true);
check("range in", g.isGaugeOutOfRange(0.54), false);
check("range above", g.isGaugeOutOfRange(1.01), true);
check("finite number", g.isFiniteGaugeValue(0.54), true);
check("finite NaN", g.isFiniteGaugeValue(NaN), false);
check("finite Infinity", g.isFiniteGaugeValue(Infinity), false);
check("finite null", g.isFiniteGaugeValue(null), false);
check("finite undefined", g.isFiniteGaugeValue(undefined), false);
check("finite string", g.isFiniteGaugeValue("0.5"), false);
check("format", g.formatGaugeValue(0.540229), "0.54");
check("format preserves above-range value", g.formatGaugeValue(1.257), "1.26");

if (failures > 0) {
  console.error(`${failures} gauge-scale check(s) failed`);
  process.exit(1);
}
console.log("gauge-scale checks passed");
