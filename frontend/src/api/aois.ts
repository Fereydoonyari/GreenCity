/**
 * Areas of Interest API client.
 */

import { apiJson } from "./http";

export type AoiKind = "city" | "neighborhood";

export interface AreaOfInterest {
  id: string;
  project_id: string;
  name: string;
  description: string;
  kind: AoiKind;
  parent_aoi_id: string | null;
  geometry: GeoJsonGeometry;
  created_at: string;
  updated_at: string;
}

export interface GeoJsonGeometry {
  type: string;
  coordinates: unknown;
}

export interface CreateAreaOfInterestPayload {
  project_id: string;
  name: string;
  description?: string;
  geometry: GeoJsonGeometry | Record<string, unknown>;
  kind?: AoiKind;
  parent_aoi_id?: string | null;
}

export async function createAreaOfInterest(
  payload: CreateAreaOfInterestPayload,
): Promise<AreaOfInterest> {
  return apiJson<AreaOfInterest>("/api/v1/areas-of-interest", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listAreasOfInterest(projectId: string): Promise<AreaOfInterest[]> {
  return apiJson<AreaOfInterest[]>(
    `/api/v1/areas-of-interest?project_id=${encodeURIComponent(projectId)}`,
  );
}

export async function deleteAreaOfInterest(aoiId: string): Promise<void> {
  await apiJson<void>(`/api/v1/areas-of-interest/${aoiId}`, { method: "DELETE" });
}
