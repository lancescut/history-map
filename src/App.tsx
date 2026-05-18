import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import maplibregl, { GeoJSONSource, Marker } from "maplibre-gl";
import {
  Layers,
  LocateFixed,
  MapPin,
  Settings
} from "lucide-react";
import {
  clampPlayableYear,
  getAliasIndex,
  getCapitals,
  getHistoricalAnecdotes,
  getHistoricalContexts,
  getHistoricalEvents,
  getIssues,
  getMetadata,
  getModernAdminUnits,
  getStoryPresets,
  getTerritories,
  getValidation,
  getYearData,
  nextYear,
  normalizeSearch,
  previousYear,
  yearLabel
} from "./data";
import { StateStore, defaultAppState, exportAppState } from "./state";
import type { StoredAppState } from "./state";
import { CollapsibleGroup } from "./components/CollapsibleGroup";
import { TimelineTicks } from "./components/TimelineTicks";
import { QualityPanel } from "./components/QualityPanel";
import { StoryPlayer } from "./components/StoryPlayer";
import { OverlapPicker, type OverlapPickerState } from "./components/OverlapPicker";
import { MapHoverTooltip, type MapHoverState } from "./components/MapHoverTooltip";
import { MapContextOverlay } from "./components/MapContextOverlay";
import { MapEventOverlay, type MapEventPulseItem } from "./components/MapEventOverlay";
import { PolityLegend } from "./components/PolityLegend";
import { OnboardingTour } from "./components/OnboardingTour";
import { BottomBar } from "./components/BottomBar";
import { SettingsControls } from "./components/SettingsControls";
import { Topbar } from "./components/Topbar";
import { SidePanel } from "./components/SidePanel";
import { historicalEventPlaybackKey } from "./event-meta";
import {
  BASEMAP_STYLE,
  applyPhysicalBasemapVisibility,
  emptyFeatureCollection,
  emptyLabelCollection,
  emptyTerritoryCollection,
  exportMapSnapshot,
  fitTerritoryBounds,
  isPolityNomadic,
  macroPeriodColor,
  mainPolityFeatures,
  migrationFeatureCollection,
  territoryBounds,
  territoryCollections
} from "./map-helpers";
import type {
  AliasIndex,
  AppState,
  CapitalsData,
  HistoricalAnecdotesData,
  HistoricalContext,
  HistoricalContextsData,
  HistoricalEvent,
  HistoricalEventsData,
  IssuesData,
  Metadata,
  PolityIssue,
  SearchEntry,
  StoryPreset,
  StoryPresetsData,
  TerritoryFeatureProperties,
  ValidationData,
  YearData,
  YearPolity
} from "./types";

const PLAYBACK_SPEEDS = [0.5, 1, 2, 5, 10];

function App() {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const currentTerritoriesRef = useRef<GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties>>(
    emptyTerritoryCollection()
  );
  // 镜头跟随：仅在演示路线剧本切幕时显式触发 reframe；首次加载、用户跳年、播放循环
  // 一律不动镜头，完全由用户自己缩放/平移。
  const needsRefitRef = useRef(false);
  const suppressMapMoveStateRef = useRef(false);
  const skipAutoFollowForYearRef = useRef<number | null>(null);
  const yearDataRef = useRef<YearData | null>(null);

  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [capitals, setCapitals] = useState<CapitalsData | null>(null);
  const [aliasIndex, setAliasIndex] = useState<AliasIndex | null>(null);
  const [territoryGeoJSON, setTerritoryGeoJSON] =
    useState<GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties> | null>(null);
  const [modernAdminUnits, setModernAdminUnits] = useState<GeoJSON.FeatureCollection | null>(null);
  const [yearData, setYearData] = useState<YearData | null>(null);
  const [appState, setReactAppState] = useState<StoredAppState>(() => defaultAppState());
  const storeRef = useRef<StateStore | null>(null);
  const [stateNotice, setStateNotice] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [overlapPicker, setOverlapPicker] = useState<OverlapPickerState | null>(null);
  const [hoverPolity, setHoverPolity] = useState<MapHoverState | null>(null);
  const [issuesData, setIssuesData] = useState<IssuesData | null>(null);
  const [validationData, setValidationData] = useState<ValidationData | null>(null);
  const [eventsData, setEventsData] = useState<HistoricalEventsData | null>(null);
  const [anecdotesData, setAnecdotesData] = useState<HistoricalAnecdotesData | null>(null);
  const [contextsData, setContextsData] = useState<HistoricalContextsData | null>(null);
  // 事件流堆栈：用户播放/跳年时把当年事件 push 到栈顶（cap 30 条防极端累积）
  const [eventStack, setEventStack] = useState<HistoricalEvent[]>([]);
  const [activeMapEvents, setActiveMapEvents] = useState<MapEventPulseItem[]>([]);
  const seenEventKeysRef = useRef<Set<string>>(new Set());
  const mapEventTimersRef = useRef<number[]>([]);
  // 标记本次 push 的新事件 key 集合，用于 CSS 淡入动画（所有刚 push 的事件而不仅栈顶）
  const freshEventKeysRef = useRef<Set<string>>(new Set());
  // 按拍发事件队列：当前年仍未发出的事件；播放 tick 一次取一个，发完才推年份
  const playQueueRef = useRef<HistoricalEvent[]>([]);
  const playQueueYearRef = useRef<number | null>(null);
  const [qualityPanelOpen, setQualityPanelOpen] = useState(false);
  const [storyPresets, setStoryPresets] = useState<StoryPresetsData | null>(null);
  const [activeStory, setActiveStory] = useState<StoryPreset | null>(null);
  const [storyStepIndex, setStoryStepIndex] = useState(0);
  const [storyAutoAdvance, setStoryAutoAdvance] = useState(true);
  const [storyPickerOpen, setStoryPickerOpen] = useState(false);
  const [settingsCollapsed, setSettingsCollapsed] = useState(true);
  void settingsCollapsed;
  void setSettingsCollapsed;
  // layer-panel hover-折叠模式：默认折叠为细条，hover 展开 4 组 header，
  // 点击某组展开 body；同时只能开一组；离开鼠标自动收起。null=无组展开。
  const [openLayerGroup, setOpenLayerGroup] = useState<string | null>(null);
  // 色盲对比模式：独立 localStorage key，不动 AppState schema。
  const [colorblindMode, setColorblindMode] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    try {
      return window.localStorage.getItem("history_map_colorblind_v1") === "1";
    } catch {
      return false;
    }
  });
  useEffect(() => {
    try {
      window.localStorage.setItem("history_map_colorblind_v1", colorblindMode ? "1" : "0");
    } catch {
      // 隐私模式或 localStorage 不可用时静默
    }
  }, [colorblindMode]);
  const importFileRef = useRef<HTMLInputElement | null>(null);

  type AppStateUpdater = Partial<StoredAppState> | ((state: StoredAppState) => StoredAppState);
  const setAppState = useCallback((updater: AppStateUpdater) => {
    const store = storeRef.current;
    if (store) {
      store.patch(updater as Parameters<StateStore["patch"]>[0]);
      return;
    }
    setReactAppState((current) => {
      const next = typeof updater === "function" ? updater(current) : { ...current, ...updater };
      return next;
    });
  }, []);

  const sidePanelOpen = appState.ui.side_panel_open;
  const searchText = appState.filters.search_keyword;
  const setSearchText = useCallback(
    (next: string) => {
      setAppState((state) => ({
        ...state,
        filters: { ...state.filters, search_keyword: next }
      }));
    },
    [setAppState]
  );
  const setSidePanelOpen = useCallback(
    (next: boolean | ((prev: boolean) => boolean)) => {
      setAppState((state) => ({
        ...state,
        ui: {
          ...state.ui,
          side_panel_open: typeof next === "function" ? next(state.ui.side_panel_open) : next
        }
      }));
    },
    [setAppState]
  );

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      getMetadata(),
      getCapitals(),
      getAliasIndex(),
      getTerritories(),
      getModernAdminUnits(),
      getIssues(),
      getValidation(),
      getHistoricalEvents(),
      getHistoricalContexts(),
      getHistoricalAnecdotes().catch(() => null),
      getStoryPresets().catch(() => null)
    ])
      .then(
        ([
          loadedMetadata,
          loadedCapitals,
          loadedAliasIndex,
          loadedTerritories,
          loadedModernAdminUnits,
          loadedIssues,
          loadedValidation,
          loadedEvents,
          loadedContexts,
          loadedAnecdotes,
          loadedStoryPresets
        ]) => {
          if (cancelled) return;
          setMetadata(loadedMetadata);
          setCapitals(loadedCapitals);
          setAliasIndex(loadedAliasIndex);
          setTerritoryGeoJSON(loadedTerritories);
          setModernAdminUnits(loadedModernAdminUnits);
          setIssuesData(loadedIssues);
          setValidationData(loadedValidation);
          setEventsData(loadedEvents);
          setContextsData(loadedContexts);
          if (loadedAnecdotes) setAnecdotesData(loadedAnecdotes);
          if (loadedStoryPresets) setStoryPresets(loadedStoryPresets);
          void StateStore.create(loadedMetadata).then(({ store, load }) => {
            if (cancelled) {
              store.destroy();
              return;
            }
            storeRef.current = store;
            if (load.source !== "default") {
              skipAutoFollowForYearRef.current = load.state.timeline.current_year;
            }
            setReactAppState(load.state);
            if (load.warning) setStateNotice(load.warning);
            store.subscribe((next) => setReactAppState(next));
          });
        }
      )
      .catch((error: Error) => setLoadError(error.message));
    return () => {
      cancelled = true;
      storeRef.current?.destroy();
      storeRef.current = null;
    };
  }, []);

  const issuesByPolity = useMemo(() => {
    const index = new Map<string, PolityIssue[]>();
    issuesData?.issues.forEach((issue) => {
      if (!issue.polity_id) return;
      const list = index.get(issue.polity_id) ?? [];
      list.push(issue);
      index.set(issue.polity_id, list);
    });
    return index;
  }, [issuesData]);

  const partialBoundaryPolities = useMemo(
    () =>
      issuesData?.issues.filter((issue) => issue.issue_type === "partial_boundary") ?? [],
    [issuesData]
  );

  const validationSummary = useMemo(() => {
    const checks = validationData?.checks ?? [];
    const pass = checks.filter((check) => check.status === "PASS").length;
    const warn = checks.filter((check) => check.status === "WARN").length;
    const fail = checks.filter((check) => check.status === "FAIL").length;
    return { total: checks.length, pass, warn, fail };
  }, [validationData]);

  const currentPlaybackYear = appState.timeline.current_year;
  const yearDataMatchesPlaybackYear = yearData?.year === currentPlaybackYear;

  const currentYearEvents = useMemo(() => {
    const events =
      eventsData?.events.filter((event) => event.year === currentPlaybackYear) ??
      (yearDataMatchesPlaybackYear ? yearData?.historical_events ?? [] : []);
    const anecdotes =
      appState.ui.show_historical_anecdotes
        ? anecdotesData?.anecdotes.filter((event) => event.year === currentPlaybackYear) ??
          (yearDataMatchesPlaybackYear ? yearData?.historical_anecdotes ?? [] : [])
        : [];
    return [...events, ...anecdotes].sort(
      (a, b) =>
        a.display_priority - b.display_priority ||
        b.importance_level - a.importance_level ||
        a.sort_order - b.sort_order ||
        a.event_id.localeCompare(b.event_id)
    );
  }, [
    anecdotesData,
    appState.ui.show_historical_anecdotes,
    currentPlaybackYear,
    eventsData,
    yearData,
    yearDataMatchesPlaybackYear
  ]);

  const currentYearContexts = useMemo(() => {
    const source =
      contextsData?.contexts.filter(
        (context) =>
          (context.start_year <= currentPlaybackYear && currentPlaybackYear <= context.end_year) ||
          context.current_year === currentPlaybackYear
      ) ?? (yearDataMatchesPlaybackYear ? yearData?.historical_contexts ?? [] : []);
    return source
      .map((context) => {
        const span = context.end_year - context.start_year;
        const progressRatio =
          span > 0
            ? (currentPlaybackYear - context.start_year) / span
            : 1;
        return {
          ...context,
          year: currentPlaybackYear,
          current_year: currentPlaybackYear,
          year_label: yearLabel(currentPlaybackYear),
          progress_ratio: Math.max(0, Math.min(1, progressRatio))
        };
      })
      .sort(
        (a, b) =>
          a.display_priority - b.display_priority ||
          a.sort_order - b.sort_order ||
          a.context_id.localeCompare(b.context_id)
      )
      .slice(0, 3);
  }, [contextsData, currentPlaybackYear, yearData, yearDataMatchesPlaybackYear]);

  const currentYearFeaturedEvents = useMemo(() => {
    const featured = currentYearEvents.slice(0, 5);
    if (!appState.ui.show_historical_anecdotes) return featured;
    if (featured.some((event) => event.is_anecdote || event.item_kind === "anecdote")) return featured;
    const firstAnecdote = currentYearEvents.find(
      (event) => event.is_anecdote || event.item_kind === "anecdote"
    );
    if (!firstAnecdote) return featured;
    return [...featured.slice(0, 4), firstAnecdote];
  }, [appState.ui.show_historical_anecdotes, currentYearEvents]);

  const timelineEventsData = useMemo<HistoricalEventsData | null>(() => {
    if (!eventsData) return null;
    if (!appState.ui.show_historical_anecdotes || !anecdotesData?.anecdotes.length) return eventsData;
    const mergedEvents = [...eventsData.events, ...anecdotesData.anecdotes].sort(
      (a, b) =>
        a.year - b.year ||
        a.display_priority - b.display_priority ||
        b.importance_level - a.importance_level ||
        a.sort_order - b.sort_order ||
        historicalEventPlaybackKey(a).localeCompare(historicalEventPlaybackKey(b))
    );
    return {
      ...eventsData,
      event_count: mergedEvents.length,
      marker_count: mergedEvents.length,
      covered_year_count: new Set(mergedEvents.map((event) => event.year)).size,
      events: mergedEvents
    };
  }, [anecdotesData, appState.ui.show_historical_anecdotes, eventsData]);

  const eventCoordinates = useCallback((event: HistoricalEvent): [number, number] | null => {
    const longitude = event.location?.longitude ?? event.longitude;
    const latitude = event.location?.latitude ?? event.latitude;
    if (typeof longitude !== "number" || typeof latitude !== "number") return null;
    if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return null;
    return [longitude, latitude];
  }, []);

  const visibleMapContexts = useMemo<HistoricalContext[]>(
    () => (currentYearEvents.length ? [] : currentYearContexts.slice(0, 1)),
    [currentYearContexts, currentYearEvents.length]
  );

  const clearMapEventTimers = useCallback(() => {
    mapEventTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    mapEventTimersRef.current = [];
  }, []);

  useEffect(() => {
    if (appState.ui.show_historical_anecdotes) return;
    setEventStack((prev) => prev.filter((event) => !(event.is_anecdote || event.item_kind === "anecdote")));
    setActiveMapEvents((prev) => prev.filter((item) => !(item.event.is_anecdote || item.event.item_kind === "anecdote")));
  }, [appState.ui.show_historical_anecdotes]);

  const pushMapEvent = useCallback((event: HistoricalEvent) => {
    if (!eventCoordinates(event)) return;
    const instanceId = `${historicalEventPlaybackKey(event)}-${event.year}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    // 收集被本次推送挤出（overflow）需要 exiting 的旧实例 id —— 给每个挤出项各自调度
    // 700ms 后移除，覆盖 CSS 520ms 淡出 transition；不再用全局 cleanupTimer 避免误删
    // 其它路径（6s expire / 跨年 force-exit）正在淡出的卡片。
    const overflowExitIds: string[] = [];
    setActiveMapEvents((prev) => {
      // 关键：保留 prev 中已经 exiting 的卡片，让它们各自的 700ms removeTimer
      // 完整播完淡出 transition，不被新 push 顺手清掉。
      const prevExiting = prev.filter((item) => item.status === "exiting");
      const stillVisible = prev.filter((item) => item.status !== "exiting");
      const nextItem: MapEventPulseItem = { instanceId, event, status: "entering" };
      const combined = [...stillVisible, nextItem];
      // cap 1：任何时刻地图上只保留 1 张主显卡，其余推为 exiting。
      // 配合「按拍发事件」：一张换一张，地图不会出现卡片堆叠。
      const overflow = Math.max(0, combined.length - 1);
      const newExiting = combined.slice(0, overflow).map((item) => {
        overflowExitIds.push(item.instanceId);
        return { ...item, status: "exiting" as const };
      });
      const kept = combined.slice(overflow);
      return [...prevExiting, ...newExiting, ...kept];
    });
    overflowExitIds.forEach((id) => {
      const t = window.setTimeout(() => {
        setActiveMapEvents((curr) => curr.filter((item) => item.instanceId !== id));
      }, 700);
      mapEventTimersRef.current.push(t);
    });
    const activateTimer = window.setTimeout(() => {
      setActiveMapEvents((prev) =>
        prev.map((item) => (item.instanceId === instanceId ? { ...item, status: "active" } : item))
      );
    }, 180);
    // 自动 6 秒后过期为 exiting；之后 700ms 完全移除（独立 timer 保证 520ms 淡出完整播放）
    const expireTimer = window.setTimeout(() => {
      setActiveMapEvents((prev) =>
        prev.map((item) =>
          item.instanceId === instanceId && item.status !== "exiting"
            ? { ...item, status: "exiting" as const }
            : item
        )
      );
      const removeTimer = window.setTimeout(() => {
        setActiveMapEvents((prev) => prev.filter((item) => item.instanceId !== instanceId));
      }, 700);
      mapEventTimersRef.current.push(removeTimer);
    }, 6000);
    mapEventTimersRef.current.push(activateTimer, expireTimer);
  }, [eventCoordinates]);

  useEffect(() => {
    return () => clearMapEventTimers();
  }, [clearMapEventTimers]);

  // 当前年份显著跳变（>25 年）时，强制让"远期事件卡片"淡出，避免不同朝代的卡片
  // 残留在地图上误导用户。配合 pushMapEvent 内 6s 自动 timer 形成双保险。
  useEffect(() => {
    setActiveMapEvents((prev) => {
      let changed = false;
      const next = prev.map((item) => {
        if (item.status === "exiting") return item;
        if (Math.abs(appState.timeline.current_year - item.event.year) > 25) {
          changed = true;
          return { ...item, status: "exiting" as const };
        }
        return item;
      });
      if (!changed) return prev;
      const removeTimer = window.setTimeout(() => {
        setActiveMapEvents((curr) => curr.filter((item) => item.status !== "exiting"));
      }, 700);
      mapEventTimersRef.current.push(removeTimer);
      return next;
    });
  }, [appState.timeline.current_year]);

  // ===== 按拍发事件 =====
  //
  // 播放模式：同年多事件不能一次性涌出（会互相挡），改为「每个播放 tick 发一个」节奏。
  // - playQueueRef: 当前年待发的剩余事件
  // - playQueueYearRef: 队列归属的年份（防年份变化时旧队列穿透）
  // 年份变化时年份 effect 立即发首个事件，把其余装进队列；后续 tick 从队列里取。
  // 手动跳年（非播放）：保留 120ms 错峰批量展开，避免逐拍长等。

  const emitMapEvent = useCallback(
    (event: HistoricalEvent) => {
      const key = historicalEventPlaybackKey(event);
      if (seenEventKeysRef.current.has(key)) return;
      seenEventKeysRef.current.add(key);
      freshEventKeysRef.current.add(key);
      const freshTimer = window.setTimeout(() => {
        freshEventKeysRef.current.delete(key);
      }, 600);
      mapEventTimersRef.current.push(freshTimer);
      setEventStack((prev) => [event, ...prev].slice(0, 30));
      pushMapEvent(event);
    },
    [pushMapEvent]
  );

  useEffect(() => {
    const events = currentYearFeaturedEvents;
    const year = currentPlaybackYear;
    if (!events.length) {
      playQueueRef.current = [];
      playQueueYearRef.current = year;
      return;
    }
    const fresh = events.filter(
      (event) => !seenEventKeysRef.current.has(historicalEventPlaybackKey(event))
    );
    if (!fresh.length) {
      playQueueRef.current = [];
      playQueueYearRef.current = year;
      return;
    }
    if (appState.timeline.is_playing) {
      // 播放：年份切到 T 立刻发首个事件，余下按 tick 节奏发
      emitMapEvent(fresh[0]);
      playQueueRef.current = fresh.slice(1);
      playQueueYearRef.current = year;
    } else {
      // 手动跳年：全部 120ms 错峰展开，不阻塞用户操作
      fresh.forEach((event, index) => {
        const timer = window.setTimeout(() => emitMapEvent(event), index * 120);
        mapEventTimersRef.current.push(timer);
      });
      playQueueRef.current = [];
      playQueueYearRef.current = year;
    }
  }, [currentPlaybackYear, currentYearFeaturedEvents, appState.timeline.is_playing, emitMapEvent]);

  useEffect(() => {
    if (!metadata) return;
    let cancelled = false;
    const currentYear = appState.timeline.current_year;
    if (!Number.isFinite(currentYear) || currentYear === 0) {
      // 防御：状态 sanitize 漏掉的极端值。把年份纠回安全值并停止播放。
      setAppState((state) => ({
        ...state,
        timeline: { ...state.timeline, current_year: -221, is_playing: false }
      }));
      return;
    }
    getYearData(currentYear)
      .then((data) => {
        if (!cancelled) setYearData(data);
        if (cancelled) return;
        // 预缓存相邻 ±2 年，避免播放时年度切换抖动（MRD §10.1 第 4 点）
        const direction = appState.timeline.is_playing ? 1 : 0;
        const offsets = direction === 1 ? [1, 2, 3, -1] : [-2, -1, 1, 2];
        offsets.forEach((offset) => {
          const adjacent = currentYear + offset;
          if (!Number.isFinite(adjacent)) return;
          if (adjacent === 0) return;
          if (adjacent < metadata.year_min || adjacent > metadata.year_max) return;
          void getYearData(adjacent).catch(() => undefined);
        });
      })
      .catch((error: Error) => {
        if (cancelled) return;
        console.warn("[year-data] fetch failed", error);
        setStateNotice(
          `${currentYear} 年数据加载失败：${error.message}。已停止播放并保持当前显示。`
        );
        // 停止播放，避免连续失败刷屏
        setAppState((state) => ({
          ...state,
          timeline: { ...state.timeline, is_playing: false }
        }));
      });
    return () => {
      cancelled = true;
    };
  }, [appState.timeline.current_year, appState.timeline.is_playing, metadata, setAppState]);

  useEffect(() => {
    yearDataRef.current = yearData;
  }, [yearData]);

  useEffect(() => {
    setOverlapPicker(null);
  }, [yearData?.year]);

  useEffect(() => {
    const store = storeRef.current;
    if (!store || !capitals || !yearData) return;
    const polityIds = new Set<string>();
    yearData.polities.forEach((p) => polityIds.add(p.polity_id));
    Object.keys(capitals.by_polity).forEach((id) => polityIds.add(id));
    const result = store.setValidIds(polityIds);
    if (result.warning) setStateNotice(result.warning);
  }, [capitals, yearData]);

  useEffect(() => {
    if (!metadata || !appState.timeline.is_playing) return;
    // 基准节拍 2000ms（1x 速度），整体播放比之前慢一半 —— 给用户充分时间看清每个事件
    const delay = Math.max(160, 2000 / appState.timeline.playback_speed);
    const timer = window.setInterval(() => {
      // 用 setAppState 拿最新 current_year；先决定本拍是「发事件」还是「推年份」
      setAppState((state) => {
        const yearNow = state.timeline.current_year;
        // 若 playQueue 归属的年份与当前年份不一致（如用户手动跳年），清空避免穿透
        if (playQueueYearRef.current !== yearNow) {
          playQueueRef.current = [];
          playQueueYearRef.current = yearNow;
        }
        if (playQueueRef.current.length > 0) {
          // 本拍发一个事件（不推年份）
          const nextEvent = playQueueRef.current.shift()!;
          // setState 内副作用容易引争议，但这里 emitMapEvent 的 setState 都用更新器，
          // React 18 批处理可正确合并；放到 microtask 里再保险一点
          queueMicrotask(() => emitMapEvent(nextEvent));
          return state;
        }
        // 队列空 → 推下一年；年份变化会触发 year-change effect 装填新队列
        const advanced = nextYear(yearNow, metadata.year_max);
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
  }, [appState.timeline.is_playing, appState.timeline.playback_speed, metadata, setAppState, emitMapEvent]);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: BASEMAP_STYLE,
      center: appState.map_view.center,
      zoom: appState.map_view.zoom,
      bearing: appState.map_view.bearing,
      pitch: appState.map_view.pitch,
      attributionControl: { compact: true, customAttribution: "Natural Earth · geoBoundaries" },
      // 允许截图导出（MRD §5.1 第 4 条预留能力）
      canvasContextAttributes: { preserveDrawingBuffer: true }
    });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");
    map.on("load", () => {
      applyPhysicalBasemapVisibility(map, appState.layers);
      if (!map.getSource("territory-previous")) {
        map.addSource("china-admin-base", { type: "geojson", data: emptyFeatureCollection() });
        map.addSource("modern-admin-reference", { type: "geojson", data: emptyFeatureCollection() });
        map.addSource("territory-previous", { type: "geojson", data: emptyTerritoryCollection() });
        map.addSource("territory-current", { type: "geojson", data: emptyTerritoryCollection() });
        map.addSource("territory-labels", { type: "geojson", data: emptyLabelCollection() });
        map.addSource("territory-overlap-badges", { type: "geojson", data: emptyLabelCollection() });
        // 中国现代行政区基底已由物理底图陆地填色覆盖；保留 source 以便 updateMapLayers 写入参考线。
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
            // 1.0 不透明：彻底消除多层 alpha 叠加产生的「重叠混合色」，确保图例 swatch 与
            // 地图实际颜色一一对应（z-order 已让小政权在上，重叠区显示小政权色）。
            // 游牧政权保留 0.55 半透明暗示「活动范围而非疆域」。
            "fill-opacity": ["case", ["get", "is_nomadic"], 0.55, 1],
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
          id: "territory-overlap-badge-circle",
          type: "circle",
          source: "territory-overlap-badges",
          paint: {
            "circle-radius": ["case", ["get", "selected"], 12, 10],
            "circle-color": ["case", ["get", "selected"], "#fff4c2", "rgba(18,24,32,0.82)"],
            "circle-stroke-color": ["case", ["get", "selected"], "#1f2937", "rgba(255,255,255,0.82)"],
            "circle-stroke-width": 1.2,
            "circle-opacity": 0.92
          }
        });
        map.addLayer({
          id: "territory-overlap-badges",
          type: "symbol",
          source: "territory-overlap-badges",
          layout: {
            "text-field": ["to-string", ["get", "overlap_count"]],
            "text-size": 11,
            "text-font": ["Noto Sans Bold"],
            "text-allow-overlap": true,
            "text-ignore-placement": true
          },
          paint: {
            "text-color": ["case", ["get", "selected"], "#1f2937", "#fff7df"],
            "text-halo-color": "rgba(20,20,20,0.4)",
            "text-halo-width": 0.6
          }
        });
        map.addLayer({
          id: "territory-labels",
          type: "symbol",
          source: "territory-labels",
          layout: {
            "text-field": ["coalesce", ["get", "polity_display_name"], ["get", "polity_name"]],
            // 字号随 zoom 与 size_rank 三档：大国 / 中国 / 小国，确保密集年份不爆字号
            "text-size": [
              "interpolate",
              ["linear"],
              ["zoom"],
              1.5,
              [
                "case",
                [">", ["get", "size_rank"], 1000000], 10,
                [">", ["get", "size_rank"], 100000], 8.5,
                7.5
              ],
              3,
              [
                "case",
                [">", ["get", "size_rank"], 1000000], 13,
                [">", ["get", "size_rank"], 100000], 11,
                9.5
              ],
              5,
              [
                "case",
                [">", ["get", "size_rank"], 1000000], 17,
                [">", ["get", "size_rank"], 100000], 14,
                11.5
              ],
              7,
              [
                "case",
                [">", ["get", "size_rank"], 1000000], 21,
                [">", ["get", "size_rank"], 100000], 17,
                13.5
              ]
            ],
            "text-font": ["Noto Sans Regular"],
            // 全政权强制可见：collision 不再隐藏，所有政权名都画出来
            "text-allow-overlap": true,
            "text-ignore-placement": true,
            // 大政权先放、小政权（值越大越后放）→ 配合 z-order，小政权可叠在大政权之上
            "symbol-sort-key": [
              "case",
              ["==", ["get", "selected"], true],
              -1e9,
              ["-", 0, ["coalesce", ["get", "size_rank"], 0]]
            ]
          },
          paint: {
            // territory fill 改 1.0 不透明后，背景多是亮色 → 文字改深灰 + 白 halo 提高可读性
            "text-color": "#1f2937",
            "text-halo-color": "#ffffff",
            "text-halo-width": 1.6,
            "text-halo-blur": 0.5,
            // 所有政权 opacity 1（去除 size_rank step LOD），不再隐藏小国
            "text-opacity": 1
          }
        });
        // CN 国界线层（BASEMAP_STYLE 里 z-order 较低，被 territory-fill 遮盖）
        // 提到 territory-labels 之下：政权疆域填色之上、政权名标签之下
        if (map.getLayer("cn-borders-line") && map.getLayer("territory-labels")) {
          map.moveLayer("cn-borders-line", "territory-labels");
        }
        map.on("click", "territory-fill-current", (event) => {
          const currentYearData = yearDataRef.current;
          if (!currentYearData) return;
          const rendered = map.queryRenderedFeatures(event.point, { layers: ["territory-fill-current"] });
          const polityById = new Map(currentYearData.polities.map((item) => [item.polity_id, item]));
          const seen = new Set<string>();
          const candidates = rendered
            .map((feature) => feature.properties?.polity_id as string | undefined)
            .filter((polityId): polityId is string => Boolean(polityId))
            .filter((polityId) => {
              if (seen.has(polityId)) return false;
              seen.add(polityId);
              return true;
            })
            .map((polityId) => polityById.get(polityId))
            .filter((polity): polity is YearPolity => Boolean(polity))
            .sort((a, b) => (a.territory.approx_area_km2 ?? Number.MAX_SAFE_INTEGER) - (b.territory.approx_area_km2 ?? Number.MAX_SAFE_INTEGER));
          if (candidates.length > 1) {
            setOverlapPicker({ x: event.point.x, y: event.point.y, candidates });
            setAppState((state) => ({
              ...state,
              timeline: { ...state.timeline, is_playing: false }
            }));
            return;
          }
          const polity = candidates[0];
          if (!polity) return;
          setOverlapPicker(null);
          setAppState((state) => ({
            ...state,
            timeline: { ...state.timeline, is_playing: false },
            selection: { selected_polity_id: polity.polity_id }
          }));
        });
        map.on("mouseenter", "territory-fill-current", () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mousemove", "territory-fill-current", (event) => {
          const currentYearData = yearDataRef.current;
          if (!currentYearData) return;
          const features = event.features ?? [];
          const polityId = features[0]?.properties?.polity_id as string | undefined;
          if (!polityId) return;
          const polity = currentYearData.polities.find((p) => p.polity_id === polityId);
          if (!polity) return;
          setHoverPolity({ polity, x: event.point.x, y: event.point.y });
        });
        map.on("mouseleave", "territory-fill-current", () => {
          map.getCanvas().style.cursor = "";
          setHoverPolity(null);
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
      if (suppressMapMoveStateRef.current) return;
      const center = map.getCenter();
      const nextView = {
        center: [center.lng, center.lat] as [number, number],
        zoom: map.getZoom(),
        bearing: map.getBearing(),
        pitch: map.getPitch()
      };
      setAppState((state) => {
        const sameView =
          Math.abs(state.map_view.center[0] - nextView.center[0]) < 0.000001 &&
          Math.abs(state.map_view.center[1] - nextView.center[1]) < 0.000001 &&
          Math.abs(state.map_view.zoom - nextView.zoom) < 0.000001 &&
          Math.abs(state.map_view.bearing - nextView.bearing) < 0.000001 &&
          Math.abs(state.map_view.pitch - nextView.pitch) < 0.000001;
        return sameView ? state : { ...state, map_view: nextView };
      });
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

  // state → map 同步：只在 mapReady 首次后做一次（恢复 IndexedDB 中保存的视角）。
  // 之后镜头完全由用户操作（moveend → state 单向）；不再因 timeline / 其它 state 变化
  // 而自动 jumpTo，避免播放时被"拉回"。
  const mapViewRestoredRef = useRef(false);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    if (mapViewRestoredRef.current) return;
    mapViewRestoredRef.current = true;
    const target = appState.map_view;
    const center = map.getCenter();
    const sameView =
      Math.abs(center.lng - target.center[0]) < 0.000001 &&
      Math.abs(center.lat - target.center[1]) < 0.000001 &&
      Math.abs(map.getZoom() - target.zoom) < 0.000001 &&
      Math.abs(map.getBearing() - target.bearing) < 0.000001 &&
      Math.abs(map.getPitch() - target.pitch) < 0.000001;
    if (sameView) return;
    suppressMapMoveStateRef.current = true;
    skipAutoFollowForYearRef.current = appState.timeline.current_year;
    map.jumpTo({
      center: target.center,
      zoom: target.zoom,
      bearing: target.bearing,
      pitch: target.pitch
    });
    window.setTimeout(() => {
      suppressMapMoveStateRef.current = false;
    }, 120);
    // 仅依赖 mapReady — 第一次进入即恢复，后续不再被 state 变化触发
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapReady]);

  const selectedPolity = useMemo(() => {
    if (!yearData || !appState.selection.selected_polity_id) return null;
    return yearData.polities.find((polity) => polity.polity_id === appState.selection.selected_polity_id) ?? null;
  }, [appState.selection.selected_polity_id, yearData]);


  const visiblePolities = useMemo(() => {
    if (!yearData) return [];
    return yearData.polities.filter((polity) => {
      if (appState.filters.polity_types.length && !appState.filters.polity_types.includes(polity.polity_type)) return false;
      if (appState.filters.territory_status === "has_territory" && polity.territory.territory_status === "missing") return false;
      if (appState.filters.territory_status === "missing" && polity.territory.territory_status !== "missing") return false;
      if ((polity.confidence_score ?? 0) < appState.filters.min_confidence_score) return false;
      if (!appState.filters.show_disputed && polity.quality.has_dispute) return false;
      if (!appState.filters.show_unmatched_ruler && polity.quality.has_unmatched_ruler) return false;
      return true;
    });
  }, [appState.filters, yearData]);

  const availablePolityTypes = useMemo(() => {
    return Array.from(new Set(yearData?.polities.map((polity) => polity.polity_type).filter(Boolean) ?? [])).sort();
  }, [yearData]);

  const territoryStats = useMemo(() => {
    const polities = yearData?.polities ?? [];
    const withTerritory = polities.filter((polity) => polity.territory.territory_status !== "missing").length;
    return {
      total: polities.length,
      withTerritory,
      missing: polities.length - withTerritory
    };
  }, [yearData]);

  // 左侧图例浮层数据：沿用 territoryCollections 同口径过滤（filters + 有疆域）
  // 仅依赖 yearData / filters，独立于地图渲染。
  const legendPolities = useMemo(() => {
    const polities = yearData?.polities ?? [];
    return polities
      .filter((polity) => {
        if (polity.territory.territory_status === "missing") return false;
        if (
          appState.filters.polity_types.length &&
          !appState.filters.polity_types.includes(polity.polity_type)
        )
          return false;
        if (appState.filters.territory_status === "missing") return false;
        if ((polity.confidence_score ?? 0) < appState.filters.min_confidence_score) return false;
        if (!appState.filters.show_disputed && polity.quality.has_dispute) return false;
        if (!appState.filters.show_unmatched_ruler && polity.quality.has_unmatched_ruler) return false;
        return true;
      })
      .sort((a, b) => (b.territory.approx_area_km2 ?? 0) - (a.territory.approx_area_km2 ?? 0));
  }, [yearData, appState.filters]);

  const updateMapLayers = useCallback(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !yearData) return;
    const suppressProgrammaticMove = () => {
      suppressMapMoveStateRef.current = true;
      window.setTimeout(() => {
        suppressMapMoveStateRef.current = false;
      }, 900);
    };

    applyPhysicalBasemapVisibility(map, appState.layers);

    const collections = territoryCollections(
      yearData,
      territoryGeoJSON,
      appState,
      colorblindMode ? "colorblind" : "default"
    );
    const chinaBaseSource = map.getSource("china-admin-base") as GeoJSONSource | undefined;
    if (chinaBaseSource) {
      chinaBaseSource.setData(modernAdminUnits ?? emptyFeatureCollection());
    }
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
    const badgeSource = map.getSource("territory-overlap-badges") as GeoJSONSource | undefined;
    if (previousSource && currentSource && labelSource && badgeSource) {
      previousSource.setData(currentTerritoriesRef.current);
      currentSource.setData(collections.territories);
      labelSource.setData(collections.labels);
      badgeSource.setData(collections.badges);
      currentTerritoriesRef.current = collections.territories;
      const skipAutoFollowForThisYear = skipAutoFollowForYearRef.current === yearData.year;
      if (skipAutoFollowForThisYear) {
        // state 恢复阶段：保留用户上次的 map_view，不要被 fit 覆盖
        skipAutoFollowForYearRef.current = null;
        needsRefitRef.current = false;
      } else if (needsRefitRef.current && collections.territories.features.length) {
        // 镜头跟随完全由 needsRefitRef 信号控制——仅在剧本切幕等明确演示场景中触发，
        // 用户主动跳年、播放推进、滑条拖动均不会自动 reframe（由用户自己缩放/平移）。
        suppressProgrammaticMove();
        fitTerritoryBounds(map, collections.territories, { focusMainOnly: true });
        needsRefitRef.current = false;
      }
      if (map.getLayer("territory-fill-previous")) {
        map.setPaintProperty("territory-fill-previous", "fill-opacity", appState.layers.territories ? 0.28 : 0);
        window.setTimeout(() => {
          if (mapRef.current === map && map.getLayer("territory-fill-previous")) {
            map.setPaintProperty("territory-fill-previous", "fill-opacity", 0);
          }
        }, 40);
      }
      ["territory-fill-current", "territory-outline", "territory-overlap-badge-circle", "territory-overlap-badges"].forEach((layerId) => {
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
          element.title = `${polity.polity_display_name || polity.polity_name} ${capital.capital_name_historical}`;
          element.addEventListener("click", () => {
            setAppState((state) => ({
              ...state,
              timeline: { ...state.timeline, is_playing: false },
              selection: { selected_polity_id: polity.polity_id }
            }));
          });
          const marker = new maplibregl.Marker({ element })
            .setLngLat([capital.longitude, capital.latitude])
            .addTo(map);
          markersRef.current.push(marker);
        });
      });
    }

    // 迁都连线仍然显示在地图上，但不再自动 fit 镜头到迁都两点 — 用户曾反馈
    // "播放时镜头偶尔缩放"正是被迁都年（-899/-514/196/313/.../1644）触发。
  }, [appState, mapReady, modernAdminUnits, territoryGeoJSON, yearData, colorblindMode]);

  useEffect(() => {
    updateMapLayers();
  }, [updateMapLayers]);

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
      // 用户主动跳年不再自动调镜头，由用户自己缩放/平移。剧本切幕会在另一处显式触发 reframe。
      setAppState((state) => ({
        ...state,
        timeline: { ...state.timeline, current_year, is_playing: false }
      }));
    },
    [metadata, setAppState]
  );

  // Story preset: 切换步骤时跳到对应年份；自动推进；演示路线场景下显式 reframe（让观众看到对应区域）
  useEffect(() => {
    if (!activeStory) return;
    const step = activeStory.steps[storyStepIndex];
    if (!step) return;
    needsRefitRef.current = true;
    jumpToYear(step.year);
    if (step.polity_id) {
      setAppState((state) => ({
        ...state,
        selection: { selected_polity_id: step.polity_id ?? null }
      }));
    }
  }, [activeStory, storyStepIndex, jumpToYear, setAppState]);

  useEffect(() => {
    if (!activeStory || !storyAutoAdvance) return;
    if (storyStepIndex >= activeStory.steps.length - 1) return;
    const dwell = activeStory.default_dwell_ms || 6000;
    const timer = window.setTimeout(() => setStoryStepIndex((i) => i + 1), dwell);
    return () => window.clearTimeout(timer);
  }, [activeStory, storyStepIndex, storyAutoAdvance]);

  const handleSearchSelect = (entry: SearchEntry) => {
    if (entry.start_year != null) {
      jumpToYear(entry.start_year);
    }
    // 选中后清空搜索框（避免 entry.alias 为字面字符串 "null"/"undefined" 写回输入框）
    setSearchText("");
    setAppState((state) => ({
      ...state,
      selection: { selected_polity_id: entry.polity_id ?? null }
    }));
    if (entry.longitude != null && entry.latitude != null && mapRef.current) {
      mapRef.current.flyTo({ center: [entry.longitude, entry.latitude], zoom: 5, duration: 900 });
    }
  };

  const selectPolity = (polity: YearPolity) => {
    setOverlapPicker(null);
    setAppState((state) => ({
      ...state,
      timeline: { ...state.timeline, is_playing: false },
      selection: { selected_polity_id: polity.polity_id }
    }));
  };

  // 图例点击：选中 + 飞到该政权疆域包围盒
  const selectAndFlyToPolity = useCallback(
    (polity: YearPolity) => {
      const map = mapRef.current;
      setOverlapPicker(null);
      setAppState((state) => ({
        ...state,
        timeline: { ...state.timeline, is_playing: false },
        selection: { selected_polity_id: polity.polity_id }
      }));
      if (!map || !territoryGeoJSON) return;
      const subset: GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties> = {
        type: "FeatureCollection",
        features: territoryGeoJSON.features.filter(
          (feature) => feature.properties.polity_id === polity.polity_id
        )
      };
      if (!subset.features.length) return;
      // 抑制 moveend 写状态，避免与"演示路线/重置"逻辑冲撞
      suppressMapMoveStateRef.current = true;
      fitTerritoryBounds(map, subset);
      window.setTimeout(() => {
        suppressMapMoveStateRef.current = false;
      }, 800);
    },
    [territoryGeoJSON]
  );

  const resetView = () => {
    // 用户主动重置视角 → 不再触发 auto-follow（已经在默认欧亚视角）
    needsRefitRef.current = false;
    mapRef.current?.flyTo({ center: [75, 38], zoom: 2.6, bearing: 0, pitch: 0, duration: 700 });
  };

  // 重置按钮：清时间/视角/选中/事件栈，保留偏好
  const handleReset = useCallback(() => {
    needsRefitRef.current = false;
    setActiveStory(null);
    setStoryStepIndex(0);
    setEventStack([]);
    setActiveMapEvents([]);
    clearMapEventTimers();
    seenEventKeysRef.current.clear();
    suppressMapMoveStateRef.current = true;
    mapRef.current?.flyTo({ center: [75, 38], zoom: 2.6, bearing: 0, pitch: 0, duration: 600 });
    window.setTimeout(() => {
      suppressMapMoveStateRef.current = false;
    }, 700);
    setAppState((state) => ({
      ...state,
      timeline: { ...state.timeline, current_year: -221, is_playing: false, playback_speed: 1 },
      map_view: { center: [75, 38], zoom: 2.6, bearing: 0, pitch: 0 },
      selection: { selected_polity_id: null }
    }));
  }, [clearMapEventTimers, setAppState]);

  const handleSnapshot = useCallback(() => {
    const map = mapRef.current;
    if (!map || !yearData) {
      setStateNotice("地图未就绪，暂时无法截图。");
      return;
    }
    exportMapSnapshot(map, {
      yearLabel: yearData.year_label,
      polityCount: yearData.polity_count,
      withTerritory: territoryStats.withTerritory,
      dataVersion: metadata?.data_version ?? "v03",
      attribution: `${metadata?.admin_boundary_source ?? "geoBoundaries"} · Natural Earth · ${
        metadata?.admin_boundary_license ?? "Public Domain"
      }`
    }).catch((error: Error) => setStateNotice(`截图失败：${error.message}`));
  }, [yearData, territoryStats.withTerritory, metadata]);

  const handleExportState = useCallback(() => exportAppState(appState), [appState]);
  const handleTriggerImport = useCallback(() => importFileRef.current?.click(), []);
  const handleImportFile = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      event.target.value = "";
      if (!file || !storeRef.current) return;
      const reader = new FileReader();
      reader.onload = () => {
        void storeRef.current!.import(String(reader.result ?? "")).then((result) => {
          if (!result.ok) {
            setStateNotice(result.warning ?? "导入失败。");
          } else if (result.warning) {
            skipAutoFollowForYearRef.current = result.state?.timeline.current_year ?? null;
            setStateNotice(`已导入：${result.warning}`);
          } else {
            skipAutoFollowForYearRef.current = result.state?.timeline.current_year ?? null;
            setStateNotice("已导入状态。");
          }
        });
      };
      reader.readAsText(file);
    },
    []
  );

  const handleClearEventStack = useCallback(() => {
    setEventStack([]);
    setActiveMapEvents([]);
    clearMapEventTimers();
    seenEventKeysRef.current.clear();
  }, [clearMapEventTimers]);

  const handleFlyToEvent = useCallback((lng: number, lat: number) => {
    mapRef.current?.flyTo({ center: [lng, lat], zoom: 5.6, duration: 900 });
  }, []);

  const handleTogglePlay = useCallback(() => {
    setAppState((state) => ({
      ...state,
      timeline: { ...state.timeline, is_playing: !state.timeline.is_playing }
    }));
  }, [setAppState]);

  const handleClearSelection = useCallback(() => {
    setAppState((state) => ({ ...state, selection: { selected_polity_id: null } }));
  }, [setAppState]);


  if (loadError) {
    return (
      <main className="app app--error">
        <h1>数据加载失败</h1>
        <p>{loadError}</p>
      </main>
    );
  }

  return (
    <main className={`app ${sidePanelOpen ? "" : "app--side-hidden"}`}>
      <section className="map-shell">
        <div ref={mapContainerRef} className="map-canvas" />
        <MapEventOverlay
          map={mapReady ? mapRef.current : null}
          items={activeMapEvents}
          onFlyToEvent={handleFlyToEvent}
        />
        <MapContextOverlay
          map={mapReady ? mapRef.current : null}
          contexts={visibleMapContexts}
          onFlyToContext={handleFlyToEvent}
        />
          <Topbar
            metadata={metadata}
            searchText={searchText}
            setSearchText={setSearchText}
            searchResults={searchResults}
            onSearchSelect={handleSearchSelect}
            storyPresets={storyPresets}
            activeStory={activeStory}
            storyPickerOpen={storyPickerOpen}
            setStoryPickerOpen={setStoryPickerOpen}
            onSelectStory={(preset) => {
              setEventStack([]);
              setActiveMapEvents([]);
              clearMapEventTimers();
              seenEventKeysRef.current.clear();
              setActiveStory(preset);
              setStoryStepIndex(0);
              setStoryAutoAdvance(true);
              setStoryPickerOpen(false);
            }}
            onExitStory={() => {
              setActiveStory(null);
              setStoryStepIndex(0);
              setStoryPickerOpen(false);
            }}
            validationSummary={validationSummary}
            qualityPanelOpen={qualityPanelOpen}
            setQualityPanelOpen={setQualityPanelOpen}
            sidePanelOpen={sidePanelOpen}
            setSidePanelOpen={setSidePanelOpen}
          />


        {stateNotice ? (
          <div className="state-notice" role="status">
            <span>{stateNotice}</span>
            <button type="button" onClick={() => setStateNotice(null)} aria-label="关闭提示">×</button>
          </div>
        ) : null}

        {activeStory ? (
          <StoryPlayer
            activeStory={activeStory}
            storyStepIndex={storyStepIndex}
            storyAutoAdvance={storyAutoAdvance}
            onExit={() => {
              setActiveStory(null);
              setStoryStepIndex(0);
              setStoryAutoAdvance(true);
            }}
            onPrev={() => {
              setStoryAutoAdvance(false);
              setStoryStepIndex((i) => Math.max(0, i - 1));
            }}
            onNext={() => {
              setStoryAutoAdvance(false);
              setStoryStepIndex((i) => Math.min(activeStory.steps.length - 1, i + 1));
            }}
            onToggleAutoAdvance={() => setStoryAutoAdvance((a) => !a)}
          />
        ) : null}

        {qualityPanelOpen && validationData ? (
          <QualityPanel
            validation={validationData}
            issues={issuesData}
            partialBoundaryPolities={partialBoundaryPolities}
            onClose={() => setQualityPanelOpen(false)}
            onSelectPolity={(polityId) => {
              setQualityPanelOpen(false);
              setAppState((state) => ({
                ...state,
                timeline: { ...state.timeline, is_playing: false },
                selection: { selected_polity_id: polityId }
              }));
            }}
          />
        ) : null}

        {yearData?.capital_migrations.length ? (
          <div className="migration-toast">
            <MapPin size={16} />
            {yearData.capital_migrations.map((migration) => (
              <span key={migration.migration_id}>
                {migration.polity_display_name || migration.polity_name} {migration.label}
                {migration.is_disputed ? "（争议）" : ""}
              </span>
            ))}
          </div>
        ) : null}

        {overlapPicker ? (
          <OverlapPicker
            state={overlapPicker}
            selectedPolityId={appState.selection.selected_polity_id}
            onClose={() => setOverlapPicker(null)}
            onSelect={selectPolity}
          />
        ) : null}

        <MapHoverTooltip state={hoverPolity} />

        <PolityLegend
          polities={legendPolities}
          selectedPolityId={appState.selection.selected_polity_id}
          onSelect={selectAndFlyToPolity}
          colorblindMode={colorblindMode}
        />

        <BottomBar
          metadata={metadata}
          appState={appState}
          jumpToYear={jumpToYear}
          onTogglePlay={handleTogglePlay}
          onReset={handleReset}
          onSnapshot={handleSnapshot}
          onExportState={handleExportState}
          onTriggerImport={handleTriggerImport}
          onImportFile={handleImportFile}
          setAppState={setAppState}
          importFileRef={importFileRef}
        />


          <div
            className="layer-panel"
            onMouseLeave={() => {
              setOpenLayerGroup(null);
              // blur 当前 focused 按钮，避免 tab-residual 与"鼠标移开即收起"的语义冲突
              if (
                document.activeElement instanceof HTMLElement &&
                document.activeElement.closest(".layer-panel")
              ) {
                document.activeElement.blur();
              }
            }}
          >
            <div className="layer-panel__trigger" aria-hidden>
              <Layers size={14} />
              <span>图层 / 显示 / 演示</span>
              <span className="layer-panel__trigger-caret">▾</span>
            </div>
            <CollapsibleGroup
              title="政权图层"
              icon={<Layers size={14} />}
              collapsed={openLayerGroup !== "polity"}
              onToggle={() => setOpenLayerGroup((g) => (g === "polity" ? null : "polity"))}
            >
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
                    setAppState((state) => ({ ...state, layers: { ...state.layers, modern_admin_reference: event.target.checked } }))
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
                    setAppState((state) => ({ ...state, layers: { ...state.layers, capital_migration_paths: event.target.checked } }))
                  }
                />
                迁都连线
              </label>
            </CollapsibleGroup>

            <CollapsibleGroup
              title="物理地理"
              collapsed={openLayerGroup !== "physical"}
              onToggle={() => setOpenLayerGroup((g) => (g === "physical" ? null : "physical"))}
            >
              <label>
                <input
                  type="checkbox"
                  checked={appState.layers.physical_rivers}
                  onChange={(event) =>
                    setAppState((state) => ({ ...state, layers: { ...state.layers, physical_rivers: event.target.checked } }))
                  }
                />
                河流
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={appState.layers.physical_lakes}
                  onChange={(event) =>
                    setAppState((state) => ({ ...state, layers: { ...state.layers, physical_lakes: event.target.checked } }))
                  }
                />
                湖泊
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={appState.layers.physical_glaciers}
                  onChange={(event) =>
                    setAppState((state) => ({ ...state, layers: { ...state.layers, physical_glaciers: event.target.checked } }))
                  }
                />
                冰盖
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={appState.layers.modern_country_boundaries}
                  onChange={(event) =>
                    setAppState((state) => ({ ...state, layers: { ...state.layers, modern_country_boundaries: event.target.checked } }))
                  }
                />
                国界参考·国际版（NE）
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={appState.layers.cn_border_overlay}
                  onChange={(event) =>
                    setAppState((state) => ({ ...state, layers: { ...state.layers, cn_border_overlay: event.target.checked } }))
                  }
                />
                国界·中国标准
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={appState.layers.geographic_lines}
                  onChange={(event) =>
                    setAppState((state) => ({ ...state, layers: { ...state.layers, geographic_lines: event.target.checked } }))
                  }
                />
                赤道/回归线
              </label>
            </CollapsibleGroup>

            <CollapsibleGroup
              title="演示"
              collapsed={openLayerGroup !== "demo"}
              onToggle={() => setOpenLayerGroup((g) => (g === "demo" ? null : "demo"))}
            >
              <p className="layer-group__hint">
                镜头由你自己缩放/平移。仅演示路线播放时会主动跟随主政权。
              </p>
              <button onClick={resetView} className="layer-action-button">
                <LocateFixed size={14} />
                重置到欧亚视角
              </button>
            </CollapsibleGroup>

            <CollapsibleGroup
              title="显示设置"
              icon={<Settings size={14} />}
              collapsed={openLayerGroup !== "settings"}
              onToggle={() => setOpenLayerGroup((g) => (g === "settings" ? null : "settings"))}
            >
              <SettingsControls
                appState={appState}
                availablePolityTypes={availablePolityTypes}
                setAppState={setAppState}
                colorblindMode={colorblindMode}
                setColorblindMode={setColorblindMode}
              />
            </CollapsibleGroup>
          </div>

      </section>

      {sidePanelOpen ? (
        <SidePanel
          yearData={yearData}
          metadata={metadata}
          eventsData={timelineEventsData}
          selectedPolity={selectedPolity}
          territoryStats={territoryStats}
          appState={appState}
          currentYearEvents={currentYearEvents}
          currentYearContexts={currentYearContexts}
          eventStack={eventStack}
          freshEventKeysRef={freshEventKeysRef}
          colorblindMode={colorblindMode}
          jumpToYear={jumpToYear}
          onClearEventStack={handleClearEventStack}
          onFlyToEvent={handleFlyToEvent}
          onClearSelection={handleClearSelection}
        />
      ) : null}

      <OnboardingTour onTriggerStoryPicker={() => setStoryPickerOpen(true)} />
    </main>
  );
}


export default App;
