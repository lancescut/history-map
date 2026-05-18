import { useEffect, useState } from "react";

const STORAGE_KEY = "history_map_onboarding_v1";

interface Step {
  title: string;
  body: string;
  // Anchor 是 CSS 选择器；引导会从该元素的位置弹出。
  anchor: string;
  // 浮层相对锚点的方位
  placement: "bottom-left" | "bottom-right" | "right" | "left";
}

const STEPS: Step[] = [
  {
    title: "时间轴在这里",
    body: "拖动滑块或点击 ▶ 自动播放，看疆域随年份变化。也可以输入具体年份直接跳转。",
    anchor: ".timeline-card",
    placement: "left"
  },
  {
    title: "点击彩色区域选政权",
    body: "鼠标悬停彩色疆域会显示政权名与年代；点击进入选中状态。多个政权重叠时会弹出候选框。",
    anchor: ".maplibregl-canvas",
    placement: "right"
  },
  {
    title: "颜色对照看这里",
    body: "左侧「当前政权」图例列出当年所有政权的颜色，点击图例就能高亮 + 飞到该政权的疆域。",
    anchor: ".polity-legend",
    placement: "right"
  },
  {
    title: "试试演示路线",
    body: "顶部「演示路线」按钮已经准备好几条主题剧本，比如「三千年统一与分裂」。点开始即自动播放。",
    anchor: ".story-picker-button",
    placement: "bottom-left"
  }
];

export function OnboardingTour({
  onTriggerStoryPicker
}: {
  onTriggerStoryPicker: () => void;
}) {
  const [stepIndex, setStepIndex] = useState<number>(() => {
    if (typeof window === "undefined") return -1;
    const dismissed = window.localStorage.getItem(STORAGE_KEY);
    return dismissed ? -1 : 0;
  });
  const [anchorRect, setAnchorRect] = useState<DOMRect | null>(null);

  const step = stepIndex >= 0 && stepIndex < STEPS.length ? STEPS[stepIndex] : null;

  // 每步重新定位锚点；锚点未就绪时会重试 6 次（300ms 一次）
  useEffect(() => {
    if (!step) {
      setAnchorRect(null);
      return;
    }
    let attempts = 0;
    let cancelled = false;
    const measure = () => {
      if (cancelled) return;
      const el = document.querySelector<HTMLElement>(step.anchor);
      if (el) {
        setAnchorRect(el.getBoundingClientRect());
        return;
      }
      attempts += 1;
      if (attempts < 6) {
        window.setTimeout(measure, 300);
      }
    };
    measure();
    return () => {
      cancelled = true;
    };
  }, [step]);

  const dismiss = () => {
    try {
      window.localStorage.setItem(STORAGE_KEY, "dismissed");
    } catch {
      // localStorage 不可用时静默忽略（隐私模式）
    }
    setStepIndex(-1);
  };

  const goNext = () => {
    if (stepIndex === STEPS.length - 1) {
      dismiss();
      onTriggerStoryPicker();
      return;
    }
    setStepIndex((index) => index + 1);
  };

  if (!step) return null;

  // 计算浮层位置：依据锚点矩形 + placement 偏移
  const tooltipStyle = (() => {
    if (!anchorRect) return { left: 24, top: 96 };
    const margin = 12;
    const tooltipWidth = 280;
    const tooltipHeight = 156;
    let left = anchorRect.left;
    let top = anchorRect.bottom + margin;
    switch (step.placement) {
      case "bottom-left":
        left = Math.max(16, anchorRect.right - tooltipWidth);
        top = anchorRect.bottom + margin;
        break;
      case "bottom-right":
        left = Math.min(window.innerWidth - tooltipWidth - 16, anchorRect.left);
        top = anchorRect.bottom + margin;
        break;
      case "right":
        left = Math.min(window.innerWidth - tooltipWidth - 16, anchorRect.right + margin);
        top = Math.max(16, anchorRect.top);
        break;
      case "left":
        left = Math.max(16, anchorRect.left - tooltipWidth - margin);
        top = Math.max(16, anchorRect.top);
        break;
    }
    // 防止顶部出屏
    if (top + tooltipHeight > window.innerHeight - 16) {
      top = Math.max(16, window.innerHeight - tooltipHeight - 16);
    }
    return { left, top };
  })();

  return (
    <>
      <div className="onboarding-backdrop" onClick={dismiss} aria-hidden />
      {anchorRect ? (
        <div
          className="onboarding-spotlight"
          style={{
            left: anchorRect.left - 4,
            top: anchorRect.top - 4,
            width: anchorRect.width + 8,
            height: anchorRect.height + 8
          }}
          aria-hidden
        />
      ) : null}
      <div className="onboarding-step" style={tooltipStyle} role="dialog" aria-label={step.title}>
        <div className="onboarding-step__head">
          <strong>{step.title}</strong>
          <span>
            {stepIndex + 1} / {STEPS.length}
          </span>
        </div>
        <p>{step.body}</p>
        <div className="onboarding-step__controls">
          <button type="button" className="onboarding-step__skip" onClick={dismiss}>
            跳过
          </button>
          <button type="button" className="onboarding-step__next" onClick={goNext}>
            {stepIndex === STEPS.length - 1 ? "开始" : "下一步 →"}
          </button>
        </div>
      </div>
    </>
  );
}
