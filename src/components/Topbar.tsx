import { Search } from "lucide-react";
import type {
  Metadata,
  SearchEntry,
  StoryPreset,
  StoryPresetsData
} from "../types";

export function Topbar({
  metadata,
  searchText,
  setSearchText,
  searchResults,
  onSearchSelect,
  storyPresets,
  activeStory,
  storyPickerOpen,
  setStoryPickerOpen,
  onSelectStory,
  onExitStory,
  validationSummary,
  qualityPanelOpen,
  setQualityPanelOpen,
  sidePanelOpen,
  setSidePanelOpen
}: {
  metadata: Metadata | null;
  searchText: string;
  setSearchText: (next: string) => void;
  searchResults: SearchEntry[];
  onSearchSelect: (entry: SearchEntry) => void;
  storyPresets: StoryPresetsData | null;
  activeStory: StoryPreset | null;
  storyPickerOpen: boolean;
  setStoryPickerOpen: (next: boolean | ((prev: boolean) => boolean)) => void;
  onSelectStory: (preset: StoryPreset) => void;
  onExitStory: () => void;
  validationSummary: { total: number; pass: number; warn: number; fail: number };
  qualityPanelOpen: boolean;
  setQualityPanelOpen: (next: boolean | ((prev: boolean) => boolean)) => void;
  sidePanelOpen: boolean;
  setSidePanelOpen: (next: boolean | ((prev: boolean) => boolean)) => void;
}) {
  return (
    <header className="topbar">
      <div>
        <h1>中国朝代更迭地图</h1>
        <p>
          v03 · {metadata?.polity_count ?? 0} 政权 · {metadata?.capital_event_count ?? 0} 都城事件 ·{" "}
          {metadata?.capital_migration_count ?? 0} 迁都事件 · {metadata?.historical_event_count ?? 0} 历史条目 ·{" "}
          {metadata?.territory_polity_count ?? 0} 县级索引疆域
        </p>
      </div>
      <div className="search-box">
        <Search size={16} />
        <input
          value={searchText}
          onChange={(event) => setSearchText(event.target.value)}
          placeholder="搜索年份、政权、君主或都城"
        />
        {searchResults.length > 0 && (
          <div className="search-results">
            {searchResults.map((entry) => (
              <button
                key={`${entry.entity_type}-${entry.entity_id}-${entry.alias}`}
                onClick={() => onSearchSelect(entry)}
              >
                <span>{entry.alias}</span>
                <small>
                  {entry.entity_type === "capital" ? "都城" : entry.entity_type === "ruler" ? "君主" : "政权/年份"}
                </small>
              </button>
            ))}
          </div>
        )}
      </div>
      {storyPresets?.presets.length ? (
        <div className="story-picker-wrap">
          <button
            type="button"
            className={`story-picker-button ${activeStory ? "is-active" : ""}`}
            onClick={() => setStoryPickerOpen((open) => !open)}
            title="演示路线"
            aria-label="演示路线"
          >
            ▶ {activeStory ? activeStory.title : "演示路线"}
          </button>
          {storyPickerOpen ? (
            <div className="story-picker-menu" role="menu">
              {storyPresets.presets.map((preset) => (
                <button
                  key={preset.preset_id}
                  type="button"
                  className={`story-picker-item ${
                    activeStory?.preset_id === preset.preset_id ? "is-active" : ""
                  }`}
                  title={preset.subtitle}
                  onClick={() => onSelectStory(preset)}
                >
                  <strong>{preset.title}</strong>
                  <small>
                    {preset.subtitle} · {preset.steps.length} 幕
                  </small>
                </button>
              ))}
              {activeStory ? (
                <button
                  type="button"
                  className="story-picker-item story-picker-item--exit"
                  onClick={onExitStory}
                >
                  <strong>退出演示路线</strong>
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
      <button
        type="button"
        className={`quality-button ${
          validationSummary.warn || validationSummary.fail ? "quality-button--warn" : ""
        }`}
        onClick={() => setQualityPanelOpen((open) => !open)}
        title="数据质量与争议项"
      >
        数据质量 · {validationSummary.pass}/{validationSummary.total}
        {validationSummary.warn ? ` · ${validationSummary.warn} WARN` : ""}
      </button>
      <button
        type="button"
        className="panel-toggle-button"
        onClick={() => setSidePanelOpen((open) => !open)}
        title={sidePanelOpen ? "隐藏右侧信息面板" : "显示右侧信息面板"}
        aria-label={sidePanelOpen ? "隐藏右侧信息面板" : "显示右侧信息面板"}
      >
        {sidePanelOpen ? "›" : "‹"}
      </button>
    </header>
  );
}
