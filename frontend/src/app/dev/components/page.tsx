import { Logo } from "@/components/brand/logo";
import { EyebrowBadge } from "@/components/brand/eyebrow-badge";
import { TwoToneHeading } from "@/components/brand/two-tone-heading";
import { ThemeToggle } from "@/components/brand/theme-toggle";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { IconTile } from "@/components/ui/icon-tile";
import { SeverityBadge } from "@/components/ui/severity-badge";
import { TechniqueChip } from "@/components/ui/technique-chip";
import { ConfidenceBadge } from "@/components/ui/confidence-badge";
import { StatusPill } from "@/components/ui/status-pill";
import { CodeBlock } from "@/components/ui/code-block";
import { Sparkline, DonutChart, BarList, TrendChart, Gauge } from "@/components/charts/charts";
import { StepCard } from "@/components/ui/step-card";
import { Database } from "lucide-react";
import { SAMPLE_SEVERITY_DONUT, SAMPLE_ATTACK_TYPES, SAMPLE_TREND } from "@/lib/data/detections";

export default function DevComponents() {
  return (
    <main className="mx-auto max-w-5xl space-y-8 p-10" style={{ background: "var(--bg)", minHeight: "100vh" }}>
      <div className="flex items-center justify-between">
        <Logo />
        <ThemeToggle />
      </div>
      <EyebrowBadge>HOW IT WORKS</EyebrowBadge>
      <TwoToneHeading lead="From Network Traffic to" accent="Threat Intelligence" className="text-4xl" />
      <div className="flex gap-3">
        <Button>Open Dashboard →</Button>
        <Button variant="outline">Watch Demo</Button>
      </div>
      <GlassCard>
        <div className="flex items-center gap-4">
          <IconTile><Database /></IconTile>
          <SeverityBadge severity="CRITICAL" />
          <TechniqueChip id="T1041" />
          <ConfidenceBadge level="High" />
          <StatusPill label="Running" />
        </div>
      </GlassCard>
      <GlassCard active>
        <StepCard n="01" title="Raw Network Flow" description="Input network traffic with 60 features" icon={<Database />} accent="var(--brand)" active />
      </GlassCard>
      <CodeBlock code={'{\n  "src_ip": "192.168.1.124",\n  "anomaly_score": 0.87,\n  "severity": "HIGH"\n}'} />
      <div className="grid grid-cols-2 gap-6">
        <Sparkline data={[3, 7, 4, 9, 5, 12, 8]} />
        <Gauge value={0.87} />
      </div>
      <DonutChart data={SAMPLE_SEVERITY_DONUT.map((d) => ({ label: d.label, pct: d.pct, color: d.color }))} centerLabel="Anomalies" centerValue="127" />
      <BarList items={SAMPLE_ATTACK_TYPES} />
      <TrendChart data={SAMPLE_TREND} yMax={80} />
    </main>
  );
}
