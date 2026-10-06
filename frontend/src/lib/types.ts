export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";

export type DetectionType =
  | "Port Scan"
  | "DDoS"
  | "Web Attack"
  | "Infiltration"
  | "Brute Force"
  | "Other";

export type Technique = {
  id: string;
  name: string;
  confidence: "High" | "Medium" | "Low";
  description: string;
};

export type Detection = {
  id: string;
  timestamp: string;
  type: DetectionType;
  srcIp: string;
  dstIp: string;
  protocol: "TCP" | "UDP" | "ICMP";
  srcPort: number;
  dstPort: number;
  score: number;
  severity: Severity;
  technique: string;
  flow: Record<string, number | string>;
  featureImportance: { name: string; value: number }[];
  mitre: { primary: Technique; related: Technique[] };
  aiAnalysis: string;
  recommendedActions: string[];
};

export type TechniqueChip = { id: string; name: string; confidence: Technique["confidence"] };

export type Kpis = {
  networkFlows: string;
  detectedAnomalies: number;
  criticalThreats: number;
  modelAccuracy: string;
};
