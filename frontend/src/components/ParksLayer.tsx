import { useEffect } from "react";
import { GeoJSON, useMap } from "react-leaflet";
import L from "leaflet";
import type { ParksLayer as ParksLayerData } from "../api/parks";

interface ParksLayerProps {
  parks: ParksLayerData | null | undefined;
}

const PARKS_PANE = "parksOutlinePane";
const CATCHMENT_PANE = "parkCatchmentPane";

/**
 * Mark OSM parks inside the AOI and nearby (within catchment).
 * Dashed ring shows the search catchment around the selected region.
 */
export function ParksLayer({ parks }: ParksLayerProps) {
  const map = useMap();

  useEffect(() => {
    if (!map.getPane(CATCHMENT_PANE)) {
      const pane = map.createPane(CATCHMENT_PANE);
      pane.style.zIndex = "445";
      pane.style.pointerEvents = "none";
    }
    if (!map.getPane(PARKS_PANE)) {
      const pane = map.createPane(PARKS_PANE);
      pane.style.zIndex = "460";
      pane.style.pointerEvents = "none";
    }
  }, [map]);

  if (!parks?.features?.length) {
    return null;
  }

  const catchment = parks.properties?.catchment;
  const signature = `${parks.features.length}-${parks.features[0]?.properties?.osm_id ?? 0}`;

  return (
    <>
      {catchment?.geometry ? (
        <GeoJSON
          key={`catchment-${signature}`}
          data={
            {
              type: "FeatureCollection",
              features: [catchment],
            } as unknown as GeoJSON.FeatureCollection
          }
          pane={CATCHMENT_PANE}
          style={() => ({
            color: "#5a8f6e",
            fillColor: "#5a8f6e",
            fillOpacity: 0.06,
            weight: 1.5,
            opacity: 0.7,
            dashArray: "6 5",
          })}
        />
      ) : null}
      <GeoJSON
        key={`parks-${signature}`}
        data={
          {
            type: "FeatureCollection",
            features: parks.features,
          } as unknown as GeoJSON.FeatureCollection
        }
        pane={PARKS_PANE}
        style={(feature) => {
          const location = String(feature?.properties?.location ?? "inside");
          const nearby = location === "nearby";
          return {
            color: nearby ? "#1a5f8a" : "#0b3d1e",
            fillColor: nearby ? "#3d9ecb" : "#2f9e57",
            fillOpacity: nearby ? 0.28 : 0.42,
            weight: nearby ? 1.75 : 2.4,
            opacity: 0.95,
            dashArray: nearby ? "4 3" : undefined,
          };
        }}
        onEachFeature={(feature, layer) => {
          const name = String(feature.properties?.name ?? "Park");
          const location = String(feature.properties?.location ?? "inside");
          const area = feature.properties?.area_m2;
          const where = location === "nearby" ? "nearby" : "inside";
          const label =
            typeof area === "number" && area > 0
              ? `${name} (${where}) · ${Math.round(area).toLocaleString()} m²`
              : `${name} (${where})`;
          layer.bindTooltip(label, {
            permanent: true,
            direction: "center",
            className: location === "nearby" ? "park-label park-label--nearby" : "park-label",
            opacity: 0.92,
          });
          if (layer instanceof L.Path) {
            layer.bringToFront();
          }
        }}
      />
    </>
  );
}
