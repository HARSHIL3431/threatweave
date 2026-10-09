"use client";

import { useSyncExternalStore } from "react";
import type { DetectionResponse } from "@/lib/api/backend";

const KEY = "threatweave.session.detections.v1";
const MAX = 100;

type Listener = () => void;
const listeners = new Set<Listener>();
let version = 0;

function subscribe(l: Listener): () => void {
  listeners.add(l);
  return () => {
    listeners.delete(l);
  };
}

function notify() {
  version += 1;
  listeners.forEach((l) => l());
}

function read(): DetectionResponse[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const v = JSON.parse(raw) as unknown;
    if (!Array.isArray(v)) return [];
    return v.filter(
      (r): r is DetectionResponse =>
        !!r && typeof r === "object" && typeof (r as DetectionResponse).request_id === "string"
    );
  } catch {
    return [];
  }
}

function write(records: DetectionResponse[]) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(records.slice(0, MAX)));
  } catch {
    // storage unavailable (private mode, quota) — session simply won't persist
  }
  notify();
}

/** Append a REAL backend DetectionResponse. Never call with fabricated data. */
export function appendSessionDetection(r: DetectionResponse): void {
  if (typeof window === "undefined") return;
  const cur = read().filter((x) => x.request_id !== r.request_id);
  write([r, ...cur]);
}

export function clearSessionDetections(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    // ignore
  }
  notify();
}

export function findSessionDetection(id: string): DetectionResponse | null {
  return read().find((r) => r.request_id === id) ?? null;
}

/** Live session records from this browser only — NOT server-side history. */
export function useSessionDetections(): DetectionResponse[] {
  return useSyncExternalStore(subscribe, snapshot, () => EMPTY);
}

const EMPTY: DetectionResponse[] = [];

let cache: { v: number; records: DetectionResponse[] } = { v: -1, records: EMPTY };

function snapshot(): DetectionResponse[] {
  if (cache.v !== version) cache = { v: version, records: read() };
  return cache.records;
}

export function sessionStats(records: DetectionResponse[]) {
  const anomalies = records.filter((r) => r.detection.is_anomaly);
  const sev = (r: DetectionResponse) => r.severity.level.toLowerCase();
  const highCritical = records.filter((r) => sev(r) === "high" || sev(r) === "critical").length;
  const bySeverity: Record<string, number> = {};
  for (const r of records) {
    const k = sev(r);
    bySeverity[k] = (bySeverity[k] ?? 0) + 1;
  }
  let cum = 0;
  const spark = records
    .slice()
    .reverse()
    .map((r) => {
      if (r.detection.is_anomaly) cum += 1;
      return cum;
    });
  return { total: records.length, anomalies: anomalies.length, highCritical, bySeverity, spark };
}

export const SESSION_SCOPE_NOTE = "This browser session only — stored locally, not server-side history.";
