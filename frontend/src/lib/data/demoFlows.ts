// SAMPLE pipeline demo data (landing demo only, not app data).
export type DemoStage = { name: string; body: string };
export type DemoFlow = { label: string; stages: DemoStage[] };

const rawBenign = `{
  "src_ip": "192.168.1.124",
  "dst_ip": "10.0.0.12",
  "protocol": "TCP",
  "src_port": 49221,
  "dst_port": 443,
  "duration": 0.802,
  "packets": 184,
  "bytes": 12448,
  "flow_type": "Benign"
}`;

export const DEMO_FLOWS: DemoFlow[] = [
  {
    label: "Benign Network Flow",
    stages: [
      { name: "Raw Flow", body: rawBenign },
      { name: "Preprocessing", body: `{
  "zero_duration_handling": "not_required",
  "log1p_transforms": "applied",
  "feature_engineering": "complete",
  "feature_count": 60,
  "status": "ready_for_scoring"
}` },
      { name: "ML Analysis", body: `{
  "model": "Isolation Forest (E2)",
  "features": 60,
  "operating_point": "OP-A",
  "threshold": 0.521919
}` },
      { name: "Anomaly Score", body: `{
  "anomaly_score": 0.21,
  "threshold": 0.5219,
  "is_anomaly": false
}` },
      { name: "Severity", body: `{
  "severity": "INFO",
  "risk_score": 0.21,
  "calibration": "placeholder"
}` },
      { name: "Attack Context", body: `{
  "mitre_techniques": [],
  "retrieved_context": []
}` },
      { name: "AI Report", body: `{
  "summary": "Traffic matches a benign HTTPS flow profile.",
  "recommendations": []
}` },
    ],
  },
  {
    label: "Anomalous Network Flow",
    stages: [
      { name: "Raw Flow", body: `{
  "src_ip": "192.168.1.77",
  "dst_ip": "10.0.0.8",
  "protocol": "TCP",
  "src_port": 60808,
  "dst_port": 443,
  "duration": 0.31,
  "packets": 96,
  "bytes": 86016,
  "flow_type": "Anomalous"
}` },
      { name: "Preprocessing", body: `{
  "zero_duration_handling": "not_required",
  "log1p_transforms": "applied",
  "feature_engineering": "complete",
  "feature_count": 60,
  "status": "ready_for_scoring"
}` },
      { name: "ML Analysis", body: `{
  "model": "Isolation Forest (E2)",
  "features": 60,
  "operating_point": "OP-A",
  "threshold": 0.521919
}` },
      { name: "Anomaly Score", body: `{
  "anomaly_score": 0.87,
  "threshold": 0.5219,
  "is_anomaly": true
}` },
      { name: "Severity", body: `{
  "severity": "HIGH",
  "risk_score": 0.87,
  "calibration": "placeholder"
}` },
      { name: "Attack Context", body: `{
  "mitre_techniques": ["T1041"],
  "retrieved_context": ["Exfiltration Over C2 Channel"]
}` },
      { name: "AI Report", body: `{
  "summary": "Potential data exfiltration over an encrypted channel.",
  "recommendations": ["Investigate the source host", "Monitor similar traffic"]
}` },
    ],
  },
  {
    label: "Zero Duration Flow",
    stages: [
      { name: "Raw Flow", body: `{
  "src_ip": "172.16.0.45",
  "dst_ip": "192.168.1.10",
  "protocol": "UDP",
  "src_port": 53,
  "dst_port": 80,
  "duration": 0,
  "packets": 2,
  "bytes": 64,
  "flow_type": "ZeroDuration"
}` },
      { name: "Preprocessing", body: `{
  "zero_duration_handling": "duration_clipped_to_1us",
  "Is_Zero_Duration": 1,
  "flow_rates_recomputed": true,
  "feature_count": 60,
  "status": "ready_for_scoring"
}` },
      { name: "ML Analysis", body: `{
  "model": "Isolation Forest (E2)",
  "features": 60,
  "operating_point": "OP-A",
  "threshold": 0.521919
}` },
      { name: "Anomaly Score", body: `{
  "anomaly_score": 0.46,
  "threshold": 0.5219,
  "is_anomaly": false
}` },
      { name: "Severity", body: `{
  "severity": "INFO",
  "risk_score": 0.46,
  "calibration": "placeholder"
}` },
      { name: "Attack Context", body: `{
  "mitre_techniques": [],
  "retrieved_context": []
}` },
      { name: "AI Report", body: `{
  "summary": "Zero-duration UDP probe flagged as low risk after clipping.",
  "recommendations": []
}` },
    ],
  },
];

export const STAGE_DEFS = [
  { n: "01", title: "Raw Network Flow", desc: "Input network traffic with 60 features", accent: "var(--brand)" },
  { n: "02", title: "Preprocessing", desc: "Clean, transform and engineer features", accent: "var(--blue)" },
  { n: "03", title: "Anomaly Detection", desc: "E2 Isolation Forest model scoring", accent: "var(--green)" },
  { n: "04", title: "Anomaly Score", desc: "Numeric score with threshold comparison", accent: "var(--amber)" },
  { n: "05", title: "Severity Classification", desc: "Risk-based severity (Info → Critical)", accent: "var(--orange)" },
  { n: "06", title: "Attack Context", desc: "MITRE ATT&CK mapping and knowledge retrieval", accent: "var(--brand)" },
  { n: "07", title: "Intelligence Report", desc: "LLM-generated analysis and recommendations", accent: "var(--indigo)" },
];

export const DEMO_STEP_DEFS = [
  { n: "01", title: "Raw Network Flow", desc: "Input network traffic with 60 features", accent: "var(--brand)" },
  { n: "02", title: "Preprocessing", desc: "Zero-duration handling, log transformations, feature engineering", accent: "var(--blue)" },
  { n: "03", title: "Anomaly Detection", desc: "E2 Isolation Forest model scoring (60 features)", accent: "var(--green)" },
  { n: "04", title: "Anomaly Score", desc: "Numeric score with threshold comparison", accent: "var(--amber)" },
  { n: "05", title: "Severity Classification", desc: "Risk-based severity level (Info → Critical)", accent: "var(--orange)" },
  { n: "06", title: "Attack Context", desc: "MITRE ATT&CK mapping and knowledge retrieval", accent: "var(--brand)" },
  { n: "07", title: "Intelligence Report", desc: "LLM-generated analysis and recommendations", accent: "var(--indigo)" },
];
