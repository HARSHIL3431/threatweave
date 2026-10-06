import { EyebrowBadge } from "@/components/brand/eyebrow-badge";
import { TwoToneHeading } from "@/components/brand/two-tone-heading";
import { ConfidenceBadge } from "@/components/ui/confidence-badge";
import { TechniqueChip } from "@/components/ui/technique-chip";
import { Button } from "@/components/ui/button";
import { AlertTriangle, Bot, Download } from "lucide-react";

const flowJson = `{
  "src_ip": "192.168.1.124",
  "dst_ip": "10.0.0.12",
  "protocol": "TCP",
  "src_port": 49221,
  "dst_port": 443,
  "duration": 0.802,
  "bytes": 12448,
  "anomaly_score": 0.87,
  "severity": "HIGH"
}`;

export function MitreAI() {
  return (
    <section className="mx-auto max-w-[1360px] px-6 py-16">
      <EyebrowBadge>MITRE ATT&amp;CK + AI INTELLIGENCE</EyebrowBadge>
      <TwoToneHeading lead="From Detection to" accent="Actionable Intelligence" className="mt-4 text-[44px]" />
      <p className="mt-3 max-w-2xl" style={{ color: "var(--text-muted)" }}>
        Automatically map detected anomalies to MITRE ATT&amp;CK techniques and generate AI-powered analyst insights with evidence and recommendations.
      </p>
      <div className="mt-10 grid gap-6 lg:grid-cols-4">
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--brand)", boxShadow: "var(--active-glow)" }}>
          <span className="rounded-md px-1.5 py-0.5 font-mono text-[11px] font-bold text-white" style={{ background: "var(--brand)" }}>01</span>
          <h3 className="mt-3 font-bold" style={{ color: "var(--text)" }}>Detected Anomaly</h3>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>Suspicious network activity identified by Isolation Forest model.</p>
          <pre className="mt-3 overflow-x-auto rounded-lg border p-3 font-mono text-[10.5px]" style={{ background: "#0A1120", borderColor: "var(--border)", color: "#C7D2E4" }}>
            {flowJson.split("\n").map((l, i) => (
              <div key={i} style={l.includes("anomaly_score") || l.includes("severity") ? { color: "var(--brand)" } : undefined}>{l}</div>
            ))}
          </pre>
          <div className="mt-3 flex items-center gap-2 rounded-lg border p-2" style={{ borderColor: "var(--border)", background: "var(--brand-soft)" }}>
            <AlertTriangle size={14} style={{ color: "var(--brand)" }} />
            <span className="text-xs font-semibold" style={{ color: "var(--brand)" }}>Anomaly Score: 0.87 / Severity: HIGH</span>
          </div>
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <span className="rounded-md px-1.5 py-0.5 font-mono text-[11px] font-bold text-white" style={{ background: "var(--blue)" }}>02</span>
          <h3 className="mt-3 font-bold" style={{ color: "var(--text)" }}>MITRE ATT&amp;CK Mapping</h3>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>Detected behavior is automatically mapped to relevant MITRE techniques.</p>
          <div className="mt-3 flex items-center gap-2">
            <TechniqueChip id="T1041" />
            <span className="text-sm font-bold" style={{ color: "var(--text)" }}>Exfiltration Over C2 Channel</span>
          </div>
          <div className="mt-1"><ConfidenceBadge level="High" /></div>
          <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>Adversaries may exfiltrate data over an existing command and control channel.</p>
          <div className="mt-3 text-xs font-semibold" style={{ color: "var(--text-muted)" }}>Related Techniques:</div>
          <div className="mt-1 flex flex-wrap gap-1.5">
            <TechniqueChip id="T1071" /> <TechniqueChip id="T1048" /> <TechniqueChip id="T1030" />
          </div>
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <span className="rounded-md px-1.5 py-0.5 font-mono text-[11px] font-bold text-white" style={{ background: "var(--green)" }}>03</span>
          <h3 className="mt-3 font-bold" style={{ color: "var(--text)" }}>AI-Generated Explanation</h3>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>LLM analyzes the flow, MITRE context, and threat intelligence to generate insights.</p>
          <div className="mt-3 rounded-lg p-3 text-xs leading-relaxed" style={{ background: "color-mix(in srgb, var(--green) 10%, transparent)", color: "var(--text)" }}>
            <Bot size={14} className="mb-1" style={{ color: "var(--green)" }} />
            This network flow shows a potential data exfiltration attempt over an encrypted channel (TCP/443). The short duration and high data transfer rate are consistent with T1041 (Exfiltration Over C2 Channel). The source appears to be an internal host communicating with an external IP, which may indicate a compromised system.
          </div>
          <div className="mt-3 text-xs font-semibold" style={{ color: "var(--text-muted)" }}>Key Indicators</div>
          <ul className="mt-1 list-disc pl-4 text-xs" style={{ color: "var(--brand)" }}>
            <li>Unusual outbound connection pattern</li>
            <li>High data transfer rate</li>
            <li>Communication on TCP/443 (encrypted)</li>
            <li>Matches known exfiltration behavior</li>
          </ul>
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <span className="rounded-md px-1.5 py-0.5 font-mono text-[11px] font-bold text-white" style={{ background: "var(--indigo)" }}>04</span>
          <h3 className="mt-3 font-bold" style={{ color: "var(--text)" }}>Analyst-Ready Report</h3>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>Generate a complete incident report with evidence and recommendations.</p>
          <div className="mt-3 rounded-lg border p-3" style={{ background: "var(--bg)", borderColor: "var(--border)" }}>
            <div className="text-sm font-bold" style={{ color: "var(--text)" }}>Security Incident Report</div>
            <div className="text-[10px]" style={{ color: "var(--text-subtle)" }}>AI-Generated Analysis</div>
            <ul className="mt-2 space-y-1 text-xs" style={{ color: "var(--text-muted)" }}>
              <li>☑ Incident Summary</li>
              <li>☑ MITRE ATT&amp;CK Techniques</li>
              <li>☑ Evidence &amp; Analysis</li>
              <li>☑ Risk Assessment</li>
              <li>☑ Recommendations</li>
            </ul>
          </div>
          <div className="mt-3"><Button><Download size={14} /> Download Report (PDF)</Button></div>
        </div>
      </div>
    </section>
  );
}
