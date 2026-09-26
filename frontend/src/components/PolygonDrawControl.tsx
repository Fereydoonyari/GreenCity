import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import L from "leaflet";
import { useMap } from "react-leaflet";

export interface DrawnPolygonPayload {
  type: string;
  coordinates: unknown;
}

interface PolygonDrawControlProps {
  onCreated: (geometry: DrawnPolygonPayload) => void;
}

/**
 * Custom polygon draw control that does NOT use Leaflet.Draw.
 *
 * Interaction:
 *  - While drawing mode is active, every map click adds a vertex.
 *  - "Finish" button (or pressing Enter) closes the polygon and emits it.
 *  - "Cancel" button (or pressing Escape) aborts.
 *  - Minimum 3 vertices required to finish.
 */
export function PolygonDrawControl({ onCreated }: PolygonDrawControlProps) {
  const map = useMap();
  const [drawing, setDrawing] = useState(false);
  const [vertexCount, setVertexCount] = useState(0);
  const pointsRef = useRef<L.LatLng[]>([]);
  const layersRef = useRef<L.Layer[]>([]);
  const polylineRef = useRef<L.Polyline | null>(null);
  const previewRef = useRef<L.Polyline | null>(null);

  const clearLayers = useCallback(() => {
    layersRef.current.forEach((l) => map.removeLayer(l));
    layersRef.current = [];
    if (polylineRef.current) {
      map.removeLayer(polylineRef.current);
      polylineRef.current = null;
    }
    if (previewRef.current) {
      map.removeLayer(previewRef.current);
      previewRef.current = null;
    }
  }, [map]);

  const redrawLines = useCallback(
    (pts: L.LatLng[]) => {
      if (polylineRef.current) map.removeLayer(polylineRef.current);
      if (pts.length >= 2) {
        polylineRef.current = L.polyline(pts, { color: "#4aa3d9", weight: 2 }).addTo(map);
      }
      // draw vertex markers
      layersRef.current.forEach((l) => map.removeLayer(l));
      layersRef.current = pts.map((pt) =>
        L.circleMarker(pt, {
          radius: 5,
          color: "#4aa3d9",
          fillColor: "#fff",
          fillOpacity: 1,
          weight: 2,
        }).addTo(map)
      );
    },
    [map]
  );

  const startDrawing = useCallback(() => {
    pointsRef.current = [];
    setVertexCount(0);
    clearLayers();
    setDrawing(true);
    map.getContainer().style.cursor = "crosshair";
  }, [map, clearLayers]);

  const cancelDrawing = useCallback(() => {
    clearLayers();
    pointsRef.current = [];
    setVertexCount(0);
    setDrawing(false);
    map.getContainer().style.cursor = "";
  }, [map, clearLayers]);

  const finishDrawing = useCallback(() => {
    const pts = pointsRef.current;
    if (pts.length < 3) return;

    // close the polygon visually
    const closed = [...pts, pts[0]];
    if (polylineRef.current) map.removeLayer(polylineRef.current);
    const poly = L.polygon(pts, { color: "#4aa3d9", fillOpacity: 0.2, weight: 2 }).addTo(map);
    layersRef.current.push(poly);

    // emit GeoJSON
    const coords = [closed.map((p) => [p.lng, p.lat])];
    onCreated({ type: "Polygon", coordinates: coords });

    // reset state but keep the drawn polygon on screen
    pointsRef.current = [];
    setVertexCount(0);
    layersRef.current.forEach((l) => {
      if (l !== poly) map.removeLayer(l);
    });
    layersRef.current = [poly];
    if (polylineRef.current) {
      map.removeLayer(polylineRef.current);
      polylineRef.current = null;
    }
    if (previewRef.current) {
      map.removeLayer(previewRef.current);
      previewRef.current = null;
    }
    setDrawing(false);
    map.getContainer().style.cursor = "";
  }, [map, onCreated]);

  // map click → add vertex
  useEffect(() => {
    if (!drawing) return;

    const handleClick = (e: L.LeafletMouseEvent) => {
      const pts = [...pointsRef.current, e.latlng];
      pointsRef.current = pts;
      setVertexCount(pts.length);
      redrawLines(pts);
    };

    const handleMouseMove = (e: L.LeafletMouseEvent) => {
      const pts = pointsRef.current;
      if (pts.length === 0) return;
      if (previewRef.current) map.removeLayer(previewRef.current);
      previewRef.current = L.polyline([pts[pts.length - 1], e.latlng], {
        color: "#4aa3d9",
        weight: 1,
        dashArray: "4 4",
        opacity: 0.7,
      }).addTo(map);
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Enter") finishDrawing();
      if (e.key === "Escape") cancelDrawing();
    };

    map.on("click", handleClick);
    map.on("mousemove", handleMouseMove);
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      map.off("click", handleClick);
      map.off("mousemove", handleMouseMove);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [drawing, map, redrawLines, finishDrawing, cancelDrawing]);

  const container = map.getContainer().parentElement;

  const toolbar = (
    <div className="draw-toolbar">
      {!drawing ? (
        <button type="button" className="draw-btn" onClick={startDrawing} title="Draw polygon">
          Draw polygon
        </button>
      ) : (
        <>
          <span className="draw-status">
            {vertexCount === 0
              ? "Click the map to add points"
              : `${vertexCount} point${vertexCount === 1 ? "" : "s"} — add more or finish`}
          </span>
          <button
            type="button"
            className="draw-btn draw-btn--finish"
            onClick={finishDrawing}
            title="Finish polygon (Enter)"
          >
            Finish
          </button>
          <button
            type="button"
            className="draw-btn draw-btn--cancel"
            onClick={cancelDrawing}
            title="Cancel (Escape)"
          >
            Cancel
          </button>
        </>
      )}
    </div>
  );

  return container ? createPortal(toolbar, container) : null;
}
