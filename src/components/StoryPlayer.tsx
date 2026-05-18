import { Pause, Play, SkipBack, SkipForward } from "lucide-react";
import { yearLabel } from "../data";
import type { StoryPreset } from "../types";

export function StoryPlayer({
  activeStory,
  storyStepIndex,
  storyAutoAdvance,
  onExit,
  onPrev,
  onNext,
  onToggleAutoAdvance
}: {
  activeStory: StoryPreset;
  storyStepIndex: number;
  storyAutoAdvance: boolean;
  onExit: () => void;
  onPrev: () => void;
  onNext: () => void;
  onToggleAutoAdvance: () => void;
}) {
  return (
    <div className="story-player" role="region" aria-label="演示路线播放">
      <div className="story-player__head">
        <div>
          <strong>{activeStory.title}</strong>
          <span>
            第 {storyStepIndex + 1} / {activeStory.steps.length} 幕 · {activeStory.subtitle}
          </span>
        </div>
        <button type="button" onClick={onExit} aria-label="退出演示路线" title="退出">
          ×
        </button>
      </div>
      <p className="story-player__narration">
        <span className="story-player__year">{yearLabel(activeStory.steps[storyStepIndex].year)}</span>
        {activeStory.steps[storyStepIndex].narration}
      </p>
      <div className="story-player__controls">
        <button type="button" disabled={storyStepIndex === 0} onClick={onPrev} aria-label="上一幕">
          <SkipBack size={15} />
        </button>
        <button
          type="button"
          className="primary-action"
          onClick={onToggleAutoAdvance}
          aria-label={storyAutoAdvance ? "暂停自动播放" : "继续自动播放"}
        >
          {storyAutoAdvance ? <Pause size={15} /> : <Play size={15} />}
        </button>
        <button
          type="button"
          disabled={storyStepIndex >= activeStory.steps.length - 1}
          onClick={onNext}
          aria-label="下一幕"
        >
          <SkipForward size={15} />
        </button>
      </div>
    </div>
  );
}
