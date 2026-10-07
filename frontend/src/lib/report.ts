import type { Detection } from "./types";

const RED = "#FF1F3D";
const NAVY = "#071020";
const SLATE = "#5B6478";
const SLATE_LIGHT = "#8A93A6";

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "#C8102E",
  HIGH: RED,
  MEDIUM: "#F59E0B",
  LOW: "#2F7BFF",
  INFO: "#8A93A6",
};

const FEATURE_DESCRIPTIONS: Record<string, string> = {
  duration: "Length of the flow in seconds",
  bytes: "Total bytes transferred in the flow",
  packets: "Total packets exchanged",
  flow_rate: "Rate of packets per second across the flow",
  fwd_packets: "Packets sent from source to destination",
  bwd_packets: "Packets sent from destination to source",
  src_ip: "Originating source IP address",
  dst_ip: "Destination IP address",
  src_port: "Source port number",
  dst_port: "Destination port number",
  protocol: "Transport protocol",
};

const fmt = (v: unknown) => (v === undefined || v === null || v === "" ? "Not available" : String(v));

export async function downloadIncidentReport(d: Detection) {
  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const PAGE_W = 210;
  const M = 15;
  const W = PAGE_W - M * 2;
  let y = 0;

  const pageHeaderFooter = (pageNum: number) => {
    if (pageNum === 1) return;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.setTextColor(NAVY);
    doc.text("THREATWEAVE", M, 10);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(SLATE_LIGHT);
    doc.text("Security Incident Report", M + 26, 10);
    doc.setDrawColor(229, 231, 235);
    doc.setLineWidth(0.2);
    doc.line(M, 12, PAGE_W - M, 12);
  };

  const ensure = (need: number) => {
    if (y + need > 282) {
      doc.addPage();
      y = 20;
    }
  };

  const section = (title: string) => {
    ensure(14);
    y += 4;
    doc.setFillColor(RED);
    doc.rect(M, y - 3.2, 3, 4.2, "F");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.setTextColor(NAVY);
    doc.text(title, M + 6, y);
    y += 3;
    doc.setDrawColor(229, 231, 235);
    doc.setLineWidth(0.2);
    doc.line(M, y, PAGE_W - M, y);
    y += 6;
  };

  const kv = (k: string, v: string) => {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9.5);
    const lines = doc.splitTextToSize(v, W - 62);
    ensure(lines.length * 5 + 2);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9.5);
    doc.setTextColor(SLATE);
    doc.text(k, M, y);
    doc.setFont("helvetica", "normal");
    doc.setTextColor("#111827");
    doc.text(lines, M + 62, y);
    y += lines.length * 5 + 2;
  };

  const paragraph = (text: string, indent = 0) => {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    const lines = doc.splitTextToSize(text, W - indent);
    ensure(lines.length * 5 + 2);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor("#374151");
    doc.text(lines, M + indent, y);
    y += lines.length * 5 + 2;
  };

  const bullet = (text: string) => {
    const lines = doc.splitTextToSize(text, W - 8);
    ensure(lines.length * 5 + 2);
    doc.setFillColor(RED);
    doc.circle(M + 1.5, y - 1.2, 0.8, "F");
    paragraph(text, 6);
  };

  const badge = (label: string, x: number, yPos: number, bg: string, fg = "#FFFFFF") => {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    const w = doc.getTextWidth(label) + 8;
    doc.setFillColor(bg);
    doc.roundedRect(x, yPos - 4.5, w, 7, 2, 2, "F");
    doc.setTextColor(fg);
    doc.text(label, x + 4, yPos);
    return w;
  };

  // ---------- Page 1 header band ----------
  doc.setFillColor(NAVY);
  doc.rect(0, 0, PAGE_W, 28, "F");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(15);
  doc.setTextColor("#FFFFFF");
  doc.text("THREAT", M, 12);
  const tw = doc.getTextWidth("THREAT");
  doc.setTextColor(RED);
  doc.text("WEAVE", M + tw, 12);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8.5);
  doc.setTextColor("#9AA6BD");
  doc.text("Security Incident Report", M, 19);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.setTextColor("#FFFFFF");
  doc.text(`ID: ${d.id}`, PAGE_W - M, 12, { align: "right" });
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8.5);
  doc.setTextColor("#9AA6BD");
  doc.text(`Generated ${new Date().toISOString().replace("T", " ").slice(0, 19)} UTC`, PAGE_W - M, 19, { align: "right" });
  doc.setFillColor(RED);
  doc.rect(0, 28, PAGE_W, 1.2, "F");

  y = 42;
  badge(d.severity, M, y, SEVERITY_COLORS[d.severity] ?? RED);
  y += 8;

  kv("Incident ID", d.id);
  kv("Classification", d.type);
  kv("Detection status", "Model inference — no confirmed compromise");
  kv("Detection timestamp", d.timestamp);
  kv("Anomaly score", `${d.score.toFixed(2)} (0.00–1.00)`);
  kv("Severity", d.severity);
  kv("MITRE reference", `${d.mitre.primary.id} — ${d.mitre.primary.name}`);

  section("Executive Summary");
  paragraph(
    d.aiAnalysis && d.aiAnalysis.trim().length > 0
      ? d.aiAnalysis.split(/\n+/)[0]
      : `ThreatWeave flagged a ${d.protocol} flow (${fmt(d.srcIp)} to ${fmt(d.dstIp)}) as ${d.type} with anomaly score ${d.score.toFixed(2)} and severity ${d.severity}. No AI analysis was supplied for this incident.`
  );

  section("Key Findings");
  bullet(`${d.type} detected on ${d.protocol} traffic from ${fmt(d.srcIp)}:${fmt(d.srcPort)} to ${fmt(d.dstIp)}:${fmt(d.dstPort)}`);
  bullet(`The anomaly detector flagged this flow with a score of ${d.score.toFixed(2)}, above its active alert threshold`);
  bullet(`Classification severity: ${d.severity}`);
  bullet(`Model-generated MITRE ATT&CK mapping: ${d.mitre.primary.id} ${d.mitre.primary.name} (${d.mitre.primary.confidence} confidence)`);

  section("Endpoints and Transport");
  kv("Source", `${fmt(d.srcIp)}:${fmt(d.srcPort)}`);
  kv("Destination", `${fmt(d.dstIp)}:${fmt(d.dstPort)}`);
  kv("Protocol", fmt(d.protocol));

  section("Detection Evidence");
  kv("Anomaly score", `${d.score.toFixed(2)}`);
  kv("Active threshold", "Not available in detection record");
  kv("Model", "Not available in detection record");
  kv("Classification", `${d.type} / ${d.severity} severity`);

  section("Network Flow Features");
  for (const [k, v] of Object.entries(d.flow)) {
    const desc = FEATURE_DESCRIPTIONS[k] ? ` — ${FEATURE_DESCRIPTIONS[k]}` : "";
    kv(k, `${fmt(v)}${desc}`);
  }

  section("Feature Importance");
  if (d.featureImportance.length === 0) {
    paragraph("No feature attribution values were supplied for this detection.");
  } else {
    ensure(8);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9.5);
    doc.setTextColor(SLATE);
    doc.text("Feature", M, y);
    doc.text("Weight", M + 120, y);
    y += 4;
    doc.setDrawColor(229, 231, 235);
    doc.line(M, y, PAGE_W - M, y);
    y += 5;
    d.featureImportance.forEach((f, i) => {
      ensure(6);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(9.5);
      doc.setTextColor("#111827");
      doc.text(f.name, M, y);
      doc.setFont("helvetica", "bold");
      doc.text(f.value.toFixed(2), M + 120, y);
      y += 5;
      // Contribution note
      ensure(5);
      doc.setFont("helvetica", "italic");
      doc.setFontSize(8.5);
      doc.setTextColor(SLATE_LIGHT);
      const featureNotes: Record<string, string> = {
        "Flow Duration": "Length of the flow in seconds",
        "Total Forward Packets": "Packets sent from source to destination",
        "Total Backward Packets": "Packets sent from destination to source",
        "Flow Bytes/s": "Byte transfer rate across the flow",
        "Packet Length Std": "Variability of packet sizes",
        "Bwd IAT Mean": "Mean time between backward packets",
        "Fwd Header Length": "Size of forward-direction headers",
        "Others": "Remaining feature contributions",
      };
      const metricNote = featureNotes[f.name] ?? (i === 0 ? "Strongest contributor to this anomaly decision" : "");
      if (metricNote) doc.text(metricNote, M, y);
      y += 5;
    });
  }

  section("MITRE ATT&CK Context");
  kv("Primary technique", `${d.mitre.primary.id} — ${d.mitre.primary.name}`);
  kv("Confidence", d.mitre.primary.confidence);
  kv("Description", d.mitre.primary.description || "No description supplied.");
  paragraph("The technique mapping above is model-generated inference from the anomaly detector. An anomaly score alone does not prove a confirmed attack or compromise.");
  if (d.mitre.related.length > 0) {
    kv("Related techniques", d.mitre.related.map((t) => `${t.id} ${t.name} (${t.confidence})`).join("; "));
  }

  section("AI-Generated Analysis");
  if (d.aiAnalysis && d.aiAnalysis.trim().length > 0) {
    paragraph(d.aiAnalysis);
  } else {
    paragraph("No AI-generated analysis was supplied for this detection.");
  }

  section("Recommended Actions");
  if (d.recommendedActions.length === 0) {
    paragraph("No recommendations were supplied for this detection.");
  } else {
    d.recommendedActions.forEach((a, i) => {
      ensure(6);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(10);
      doc.setTextColor(RED);
      doc.text(`${i + 1}.`, M, y);
      paragraph(a, 8);
    });
  }

  section("Technical Appendix");
  paragraph("Full flow record as supplied by the data source:");
  const jsonLines = JSON.stringify({ score: d.score, severity: d.severity, technique: d.mitre.primary.id, flow: d.flow }, null, 2).split("\n");
  doc.setFont("courier", "normal");
  doc.setFontSize(8);
  doc.setTextColor("#111827");
  for (const line of jsonLines) {
    ensure(4.5);
    doc.text(line.replace(/\t/g, "  "), M, y);
    y += 4.5;
  }
  doc.setFont("helvetica", "normal");

  // ---------- Footer on every page ----------
  const total = doc.getNumberOfPages();
  for (let i = 1; i <= total; i++) {
    doc.setPage(i);
    pageHeaderFooter(i);
    doc.setDrawColor(229, 231, 235);
    doc.setLineWidth(0.2);
    doc.line(M, 285, PAGE_W - M, 285);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(SLATE_LIGHT);
    doc.text("ThreatWeave — Confidential", M, 290);
    doc.text(`Generated ${new Date().toISOString().replace("T", " ").slice(0, 19)} UTC`, PAGE_W / 2, 290, { align: "center" });
    doc.text(`Page ${i} of ${total}`, PAGE_W - M, 290, { align: "right" });
  }

  doc.save(`ThreatWeave-Incident-${d.id}.pdf`);
}
