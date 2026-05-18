import {
  useCallback,
  useLayoutEffect,
  useMemo,
  useRef,
  type MutableRefObject
} from "react";
import { yearLabel } from "../data";
import {
  COVERAGE_ROLE_LABELS,
  EVENT_TYPE_GLYPHS,
  coverageRoleLabel,
  eventTypeLabel,
  historicalEventPlaybackKey
} from "../event-meta";
import { effectiveTerritoryColor, isPolityNomadic, polityDisplayName } from "../map-helpers";
import { VerticalTimeline } from "./VerticalTimeline";
import type { StoredAppState } from "../state";
import type {
  HistoricalEvent,
  HistoricalEventsData,
  HistoricalContext,
  Metadata,
  YearData,
  YearPolity
} from "../types";

interface TerritoryStats {
  total: number;
  withTerritory: number;
  missing: number;
}

export interface SidePanelProps {
  yearData: YearData | null;
  metadata: Metadata | null;
  eventsData: HistoricalEventsData | null;
  selectedPolity: YearPolity | null;
  territoryStats: TerritoryStats;
  appState: StoredAppState;
  currentYearEvents: HistoricalEvent[];
  currentYearContexts: HistoricalContext[];
  eventStack: HistoricalEvent[];
  freshEventKeysRef: MutableRefObject<Set<string>>;
  jumpToYear: (year: number) => void;
  onClearEventStack: () => void;
  onFlyToEvent: (lng: number, lat: number) => void;
  onClearSelection: () => void;
  colorblindMode: boolean;
}

export function SidePanel(props: SidePanelProps) {
  return (
    <aside className="side-panel">
      <EventStreamCard
        yearData={props.yearData}
        metadata={props.metadata}
        territoryStats={props.territoryStats}
        selectedPolity={props.selectedPolity}
        onClearSelection={props.onClearSelection}
        colorblindMode={props.colorblindMode}
        currentYearEvents={props.currentYearEvents}
        currentYearContexts={props.currentYearContexts}
        eventStack={props.eventStack}
        freshEventKeysRef={props.freshEventKeysRef}
        onClearEventStack={props.onClearEventStack}
        onFlyToEvent={props.onFlyToEvent}
        eventsData={props.eventsData}
        currentYear={props.appState.timeline.current_year}
        jumpToYear={props.jumpToYear}
      />
    </aside>
  );
}

function EventStreamCard({
  yearData,
  metadata,
  territoryStats,
  selectedPolity,
  onClearSelection,
  colorblindMode,
  currentYearEvents,
  currentYearContexts,
  eventStack,
  freshEventKeysRef,
  onClearEventStack,
  onFlyToEvent,
  eventsData,
  currentYear,
  jumpToYear
}: {
  yearData: YearData | null;
  metadata: Metadata | null;
  territoryStats: TerritoryStats;
  selectedPolity: YearPolity | null;
  onClearSelection: () => void;
  colorblindMode: boolean;
  currentYearEvents: HistoricalEvent[];
  currentYearContexts: HistoricalContext[];
  eventStack: HistoricalEvent[];
  freshEventKeysRef: MutableRefObject<Set<string>>;
  onClearEventStack: () => void;
  onFlyToEvent: (lng: number, lat: number) => void;
  eventsData: HistoricalEventsData | null;
  currentYear: number;
  jumpToYear: (year: number) => void;
}) {
  const walkedIds = useMemo(
    () => new Set(eventStack.map((event) => historicalEventPlaybackKey(event))),
    [eventStack]
  );
  // 二分查找：下一个有事件的年份（严格大于当前年）
  const nextEventYear = useMemo(() => {
    const events = eventsData?.events;
    if (!events?.length) return null;
    const years = Array.from(new Set(events.map((e) => e.year))).sort((a, b) => a - b);
    let lo = 0;
    let hi = years.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (years[mid] > currentYear) hi = mid;
      else lo = mid + 1;
    }
    return lo < years.length ? years[lo] : null;
  }, [eventsData, currentYear]);
  const currentHasEvents = currentYearEvents.length > 0;
  const primaryContext = currentYearContexts[0] ?? null;
  const yearDataMatchesCurrent = yearData?.year === currentYear;
  const stackItemRefs = useRef(new Map<string, HTMLLIElement>());
  const previousStackRectsRef = useRef(new Map<string, DOMRect>());
  const setStackItemRef = useCallback((eventId: string, node: HTMLLIElement | null) => {
    if (node) {
      stackItemRefs.current.set(eventId, node);
    } else {
      stackItemRefs.current.delete(eventId);
    }
  }, []);

  useLayoutEffect(() => {
    const previousRects = previousStackRectsRef.current;
    const nextRects = new Map<string, DOMRect>();

    stackItemRefs.current.forEach((node, eventId) => {
      const nextRect = node.getBoundingClientRect();
      nextRects.set(eventId, nextRect);
      const previousRect = previousRects.get(eventId);
      if (!previousRect) return;
      const deltaY = previousRect.top - nextRect.top;
      if (Math.abs(deltaY) < 1) return;

      node.style.transition = "none";
      node.style.transform = `translateY(${deltaY}px)`;
      window.requestAnimationFrame(() => {
        node.style.transition = "";
        node.style.transform = "";
      });
    });

    previousStackRectsRef.current = nextRects;
  }, [eventStack]);

  return (
    <section className="event-stream-card">
      {/* 合并的年份概览 head */}
      <div className="event-stream-card__year-head">
        <div className="event-stream-card__year-row">
          <span className="event-stream-card__year-label">当前年份</span>
          <strong className="event-stream-card__year-value">
            {yearLabel(currentYear)}
          </strong>
        </div>
        <p className="event-stream-card__year-meta">
          {yearDataMatchesCurrent
            ? `${territoryStats.total} 政权 · ${territoryStats.withTerritory} 有疆域 · ${yearData?.capital_migrations.length ?? 0} 迁都`
            : "政权与疆域资料加载中"}
        </p>
        <HistoricalContextCard context={primaryContext} />
        {/* 始终渲染：用 visibility:hidden 占位，避免下方播放足迹/rail 因 head 高度变化而跳动 */}
        <button
          type="button"
          className="event-stream-card__next-year"
          style={{
            visibility: !currentHasEvents && nextEventYear !== null ? "visible" : "hidden"
          }}
          onClick={() => nextEventYear !== null && jumpToYear(nextEventYear)}
          title={nextEventYear !== null ? `跳到下一个事件/典故年份 ${yearLabel(nextEventYear)}` : ""}
          tabIndex={!currentHasEvents && nextEventYear !== null ? 0 : -1}
        >
          → 下一个事件/典故：{nextEventYear !== null ? yearLabel(nextEventYear) : "—"}
        </button>
        <div
          className="event-stream-card__selected"
          style={{ visibility: selectedPolity ? "visible" : "hidden" }}
        >
          {selectedPolity ? (
            <>
              <span
                className="event-stream-card__selected-swatch"
                style={{
                  backgroundColor: effectiveTerritoryColor(
                    selectedPolity.macro_period,
                    selectedPolity.polity_id,
                    isPolityNomadic(selectedPolity),
                    { palette: colorblindMode ? "colorblind" : "default", selected: true }
                  )
                }}
                aria-hidden
              />
              <div className="event-stream-card__selected-text">
                <strong>{polityDisplayName(selectedPolity)}</strong>
                <small>
                  {selectedPolity.polity_name_disambiguation || `${selectedPolity.macro_period} · ${selectedPolity.polity_type}`}
                </small>
              </div>
              <button
                type="button"
                className="event-stream-card__selected-clear"
                onClick={onClearSelection}
                aria-label="清除选中政权"
                title="清除选中政权"
              >
                ×
              </button>
            </>
          ) : (
            // 占位 — 视觉隐藏但保留高度
            <>
              <span className="event-stream-card__selected-swatch" aria-hidden />
              <div className="event-stream-card__selected-text">
                <strong>—</strong>
                <small>—</small>
              </div>
            </>
          )}
        </div>
      </div>

      <header className="event-stream-card__head event-stream-card__head--trail">
        <h2>播放足迹</h2>
        <span className="event-stream-card__count">{eventStack.length}</span>
        {eventStack.length ? (
          <button
            type="button"
            className="event-stream-card__clear"
            onClick={onClearEventStack}
            aria-label="清空事件流"
            title="清空事件流"
          >
            清空
          </button>
        ) : null}
      </header>
      <div className="event-stack-grid">
        <VerticalTimeline
          events={eventsData?.events ?? []}
          walkedIds={walkedIds}
          yearMin={metadata?.year_min ?? -1046}
          yearMax={metadata?.year_max ?? 1912}
          currentYear={currentYear}
          onJump={jumpToYear}
        />
        {eventStack.length === 0 ? (
          <div className="event-stream-card__empty event-stream-card__empty--trail">
            播放或拖动年份滑块时，途经的重要历史事件会按时间顺序累积在这里。
          </div>
        ) : (
          <ol className="event-stream-card__body" aria-label="按时间倒序的历史事件流">
            {eventStack.map((event) => {
              const eventKey = historicalEventPlaybackKey(event);
              return (
                <EventListItem
                  key={eventKey}
                  event={event}
                  isFresh={freshEventKeysRef.current.has(eventKey)}
                  itemRef={(node) => setStackItemRef(eventKey, node)}
                  onFlyToEvent={onFlyToEvent}
                />
              );
            })}
          </ol>
        )}
      </div>
    </section>
  );
}

function HistoricalContextCard({ context }: { context: HistoricalContext | null }) {
  const progress = Math.round((context?.progress_ratio ?? 0) * 100);
  const rangeLabel = context ? `${context.start_label}–${context.end_label}` : "—";
  return (
    <div
      className="event-stream-card__context"
      style={{ visibility: context ? "visible" : "hidden" }}
      aria-live="polite"
    >
      {context ? (
        <>
          <div className="event-stream-card__context-head">
            <span>历史脉络</span>
            <strong>{rangeLabel}</strong>
          </div>
          <div className="event-stream-card__context-title">{context.title}</div>
          <p>{context.description}</p>
          <div className="event-stream-card__context-progress" aria-label={`阶段进度 ${progress}%`}>
            <span style={{ width: `${progress}%` }} />
          </div>
        </>
      ) : (
        <>
          <div className="event-stream-card__context-head">
            <span>历史脉络</span>
            <strong>—</strong>
          </div>
          <div className="event-stream-card__context-title">—</div>
          <p>—</p>
          <div className="event-stream-card__context-progress">
            <span />
          </div>
        </>
      )}
    </div>
  );
}

function EventListItem({
  event,
  isFresh,
  itemRef,
  onFlyToEvent
}: {
  event: HistoricalEvent;
  isFresh: boolean;
  itemRef?: (node: HTMLLIElement | null) => void;
  onFlyToEvent: (lng: number, lat: number) => void;
}) {
  const isAnecdote = event.is_anecdote || event.item_kind === "anecdote";
  const longitude = event.location?.longitude ?? event.longitude;
  const latitude = event.location?.latitude ?? event.latitude;
  const hasCoords = longitude != null && latitude != null;
  const historicalName = event.location?.historical_name || event.location_historical_name || event.location_name;
  const modernName = event.location?.modern_name || event.location_modern_name || event.location_name;
  const locationLabel =
    historicalName && modernName && historicalName !== modernName
      ? `${historicalName}/今${modernName}`
      : historicalName || modernName || (hasCoords ? "地图位置" : null);
  const description = isAnecdote ? event.story_text || event.description : event.description;
  const sourceLabel =
    isAnecdote && event.source_title
      ? event.source_section
        ? `出自${event.source_title}·${event.source_section}`
        : event.source_title === "民间流传"
          ? "民间流传"
          : `出自${event.source_title}`
      : "";

  return (
    <li
      ref={itemRef}
      className={`event-item event-item--${event.event_type} ${isAnecdote ? "event-item--anecdote" : ""} ${isFresh ? "is-fresh" : ""}`}
    >
      <span className="event-item__glyph" aria-hidden>
        {EVENT_TYPE_GLYPHS[event.event_type] ?? "●"}
      </span>
      <div className="event-item__body">
        <div className="event-item__head-row">
          <strong className="event-item__title">{event.title}</strong>
          <span className="event-item__year">{event.date_label || event.year_label}</span>
        </div>
        {description ? (
          <p className={`event-item__desc ${isAnecdote ? "event-item__desc--story" : ""}`}>
            {description}
          </p>
        ) : null}
        <div className="event-item__meta-row">
          <span className="event-item__type">{eventTypeLabel(event.event_type)}</span>
          {event.primary_education_stage ? (
            <span className={`event-item__stage event-item__stage--${event.primary_education_stage}`}>
              {event.primary_education_stage}
            </span>
          ) : null}
          {event.coverage_role ? (
            <span
              className={`event-item__coverage event-item__coverage--${event.coverage_role}`}
              title={COVERAGE_ROLE_LABELS[event.coverage_role] ? undefined : event.coverage_role}
            >
              {coverageRoleLabel(event.coverage_role)}
            </span>
          ) : null}
          {locationLabel ? (
            hasCoords ? (
              <button
                type="button"
                className="event-item__location-inline event-item__location-inline--link"
                onClick={() => onFlyToEvent(longitude!, latitude!)}
                title={`${locationLabel}（点击跳到地图位置）`}
              >
                地点 {locationLabel}
              </button>
            ) : (
              <span className="event-item__location-inline event-item__location-inline--missing">
                地点 {locationLabel}
              </span>
            )
          ) : !hasCoords ? (
            <span className="event-item__location-inline event-item__location-inline--missing">
              地点 无坐标
            </span>
          ) : null}
          {sourceLabel ? <span className="event-item__source-inline">{sourceLabel}</span> : null}
        </div>
      </div>
    </li>
  );
}
