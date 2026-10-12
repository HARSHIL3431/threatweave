import { expect, test } from "@playwright/test";

// P1-27 runtime verification of the P1-24 trust-presentation wording.
// Asserts visible user-facing text (roles/text), not CSS internals.
// Static and mock-preview routes run without a backend; routes marked
// LIVE need the documented backend on localhost:8001.

test.describe("landing trust presentation", () => {
  test("model stat uses lab-measured terminology", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Lab-measured F1 (E2)")).toBeVisible();
    await expect(page.getByText("F1-validated")).toHaveCount(0);
  });

  test("dataset counts read as dataset statistics", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Dataset Network Flows")).toBeVisible();
    await expect(page.getByText("Frozen Feature Contract")).toBeVisible();
  });

  test("severity copy is score-based, mock preview is labeled", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/Score-based severity/).first()).toBeVisible();
    await expect(page.getByText("Risk-based severity")).toHaveCount(0);
    await expect(
      page.getByText(/Illustrative mock preview/)
    ).toBeVisible();
  });

  test("confidence badge carries a non-calibrated tooltip", async ({ page }) => {
    await page.goto("/");
    const badge = page.getByText("High Confidence").first();
    await expect(badge).toBeVisible();
    await expect(badge).toHaveAttribute(
      "title",
      "Similarity-based candidate qualifier — not calibrated confidence"
    );
  });
});

test.describe("sample detection views", () => {
  test("mock record shows SAMPLE banner, not model claims", async ({ page }) => {
    await page.goto("/detections/d1");
    await expect(page.getByText("SAMPLE", { exact: true })).toBeVisible();
    await expect(
      page.getByText(/mock data for UI preview, not backend output/)
    ).toBeVisible();
    await expect(
      page.getByText(/not a model assessment/)
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Export Sample Report/ })
    ).toBeVisible();
  });

  test("sample PDF download is a real PDF with approved wording", async ({ page }) => {
    await page.goto("/detections/d1");
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /Export Sample Report/ }).click();
    const download = await downloadPromise;
    const path = await download.path();
    expect(path).toBeTruthy();
    const fs = await import("node:fs");
    const bytes = fs.readFileSync(path!);
    expect(bytes.subarray(0, 5).toString()).toBe("%PDF-");
    const text = bytes.toString("latin1");
    expect(text).toContain("SAMPLE");
    expect(text).toContain("uncalibrated");
    expect(text).toContain("similarity band");
  });
});

test.describe("live views keep honest framing", () => {
  test("mitre page frames results as candidates", async ({ page }) => {
    await page.goto("/mitre");
    await expect(
      page.getByText(/grounded candidates,/)
    ).toBeVisible();
  });

  test("dashboard session captions stay descriptive", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(
      page.getByText(/placeholder severity bands/).first()
    ).toBeVisible();
  });
});
