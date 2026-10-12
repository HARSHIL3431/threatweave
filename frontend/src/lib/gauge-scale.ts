/**
 * Pure display-scale helpers for the anomaly-score Gauge (P1-12).
 *
 * The anomaly score is uncalibrated and NOT guaranteed to lie in [0, 1],
 * so the dial is a capped display range, never a normalization. These
 * helpers keep the capping, formatting, and validity rules in one tested
 * place. No imports: safe to compile standalone for the Node check script.
 */
export const GAUGE_DISPLAY_MIN = 0;
export const GAUGE_DISPLAY_MAX = 1;

export function isFiniteGaugeValue(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function clampGaugeDisplay(value: number): number {
  return Math.max(GAUGE_DISPLAY_MIN, Math.min(GAUGE_DISPLAY_MAX, value));
}

export function isGaugeOutOfRange(value: number): boolean {
  return value < GAUGE_DISPLAY_MIN || value > GAUGE_DISPLAY_MAX;
}

export function formatGaugeValue(value: number): string {
  return value.toFixed(2);
}
