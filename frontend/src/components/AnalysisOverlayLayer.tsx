import { useEffect } from "react";
import { GeoJSON, useMap } from "react-leaflet";
import L from "leaflet";
import type { OverlayMask } from "../api/analysisJobs";
import type { OverlayMode } from "../lib/vegetationColors";
import {
  heatExposureFill,
  hotspotOpacity,
  vegetationDensityFill,
  vegetationDensityOpacity,
  vegetationHotspotFill,
} from "../lib/vegetationColors";

interface AnalysisOverlayLayerProps {
  mask: OverlayMask | null | undefined;
  mode: OverlayMode;
}

const OVERLAY_PANE = "analysisOverlayPane";

/**
 * Exclusive analysis overlay (vegetation density / veg hotspots / heat).
 */
export function AnalysisOverlayLayer({ mask, mode }: AnalysisOverlayLayerProps) {
  const map = useMap();

  useEffect(() => {
    if (!map.getPane(OVERLAY_PANE)) {
      const pane = map.createPane(OVERLAY_PANE);
      pane.style.zIndex = "450";
      pane.style.pointerEvents = "none";
    }
  }, [map]);

  if (mode === "off" || !mask?.features?.length) {
    return null;
  }

  const signature = `${mode}-${mask.features.length}-${mask.features[0]?.properties?.mean_ndvi ?? mask.features[0]?.properties?.mean_lst_c ?? mask.features[0]?.properties?.intensity ?? 0}`;

  return (
    <GeoJSON
      key={`overlay-${signature}`}
      data={
        {
          type: "FeatureCollection",
          features: mask.features,
        } as unknown as GeoJSON.FeatureCollection
      }
      pane={OVERLAY_PANE}
      style={(feature) => styleForFeature(mode, feature?.properties)}
      onEachFeature={(_feature, layer) => {
        if (layer instanceof L.Path) {
          layer.bringToFront();
        }
      }}
    />
  );
}

function styleForFeature(
  mode: OverlayMode,
  props: Record<string, unknown> | null | undefined,
): L.PathOptions {
  if (mode === "vegetation") {
    const densityClass = String(props?.density_class ?? "moderate");
    const density = typeof props?.density === "number" ? props.density : 0.5;
    return {
      color: vegetationDensityFill(densityClass),
      fillColor: vegetationDensityFill(densityClass),
      fillOpacity: vegetationDensityOpacity(density),
      weight: 0.35,
      opacity: 0.55,
    };
  }

  const hotspotClass = String(props?.hotspot_class ?? "medium");
  const intensity = typeof props?.intensity === "number" ? props.intensity : 0.5;
  const fill =
    mode === "heat" ? heatExposureFill(hotspotClass) : vegetationHotspotFill(hotspotClass);

  return {
    color: fill,
    fillColor: fill,
    fillOpacity: hotspotOpacity(intensity),
    weight: 0.35,
    opacity: 0.55,
  };
}
