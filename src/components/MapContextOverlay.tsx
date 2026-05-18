import { useEffect, useState } from "react";
import type { LngLatLike, Map as MapLibreMap } from "maplibre-gl";
import type { HistoricalContext } from "../types";

interface ProjectedContext {
  context: HistoricalContext;
  point: { x: number; y: number };
}

interface MapContextOverlayProps {
  map: MapLibreMap | null;
  contexts: HistoricalContext[];
  onFlyToContext?: (lng: number, lat: number) => void;
}

function contextCoordinates(context: HistoricalContext): [number, number] | null {
  const lng = context.location?.longitude ?? context.longitude;
  const lat = context.location?.latitude ?? context.latitude;
  if (typeof lng !== "number" || typeof lat !== "number") return null;
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) return null;
  return [lng, lat];
}

export function MapContextOverlay({ map, contexts, onFlyToContext }: MapContextOverlayProps) {
  const [projected, setProjected] = useState<ProjectedContext[]>([]);

  useEffect(() => {
    if (!map) {
      setProjected([]);
      return;
    }

    const update = () => {
      const container = map.getContainer();
      const width = container.clientWidth || 0;
      const height = container.clientHeight || 0;
      const next: ProjectedContext[] = [];
      contexts.slice(0, 1).forEach((context) => {
        const coordinates = contextCoordinates(context);
        if (!coordinates) return;
        const point = map.project(coordinates as LngLatLike);
        if (point.x < -60 || point.y < -60 || point.x > width + 60 || point.y > height + 60) return;
        next.push({ context, point: { x: point.x, y: point.y } });
      });
      setProjected(next);
    };

    update();
    map.on("move", update);
    map.on("zoom", update);
    map.on("resize", update);
    window.addEventListener("resize", update);
    return () => {
      map.off("move", update);
      map.off("zoom", update);
      map.off("resize", update);
      window.removeEventListener("resize", update);
    };
  }, [contexts, map]);

  if (!projected.length) return null;

  return (
    <div className="map-context-overlay" aria-hidden="false">
      {projected.map(({ context, point }) => {
        const coordinates = contextCoordinates(context);
        const progress = Math.round((context.progress_ratio ?? 0) * 100);
        return (
          <button
            key={`${context.context_id}:${context.current_year}`}
            type="button"
            className="map-context-marker"
            style={{ left: point.x, top: point.y }}
            aria-label={`${context.year_label} 脉络 ${context.title}`}
            title={`${context.title} · ${progress}%`}
            onClick={() => {
              if (coordinates) onFlyToContext?.(coordinates[0], coordinates[1]);
            }}
          >
            <span className="map-context-marker__dot" aria-hidden />
            <span className="map-context-marker__callout">
              <span className="map-context-marker__meta">
                <b>脉络</b>
                <small>{context.year_label} · {progress}%</small>
              </span>
              <strong>{context.title}</strong>
              <span className="map-context-marker__desc">{context.description}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
