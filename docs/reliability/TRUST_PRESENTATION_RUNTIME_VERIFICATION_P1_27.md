# Trust Presentation Runtime Verification (P1-27, DI-008 + DI-007 presentation)

Browser verification of the P1-24 wording changes. No product, detector,
retrieval, guard, threshold, contract, or calibration change in this
phase. No browser E2E run existed before; the Playwright setup below is
the repo's first (dependency `@playwright/test` pre-existed, browsers
pre-installed — nothing installed).

## 1. Environment and commands

- Browser: Playwright 1.62.1, Chromium 1234 headless (pre-installed at
  `%LOCALAPPDATA%\ms-playwright`), two projects: `chromium-light`
  (Desktop Chrome) and `chromium-dark-narrow` (dark scheme, 390×844).
- Frontend: `npm run build` (Next.js 16.3.8 Turbopack, clean) then
  `npm run start -- -p 3000` (documented production serve).
- Backend: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8001`
  (documented command; model + FAISS artifacts present).
- Tests: `npx playwright test` (`frontend/playwright.config.ts`,
  `frontend/tests/e2e/trust-presentation.spec.ts`, 8 tests × 2 projects).
  Both servers stopped after verification (PIDs verified down).

## 2. Routes and states exercised

- `/` landing (hero stats, how-it-works severity copy, mitre-ai mock
  section, ConfidenceBadge tooltip) — static, no backend needed.
- `/detections/d1` mock record (SAMPLE banner, severity caption, Export
  Sample Report button, real PDF download parsed from bytes).
- `/mitre` (candidate framing; backend live for status), `/dashboard`
  (session KPI captions) — loaded against the running backend.
- Dark scheme + 390 px viewport: same 8 assertions (readability/visibility
  of labels, banners, and copy confirmed in that configuration).
- Live backend spot checks (outside browser): `/api/v1/detect` on fixture
  anomalous flow → `is_anomaly true, 0.5402, medium`; benign →
  `false, 0.4518, info` (matches documented live-sample expectations);
  `/api/v1/rag/query` "port scan reconnaissance" → T1595 top 0.5498.
  Detection + dashboard functionality available; nothing changed to make
  tests pass.

## 3. Results: 16/16 pass, zero fixes required

All P1-24 wording verified rendered: "Lab-measured F1 (E2)" (and no
"F1-validated" anywhere), "Dataset Network Flows", "Frozen Feature
Contract", "Score-based severity" (no "Risk-based severity"), the
mitre-ai illustrative-mock caption, the badge tooltip text, SAMPLE
banner + "not backend output" + "not a model assessment" on the mock
record, downloaded bytes starting `%PDF-` containing "SAMPLE",
"uncalibrated", and "similarity band", mitre "grounded candidates"
framing, and "placeholder severity bands" dashboard captions. No
misleading wording introduced via tooltip, responsive, or conditional
rendering in the exercised states.

## 4. Not run / limitations

No test framework pre-existed (this adds the first spec — no competing
framework created). Live `/explain` and backend-PDF flows were not
driven in the browser (backend PDF wording is covered by
`test_report_service.py` string assertions instead). No screenshots
taken (text assertions deemed sufficient and less brittle). Operator
reception (DI-008's actual question) is still unmeasured — passing UI
tests do not validate interpretation. Calibration (DI-007) untouched.
