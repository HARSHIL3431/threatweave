// Types matching the backend report contract (app/schemas/report.py).
// Kept minimal — only the fields the frontend consumes today.

export type ReportType = 'analysis' | 'anomaly' | 'benign'

export interface ReportGenerateRequest {
  report_type?: ReportType
  app_name?: string
  request_id?: string
  flow: Record<string, number>
  top_k?: number
}

export interface ReportResponse {
  report_id: string
  request_id: string
  report_type: string
  app_name: string
  status: 'generated' | 'failed'
  file_name: string
  pdf_path: string
  download_url: string
  size_bytes: number
  generated_at: string
}