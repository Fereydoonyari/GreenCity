/**
 * Approximate polygon / multipolygon centroid from GeoJSON coordinates.
 * Good enough for climate banding from a city AOI.
 */

import type { GeoJsonGeometry } from "../api/aois";

function ringCentroid(ring: number[][]): { lat: number; lon: number } | null {
  if (!Array.isArray(ring) || ring.length < 3) {
    return null;
  }
  let sumLon = 0;
  let sumLat = 0;
  let n = 0;
  for (const pt of ring) {
    if (!Array.isArray(pt) || pt.length < 2) {
      continue;
    }
    const lon = Number(pt[0]);
    const lat = Number(pt[1]);
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) {
      continue;
    }
    sumLon += lon;
    sumLat += lat;
    n += 1;
  }
  if (n === 0) {
    return null;
  }
  return { lon: sumLon / n, lat: sumLat / n };
}

export function geometryCentroid(
  geometry: GeoJsonGeometry | Record<string, unknown> | null | undefined,
): { lat: number; lon: number } | null {
  if (!geometry || typeof geometry !== "object") {
    return null;
  }
  const type = String((geometry as { type?: string }).type || "");
  const coordinates = (geometry as { coordinates?: unknown }).coordinates;

  if (type === "Polygon" && Array.isArray(coordinates) && Array.isArray(coordinates[0])) {
    return ringCentroid(coordinates[0] as number[][]);
  }
  if (type === "MultiPolygon" && Array.isArray(coordinates) && Array.isArray(coordinates[0])) {
    const firstPoly = coordinates[0] as unknown[];
    if (Array.isArray(firstPoly) && Array.isArray(firstPoly[0])) {
      return ringCentroid(firstPoly[0] as number[][]);
    }
  }
  return null;
}
