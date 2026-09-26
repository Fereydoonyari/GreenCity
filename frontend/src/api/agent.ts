/**
 * Agentic neighborhood brief / comparison narratives.
 */

import { apiJson } from "./http";
import type { IndicatorValues } from "./scoring";

export interface NeighborhoodSnapshotPayload {
  id: string;
  name: string;
  score: number;
  priority_band: string;
  rank?: number | null;
  indicators: IndicatorValues;
}

export interface NarrativeSection {
  title: string;
  body: string;
}

export interface AgentNarrative {
  title: string;
  kind: "neighborhood_brief" | "neighborhood_comparison" | string;
  focus_name: string | null;
  sections: NarrativeSection[];
  source: string;
}

export async function requestNeighborhoodBrief(payload: {
  project_id: string;
  focus: NeighborhoodSnapshotPayload;
  peers: NeighborhoodSnapshotPayload[];
}): Promise<AgentNarrative> {
  return apiJson<AgentNarrative>("/api/v1/agent/neighborhood-brief", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function requestNeighborhoodComparison(payload: {
  project_id: string;
  neighborhoods: NeighborhoodSnapshotPayload[];
}): Promise<AgentNarrative> {
  return apiJson<AgentNarrative>("/api/v1/agent/neighborhood-comparison", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface CityLocationPayload {
  name: string;
  latitude: number;
  longitude: number;
}

export async function requestVegetationPlan(payload: {
  project_id: string;
  city: CityLocationPayload;
  focus: NeighborhoodSnapshotPayload;
}): Promise<AgentNarrative> {
  return apiJson<AgentNarrative>("/api/v1/agent/vegetation-plan", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
