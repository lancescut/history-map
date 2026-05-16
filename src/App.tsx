import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import maplibregl, { GeoJSONSource, LngLatBoundsLike, Marker } from "maplibre-gl";
import {
  Download,
  Gauge,
  Layers,
  LocateFixed,
  MapPin,
  Pause,
  Play,
  RotateCcw,
  Search,
  SkipBack,
  SkipForward
} from "lucide-react";
import {
  clampPlayableYear,
  getAliasIndex,
  getCapitals,
  getMetadata,
  getModernAdminUnits,
  getTerritories,
  getYearData,
  nextYear,
  normalizeSearch,
  previousYear,
  yearLabel
} from "./data";
import { defaultAppState, exportAppState, loadAppState, resetAppState, saveAppState } from "./state";
import type {
  AliasIndex,
  AppState,
  CapitalEvent,
  CapitalsData,
  Metadata,
  SearchEntry,
  TerritoryFeatureProperties,
  YearData,
  YearPolity
} from "./types";

const PLAYBACK_SPEEDS = [0.5, 1, 2, 5, 10];

const PERIOD_COLORS = [
  "#d9594c",
  "#4f9c72",
  "#4b83c4",
  "#c58b32",
  "#8f6cc8",
  "#d46c9f",
  "#54a8a8",
  "#b7a553",
  "#6f8f4f",
  "#c76f4d"
];

function stableColor(value: string): string {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return PERIOD_COLORS[hash % PERIOD_COLORS.length];
}

function isNomadic(polityType: string, polityName: string): boolean {
  return /游牧|丁零|高车|柔然|突厥|契丹|蒙古|辽|金|匈奴|鲜卑|吐蕃/.test(`${polityType}${polityName}`);
}

function emptyTerritoryCollection(): GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties> {
  return { type: "FeatureCollection", features: [] };
}

function emptyLabelCollection(): GeoJSON.FeatureCollection<GeoJSON.Point> {
  return { type: "FeatureCollection", features: [] };
}

function emptyFeatureCollection(): GeoJSON.FeatureCollection {
  return { type: "FeatureCollection", features: [] };
}

function migrationFeatureCollection(yearData: YearData | null): GeoJSON.FeatureCollection<GeoJSON.LineString> {
  return {
    type: "FeatureCollection",
    features:
      yearData?.capital_migrations.map((migration) => ({
        type: "Feature",
        geometry: {
          type: "LineString",
          coordinates: [migration.from_coordinates, migration.to_coordinates]
        },
        properties: {
          migration_id: migration.migration_id,
          label: migration.label,
          is_disputed: migration.is_disputed
        }
      })) ?? []
  };
}

function territoryCollections(
  yearData: YearData | null,
  territoryGeoJSON: GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties> | null,
  state: AppState
): {
  territories: GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties>;
  labels: GeoJSON.FeatureCollection<GeoJSON.Point>;
} {
  if (!yearData || !territoryGeoJSON || !state.layers.territories) {
    return { territories: emptyTerritoryCollection(), labels: emptyLabelCollection() };
  }
  const polityById = new Map(yearData.polities.map((polity) => [polity.polity_id, polity]));
  const features: GeoJSON.Feature<GeoJSON.MultiPolygon, TerritoryFeatureProperties>[] = [];
  const labelFeatures: GeoJSON.Feature<GeoJSON.Point>[] = [];

  territoryGeoJSON.features.forEach((feature) => {
    const polity = polityById.get(feature.properties.polity_id);
    if (!polity) return;
    if (state.filters.territory_status === "has_territory" && polity.territory.territory_status === "missing") return;
    if (state.filters.territory_status === "missing") return;
    if ((polity.confidence_score ?? 0) < state.filters.min_confidence_score) return;
    if (!state.filters.show_disputed && polity.quality.has_dispute) return;

    const color = stableColor(`${polity.macro_period}-${polity.polity_id}`);
    const selected = polity.polity_id === state.selection.selected_polity_id;
    const properties = {
      ...feature.properties,
      ...polity.territory,
      polity_id: polity.polity_id,
      polity_name: polity.polity_name,
      macro_period: polity.macro_period,
      dynasty_name: polity.dynasty_name,
      polity_type: polity.polity_type,
      color,
      selected,
      is_nomadic: isNomadic(polity.polity_type, polity.polity_name)
    } as TerritoryFeatureProperties & { is_nomadic: boolean };
    features.push({ ...feature, properties });
    if (polity.territory.centroid && state.layers.territory_labels) {
      labelFeatures.push({
        type: "Feature",
        geometry: { type: "Point", coordinates: polity.territory.centroid },
        properties: {
          polity_id: polity.polity_id,
          polity_name: polity.polity_name,
          size_rank: polity.territory.approx_area_km2 ?? 0,
          selected
        }
      });
    }
  });

  return {
    territories: { type: "FeatureCollection", features },
    labels: { type: "FeatureCollection", features: labelFeatures }
  };
}

function fitMigrationBounds(map: maplibregl.Map, yearData: YearData): void {
  if (!yearData.capital_migrations.length) return;
  const points = yearData.capital_migrations.flatMap((migration) => [migration.from_coordinates, migration.to_coordinates]);
  const bounds = points.reduce(
    (current, point) => current.extend(point),
    new maplibregl.LngLatBounds(points[0], points[0])
  );
  map.fitBounds(bounds as LngLatBoundsLike, { padding: 120, maxZoom: 5.8, duration: 800 });
}

function territoryBounds(
  collection: GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties>
): maplibregl.LngLatBounds | null {
  const coordinates = collection.features.flatMap((feature) =>
    feature.geometry.coordinates.flatMap((polygon) => polygon.flatMap((ring) => ring))
  );
  if (!coordinates.length) return null;
  return coordinates.reduce(
    (bounds, coordinate) => bounds.extend(coordinate as [number, number]),
    new maplibregl.LngLatBounds(coordinates[0] as [number, number], coordinates[0] as [number, number])
  );
}

function fitTerritoryBounds(
  map: maplibregl.Map,
  collection: GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties>
): void {
  const bounds = territoryBounds(collection);
  if (!bounds) return;
  map.fitBounds(bounds as LngLatBoundsLike, {
    padding: {
      top: 96,
      bottom: 96,
      left: 96,
      right: window.innerWidth >= 980 ? 520 : 96
    },
    maxZoom: 5.2,
    duration: 700
  });
}

function eventTypeLabel(event: CapitalEvent): string {
  const labels: Record<string, string> = {
    initial_capital: "初始都城",
    relocation: "迁都",
    co_capital: "陪都",
    temporary_capital: "临时都城",
    disputed: "争议迁都"
  };
  return labels[event.event_type] ?? event.event_type;
}

function App() {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const currentTerritoriesRef = useRef<GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties>>(
    emptyTerritoryCollection()
  );
  const fittedYearRef = useRef<number | null>(null);
  const yearDataRef = useRef<YearData | null>(null);

  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [capitals, setCapitals] = useState<CapitalsData | null>(null);
  const [aliasIndex, setAliasIndex] = useState<AliasIndex | null>(null);
  const [territoryGeoJSON, setTerritoryGeoJSON] =
    useState<GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties> | null>(null);
  const [modernAdminUnits, setModernAdminUnits] = useState<GeoJSON.FeatureCollection | null>(null);
  const [yearData, setYearData] = useState<YearData | null>(null);
  const [appState, setAppState] = useState<AppState>(defaultAppState());
  const [searchText, setSearchText] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getMetadata(), getCapitals(), getAliasIndex(), getTerritories(), getModernAdminUnits()])
      .then(([loadedMetadata, loadedCapitals, loadedAliasIndex, loadedTerritories, loadedModernAdminUnits]) => {
        if (cancelled) return;
        setMetadata(loadedMetadata);
        setCapitals(loadedCapitals);
        setAliasIndex(loadedAliasIndex);
        setTerritoryGeoJSON(loadedTerritories);
        setModernAdminUnits(loadedModernAdminUnits);
        setAppState(loadAppState(loadedMetadata));
      })
      .catch((error: Error) => setLoadError(error.message));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!metadata) return;
    let cancelled = false;
    getYearData(appState.timeline.current_year)
      .then((data) => {
        if (!cancelled) setYearData(data);
      })
      .catch((error: Error) => setLoadError(error.message));
    return () => {
      cancelled = true;
    };
  }, [appState.timeline.current_year, metadata]);

  useEffect(() => {
    yearDataRef.current = yearData;
  }, [yearData]);

  useEffect(() => {
    if (!metadata) return;
    saveAppState(appState);
  }, [appState, metadata]);

  useEffect(() => {
    if (!metadata || !appState.timeline.is_playing) return;
    const delay = Math.max(80, 1000 / appState.timeline.playback_speed);
    const timer = window.setInterval(() => {
      setAppState((state) => {
        const advanced = nextYear(state.timeline.current_year, metadata.year_max);
        return {
          ...state,
          timeline: {
            ...state.timeline,
            current_year: advanced,
            is_playing: advanced < metadata.year_max
          }
        };
      });
    }, delay);
    return () => window.clearInterval(timer);
  }, [appState.timeline.is_playing, appState.timeline.playback_speed, metadata]);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: "https://demotiles.maplibre.org/style.json",
      center: appState.map_view.center,
      zoom: appState.map_view.zoom,
      bearing: appState.map_view.bearing,
      pitch: appState.map_view.pitch,
      attributionControl: { compact: true }
    });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");
    map.on("load", () => {
      if (!map.getSource("territory-previous")) {
        map.addSource("modern-admin-reference", { type: "geojson", data: emptyFeatureCollection() });
        map.addSource("territory-previous", { type: "geojson", data: emptyTerritoryCollection() });
        map.addSource("territory-current", { type: "geojson", data: emptyTerritoryCollection() });
        map.addSource("territory-labels", { type: "geojson", data: emptyLabelCollection() });
        map.addLayer({
          id: "modern-admin-reference",
          type: "line",
          source: "modern-admin-reference",
          layout: {
            visibility: "none"
          },
          paint: {
            "line-color": "rgba(255,255,255,0.5)",
            "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.45, 6, 1.1],
            "line-opacity": 0.48,
            "line-dasharray": [1, 1.6]
          }
        });
        map.addLayer({
          id: "territory-fill-previous",
          type: "fill",
          source: "territory-previous",
          paint: {
            "fill-color": ["coalesce", ["get", "color"], "#d9594c"],
            "fill-opacity": 0,
            "fill-opacity-transition": { duration: 650, delay: 0 },
            "fill-outline-color": "rgba(255,255,255,0.25)"
          }
        });
        map.addLayer({
          id: "territory-fill-current",
          type: "fill",
          source: "territory-current",
          paint: {
            "fill-color": ["coalesce", ["get", "color"], "#d9594c"],
            "fill-opacity": ["case", ["get", "selected"], 0.84, ["get", "is_nomadic"], 0.48, 0.68],
            "fill-opacity-transition": { duration: 650, delay: 0 },
            "fill-outline-color": "rgba(255,255,255,0.2)"
          }
        });
        map.addLayer({
          id: "territory-outline",
          type: "line",
          source: "territory-current",
          paint: {
            "line-color": ["case", ["get", "selected"], "#fff4c2", "rgba(255,255,255,0.62)"],
            "line-width": ["case", ["get", "selected"], 3.2, 1.2],
            "line-opacity": 0.9,
            "line-dasharray": ["case", ["get", "is_nomadic"], ["literal", [1.2, 1.2]], ["literal", [1, 0]]]
          }
        });
        map.addLayer({
          id: "territory-labels",
          type: "symbol",
          source: "territory-labels",
          layout: {
            "text-field": ["get", "polity_name"],
            "text-size": ["interpolate", ["linear"], ["zoom"], 3, 11, 5, 14, 7, 17],
            "text-font": ["Noto Sans Regular"],
            "text-allow-overlap": false,
            "text-ignore-placement": false
          },
          paint: {
            "text-color": "#fff7df",
            "text-halo-color": "rgba(20,20,20,0.86)",
            "text-halo-width": 1.2,
            "text-opacity": ["case", [">", ["get", "size_rank"], 300000], 1, 0.78]
          }
        });
        map.on("click", "territory-fill-current", (event) => {
          const feature = event.features?.[0];
          const polityId = feature?.properties?.polity_id as string | undefined;
          if (!polityId) return;
          const polity = yearDataRef.current?.polities.find((item) => item.polity_id === polityId);
          setAppState((state) => ({
            ...state,
            timeline: { ...state.timeline, is_playing: false },
            selection: {
              selected_polity_id: polityId,
              selected_capital_event_id: polity?.capitals[0]?.capital_event_id ?? null
            }
          }));
        });
        map.on("mouseenter", "territory-fill-current", () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "territory-fill-current", () => {
          map.getCanvas().style.cursor = "";
        });
      }
      if (!map.getSource("migration-lines")) {
        map.addSource("migration-lines", {
          type: "geojson",
          data: migrationFeatureCollection(yearData)
        });
        map.addLayer({
          id: "migration-lines",
          type: "line",
          source: "migration-lines",
          paint: {
            "line-color": ["case", ["get", "is_disputed"], "#f59e0b", "#e11d48"],
            "line-width": 3,
            "line-opacity": 0.8,
            "line-dasharray": [1.2, 1.2]
          }
        });
      }
      setMapReady(true);
    });
    map.on("moveend", () => {
      const center = map.getCenter();
      setAppState((state) => ({
        ...state,
        map_view: {
          center: [center.lng, center.lat],
          zoom: map.getZoom(),
          bearing: map.getBearing(),
          pitch: map.getPitch()
        }
      }));
    });
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      setMapReady(false);
    };
    // Map should initialize only once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectedPolity = useMemo(() => {
    if (!yearData || !appState.selection.selected_polity_id) return null;
    return yearData.polities.find((polity) => polity.polity_id === appState.selection.selected_polity_id) ?? null;
  }, [appState.selection.selected_polity_id, yearData]);

  const selectedCapital = useMemo(() => {
    if (!capitals || !appState.selection.selected_capital_event_id) return null;
    return (
      capitals.capital_events.find(
        (capital) => capital.capital_event_id === appState.selection.selected_capital_event_id
      ) ?? null
    );
  }, [appState.selection.selected_capital_event_id, capitals]);

  const visiblePolities = useMemo(() => {
    if (!yearData) return [];
    return yearData.polities.filter((polity) => {
      if (appState.filters.territory_status === "has_territory" && polity.territory.territory_status === "missing") return false;
      if (appState.filters.territory_status === "missing" && polity.territory.territory_status !== "missing") return false;
      if ((polity.confidence_score ?? 0) < appState.filters.min_confidence_score) return false;
      if (!appState.filters.show_disputed && polity.quality.has_dispute) return false;
      return true;
    });
  }, [appState.filters, yearData]);

  const territoryStats = useMemo(() => {
    const polities = yearData?.polities ?? [];
    const withTerritory = polities.filter((polity) => polity.territory.territory_status !== "missing").length;
    return {
      total: polities.length,
      withTerritory,
      missing: polities.length - withTerritory
    };
  }, [yearData]);

  const updateMapLayers = useCallback(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !yearData) return;

    const collections = territoryCollections(yearData, territoryGeoJSON, appState);
    const adminSource = map.getSource("modern-admin-reference") as GeoJSONSource | undefined;
    if (adminSource) {
      adminSource.setData(modernAdminUnits ?? emptyFeatureCollection());
    }
    if (map.getLayer("modern-admin-reference")) {
      map.setLayoutProperty(
        "modern-admin-reference",
        "visibility",
        appState.layers.modern_admin_reference ? "visible" : "none"
      );
    }

    const previousSource = map.getSource("territory-previous") as GeoJSONSource | undefined;
    const currentSource = map.getSource("territory-current") as GeoJSONSource | undefined;
    const labelSource = map.getSource("territory-labels") as GeoJSONSource | undefined;
    if (previousSource && currentSource && labelSource) {
      previousSource.setData(currentTerritoriesRef.current);
      currentSource.setData(collections.territories);
      labelSource.setData(collections.labels);
      currentTerritoriesRef.current = collections.territories;
      if (collections.territories.features.length && fittedYearRef.current !== yearData.year) {
        fitTerritoryBounds(map, collections.territories);
        fittedYearRef.current = yearData.year;
      }
      if (map.getLayer("territory-fill-previous")) {
        map.setPaintProperty("territory-fill-previous", "fill-opacity", appState.layers.territories ? 0.28 : 0);
        window.setTimeout(() => {
          if (map.getLayer("territory-fill-previous")) {
            map.setPaintProperty("territory-fill-previous", "fill-opacity", 0);
          }
        }, 40);
      }
      ["territory-fill-current", "territory-outline"].forEach((layerId) => {
        if (map.getLayer(layerId)) {
          map.setLayoutProperty(layerId, "visibility", appState.layers.territories ? "visible" : "none");
        }
      });
      if (map.getLayer("territory-labels")) {
        map.setLayoutProperty(
          "territory-labels",
          "visibility",
          appState.layers.territories && appState.layers.territory_labels ? "visible" : "none"
        );
      }
    }

    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    const source = map.getSource("migration-lines") as GeoJSONSource | undefined;
    if (source) {
      source.setData(migrationFeatureCollection(appState.layers.capital_migration_paths ? yearData : null));
    }
    if (map.getLayer("migration-lines")) {
      map.setLayoutProperty("migration-lines", "visibility", appState.layers.capital_migration_paths ? "visible" : "none");
    }

    const migrationEventIds = new Set(
      yearData.capital_migrations.flatMap((migration) => [
        migration.from_capital_event_id,
        migration.to_capital_event_id
      ])
    );

    if (appState.layers.capitals) {
      yearData.polities.forEach((polity) => {
        polity.capitals.forEach((capital) => {
          const element = document.createElement("button");
          element.type = "button";
          element.className = [
            "capital-marker",
            capital.is_primary ? "capital-marker--primary" : "capital-marker--secondary",
            capital.is_disputed ? "capital-marker--disputed" : "",
            migrationEventIds.has(capital.capital_event_id) ? "capital-marker--pulse" : ""
          ]
            .filter(Boolean)
            .join(" ");
          element.textContent = capital.is_primary ? "★" : "◇";
          element.title = `${polity.polity_name} ${capital.capital_name_historical}`;
          element.addEventListener("click", () => {
            setAppState((state) => ({
              ...state,
              timeline: { ...state.timeline, is_playing: false },
              selection: {
                selected_polity_id: polity.polity_id,
                selected_capital_event_id: capital.capital_event_id
              }
            }));
          });
          const marker = new maplibregl.Marker({ element })
            .setLngLat([capital.longitude, capital.latitude])
            .addTo(map);
          markersRef.current.push(marker);
        });
      });
    }

    if (yearData.capital_migrations.length && appState.layers.capital_migration_paths) {
      fitMigrationBounds(map, yearData);
    }
  }, [appState, mapReady, modernAdminUnits, territoryGeoJSON, yearData]);

  useEffect(() => {
    updateMapLayers();
  }, [updateMapLayers]);

  useEffect(() => {
    if (!capitals || !appState.selection.selected_capital_event_id) return;
    const exists = capitals.capital_events.some(
      (capital) => capital.capital_event_id === appState.selection.selected_capital_event_id
    );
    if (!exists) {
      setAppState((state) => ({
        ...state,
        selection: { ...state.selection, selected_capital_event_id: null }
      }));
    }
  }, [appState.selection.selected_capital_event_id, capitals]);

  const searchResults = useMemo<SearchEntry[]>(() => {
    if (!aliasIndex || !searchText.trim()) return [];
    const normalized = normalizeSearch(searchText);
    const directYear = /^-?\d+$/.test(searchText.trim()) ? Number(searchText.trim()) : null;
    const results = aliasIndex.entries
      .filter((entry) => entry.normalized.includes(normalized) || normalizeSearch(entry.alias).includes(normalized))
      .slice(0, 12);
    if (directYear !== null) {
      return [
        {
          alias: yearLabel(directYear),
          normalized: String(directYear),
          entity_type: "polity",
          entity_id: "__year__",
          label: `跳转到 ${yearLabel(directYear)}`,
          start_year: directYear,
          end_year: directYear
        },
        ...results
      ];
    }
    return results;
  }, [aliasIndex, searchText]);

  const jumpToYear = useCallback(
    (year: number) => {
      if (!metadata) return;
      const current_year = clampPlayableYear(year, metadata.year_min, metadata.year_max);
      setAppState((state) => ({
        ...state,
        timeline: { ...state.timeline, current_year, is_playing: false }
      }));
    },
    [metadata]
  );

  const handleSearchSelect = (entry: SearchEntry) => {
    if (entry.start_year != null) {
      jumpToYear(entry.start_year);
    }
    setSearchText(entry.alias);
    setAppState((state) => ({
      ...state,
      selection: {
        selected_polity_id: entry.polity_id ?? null,
        selected_capital_event_id: entry.capital_event_id ?? null
      }
    }));
    if (entry.longitude != null && entry.latitude != null && mapRef.current) {
      mapRef.current.flyTo({ center: [entry.longitude, entry.latitude], zoom: 5, duration: 900 });
    }
  };

  const selectPolity = (polity: YearPolity) => {
    setAppState((state) => ({
      ...state,
      timeline: { ...state.timeline, is_playing: false },
      selection: {
        selected_polity_id: polity.polity_id,
        selected_capital_event_id: polity.capitals[0]?.capital_event_id ?? null
      }
    }));
  };

  const resetView = () => {
    mapRef.current?.flyTo({ center: [105, 35], zoom: 3.3, bearing: 0, pitch: 0, duration: 700 });
  };

  if (loadError) {
    return (
      <main className="app app--error">
        <h1>数据加载失败</h1>
        <p>{loadError}</p>
      </main>
    );
  }

  return (
    <main className="app">
      <section className="map-shell">
        <div ref={mapContainerRef} className="map-canvas" />
        <header className="topbar">
          <div>
            <h1>中国朝代更迭地图</h1>
            <p>
              v03 · {metadata?.polity_count ?? 0} 政权 · {metadata?.capital_event_count ?? 0} 都城事件 ·{" "}
              {metadata?.capital_migration_count ?? 0} 迁都事件 · {metadata?.territory_polity_count ?? 0} 近似疆域
            </p>
          </div>
          <div className="search-box">
            <Search size={16} />
            <input
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="搜索年份、政权、君主或都城"
            />
            {searchResults.length > 0 && (
              <div className="search-results">
                {searchResults.map((entry) => (
                  <button key={`${entry.entity_type}-${entry.entity_id}-${entry.alias}`} onClick={() => handleSearchSelect(entry)}>
                    <span>{entry.alias}</span>
                    <small>{entry.entity_type === "capital" ? "都城" : entry.entity_type === "ruler" ? "君主" : "政权/年份"}</small>
                  </button>
                ))}
              </div>
            )}
          </div>
        </header>

        {yearData?.capital_migrations.length ? (
          <div className="migration-toast">
            <MapPin size={16} />
            {yearData.capital_migrations.map((migration) => (
              <span key={migration.migration_id}>
                {migration.polity_name} {migration.label}
                {migration.is_disputed ? "（争议）" : ""}
              </span>
            ))}
          </div>
        ) : null}

        <div className="layer-panel">
          <div className="panel-title">
            <Layers size={16} />
            图层
          </div>
          <label>
            <input
              type="checkbox"
              checked={appState.layers.territories}
              onChange={(event) =>
                setAppState((state) => ({ ...state, layers: { ...state.layers, territories: event.target.checked } }))
              }
            />
            政权疆域
          </label>
          <label>
            <input
              type="checkbox"
              checked={appState.layers.territory_labels}
              onChange={(event) =>
                setAppState((state) => ({ ...state, layers: { ...state.layers, territory_labels: event.target.checked } }))
              }
            />
            政权标签
          </label>
          <label>
            <input
              type="checkbox"
              checked={appState.layers.modern_admin_reference}
              onChange={(event) =>
                setAppState((state) => ({
                  ...state,
                  layers: { ...state.layers, modern_admin_reference: event.target.checked }
                }))
              }
            />
            现代省界参考
          </label>
          <label>
            <input
              type="checkbox"
              checked={appState.layers.capitals}
              onChange={(event) =>
                setAppState((state) => ({ ...state, layers: { ...state.layers, capitals: event.target.checked } }))
              }
            />
            都城 marker
          </label>
          <label>
            <input
              type="checkbox"
              checked={appState.layers.capital_migration_paths}
              onChange={(event) =>
                setAppState((state) => ({
                  ...state,
                  layers: { ...state.layers, capital_migration_paths: event.target.checked }
                }))
              }
            />
            迁都连线
          </label>
          <button onClick={resetView}>
            <LocateFixed size={15} />
            重置视角
          </button>
        </div>

        <div className="territory-legend">
          <strong>疆域口径</strong>
          <span>{metadata?.territory_label ?? "现代省级行政边界拼合，非历史精确边界"}</span>
          <span>实线：定居政权 · 虚线：游牧/活动范围</span>
          <span>
            边界源：{metadata?.admin_boundary_source ?? "geoBoundaries"} ·{" "}
            {metadata?.admin_boundary_license ?? "Public Domain"}
          </span>
        </div>
      </section>

      <aside className="side-panel">
        <div className="year-card">
          <span className="label">当前年份</span>
          <strong>{yearData?.year_label ?? "加载中"}</strong>
          <p>
            {territoryStats.total} 个政权 · {territoryStats.withTerritory} 有疆域 · {territoryStats.missing} 无法估算 ·{" "}
            {yearData?.capital_migrations.length ?? 0} 个迁都事件
          </p>
        </div>

        <section className="timeline-card">
          <div className="timeline-actions">
            <button onClick={() => metadata && jumpToYear(previousYear(appState.timeline.current_year, metadata.year_min))}>
              <SkipBack size={17} />
            </button>
            <button
              className="primary-action"
              onClick={() =>
                setAppState((state) => ({
                  ...state,
                  timeline: { ...state.timeline, is_playing: !state.timeline.is_playing }
                }))
              }
            >
              {appState.timeline.is_playing ? <Pause size={18} /> : <Play size={18} />}
            </button>
            <button onClick={() => metadata && jumpToYear(nextYear(appState.timeline.current_year, metadata.year_max))}>
              <SkipForward size={17} />
            </button>
            <button onClick={() => metadata && setAppState(resetAppState(metadata))}>
              <RotateCcw size={17} />
            </button>
            <button onClick={() => exportAppState(appState)}>
              <Download size={17} />
            </button>
          </div>
          <input
            type="range"
            min={metadata?.year_min ?? -1046}
            max={metadata?.year_max ?? 1912}
            value={appState.timeline.current_year}
            onChange={(event) => jumpToYear(Number(event.target.value))}
          />
          <div className="year-input-row">
            <input
              type="number"
              value={appState.timeline.current_year}
              onChange={(event) => jumpToYear(Number(event.target.value))}
            />
            <select
              value={appState.timeline.playback_speed}
              onChange={(event) =>
                setAppState((state) => ({
                  ...state,
                  timeline: { ...state.timeline, playback_speed: Number(event.target.value) }
                }))
              }
            >
              {PLAYBACK_SPEEDS.map((speed) => (
                <option key={speed} value={speed}>
                  {speed}x
                </option>
              ))}
            </select>
          </div>
          <div className="migration-ticks">
            {metadata?.capital_migration_years.map((year) => (
              <button key={year} title={yearLabel(year)} onClick={() => jumpToYear(year)}>
                <span>{yearLabel(year)}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="filter-card">
          <div className="panel-heading">
            <h2>筛选</h2>
            <span>{visiblePolities.length}</span>
          </div>
          <label>
            疆域状态
            <select
              value={appState.filters.territory_status}
              onChange={(event) =>
                setAppState((state) => ({
                  ...state,
                  filters: {
                    ...state.filters,
                    territory_status: event.target.value as AppState["filters"]["territory_status"]
                  }
                }))
              }
            >
              <option value="all">全部</option>
              <option value="has_territory">已生成疆域</option>
              <option value="missing">无法估算</option>
            </select>
          </label>
          <label>
            最低置信度 {appState.filters.min_confidence_score}
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={appState.filters.min_confidence_score}
              onChange={(event) =>
                setAppState((state) => ({
                  ...state,
                  filters: { ...state.filters, min_confidence_score: Number(event.target.value) }
                }))
              }
            />
          </label>
          <label className="inline-check">
            <input
              type="checkbox"
              checked={appState.filters.show_disputed}
              onChange={(event) =>
                setAppState((state) => ({
                  ...state,
                  filters: { ...state.filters, show_disputed: event.target.checked }
                }))
              }
            />
            显示争议项
          </label>
        </section>

        <section className="panel-section">
          <div className="panel-heading">
            <h2>年度概况</h2>
            <span>{visiblePolities.length}</span>
          </div>
          <div className="polity-list">
            {visiblePolities.map((polity) => (
              <button
                key={polity.polity_id}
                className={polity.polity_id === appState.selection.selected_polity_id ? "selected" : ""}
                onClick={() => selectPolity(polity)}
              >
                <span>{polity.polity_name}</span>
                <small className={polity.territory.territory_status}>
                  {polity.territory.territory_status === "missing"
                    ? "疆域无法估算"
                    : `${polity.territory.matched_admin_units.join("、")} · ${polity.territory.match_confidence}`}
                </small>
              </button>
            ))}
            {!visiblePolities.length ? <div className="empty-list">当前筛选条件下没有政权记录。</div> : null}
          </div>
        </section>

        <section className="panel-section detail-section">
          <div className="panel-heading">
            <h2>都城时间线</h2>
            <Gauge size={16} />
          </div>
          {selectedPolity ? (
            <PolityDetail
              polity={selectedPolity}
              allCapitalEvents={capitals?.by_polity[selectedPolity.polity_id] ?? []}
              selectedCapital={selectedCapital}
              onSelectCapital={(capital) =>
                setAppState((state) => ({
                  ...state,
                  selection: {
                    selected_polity_id: capital.polity_id,
                    selected_capital_event_id: capital.capital_event_id
                  }
                }))
              }
            />
          ) : (
            <div className="empty-state">选择地图上的都城 marker 或年度政权列表查看详情。</div>
          )}
        </section>
      </aside>
    </main>
  );
}

function PolityDetail({
  polity,
  allCapitalEvents,
  selectedCapital,
  onSelectCapital
}: {
  polity: YearPolity;
  allCapitalEvents: CapitalEvent[];
  selectedCapital: CapitalEvent | null;
  onSelectCapital: (capital: CapitalEvent) => void;
}) {
  return (
    <div className="polity-detail">
      <div className="detail-title">
        <div>
          <h3>{polity.polity_name}</h3>
          <p>{polity.macro_period} · {polity.polity_type}</p>
        </div>
        <span className={`quality-chip ${polity.capital_quality.status}`}>{polity.capital_quality.label}</span>
      </div>

      <div className="territory-detail">
        <strong>当前疆域</strong>
        {polity.territory.territory_status === "missing" ? (
          <p>无法估算：该政权暂无可解析现代行政区匹配，不渲染伪疆域。</p>
        ) : (
          <>
            <p>
              {polity.territory.matched_admin_units.join("、")} · 约{" "}
              {Math.round(polity.territory.approx_area_km2 ?? 0).toLocaleString()} 平方公里
            </p>
            <p>
              匹配置信度 {polity.territory.match_confidence} · {polity.territory.label}
            </p>
            <p>
              边界源 {polity.territory.geometry_source_attribution ?? "geoBoundaries"} ·{" "}
              {polity.territory.geometry_source_license ?? "Public Domain"} ·{" "}
              {polity.territory.geometry_coordinate_count?.toLocaleString() ?? 0} 点
            </p>
          </>
        )}
      </div>

      {polity.capitals.length ? (
        <div className="current-capitals">
          {polity.capitals.map((capital) => (
            <button
              key={capital.capital_event_id}
              className={selectedCapital?.capital_event_id === capital.capital_event_id ? "selected" : ""}
              onClick={() => onSelectCapital(capital)}
            >
              <strong>{capital.capital_name_historical}</strong>
              <span>{capital.capital_name_modern}</span>
              <small>{eventTypeLabel(capital)} · 置信度 {capital.confidence_score}</small>
            </button>
          ))}
        </div>
      ) : (
        <div className="warning-box">暂无可解析都城资料，不渲染伪 marker。</div>
      )}

      {allCapitalEvents.length ? (
        <ol className="capital-timeline">
          {allCapitalEvents.map((capital) => (
            <li key={capital.capital_event_id} className={capital.is_disputed ? "disputed" : ""}>
              <button onClick={() => onSelectCapital(capital)}>
                <span className="timeline-dot" />
                <strong>
                  {capital.valid_from_label} - {capital.valid_to_label}
                </strong>
                <span>
                  {capital.capital_name_historical}（{capital.capital_name_modern}）
                </span>
                <small>
                  {eventTypeLabel(capital)} · {capital.location_precision} · 置信度 {capital.confidence_score}
                </small>
              </button>
            </li>
          ))}
        </ol>
      ) : null}

      <div className="source-box">
        <strong>来源追溯</strong>
        <p>{selectedCapital?.source_titles ?? polity.polity_source_titles}</p>
        <p>{selectedCapital?.source_raw ?? polity.polity_source_raw}</p>
        {selectedCapital?.confidence_note ? <p>{selectedCapital.confidence_note}</p> : null}
      </div>

      {polity.rulers.length ? (
        <div className="ruler-box">
          <strong>当前君主</strong>
          {polity.rulers.slice(0, 3).map((ruler) => (
            <p key={ruler.ruler_id}>{ruler.ruler_name || ruler.ruler_title}</p>
          ))}
        </div>
      ) : (
        <div className="ruler-box muted">该年度暂未匹配到可解析君主年表。</div>
      )}
    </div>
  );
}

export default App;
