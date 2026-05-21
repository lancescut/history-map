import { useCallback, type ChangeEvent } from "react";
import {
  Camera,
  Download,
  Pause,
  Play,
  RotateCcw,
  SkipBack,
  SkipForward,
  Upload
} from "lucide-react";
import { nextYear, previousYear } from "../data";
import type { StoredAppState } from "../state";
import type { Metadata } from "../types";

const PLAYBACK_SPEEDS = [0.5, 1, 2, 5, 10];

type AppStateUpdater = Partial<StoredAppState> | ((state: StoredAppState) => StoredAppState);
type SetAppState = (updater: AppStateUpdater) => void;

export function BottomBar({
  metadata,
  appState,
  jumpToYear,
  onTogglePlay,
  onReset,
  onSnapshot,
  onExportState,
  onTriggerImport,
  onImportFile,
  setAppState,
  importFileRef,
  currentYearEventCount
}: {
  metadata: Metadata | null;
  appState: StoredAppState;
  jumpToYear: (year: number) => void;
  onTogglePlay: () => void;
  onReset: () => void;
  onSnapshot: () => void;
  onExportState: () => void;
  onTriggerImport: () => void;
  onImportFile: (event: ChangeEvent<HTMLInputElement>) => void;
  setAppState: SetAppState;
  importFileRef: React.RefObject<HTMLInputElement | null>;
  currentYearEventCount: number;
}) {
  // 当前年事件数 + 预计耗时（2000ms/事件，受 playback_speed 缩放）。给用户一个"为什么这一年播这么久"的可读解释。
  const estimatedSeconds = Math.ceil((currentYearEventCount * 2000) / appState.timeline.playback_speed / 1000);
  const handleSpeedChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>) => {
      setAppState((state) => ({
        ...state,
        timeline: { ...state.timeline, playback_speed: Number(event.target.value) }
      }));
    },
    [setAppState]
  );

  return (
    <div className="bottom-bar" role="region" aria-label="播放控制与时间轴">
      <div className="bottom-bar__controls">
        <button
          onClick={() => metadata && jumpToYear(previousYear(appState.timeline.current_year, metadata.year_min))}
          aria-label="上一年"
          title="上一年"
        >
          <SkipBack size={15} />
        </button>
        <button
          className="primary-action"
          onClick={onTogglePlay}
          aria-label={appState.timeline.is_playing ? "暂停" : "播放"}
          title={appState.timeline.is_playing ? "暂停" : "播放"}
        >
          {appState.timeline.is_playing ? <Pause size={16} /> : <Play size={16} />}
        </button>
        <button
          onClick={() => metadata && jumpToYear(nextYear(appState.timeline.current_year, metadata.year_max))}
          aria-label="下一年"
          title="下一年"
        >
          <SkipForward size={15} />
        </button>
        <button onClick={onReset} aria-label="重置" title="重置时间与视角">
          <RotateCcw size={15} />
        </button>
      </div>

      <div className="bottom-bar__timeline">
        <input
          type="range"
          min={metadata?.year_min ?? -1046}
          max={metadata?.year_max ?? 1912}
          value={appState.timeline.current_year}
          onChange={(event) => jumpToYear(Number(event.target.value))}
          aria-label="年份滑块"
        />
      </div>

      <div className="bottom-bar__year">
        <input
          type="number"
          value={appState.timeline.current_year}
          onChange={(event) => jumpToYear(Number(event.target.value))}
          aria-label="年份输入"
        />
        {currentYearEventCount > 0 ? (
          <span
            className="bottom-bar__year-hint"
            title={`本年 ${currentYearEventCount} 条事件 · 按 ${appState.timeline.playback_speed}x 速度预计 ${estimatedSeconds} 秒播完才会推进下一年`}
          >
            · {currentYearEventCount} 条 · ~{estimatedSeconds}s
          </span>
        ) : null}
        <select
          value={appState.timeline.playback_speed}
          onChange={handleSpeedChange}
          aria-label="播放速度"
        >
          {PLAYBACK_SPEEDS.map((speed) => (
            <option key={speed} value={speed}>
              {speed}x
            </option>
          ))}
        </select>
      </div>

      <div className="bottom-bar__io">
        <button onClick={onSnapshot} aria-label="导出截图" title="导出地图截图 PNG">
          <Camera size={14} />
        </button>
        <button onClick={onExportState} aria-label="导出状态" title="导出当前状态 JSON">
          <Download size={14} />
        </button>
        <button onClick={onTriggerImport} aria-label="导入状态" title="导入状态 JSON">
          <Upload size={14} />
        </button>
        <input
          ref={importFileRef}
          type="file"
          accept="application/json,.json"
          style={{ display: "none" }}
          onChange={onImportFile}
        />
      </div>
    </div>
  );
}
