import type { AppState, Metadata } from "./types";
import { clampPlayableYear } from "./data";

const STATE_KEY = "history-map-state-v03";

export function defaultAppState(metadata?: Metadata): AppState {
  const currentYear = metadata ? -688 : -221;
  return {
    schema_version: "1.2.0",
    data_version: "v03",
    updated_at: new Date().toISOString(),
    timeline: {
      current_year: currentYear,
      is_playing: false,
      playback_speed: 1
    },
    map_view: {
      center: [105, 35],
      zoom: 3.3,
      bearing: 0,
      pitch: 0
    },
    selection: {
      selected_polity_id: null,
      selected_capital_event_id: null
    },
    layers: {
      territories: true,
      territory_labels: true,
      modern_admin_reference: false,
      capitals: true,
      capital_migration_paths: true
    },
    filters: {
      territory_status: "all",
      min_confidence_score: 0,
      show_disputed: true
    }
  };
}

export function loadAppState(metadata: Metadata): AppState {
  const fallback = defaultAppState(metadata);
  try {
    const raw = localStorage.getItem(STATE_KEY);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw) as Partial<AppState>;
    if (parsed.schema_version !== "1.2.0" || parsed.data_version !== "v03") {
      return fallback;
    }
    return {
      ...fallback,
      ...parsed,
      timeline: {
        ...fallback.timeline,
        ...parsed.timeline,
        current_year: clampPlayableYear(
          parsed.timeline?.current_year ?? fallback.timeline.current_year,
          metadata.year_min,
          metadata.year_max
        ),
        playback_speed: parsed.timeline?.playback_speed ?? fallback.timeline.playback_speed,
        is_playing: parsed.timeline?.is_playing ?? false
      },
      map_view: {
        ...fallback.map_view,
        ...parsed.map_view
      },
      selection: {
        ...fallback.selection,
        ...parsed.selection
      },
      layers: {
        ...fallback.layers,
        ...parsed.layers
      },
      filters: {
        ...fallback.filters,
        ...parsed.filters
      }
    };
  } catch {
    localStorage.removeItem(STATE_KEY);
    return fallback;
  }
}

export function saveAppState(state: AppState): void {
  localStorage.setItem(
    STATE_KEY,
    JSON.stringify({
      ...state,
      updated_at: new Date().toISOString()
    })
  );
}

export function exportAppState(state: AppState): void {
  const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `history-map-state-v03-${new Date().toISOString().replace(/[:.]/g, "")}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

export function resetAppState(metadata: Metadata): AppState {
  localStorage.removeItem(STATE_KEY);
  return defaultAppState(metadata);
}
