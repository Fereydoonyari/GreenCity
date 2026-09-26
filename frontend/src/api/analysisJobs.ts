/**
 * Analysis job + LangGraph orchestration API client.
 */

import { apiJson } from "./http";
import type { AnalysisReport } from "./reports";
import type { GreenDeficiencyScore, IndicatorValues } from "./scoring";

export interface AnalysisJob {
  id: string;
  project_id: string;
  aoi_id: string;
  scoring_profile_id: string;
  status: string;
  current_step: string;
  progress_pct: number;
  error_message: string | null;
}

export interface AnalysisOrchestration {
  aoi_id: string;
  scoring_profile_id: string;
  indicators: IndicatorValues;
  green_deficiency_score: GreenDeficiencyScore;
  steps_completed: string[];
  summary: string;
  vegetation_source: string;
  green_area_source: string;
  report: AnalysisReport | null;
  vegetation_mask?: OverlayMask | null;
  vegetation_hotspot_mask?: OverlayMask | null;
  park_access_mask?: OverlayMask | null;
  heat_exposure_mask?: OverlayMask | null;
  mean_nearest_park_distance_m?: number | null;
  median_nearest_park_distance_m?: number | null;
  mean_nearest_park_walk_min?: number | null;
  median_nearest_park_walk_min?: number | null;
  mean_lst_c?: number | null;
  heat_source?: string;
}

export interface OverlayFeatureProperties {
  density_class?: string;
  density?: number;
  mean_ndvi?: number;
  ndvi_min?: number;
  ndvi_max?: number;
  pixel_count?: number;
  hotspot_class?: string;
  intensity?: number;
  nearest_park_distance_m?: number;
  nearest_park_walk_min?: number;
  mean_lst_c?: number;
  mask_kind?: string;
}

export interface OverlayMask {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: {
      type: string;
      coordinates: unknown;
    };
    properties: OverlayFeatureProperties;
  }>;
  properties?: {
    crs?: string;
    tile_size_px?: number;
    mask_kind?: string;
    legend?: Array<Record<string, unknown>>;
    parks?: OverlayMask;
    walk_distance_m?: number;
  };
}

/** @deprecated Use OverlayMask */
export type VegetationDensityMask = OverlayMask;
export type VegetationDensityFeatureProperties = OverlayFeatureProperties;

export interface RunAnalysisResponse {
  job: AnalysisJob;
  analysis: AnalysisOrchestration;
}

export async function createAnalysisJob(payload: {
  project_id: string;
  aoi_id: string;
  scoring_profile_id: string;
}): Promise<AnalysisJob> {
  return apiJson<AnalysisJob>("/api/v1/analysis-jobs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runAnalysisJob(
  jobId: string,
  payload: {
    vegetation_coverage?: number | null;
    green_area_m2?: number | null;
    park_walk_distance_m?: number;
    auto_start?: boolean;
  } = {},
): Promise<RunAnalysisResponse> {
  return apiJson<RunAnalysisResponse>(`/api/v1/analysis-jobs/${jobId}/run`, {
    method: "POST",
    body: JSON.stringify({
      vegetation_coverage: payload.vegetation_coverage ?? null,
      green_area_m2: payload.green_area_m2 ?? null,
      park_walk_distance_m: payload.park_walk_distance_m ?? 300,
      auto_start: payload.auto_start ?? true,
    }),
  });
}
