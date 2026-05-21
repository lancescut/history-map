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
  // 兼容 vIndian polity 缺 territory.active_control_types 的情况，全程用可选链。
  const hasInfluence = polities.some((polity) => polity.territory?.active_control_types?.includes("influence"));
  return (
    <aside className="polity-legend" aria-label="当前政权图例">
      <div className="polity-legend__title">
        当前政权 · {polities.length}
      </div>
      <ul className="polity-legend__list">
        {polities.map((polity) => {
          const nomadic = isPolityNomadic(polity);
          const hasInfluenceZone = polity.territory?.active_control_types?.includes("influence") ?? false;
          const selected = polity.polity_id === selectedPolityId;
          // 与地图一致的渲染色（源色 ⊕ 底图色 ⊕ opacity）—— 避免"图例鲜艳/地图淡"的感知偏差
          const color = effectiveTerritoryColor(
            polity.macro_period,
            polity.polity_id,
            nomadic,
            {
              palette: colorblindMode ? "colorblind" : "default",
              selected,
              datasetId: polity.dataset_id
            }
          );
          const datasetBadge =
            polity.dataset_id === "vIndian" ? (
              <span className="dataset-badge dataset-badge--in" title="印度史">印</span>
            ) : polity.dataset_id === "v03" ? (
              <span className="dataset-badge dataset-badge--cn" title="中国史">中</span>
            ) : null;
          return (
            <li key={`${polity.dataset_id ?? "v03"}::${polity.polity_id}`}>
              <button
                type="button"
                className={`polity-legend__row ${selected ? "is-selected" : ""}`}
                onClick={() => onSelect(polity)}
                title={`${polityDisplayName(polity)} · ${polity.polity_name_disambiguation || `${polity.macro_period} · ${polity.polity_type}`}${nomadic ? " · 游牧" : ""}`}
              >
                <span className="polity-legend__swatches" aria-hidden>
                  <span
                    className={`polity-legend__swatch ${nomadic ? "polity-legend__swatch--nomadic" : ""}`}
                    style={{ background: color }}
                  />
                  {hasInfluenceZone ? (
                    <span
                      className="polity-legend__swatch polity-legend__swatch--influence"
                      style={{
                        backgroundImage: `repeating-linear-gradient(45deg, transparent 0 4px, ${color} 4px 6px, transparent 6px 10px)`
                      }}
                    />
                  ) : null}
                </span>
                <span className="polity-legend__name">
                  {datasetBadge}
                  {polityDisplayName(polity)}
                  {nomadic ? <span className="polity-legend__nomadic-tag">游牧</span> : null}
                  {hasInfluenceZone ? <span className="polity-legend__nomadic-tag">影响区</span> : null}
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
      {hasInfluence ? (
        <p className="polity-legend__footnote">
          斜纹代表都护、羁縻或势力影响区，不等同完整实控疆域
        </p>
      ) : null}
    </aside>
  );
}
