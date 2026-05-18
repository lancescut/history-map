import type { StoredAppState } from "../state";
import type { AppState } from "../types";

type AppStateUpdater = Partial<StoredAppState> | ((state: StoredAppState) => StoredAppState);
type SetAppState = (updater: AppStateUpdater) => void;

export function SettingsControls({
  appState,
  availablePolityTypes,
  setAppState,
  colorblindMode,
  setColorblindMode
}: {
  appState: StoredAppState;
  availablePolityTypes: string[];
  setAppState: SetAppState;
  colorblindMode: boolean;
  setColorblindMode: (next: boolean | ((prev: boolean) => boolean)) => void;
}) {
  return (
    <>
      <label className="settings-row settings-row--toggle">
        <span>
          色盲对比模式
          <small>切到 Okabe-Ito 7 色调色板，对色盲友好</small>
        </span>
        <input
          type="checkbox"
          checked={colorblindMode}
          onChange={(event) => setColorblindMode(event.target.checked)}
        />
      </label>
      <label className="settings-row settings-row--toggle">
        <span>
          播放典故
          <small>把成语和历史典故加入年份播放</small>
        </span>
        <input
          type="checkbox"
          checked={appState.ui.show_historical_anecdotes}
          onChange={(event) =>
            setAppState((state) => ({
              ...state,
              ui: { ...state.ui, show_historical_anecdotes: event.target.checked }
            }))
          }
        />
      </label>
      {availablePolityTypes.length ? (
        <div className="type-filter-group">
          <span className="type-filter-group__label">政权类型</span>
          <div className="type-filter-options">
            {availablePolityTypes.map((type) => {
              const selectedTypes = appState.filters.polity_types;
              const checked = selectedTypes.length === 0 || selectedTypes.includes(type);
              return (
                <label key={type} className="inline-check">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(event) =>
                      setAppState((state) => {
                        const currentTypes = state.filters.polity_types.length
                          ? state.filters.polity_types
                          : availablePolityTypes;
                        const nextTypes = event.target.checked
                          ? Array.from(new Set([...currentTypes, type]))
                          : currentTypes.filter((item) => item !== type);
                        return {
                          ...state,
                          filters: {
                            ...state.filters,
                            polity_types:
                              nextTypes.length === availablePolityTypes.length ? [] : nextTypes
                          }
                        };
                      })
                    }
                  />
                  {type}
                </label>
              );
            })}
          </div>
        </div>
      ) : null}
      <label className="settings-row">
        <span>疆域状态</span>
        <select
          value={appState.filters.territory_status}
          onChange={(event) =>
            setAppState((state) => ({
              ...state,
              filters: {
                ...state.filters,
                territory_status: event.target.value as AppState["filters"]["territory_status"]
              }
            }))
          }
        >
          <option value="all">全部</option>
          <option value="has_territory">已生成疆域</option>
          <option value="missing">无法估算</option>
        </select>
      </label>
      <label className="settings-row">
        <span>最低置信度 {appState.filters.min_confidence_score}</span>
        <input
          type="range"
          min="0"
          max="100"
          step="5"
          value={appState.filters.min_confidence_score}
          onChange={(event) =>
            setAppState((state) => ({
              ...state,
              filters: { ...state.filters, min_confidence_score: Number(event.target.value) }
            }))
          }
        />
      </label>
      <label className="inline-check">
        <input
          type="checkbox"
          checked={appState.filters.show_disputed}
          onChange={(event) =>
            setAppState((state) => ({
              ...state,
              filters: { ...state.filters, show_disputed: event.target.checked }
            }))
          }
        />
        显示争议项
      </label>
      <label className="inline-check">
        <input
          type="checkbox"
          checked={appState.filters.show_unmatched_ruler}
          onChange={(event) =>
            setAppState((state) => ({
              ...state,
              filters: { ...state.filters, show_unmatched_ruler: event.target.checked }
            }))
          }
        />
        显示未匹配君主年表
      </label>
    </>
  );
}
