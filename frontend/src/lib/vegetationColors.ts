/**
 * Colors for map overlay masks (vegetation density + hotspots).
 */

export type OverlayMode = "off" | "vegetation" | "veg_hotspots" | "heat";

export function vegetationDensityFill(densityClass: string): string {
  switch (densityClass) {
    case "dense":
      return "#0d5c2e";
    case "moderate":
      return "#2f9e57";
    case "sparse":
      return "#8fd4a4";
    default:
      return "#4a8f63";
  }
}

export function vegetationDensityOpacity(density: number): number {
  return Math.min(0.9, Math.max(0.55, 0.45 + density * 0.4));
}

/** Low-vegetation hotspot fills (warm / alert). */
export function vegetationHotspotFill(hotspotClass: string): string {
  switch (hotspotClass) {
    case "critical":
      return "#b42318";
    case "high":
      return "#e05a2b";
    case "elevated":
      return "#f0a202";
    default:
      return "#d97706";
  }
}

/** Park access distance classes (green → soft amber when farther). */
export function parkAccessFill(hotspotClass: string): string {
  switch (hotspotClass) {
    case "well_served":
      return "#1b7a45";
    case "moderate":
      return "#7cb342";
    case "underserved":
      return "#c4a35a";
    default:
      return "#8a8a8a";
  }
}

export function parkAccessOpacity(intensity: number): number {
  // Keep farther tiles lighter so the map is not a solid wash.
  return Math.min(0.72, Math.max(0.28, 0.55 - intensity * 0.22));
}

/** Heat exposure fills (cool → extreme). */
export function heatExposureFill(hotspotClass: string): string {
  switch (hotspotClass) {
    case "elevated":
      return "#f4a261";
    case "high":
      return "#e76f51";
    case "extreme":
      return "#9b2226";
    default:
      return "#e9c46a";
  }
}

export function hotspotOpacity(intensity: number): number {
  return Math.min(0.88, Math.max(0.45, 0.35 + intensity * 0.5));
}
