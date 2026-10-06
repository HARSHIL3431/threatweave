export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status?: number,
    public details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const DEFAULT_BASE = "/api";

export function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_BASE;
}

export async function apiFetch<T>(path: string, init?: RequestInit, timeoutMs = 30000): Promise<T> {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${apiBase()}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    });
    const text = await res.text();
    let data: unknown = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = text;
    }
    if (!res.ok) {
      const d = data as { error_code?: string; message?: string; detail?: unknown } | null;
      throw new ApiError(d?.error_code ?? `HTTP_${res.status}`, d?.message ?? (typeof d?.detail === "string" ? d.detail : `Request failed with status ${res.status}`), res.status, d?.detail);
    }
    return data as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if ((e as Error).name === "AbortError") throw new ApiError("TIMEOUT", "Request timed out");
    throw new ApiError("NETWORK_ERROR", (e as Error).message);
  } finally {
    clearTimeout(t);
  }
}
