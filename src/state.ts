import type { AppState, DatasetId, Metadata } from "./types";
import { DATASET_IDS } from "./types";
import { clampPlayableYear } from "./data";

// 跨数据源 year 范围的并集，用于 sanitizeState 在尚未合并多源 metadata 时的宽松 clamp。
// vIndian metadata.year_min 实际为 -7000（取数据中最早事件，覆盖 manifest 的 -3300）。
const KNOWN_YEAR_MIN = -7000;
const KNOWN_YEAR_MAX = 1990;

const APP_ID = "chinese-dynasty-history-map";
const APP_VERSION = "0.3.0";
const SCHEMA_VERSION = "2.7.0" as const;
const DATA_VERSION = "v03" as const;

function sanitizeActiveDatasets(raw: unknown): DatasetId[] {
  if (!Array.isArray(raw)) return ["v03"];
  const seen = new Set<DatasetId>();
  for (const value of raw) {
    if (typeof value !== "string") continue;
    if ((DATASET_IDS as readonly string[]).includes(value)) {
      seen.add(value as DatasetId);
    }
  }
  if (seen.size === 0) return ["v03"];
  // 保持 DATASET_IDS 中定义的顺序（v03 在前），便于 round-robin 输出稳定。
  return DATASET_IDS.filter((id) => seen.has(id));
}
const DB_NAME = "history-map-state";
const DB_STORE = "app_state";
const DB_KEY = "last_session";
const LEGACY_LS_KEY = "history-map-state-v03";
const LS_INDEX_KEY = "history-map-state-index";
const BROADCAST_CHANNEL = "history-map-state-sync";

const SAVE_DEBOUNCE_MS = 500;

export interface StoredAppState extends AppState {
  app_id: string;
  app_version: string;
}

export interface StateLoadResult {
  state: StoredAppState;
  warning?: string;
  source: "default" | "indexeddb" | "localstorage" | "migrated" | "corrupted";
}

export type Listener = (state: StoredAppState, source: "self" | "broadcast") => void;

interface MigrationStep {
  from: string;
  to: string;
  migrate: (raw: Record<string, unknown>) => Record<string, unknown>;
}

const MIGRATIONS: MigrationStep[] = [
  { from: "1.0.0", to: "1.3.0", migrate: (raw) => raw },
  { from: "1.1.0", to: "1.3.0", migrate: (raw) => raw },
  { from: "1.2.0", to: "1.3.0", migrate: (raw) => raw },
  {
    from: "1.3.0",
    to: "2.0.0",
    migrate: (raw) => ({
      ...raw,
      app_id: APP_ID,
      app_version: APP_VERSION,
      schema_version: "2.0.0"
    })
  },
  {
    from: "2.0.0",
    to: "2.1.0",
    migrate: (raw) => {
      // 移除 auto-hide-card 机制；从 card_pins.side_panel 推断 side_panel_open。
      const prevUi = (raw.ui as Record<string, unknown> | undefined) ?? {};
      const cardPins = (prevUi.card_pins as Record<string, unknown> | undefined) ?? {};
      return {
        ...raw,
        ui: { side_panel_open: cardPins.side_panel == null ? true : Boolean(cardPins.side_panel) },
        schema_version: "2.1.0"
      };
    }
  },
  {
    from: "2.1.0",
    to: "2.2.0",
    migrate: (raw) => {
      const prevTimeline = (raw.timeline as Record<string, unknown> | undefined) ?? {};
      const prevFilters = (raw.filters as Record<string, unknown> | undefined) ?? {};
      return {
        ...raw,
        timeline: { ...prevTimeline, timeline_mode: "current_year" },
        filters: {
          ...prevFilters,
          polity_types: Array.isArray(prevFilters.polity_types) ? prevFilters.polity_types : [],
          show_unmatched_ruler:
            prevFilters.show_unmatched_ruler == null ? true : Boolean(prevFilters.show_unmatched_ruler),
          search_keyword: typeof prevFilters.search_keyword === "string" ? prevFilters.search_keyword : ""
        },
        schema_version: "2.2.0"
      };
    }
  },
  {
    from: "2.2.0",
    to: "2.3.0",
    migrate: (raw) => {
      // 用户偏好：镜头不再自动调远近；默认视角改为欧亚正中。强制覆盖旧偏好一次。
      const prevUi = (raw.ui as Record<string, unknown> | undefined) ?? {};
      return {
        ...raw,
        ui: { ...prevUi, auto_follow_main_polity: false },
        map_view: { center: [75, 38], zoom: 2.6, bearing: 0, pitch: 0 },
        schema_version: "2.3.0"
      };
    }
  },
  {
    from: "2.3.0",
    to: "2.4.0",
    migrate: (raw) => {
      // 移除 selected_capital_event_id 死字段（详情面板已删，该字段已无 UI 展示路径）
      const prevSelection = (raw.selection as Record<string, unknown> | undefined) ?? {};
      const { selected_capital_event_id: _drop, ...selectionKept } = prevSelection;
      void _drop;
      return {
        ...raw,
        selection: selectionKept,
        schema_version: "2.4.0"
      };
    }
  },
  {
    from: "2.4.0",
    to: "2.5.0",
    migrate: (raw) => {
      const prevUi = (raw.ui as Record<string, unknown> | undefined) ?? {};
      return {
        ...raw,
        ui: { ...prevUi, show_historical_anecdotes: false },
        schema_version: "2.5.0"
      };
    }
  },
  {
    from: "2.5.0",
    to: "2.6.0",
    migrate: (raw) => {
      const prevLayers = (raw.layers as Record<string, unknown> | undefined) ?? {};
      return {
        ...raw,
        layers: {
          ...prevLayers,
          strategic_locations:
            prevLayers.strategic_locations == null ? true : Boolean(prevLayers.strategic_locations),
          strategic_location_labels:
            prevLayers.strategic_location_labels == null ? false : Boolean(prevLayers.strategic_location_labels),
          graticule: prevLayers.graticule == null ? true : Boolean(prevLayers.graticule),
          graticule_labels: prevLayers.graticule_labels == null ? true : Boolean(prevLayers.graticule_labels)
        },
        schema_version: "2.6.0"
      };
    }
  },
  {
    from: "2.6.0",
    to: "2.7.0",
    migrate: (raw) => {
      // 多数据源播放：注入 datasets.active 默认 ["v03"]（中国史），ui.show_mythology=true。
      const prevUi = (raw.ui as Record<string, unknown> | undefined) ?? {};
      return {
        ...raw,
        datasets: { active: ["v03"] },
        ui: {
          ...prevUi,
          show_mythology: prevUi.show_mythology == null ? true : Boolean(prevUi.show_mythology)
        },
        schema_version: "2.7.0"
      };
    }
  }
];

export function defaultAppState(metadata?: Metadata): StoredAppState {
  void metadata;
  return {
    schema_version: SCHEMA_VERSION,
    app_id: APP_ID,
    app_version: APP_VERSION,
    data_version: DATA_VERSION,
    updated_at: new Date().toISOString(),
    datasets: {
      active: ["v03"]
    },
    timeline: {
      current_year: -221,
      is_playing: false,
      playback_speed: 1,
      timeline_mode: "current_year"
    },
    map_view: {
      // 默认视角：欧亚大陆居中（经度 75° / 纬度 38°），略偏左补偿右侧信息面板宽度，
      // 使中国与中亚、中东、欧洲边缘都可见。
      center: [75, 38],
      zoom: 2.6,
      bearing: 0,
      pitch: 0
    },
    selection: {
      selected_polity_id: null
    },
    layers: {
      territories: true,
      territory_labels: true,
      modern_admin_reference: false,
      capitals: true,
      capital_migration_paths: true,
      physical_rivers: true,
      physical_lakes: true,
      physical_glaciers: true,
      geographic_lines: false,
      graticule: true,
      graticule_labels: true,
      modern_country_boundaries: true,
      cn_border_overlay: true,
      strategic_locations: true,
      strategic_location_labels: false
    },
    filters: {
      polity_types: [],
      territory_status: "all",
      min_confidence_score: 0,
      show_disputed: true,
      show_unmatched_ruler: true,
      search_keyword: ""
    },
    ui: {
      side_panel_open: true,
      // 默认关闭自动跟随：镜头由用户自己缩放/平移；演示路线启动时会临时启用。
      auto_follow_main_polity: false,
      show_historical_anecdotes: false,
      show_mythology: true,
      panel_collapsed: {
        layers_polity: false,
        layers_physical: true,
        layers_demo: true,
        legend: true
      }
    }
  };
}

// ----- IndexedDB low-level wrapper -----

let dbPromise: Promise<IDBDatabase | null> | null = null;

function openDb(): Promise<IDBDatabase | null> {
  if (typeof indexedDB === "undefined") return Promise.resolve(null);
  if (!dbPromise) {
    dbPromise = new Promise((resolve) => {
      const request = indexedDB.open(DB_NAME, 1);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(DB_STORE)) {
          db.createObjectStore(DB_STORE);
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => {
        console.warn("[state] indexedDB open failed", request.error);
        resolve(null);
      };
      request.onblocked = () => resolve(null);
    });
  }
  return dbPromise;
}

async function idbGet(): Promise<StoredAppState | null> {
  const db = await openDb();
  if (!db) return null;
  return new Promise((resolve) => {
    const tx = db.transaction(DB_STORE, "readonly");
    const store = tx.objectStore(DB_STORE);
    const request = store.get(DB_KEY);
    request.onsuccess = () => resolve((request.result as StoredAppState | undefined) ?? null);
    request.onerror = () => resolve(null);
  });
}

async function idbPut(state: StoredAppState): Promise<boolean> {
  const db = await openDb();
  if (!db) return false;
  return new Promise((resolve) => {
    const tx = db.transaction(DB_STORE, "readwrite");
    const store = tx.objectStore(DB_STORE);
    const request = store.put(state, DB_KEY);
    request.onsuccess = () => resolve(true);
    request.onerror = () => resolve(false);
  });
}

async function idbClear(): Promise<void> {
  const db = await openDb();
  if (!db) return;
  return new Promise((resolve) => {
    const tx = db.transaction(DB_STORE, "readwrite");
    tx.objectStore(DB_STORE).delete(DB_KEY);
    tx.oncomplete = () => resolve();
    tx.onerror = () => resolve();
  });
}

// ----- Migration + sanitization -----

function migrateRaw(raw: Record<string, unknown>): { migrated: Record<string, unknown>; ok: boolean } {
  let current = { ...raw };
  let version = (current.schema_version as string | undefined) ?? "1.0.0";
  const visited = new Set<string>();
  while (version !== SCHEMA_VERSION) {
    if (visited.has(version)) return { migrated: current, ok: false };
    visited.add(version);
    const step = MIGRATIONS.find((m) => m.from === version);
    if (!step) return { migrated: current, ok: false };
    current = step.migrate(current);
    current.schema_version = step.to;
    version = step.to;
  }
  return { migrated: current, ok: true };
}

function sanitizeState(
  candidate: Record<string, unknown>,
  metadata: Metadata
): { state: StoredAppState; warnings: string[] } {
  const fallback = defaultAppState(metadata);
  const warnings: string[] = [];

  const timeline = (candidate.timeline as Record<string, unknown> | undefined) ?? {};
  const mapView = (candidate.map_view as Record<string, unknown> | undefined) ?? {};
  const selection = (candidate.selection as Record<string, unknown> | undefined) ?? {};
  const layers = (candidate.layers as Record<string, unknown> | undefined) ?? {};
  const filters = (candidate.filters as Record<string, unknown> | undefined) ?? {};
  const ui = (candidate.ui as Record<string, unknown> | undefined) ?? {};
  const datasetsBlock = (candidate.datasets as Record<string, unknown> | undefined) ?? {};
  const activeDatasets = sanitizeActiveDatasets(datasetsBlock.active);

  const rawYear = Number(timeline.current_year ?? fallback.timeline.current_year);
  // 用 union(v03, vIndian) 作宽松范围：sanitize 在 StateStore 初始化时只看到 v03 metadata，
  // 但持久化的 active 可能含 vIndian（其年份范围更宽）。直接用 v03 范围会把 -3000 错误地夹回 -1046。
  const effectiveMin = Math.min(metadata.year_min, KNOWN_YEAR_MIN);
  const effectiveMax = Math.max(metadata.year_max, KNOWN_YEAR_MAX);
  const clampedYear = clampPlayableYear(
    Number.isFinite(rawYear) ? rawYear : fallback.timeline.current_year,
    effectiveMin,
    effectiveMax
  );
  if (clampedYear !== rawYear) {
    warnings.push(
      `恢复时年份 ${rawYear} 超出数据范围（${effectiveMin}–${effectiveMax}），已跳到 ${clampedYear}。`
    );
  }

  const center = mapView.center as [number, number] | undefined;
  const validCenter = Array.isArray(center) && center.length === 2 && center.every((v) => Number.isFinite(v));

  const filtersTerritory = filters.territory_status as string | undefined;
  const territoryStatus =
    filtersTerritory === "has_territory" || filtersTerritory === "missing" || filtersTerritory === "all"
      ? filtersTerritory
      : fallback.filters.territory_status;
  const polityTypes = Array.isArray(filters.polity_types)
    ? filters.polity_types.filter((value): value is string => typeof value === "string" && value.length > 0)
    : fallback.filters.polity_types;

  const state: StoredAppState = {
    schema_version: SCHEMA_VERSION,
    app_id: APP_ID,
    app_version: APP_VERSION,
    data_version: DATA_VERSION,
    updated_at: typeof candidate.updated_at === "string" ? (candidate.updated_at as string) : new Date().toISOString(),
    datasets: {
      active: activeDatasets
    },
    timeline: {
      current_year: clampedYear,
      is_playing: Boolean(timeline.is_playing ?? false),
      playback_speed: Number(timeline.playback_speed ?? fallback.timeline.playback_speed) || fallback.timeline.playback_speed,
      timeline_mode: "current_year"
    },
    map_view: validCenter
      ? {
          center: center as [number, number],
          zoom: Number(mapView.zoom ?? fallback.map_view.zoom),
          bearing: Number(mapView.bearing ?? 0),
          pitch: Number(mapView.pitch ?? 0)
        }
      : fallback.map_view,
    selection: {
      selected_polity_id:
        typeof selection.selected_polity_id === "string" ? (selection.selected_polity_id as string) : null
    },
    layers: {
      territories: Boolean(layers.territories ?? fallback.layers.territories),
      territory_labels: Boolean(layers.territory_labels ?? fallback.layers.territory_labels),
      modern_admin_reference: Boolean(layers.modern_admin_reference ?? fallback.layers.modern_admin_reference),
      capitals: Boolean(layers.capitals ?? fallback.layers.capitals),
      capital_migration_paths: Boolean(layers.capital_migration_paths ?? fallback.layers.capital_migration_paths),
      physical_rivers: Boolean(layers.physical_rivers ?? fallback.layers.physical_rivers),
      physical_lakes: Boolean(layers.physical_lakes ?? fallback.layers.physical_lakes),
      physical_glaciers: Boolean(layers.physical_glaciers ?? fallback.layers.physical_glaciers),
      geographic_lines: Boolean(layers.geographic_lines ?? fallback.layers.geographic_lines),
      graticule: Boolean(layers.graticule ?? fallback.layers.graticule),
      graticule_labels: Boolean(layers.graticule_labels ?? fallback.layers.graticule_labels),
      modern_country_boundaries: Boolean(
        layers.modern_country_boundaries ?? fallback.layers.modern_country_boundaries
      ),
      cn_border_overlay: Boolean(
        layers.cn_border_overlay ?? fallback.layers.cn_border_overlay
      ),
      strategic_locations: Boolean(layers.strategic_locations ?? fallback.layers.strategic_locations),
      strategic_location_labels: Boolean(
        layers.strategic_location_labels ?? fallback.layers.strategic_location_labels
      )
    },
    filters: {
      polity_types: polityTypes,
      territory_status: territoryStatus,
      min_confidence_score: Number(filters.min_confidence_score ?? 0),
      show_disputed: Boolean(filters.show_disputed ?? true),
      show_unmatched_ruler: Boolean(filters.show_unmatched_ruler ?? true),
      search_keyword: typeof filters.search_keyword === "string" ? filters.search_keyword : ""
    },
    ui: {
      side_panel_open:
        ui.side_panel_open == null ? fallback.ui.side_panel_open : Boolean(ui.side_panel_open),
      auto_follow_main_polity:
        ui.auto_follow_main_polity == null
          ? fallback.ui.auto_follow_main_polity
          : Boolean(ui.auto_follow_main_polity),
      show_historical_anecdotes:
        ui.show_historical_anecdotes == null
          ? fallback.ui.show_historical_anecdotes
          : Boolean(ui.show_historical_anecdotes),
      show_mythology:
        ui.show_mythology == null ? fallback.ui.show_mythology : Boolean(ui.show_mythology),
      panel_collapsed: {
        ...fallback.ui.panel_collapsed,
        ...((ui.panel_collapsed as Record<string, unknown> | undefined) ?? {})
      } as AppState["ui"]["panel_collapsed"]
    }
  };
  return { state, warnings };
}

// ----- StateStore public API -----

export class StateStore {
  private metadata: Metadata;
  private current: StoredAppState;
  private listeners = new Set<Listener>();
  private channel: BroadcastChannel | null = null;
  private saveTimer: number | null = null;
  private pending: StoredAppState | null = null;
  private knownValidPolityIds: Set<string> | null = null;

  constructor(metadata: Metadata, initial: StoredAppState) {
    this.metadata = metadata;
    this.current = initial;
    if (typeof BroadcastChannel !== "undefined") {
      try {
        this.channel = new BroadcastChannel(BROADCAST_CHANNEL);
        this.channel.addEventListener("message", (event) => this.onBroadcast(event));
      } catch (error) {
        console.warn("[state] BroadcastChannel unavailable", error);
      }
    }
    if (typeof window !== "undefined") {
      window.addEventListener("beforeunload", () => this.flush());
      window.addEventListener("pagehide", () => this.flush());
    }
  }

  static async create(metadata: Metadata): Promise<{ store: StateStore; load: StateLoadResult }> {
    const load = await loadInitialState(metadata);
    const store = new StateStore(metadata, load.state);
    if (load.source !== "indexeddb") {
      // Persist sanitized/migrated/default value to IDB so the next session reads from canonical store.
      await idbPut(load.state);
      writeIndex(load.state);
    }
    return { store, load };
  }

  getState(): StoredAppState {
    return this.current;
  }

  setValidIds(polityIds: Set<string>): { changed: boolean; warning?: string } {
    this.knownValidPolityIds = polityIds;
    const next = { ...this.current };
    let changed = false;
    if (
      next.selection.selected_polity_id &&
      !polityIds.has(next.selection.selected_polity_id)
    ) {
      next.selection = { ...next.selection, selected_polity_id: null };
      changed = true;
    }
    if (changed) {
      this.applyAndPersist(next, "self");
      return {
        changed: true,
        warning: "上次选中的政权在当前数据版本中不存在，已清除选中项。"
      };
    }
    return { changed: false };
  }

  patch(partial: Partial<StoredAppState> | ((state: StoredAppState) => StoredAppState)): StoredAppState {
    const next = typeof partial === "function" ? partial(this.current) : { ...this.current, ...partial };
    next.updated_at = new Date().toISOString();
    this.applyAndPersist(next, "self");
    return next;
  }

  replace(next: StoredAppState): StoredAppState {
    const merged: StoredAppState = { ...next, updated_at: new Date().toISOString() };
    this.applyAndPersist(merged, "self");
    return merged;
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  async reset(): Promise<StoredAppState> {
    const next = defaultAppState(this.metadata);
    await idbPut(next);
    writeIndex(next);
    this.current = next;
    this.emit("self");
    this.broadcast(next);
    return next;
  }

  export(): string {
    return JSON.stringify(this.current, null, 2);
  }

  async import(json: string): Promise<{ ok: boolean; warning?: string; state?: StoredAppState }> {
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(json) as Record<string, unknown>;
    } catch (error) {
      return { ok: false, warning: `JSON 解析失败：${(error as Error).message}` };
    }
    if (parsed.app_id && parsed.app_id !== APP_ID) {
      return { ok: false, warning: `app_id 不匹配（期望 ${APP_ID}，得到 ${parsed.app_id}）。` };
    }
    if (parsed.data_version && parsed.data_version !== DATA_VERSION) {
      return {
        ok: false,
        warning: `data_version 不匹配（期望 ${DATA_VERSION}，得到 ${parsed.data_version}）。`
      };
    }
    const { migrated, ok } = migrateRaw(parsed);
    if (!ok) {
      return { ok: false, warning: `无法迁移 schema_version=${parsed.schema_version}。` };
    }
    const { state, warnings } = sanitizeState(migrated, this.metadata);
    const next = { ...state, updated_at: new Date().toISOString() };
    await idbPut(next);
    writeIndex(next);
    this.current = next;
    this.emit("self");
    this.broadcast(next);
    return { ok: true, state: next, warning: warnings.length ? warnings.join(" ") : undefined };
  }

  flush(): void {
    if (this.saveTimer != null) {
      window.clearTimeout(this.saveTimer);
      this.saveTimer = null;
    }
    if (this.pending) {
      void idbPut(this.pending);
      writeIndex(this.pending);
      this.pending = null;
    }
  }

  destroy(): void {
    this.flush();
    this.channel?.close();
    this.channel = null;
    this.listeners.clear();
  }

  private applyAndPersist(next: StoredAppState, source: "self" | "broadcast"): void {
    this.current = next;
    this.pending = next;
    if (source === "self") {
      this.scheduleSave();
      this.broadcast(next);
    }
    this.emit(source);
  }

  private scheduleSave(): void {
    if (this.saveTimer != null) window.clearTimeout(this.saveTimer);
    this.saveTimer = window.setTimeout(() => {
      this.saveTimer = null;
      if (this.pending) {
        void idbPut(this.pending);
        writeIndex(this.pending);
        this.pending = null;
      }
    }, SAVE_DEBOUNCE_MS);
  }

  private emit(source: "self" | "broadcast"): void {
    this.listeners.forEach((listener) => listener(this.current, source));
  }

  private broadcast(state: StoredAppState): void {
    if (!this.channel) return;
    try {
      this.channel.postMessage({ type: "state", state });
    } catch (error) {
      console.warn("[state] broadcast failed", error);
    }
  }

  private onBroadcast(event: MessageEvent<{ type: string; state: StoredAppState }>): void {
    if (event.data?.type !== "state" || !event.data.state) return;
    const incoming = event.data.state;
    // Last-write-wins by updated_at.
    if (
      typeof incoming.updated_at === "string" &&
      typeof this.current.updated_at === "string" &&
      incoming.updated_at <= this.current.updated_at
    ) {
      return;
    }
    this.applyAndPersist(incoming, "broadcast");
  }
}

// ----- Initial load logic -----

async function loadInitialState(metadata: Metadata): Promise<StateLoadResult> {
  // Attempt IDB first.
  const idb = await idbGet().catch(() => null);
  if (idb && idb.schema_version) {
    return finalizeLoad(metadata, idb as unknown as Record<string, unknown>, "indexeddb");
  }
  // Fall back to legacy localStorage entry from earlier versions.
  if (typeof localStorage !== "undefined") {
    const legacyRaw = localStorage.getItem(LEGACY_LS_KEY);
    if (legacyRaw) {
      try {
        const parsed = JSON.parse(legacyRaw) as Record<string, unknown>;
        const result = finalizeLoad(metadata, parsed, "localstorage");
        // remove legacy entry to prevent re-migration noise
        localStorage.removeItem(LEGACY_LS_KEY);
        return result;
      } catch (error) {
        console.warn("[state] legacy localStorage corrupted; ignoring", error);
      }
    }
  }
  return {
    state: defaultAppState(metadata),
    source: "default"
  };
}

function finalizeLoad(
  metadata: Metadata,
  raw: Record<string, unknown>,
  baseSource: "indexeddb" | "localstorage"
): StateLoadResult {
  try {
    const { migrated, ok } = migrateRaw(raw);
    if (!ok) {
      return {
        state: defaultAppState(metadata),
        warning: "本地状态 schema 不兼容，已重置为默认状态。",
        source: "corrupted"
      };
    }
    const { state, warnings } = sanitizeState(migrated, metadata);
    const source: StateLoadResult["source"] =
      raw.schema_version === SCHEMA_VERSION ? baseSource : "migrated";
    return {
      state,
      warning: warnings.length ? warnings.join(" ") : undefined,
      source
    };
  } catch (error) {
    console.warn("[state] corrupted state; resetting", error);
    return {
      state: defaultAppState(metadata),
      warning: "本地状态损坏，已重置为默认状态。",
      source: "corrupted"
    };
  }
}

function writeIndex(state: StoredAppState): void {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(
      LS_INDEX_KEY,
      JSON.stringify({
        updated_at: state.updated_at,
        schema_version: state.schema_version,
        app_version: state.app_version,
        data_version: state.data_version
      })
    );
  } catch (error) {
    console.warn("[state] localStorage index write failed", error);
  }
}

// ----- Convenience helpers preserved for incremental App migration -----

export function exportAppState(state: StoredAppState): void {
  const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  link.download = `history-map-state-${state.data_version}-${stamp}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

// Backward-compat shim — old callers still use loadAppState/saveAppState/resetAppState.
// These now defer to the StateStore-managed copy where possible. The App is being migrated.

let inMemoryState: StoredAppState | null = null;

export function loadAppState(metadata: Metadata): StoredAppState {
  if (inMemoryState) return inMemoryState;
  inMemoryState = defaultAppState(metadata);
  return inMemoryState;
}

export function saveAppState(state: StoredAppState): void {
  inMemoryState = state;
}

export function resetAppState(metadata: Metadata): StoredAppState {
  inMemoryState = defaultAppState(metadata);
  return inMemoryState;
}

export { APP_ID, APP_VERSION, SCHEMA_VERSION, DATA_VERSION };

export type { StoredAppState as AppStateWithMeta };
