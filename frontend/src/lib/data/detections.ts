import type { Detection, Kpis } from "../types";

// SAMPLE: no backend source. Typed mock dataset behind USE_MOCK.
export const MOCK_DETECTIONS: Detection[] = [
  {
    id: "d1",
    timestamp: "2026-09-20T14:23:06Z",
    type: "Port Scan",
    srcIp: "192.168.1.124",
    dstIp: "10.0.0.12",
    protocol: "TCP",
    srcPort: 49221,
    dstPort: 443,
    score: 0.87,
    severity: "HIGH",
    technique: "T1046",
    flow: {
      src_ip: "192.168.1.124", dst_ip: "10.0.0.12", protocol: "TCP", src_port: 49221, dst_port: 443,
      duration: 0.802, bytes: 12448, packets: 24, flow_rate: 15527.8, fwd_packets: 12, bwd_packets: 12,
    },
    featureImportance: [
      { name: "Flow Duration", value: 0.22 },
      { name: "Total Forward Packets", value: 0.18 },
      { name: "Total Backward Packets", value: 0.15 },
      { name: "Flow Bytes/s", value: 0.12 },
      { name: "Packet Length Std", value: 0.09 },
      { name: "Bwd IAT Mean", value: 0.08 },
      { name: "Fwd Header Length", value: 0.06 },
      { name: "Others", value: 0.10 },
    ],
    mitre: {
      primary: { id: "T1041", name: "Exfiltration Over C2 Channel", confidence: "High", description: "Adversaries may exfiltrate data over an existing command and control channel. This technique is often used to avoid detection by blending with normal network communications." },
      related: [
        { id: "T1071", name: "Application Layer Protocol", confidence: "Medium", description: "" },
        { id: "T1048", name: "Exfiltration Over Alternative Protocol", confidence: "Medium", description: "" },
        { id: "T1030", name: "Data Transfer Size Limits", confidence: "Low", description: "" },
      ],
    },
    aiAnalysis: "This network flow shows characteristics of a potential data exfiltration attempt. The short duration and high data transfer rate, combined with the destination port (443) and flow patterns, suggest the use of an encrypted channel for C2 communication.",
    recommendedActions: [
      "Investigate the source host for unauthorized activity",
      "Check for data exfiltration indicators",
      "Monitor similar traffic patterns",
      "Review endpoint logs for related activity",
    ],
  },
  {
    id: "d2",
    timestamp: "2026-09-20T14:20:11Z",
    type: "DDoS", srcIp: "172.16.0.45", dstIp: "192.168.1.10", protocol: "UDP", srcPort: 53, dstPort: 80,
    score: 0.72, severity: "MEDIUM", technique: "T1498",
    flow: { src_ip: "172.16.0.45", dst_ip: "192.168.1.10", protocol: "UDP", src_port: 53, dst_port: 80, duration: 12.4, bytes: 2048000, packets: 18400, flow_rate: 165161.3, fwd_packets: 9200, bwd_packets: 0 },
    featureImportance: [], mitre: { primary: { id: "T1498", name: "Network Denial of Service", confidence: "High", description: "" }, related: [] },
    aiAnalysis: "", recommendedActions: [],
  },
  {
    id: "d3",
    timestamp: "2026-09-20T14:18:32Z",
    type: "Web Attack", srcIp: "10.0.0.23", dstIp: "192.168.1.5", protocol: "TCP", srcPort: 51514, dstPort: 8080,
    score: 0.68, severity: "MEDIUM", technique: "T1190",
    flow: { src_ip: "10.0.0.23", dst_ip: "192.168.1.5", protocol: "TCP", src_port: 51514, dst_port: 8080, duration: 0.44, bytes: 5120, packets: 12, flow_rate: 11636.4, fwd_packets: 6, bwd_packets: 6 },
    featureImportance: [], mitre: { primary: { id: "T1190", name: "Exploit Public-Facing Application", confidence: "Medium", description: "" }, related: [] },
    aiAnalysis: "", recommendedActions: [],
  },
  {
    id: "d4",
    timestamp: "2026-09-20T14:15:47Z",
    type: "Infiltration", srcIp: "192.168.1.77", dstIp: "10.0.0.8", protocol: "TCP", srcPort: 60808, dstPort: 22,
    score: 0.91, severity: "CRITICAL", technique: "T1041",
    flow: { src_ip: "192.168.1.77", dst_ip: "10.0.0.8", protocol: "TCP", src_port: 60808, dst_port: 22, duration: 3.2, bytes: 86016, packets: 96, flow_rate: 26880.0, fwd_packets: 48, bwd_packets: 48 },
    featureImportance: [], mitre: { primary: { id: "T1041", name: "Exfiltration Over C2 Channel", confidence: "High", description: "" }, related: [] },
    aiAnalysis: "", recommendedActions: [],
  },
  {
    id: "d5",
    timestamp: "2026-09-20T14:12:03Z",
    type: "Brute Force", srcIp: "10.0.0.12", dstIp: "192.168.1.20", protocol: "TCP", srcPort: 47123, dstPort: 3389,
    score: 0.61, severity: "LOW", technique: "T1110",
    flow: { src_ip: "10.0.0.12", dst_ip: "192.168.1.20", protocol: "TCP", src_port: 47123, dst_port: 3389, duration: 8.1, bytes: 30208, packets: 42, flow_rate: 3730.1, fwd_packets: 21, bwd_packets: 21 },
    featureImportance: [], mitre: { primary: { id: "T1110", name: "Brute Force", confidence: "Medium", description: "" }, related: [] },
    aiAnalysis: "", recommendedActions: [],
  },
];

export const MOCK_KPIS: Kpis = {
  networkFlows: "2.84M",
  detectedAnomalies: 127,
  criticalThreats: 14,
  modelAccuracy: "94.7%",
};

// SAMPLE aggregates matching reference image 08/10 (values intentionally not normalized)
export const SAMPLE_ACTIVITY = [
  { t: "00:00", v: 8 }, { t: "04:00", v: 14 }, { t: "08:00", v: 28 }, { t: "12:00", v: 22 },
  { t: "16:00", v: 34 }, { t: "20:00", v: 18 }, { t: "24:00", v: 12 },
];

export const SAMPLE_SEVERITY_DONUT = [
  { label: "Critical", count: 14, pct: 11, color: "var(--brand)" },
  { label: "High", count: 32, pct: 25, color: "var(--orange)" },
  { label: "Medium", count: 46, pct: 36, color: "var(--amber)" },
  { label: "Low", count: 25, pct: 20, color: "#D9C46A" },
  { label: "Informational", count: 10, pct: 8, color: "var(--text-subtle)" },
];

export const SAMPLE_ATTACK_TYPES = [
  { label: "Port Scan", pct: 32, color: "var(--brand)" },
  { label: "DDoS", pct: 24, color: "var(--orange)" },
  { label: "Web Attack", pct: 16, color: "var(--amber)" },
  { label: "Infiltration", pct: 11, color: "#F2A65A" },
  { label: "Brute Force", pct: 8, color: "var(--text-subtle)" },
  { label: "Others", pct: 7, color: "var(--text-subtle)" },
];

export const SAMPLE_TREND = [
  { day: "Sep 14", v: 28 }, { day: "Sep 15", v: 12 }, { day: "Sep 16", v: 35 }, { day: "Sep 17", v: 42 },
  { day: "Sep 18", v: 65 }, { day: "Sep 19", v: 38 }, { day: "Sep 20", v: 24 },
];

export const SAMPLE_TOP_IPS = [
  { ip: "192.168.1.124", count: 32 }, { ip: "10.0.0.23", count: 24 }, { ip: "172.16.0.45", count: 18 },
  { ip: "192.168.1.77", count: 14 }, { ip: "10.0.0.12", count: 11 },
];
