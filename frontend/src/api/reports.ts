/**
 * Explainable report API types (payload returned from orchestration / reports).
 */

export interface ReportDriver {
  key: string;
  label: string;
  raw_value: number;
  weighted_points: number;
  direction: string;
  explanation: string;
}

export interface AnalysisReport {
  id: string;
  analysis_job_id: string;
  aoi_id: string;
  scoring_profile_id: string;
  headline: string;
  executive_summary: string;
  priority_band: string;
  score: number;
  drivers: ReportDriver[];
  recommendations: string[];
  methodology_notes: string;
  source: string;
  created_at: string;
  updated_at: string;
}
