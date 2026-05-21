import { Search } from "lucide-react";
import type {
  DatasetId,
  Metadata,
  SearchEntry,
  StoryPreset,
  StoryPresetsData
} from "../types";

const DATASET_LABELS: Record<DatasetId, { short: string; full: string }> = {
  v03: { short: "中国", full: "中国史" },
  vIndian: { short: "印度", full: "印度史" }
};

function datasetButtonLabel(active: DatasetId[]): string {
  if (active.length === 0) return "选择数据源";
  if (active.length === 1) return DATASET_LABELS[active[0]].full;
  return active.map((id) => DATASET_LABELS[id].short).join(" + ");
}

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
  setSidePanelOpen,
  activeDatasets,
  datasetPickerOpen,
  setDatasetPickerOpen,
  onToggleDataset
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
  activeDatasets: DatasetId[];
  datasetPickerOpen: boolean;
  setDatasetPickerOpen: (next: boolean | ((prev: boolean) => boolean)) => void;
  onToggleDataset: (id: DatasetId) => void;
}) {
  const datasetLabelMap: Record<DatasetId, string> = { v03: "中国史", vIndian: "印度史" };
  const datasetTagInline = activeDatasets.map((id) => datasetLabelMap[id]).join(" + ");
  const title = activeDatasets.length === 1 && activeDatasets[0] === "v03"
    ? "中国朝代更迭地图"
    : `世界历史地图 · ${datasetTagInline}`;
  return (
    <header className="topbar">
      <div>
        <h1>{title}</h1>
        <p>
          {datasetTagInline} · {metadata?.polity_count ?? 0} 政权 · {metadata?.capital_event_count ?? 0} 都城事件 ·{" "}
          {metadata?.capital_migration_count ?? 0} 迁都事件 · {metadata?.historical_event_count ?? 0} 历史条目 ·{" "}
          {metadata?.strategic_location_count ?? 0} 战略要地 ·{" "}
          {metadata?.territory_polity_count ?? 0} 政权疆域
        </p>
      </div>
      <div className="search-box">
        <Search size={16} />
        <input
          value={searchText}
          onChange={(event) => setSearchText(event.target.value)}
          placeholder="搜索年份、政权、君主、都城或战略要地"
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
                  {entry.entity_type === "capital"
                    ? "都城"
                    : entry.entity_type === "ruler"
                      ? "君主"
                      : entry.entity_type === "strategic_location"
                        ? "战略要地"
                        : "政权/年份"}
                </small>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="story-picker-wrap dataset-picker-wrap">
        <button
          type="button"
          className={`story-picker-button ${activeDatasets.length > 1 ? "is-active" : ""}`}
          onClick={() => setDatasetPickerOpen((open) => !open)}
          title="选择播放数据源"
          aria-label="选择播放数据源"
        >
          🌐 {datasetButtonLabel(activeDatasets)}
        </button>
        {datasetPickerOpen ? (
          <div className="story-picker-menu" role="menu">
            {(["v03", "vIndian"] as DatasetId[]).map((id) => {
              const isLastChecked = activeDatasets.length === 1 && activeDatasets[0] === id;
              const checked = activeDatasets.includes(id);
              return (
                <label
                  key={id}
                  className={`story-picker-item dataset-picker-item ${checked ? "is-active" : ""}`}
                  title={isLastChecked ? "至少保留一个数据源" : undefined}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={isLastChecked}
                    onChange={() => onToggleDataset(id)}
                  />
                  <strong>{DATASET_LABELS[id].full}</strong>
                  <small>{id}</small>
                </label>
              );
            })}
            <div className="dataset-picker-hint">
              <small>多选时事件按 A-B-A-B 交错播放；同年所有事件播完才进下一年</small>
            </div>
          </div>
        ) : null}
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
                  <strong>
                    {preset.dataset_id === "vIndian" ? (
                      <span className="dataset-badge dataset-badge--in" style={{ marginRight: 6 }}>印</span>
                    ) : (
                      <span className="dataset-badge dataset-badge--cn" style={{ marginRight: 6 }}>中</span>
                    )}
                    {preset.title}
                  </strong>
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
