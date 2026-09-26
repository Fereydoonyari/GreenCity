/**
 * Scoring and ranking API client.
 */

import { apiJson } from "./http";

export interface IndicatorValues {
  vegetation_coverage: number;
  green_area_per_m2: number;
  road_density: number;
  built_up_ratio: number;
}

export interface IndicatorContribution {
  key: string;
  raw_value: number;
  normalised: number;
  deficiency_component: number;
  weight: number;
  weighted_contribution: number;
  direction: string;
}

export interface GreenDeficiencyScore {
  score: number;
  priority_band: string;
  normalisation: string;
  contributions: IndicatorContribution[];
}

export interface RankedNeighborhood {
  id: string;
  label: string;
  rank: number;
  green_deficiency_score: GreenDeficiencyScore;
  indicators: IndicatorValues;
}

export interface RankNeighborhoodsResponse {
  scoring_profile_id: string;
  rankings: RankedNeighborhood[];
}

export async function rankNeighborhoods(payload: {
  scoring_profile_id: string;
  items: Array<{ id: string; label: string; indicators: IndicatorValues }>;
}): Promise<RankNeighborhoodsResponse> {
  return apiJson<RankNeighborhoodsResponse>("/api/v1/scoring/rank", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
