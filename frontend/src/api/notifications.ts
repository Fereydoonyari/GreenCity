/**
 * Notification API (analysis summary emails).
 */

import { apiJson } from "./http";

export async function sendComparisonSummaryEmail(input: {
  project_id: string;
  rankings: Array<{
    rank: number;
    name: string;
    score: number;
    priority_band: string;
  }>;
  notes?: string;
}): Promise<void> {
  await apiJson<void>("/api/v1/notifications/comparison-summary", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
