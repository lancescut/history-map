import type { YearPolity } from "../types";
import { polityDisplayName } from "../map-helpers";

export interface OverlapPickerState {
  x: number;
  y: number;
  candidates: YearPolity[];
}

export function OverlapPicker({
  state,
  selectedPolityId,
  onClose,
  onSelect
}: {
  state: OverlapPickerState;
  selectedPolityId: string | null;
  onClose: () => void;
  onSelect: (polity: YearPolity) => void;
}) {
  return (
    <div
      className="overlap-picker"
      style={{
        left: `min(${state.x + 14}px, calc(100% - 340px))`,
        top: `min(${state.y + 14}px, calc(100% - 280px))`
      }}
    >
      <div className="overlap-picker__header">
        <div>
          <strong>重叠疆域</strong>
          <span>{state.candidates.length} 个候选政权</span>
        </div>
        <button type="button" aria-label="关闭重叠候选" onClick={onClose}>
          ×
        </button>
      </div>
      <div className="overlap-picker__list">
        {state.candidates.map((polity) => (
          <button
            type="button"
            key={polity.polity_id}
            className={polity.polity_id === selectedPolityId ? "selected" : ""}
            onClick={() => onSelect(polity)}
          >
            <span>{polityDisplayName(polity)}</span>
            <small>
              {polity.territory.matched_admin_units.join("、") || "暂无摘要范围"} ·{" "}
              {polity.territory.matched_county_count.toLocaleString()} 县级单元
              {polity.territory.active_control_types?.includes("influence") ? " · 含影响区" : ""}
            </small>
          </button>
        ))}
      </div>
    </div>
  );
}
