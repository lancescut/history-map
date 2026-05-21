import type { YearPolity } from "../types";
import { yearLabel } from "../data";
import { isPolityNomadic, polityDisplayName } from "../map-helpers";

export interface MapHoverState {
  polity: YearPolity;
  x: number;
  y: number;
  controlLabel?: string;
  controlType?: "direct" | "influence";
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
      <strong>
        {polity.dataset_id === "vIndian" ? (
          <span className="dataset-badge dataset-badge--in" style={{ marginRight: 6 }}>印</span>
        ) : polity.dataset_id === "v03" ? (
          <span className="dataset-badge dataset-badge--cn" style={{ marginRight: 6 }}>中</span>
        ) : null}
        {polityDisplayName(polity)}
      </strong>
      <span>
        {startLabel} – {endLabel}
      </span>
      <small>
        {polity.polity_name_disambiguation || `${polity.macro_period || ""}${polity.polity_type ? ` · ${polity.polity_type}` : ""}`}
      </small>
      {state.controlLabel ? (
        <small className={state.controlType === "influence" ? "map-hover-tooltip__influence-note" : ""}>
          {state.controlLabel}
        </small>
      ) : null}
      {nomadic ? (
        <small className="map-hover-tooltip__nomadic-note">
          📐 游牧政权·实际活动范围可能超出图示
        </small>
      ) : null}
    </div>
  );
}
