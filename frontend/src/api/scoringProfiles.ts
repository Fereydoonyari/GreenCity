/**
 * Scoring profile API client.
 */

import { apiJson } from "./http";

export interface ScoringProfile {
  id: string;
  owner_id: string;
  name: string;
  description: string;
  is_default: boolean;
}

export async function createBalancedScoringProfile(
  name = "Balanced default",
): Promise<ScoringProfile> {
  return apiJson<ScoringProfile>("/api/v1/scoring-profiles", {
    method: "POST",
    body: JSON.stringify({
      name,
      description: "Equal weights across four green-deficiency indicators",
      use_balanced_defaults: true,
      is_default: true,
    }),
  });
}

export async function listMyScoringProfiles(): Promise<ScoringProfile[]> {
  return apiJson<ScoringProfile[]>("/api/v1/scoring-profiles");
}
