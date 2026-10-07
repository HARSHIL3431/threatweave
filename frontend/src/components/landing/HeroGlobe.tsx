"use client";

import { Component, ReactNode, useSyncExternalStore } from "react";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import { useTheme } from "next-themes";

const Orbis = dynamic(() => import("./orbis.js"), { ssr: false });

function Globe() {
  const hotspots = [
    { x: 320, y: 120, r: 6 },
    { x: 130, y: 330, r: 5 },
    { x: 330, y: 260, r: 5 },
  ];
  return (
    <svg viewBox="0 0 520 480" className="h-full w-full" aria-hidden>
      <defs>
        <radialGradient id="globeGlow" cx="50%" cy="50%" r="50%">
          <stop offset="60%" stopColor="transparent" />
          <stop offset="100%" stopColor="rgba(59,140,255,0.25)" />
        </radialGradient>
        <pattern id="dots" width="7" height="7" patternUnits="userSpaceOnUse">
          <circle cx="2" cy="2" r="1.4" fill="#3B8CFF" opacity="0.85" />
        </pattern>
      </defs>
      <circle cx="260" cy="240" r="185" fill="url(#dots)" opacity="0.9" />
      <circle cx="260" cy="240" r="185" fill="url(#globeGlow)" />
      <circle cx="260" cy="240" r="185" fill="none" stroke="rgba(59,140,255,0.5)" strokeWidth="1" />
      <ellipse cx="260" cy="240" rx="185" ry="60" fill="none" stroke="rgba(59,140,255,0.3)" />
      <ellipse cx="260" cy="240" rx="60" ry="185" fill="none" stroke="rgba(59,140,255,0.2)" />
      {hotspots.map((h, i) => (
        <g key={i}>
          <motion.circle cx={h.x} cy={h.y} r={h.r} fill="var(--brand)"
            animate={{ opacity: [1, 0.4, 1] }} transition={{ repeat: Infinity, duration: 2, delay: i * 0.5 }} />
          <motion.circle cx={h.x} cy={h.y} r={h.r} fill="none" stroke="var(--brand)" strokeWidth="1.5"
            animate={{ r: [h.r, h.r + 18], opacity: [0.8, 0] }} transition={{ repeat: Infinity, duration: 2, delay: i * 0.5 }} />
        </g>
      ))}
      <path d="M320 120 Q 200 60 130 330" fill="none" stroke="var(--brand)" strokeWidth="1" opacity="0.6" />
      <path d="M320 120 Q 420 180 330 260" fill="none" stroke="var(--brand)" strokeWidth="1" opacity="0.6" />
      <path d="M130 330 Q 240 380 330 260" fill="none" stroke="var(--brand)" strokeWidth="1" opacity="0.4" />
    </svg>
  );
}

class GlobeErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? <Globe /> : this.props.children;
  }
}

const tintDark = {
  backdrop: "transparent",
  ocean: "#0B1730",
  land: "#9AA6BD",
  grid: "rgba(154, 166, 189, 0.12)",
  accent: "#FF1F3D",
  text: "#F4F6FB",
  muted: "#9AA6BD",
};

const tintLight = {
  backdrop: "transparent",
  ocean: "#E9EEF7",
  land: "#5B6478",
  grid: "rgba(91, 100, 120, 0.14)",
  accent: "#E5132B",
  text: "#0B1B3A",
  muted: "#5B6478",
};

export function HeroGlobe() {
  const { resolvedTheme } = useTheme();
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );
  const dark = !mounted || resolvedTheme === "dark";
  return (
    <div className="hero-globe-scope h-full w-full">
      <style>{`.hero-globe-scope [class$="scroll"]{display:none!important}.hero-globe-scope [class$="pin"]{display:none!important}`}</style>
      <GlobeErrorBoundary>
        <div className="absolute left-[-10%] top-[9%] h-[120%] w-[120%]">
          <Orbis
          places={[
            {
              city: "Hub",
              country: "",
              lat: 20,
              lng: 0,
              timezone: "UTC",
            },
          ]}
          words={{ eyebrow: "", heading: "" }}
          deck={{ index: false }}
          tint={dark ? tintDark : tintLight}
          />
        </div>
      </GlobeErrorBoundary>
    </div>
  );
}
