"use client";

import { useEffect, useState } from "react";
import { getHealth, type HealthResponse } from "@/lib/api/backend";

export function useHealth() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let alive = true;
    getHealth()
      .then((h) => alive && setHealth(h))
      .catch(() => alive && setError(true));
    return () => { alive = false; };
  }, []);
  return { health, error };
}
