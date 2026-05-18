import type { YearPolity } from "../types";
import { yearLabel } from "../data";
import { isPolityNomadic, polityDisplayName } from "../map-helpers";

export interface MapHoverState {
  polity: YearPolity;
  x: number;
  y: number;
}

export function MapHoverTooltip({ state }: { state: MapHoverState | null }) {
  if (!state) return null;
  const { polity, x, y } = state;
  const startLabel =
    polity.polity_start_year != null ? yearLabel(polity.polity_start_year) : "?";
  const endLabel =
    polity.polity_end_year != null ? yearLabel(polity.polity_end_year) : "今";
  const nomadic = isPolityNomadic(polity);
  return (
    <div
      className="map-hover-tooltip"
      style={{
        left: `min(${x + 14}px, calc(100% - 220px))`,
        top: `min(${y + 14}px, calc(100% - 100px))`
      }}
      role="tooltip"
    >
      <strong>{polityDisplayName(polity)}</strong>
      <span>
        {startLabel} – {endLabel}
      </span>
      <small>
        {polity.polity_name_disambiguation || `${polity.macro_period} · ${polity.polity_type}`}
      </small>
      {nomadic ? (
        <small className="map-hover-tooltip__nomadic-note">
          📐 游牧政权·实际活动范围可能超出图示
        </small>
      ) : null}
    </div>
  );
}
