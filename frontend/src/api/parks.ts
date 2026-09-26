/**
 * OSM urban-context API (parks layer for map marking).
 */

import { apiJson } from "./http";

export interface ParkFeatureProperties {
  osm_id: number;
  name: string;
  area_m2: number;
  location: "inside" | "nearby" | string;
  mask_kind?: string;
}

export interface ParksLayer {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: {
      type: string;
      coordinates: unknown;
    };
    properties: ParkFeatureProperties;
  }>;
  properties?: {
    mask_kind?: string;
    catchment_m?: number;
    inside_count?: number;
    nearby_count?: number;
    count?: number;
    catchment?: {
      type: "Feature";
      geometry: {
        type: string;
        coordinates: unknown;
      };
      properties?: Record<string, unknown>;
    };
  };
}

export async function fetchParksForAoi(aoiId: string): Promise<ParksLayer> {
  return apiJson<ParksLayer>(`/api/v1/urban-context/aois/${aoiId}/parks`);
}
