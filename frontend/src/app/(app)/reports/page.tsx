import { LiveWorkflow } from "@/components/app/live-workflow";

export default function Reports() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-bold" style={{ color: "var(--text)" }}>Reports</h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Run a flow through the live pipeline (frozen E2 model → severity → MITRE RAG → grounded explanation)
          and download the server-generated incident PDF.
        </p>
      </div>
      <LiveWorkflow />
    </div>
  );
}
