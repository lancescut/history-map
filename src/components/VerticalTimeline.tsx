import { useMemo } from "react";
import { yearLabel } from "../data";
import { historicalEventPlaybackKey } from "../event-meta";
import type { HistoricalEvent } from "../types";

export function VerticalTimeline({
  events,
  walkedIds,
  yearMin,
  yearMax,
  currentYear,
  onJump
}: {
  events: HistoricalEvent[];
  walkedIds: Set<string>;
  yearMin: number;
  yearMax: number;
  currentYear: number;
  onJump: (year: number) => void;
}) {
  const span = Math.max(1, yearMax - yearMin);
  // 同年多事件聚合到一个点（避免完全重叠），按年份索引一次性算好位置。
  // 顺序：先按 year 升序，让 walked 事件在 z-order 上排在普通点之上。
  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) => a.year - b.year);
  }, [events]);

  const cursorPercent = ((currentYear - yearMin) / span) * 100;

  return (
    <div className="vertical-timeline" role="presentation">
      <div className="vertical-timeline__rail" aria-hidden />
      {sortedEvents.map((event) => {
        const top = ((event.year - yearMin) / span) * 100;
        const walked = walkedIds.has(historicalEventPlaybackKey(event));
        return (
          <button
            type="button"
            key={event.event_id}
            className={`vertical-timeline__dot ${walked ? "is-walked" : ""} vertical-timeline__dot--${event.event_type}`}
            style={{ top: `${top}%` }}
            onClick={() => onJump(event.year)}
            title={`${yearLabel(event.year)}　${event.title}`}
            aria-label={`${yearLabel(event.year)} ${event.title}`}
          />
        );
      })}
      <div
        className="vertical-timeline__cursor"
        style={{ top: `${cursorPercent}%` }}
        aria-hidden
      />
    </div>
  );
}
