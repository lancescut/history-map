import { yearLabel } from "../data";
import { EVENT_TYPE_GLYPHS } from "../event-meta";
import type { HistoricalEvent } from "../types";

export function TimelineTicks({
  yearMin,
  yearMax,
  migrationYears,
  events,
  currentYear,
  onJump
}: {
  yearMin: number;
  yearMax: number;
  migrationYears: number[];
  events: HistoricalEvent[];
  currentYear: number;
  onJump: (year: number) => void;
}) {
  const span = Math.max(1, yearMax - yearMin);
  const positionFor = (year: number): number => ((year - yearMin) / span) * 100;
  return (
    <div className="timeline-ticks">
      <div className="timeline-ticks__track" />
      {events.map((event) => (
        <button
          key={`event-${event.event_id}`}
          type="button"
          className={`timeline-tick timeline-tick--event timeline-tick--${event.event_type}`}
          style={{ left: `${positionFor(event.year)}%` }}
          title={`${event.year_label}　${event.title}`}
          onClick={() => onJump(event.year)}
        >
          <span>{EVENT_TYPE_GLYPHS[event.event_type] ?? "●"}</span>
        </button>
      ))}
      {migrationYears.map((year) => (
        <button
          key={`migration-${year}`}
          type="button"
          className="timeline-tick timeline-tick--migration"
          style={{ left: `${positionFor(year)}%` }}
          title={`${yearLabel(year)}　迁都事件`}
          onClick={() => onJump(year)}
        >
          <span>⇄</span>
        </button>
      ))}
      <div
        className="timeline-ticks__cursor"
        style={{ left: `${positionFor(currentYear)}%` }}
        aria-hidden
      />
    </div>
  );
}
