import { effectiveTerritoryColor, isPolityNomadic, polityDisplayName } from "../map-helpers";
import type { YearPolity } from "../types";

export function PolityLegend({
  polities,
  selectedPolityId,
  onSelect,
  colorblindMode = false
}: {
  polities: YearPolity[];
  selectedPolityId: string | null;
  onSelect: (polity: YearPolity) => void;
  colorblindMode?: boolean;
}) {
  if (!polities.length) return null;
  const hasNomadic = polities.some((polity) => isPolityNomadic(polity));
  return (
    <aside className="polity-legend" aria-label="当前政权图例">
      <div className="polity-legend__title">
        当前政权 · {polities.length}
      </div>
      <ul className="polity-legend__list">
        {polities.map((polity) => {
          const nomadic = isPolityNomadic(polity);
          const selected = polity.polity_id === selectedPolityId;
          // 与地图一致的渲染色（源色 ⊕ 底图色 ⊕ opacity）—— 避免"图例鲜艳/地图淡"的感知偏差
          const color = effectiveTerritoryColor(
            polity.macro_period,
            polity.polity_id,
            nomadic,
            {
              palette: colorblindMode ? "colorblind" : "default",
              selected
            }
          );
          return (
            <li key={polity.polity_id}>
              <button
                type="button"
                className={`polity-legend__row ${selected ? "is-selected" : ""}`}
                onClick={() => onSelect(polity)}
                title={`${polityDisplayName(polity)} · ${polity.polity_name_disambiguation || `${polity.macro_period} · ${polity.polity_type}`}${nomadic ? " · 游牧" : ""}`}
              >
                <span
                  className={`polity-legend__swatch ${nomadic ? "polity-legend__swatch--nomadic" : ""}`}
                  style={{ background: color }}
                  aria-hidden
                />
                <span className="polity-legend__name">
                  {polityDisplayName(polity)}
                  {nomadic ? <span className="polity-legend__nomadic-tag">游牧</span> : null}
                </span>
                <small className="polity-legend__sub">{polity.polity_type}</small>
              </button>
            </li>
          );
        })}
      </ul>
      {hasNomadic ? (
        <p className="polity-legend__footnote">
          带「游牧」标签的政权，活动范围可能超出本图覆盖
        </p>
      ) : null}
    </aside>
  );
}
