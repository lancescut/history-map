import { useEffect, useMemo, useRef, useState } from "react";
import type { LngLatLike, Map as MapLibreMap } from "maplibre-gl";
import { coverageRoleLabel } from "../event-meta";
import type { HistoricalEvent } from "../types";

// 位置持久化：每张卡首次落点后，整个生命周期（entering→active→exiting）保留在该位置；
// 新进卡片只与已记忆位置避让。地图相同的地理坐标 + 同一 placeLeft 选择得到稳定的 anchor。
interface CachedPlacement {
  // 锚点（基于地理坐标 + 屏幕投影实时算）
  lng: number;
  lat: number;
  placeLeft: boolean;
  // 相对锚点的 callout 偏移（首次确定后不再变化）
  offsetX: number;
  offsetY: number;
}

export type MapEventPulseStatus = "entering" | "active" | "exiting";

export interface MapEventPulseItem {
  instanceId: string;
  event: HistoricalEvent;
  status: MapEventPulseStatus;
}

interface ProjectedEvent {
  item: MapEventPulseItem;
  point: { x: number; y: number };
  callout: { x: number; y: number; width: number; height: number; placeLeft: boolean };
}

interface MapEventOverlayProps {
  map: MapLibreMap | null;
  items: MapEventPulseItem[];
  onFlyToEvent?: (lng: number, lat: number) => void;
}

const CALLOUT_WIDTH = 252;
// 高度需≥实际渲染最大高度（含 2-line desc + place 行），否则 collision 算法会漏算导致 7-15px 重叠。
// CSS 同步 max-height + overflow:hidden 保证不超过该值。
const CALLOUT_HEIGHT = 140;
const EDGE_PADDING = 14;

function eventColorClass(event: HistoricalEvent): string {
  if (event.is_anecdote || event.item_kind === "anecdote" || event.event_type === "allusion") return "map-event--anecdote";
  if (event.coverage_role === "range_anchor") return "map-event--range";
  if (event.coverage_role === "annual_chronicle") return "map-event--chronicle";
  const eventType = event.event_type;
  if (eventType.includes("war")) return "map-event--war";
  if (eventType.includes("start")) return "map-event--start";
  if (eventType.includes("end")) return "map-event--end";
  if (eventType.includes("reform") || eventType.includes("institution")) return "map-event--institution";
  if (eventType.includes("treaty") || eventType.includes("diplomacy")) return "map-event--diplomacy";
  return "map-event--default";
}

function eventCoordinates(event: HistoricalEvent): [number, number] | null {
  const lng = event.location?.longitude ?? event.longitude;
  const lat = event.location?.latitude ?? event.latitude;
  if (typeof lng !== "number" || typeof lat !== "number") return null;
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) return null;
  return [lng, lat];
}

function stageLabel(event: HistoricalEvent): string {
  return event.primary_education_stage || event.education_stage_tags?.[0] || "";
}

function coverageLabel(event: HistoricalEvent): string {
  return event.coverage_role ? coverageRoleLabel(event.coverage_role) : "";
}

export function MapEventOverlay({ map, items, onFlyToEvent }: MapEventOverlayProps) {
  const [projected, setProjected] = useState<ProjectedEvent[]>([]);
  // 每个 instanceId 的首次落点（offsetX/offsetY 相对锚点）；item 整个生命周期使用此偏移
  const placementsRef = useRef<Map<string, CachedPlacement>>(new Map());

  useEffect(() => {
    if (!map) {
      setProjected([]);
      return;
    }

    const update = () => {
      const container = map.getContainer();
      const width = container.clientWidth || 0;
      const height = container.clientHeight || 0;
      const gap = 8;
      const placements = placementsRef.current;

      // 第一遍：剔除已不在 items 中的位置缓存
      const currentIds = new Set(items.map((item) => item.instanceId));
      for (const id of Array.from(placements.keys())) {
        if (!currentIds.has(id)) placements.delete(id);
      }

      // 第二遍：用 items 顺序遍历。已有 placement 的卡片直接复用锚点+偏移；
      // 新卡（无 placement）才走碰撞算法，且 vs 已记忆+本次已计算的所有位置避让。
      // 这里的 placed 数组用于排序后的碰撞集合（包含所有已分配位置的卡片，无论 entering/active/exiting）
      const placed: ProjectedEvent[] = [];

      const collidesAny = (x: number, y: number): ProjectedEvent | null => {
        for (const other of placed) {
          if (
            x < other.callout.x + other.callout.width + gap &&
            x + CALLOUT_WIDTH + gap > other.callout.x &&
            y < other.callout.y + other.callout.height + gap &&
            y + CALLOUT_HEIGHT + gap > other.callout.y
          ) {
            return other;
          }
        }
        return null;
      };

      // 先处理已有 placement 的（保持位置稳定，不参与碰撞重算）
      const newItems: typeof items = [];
      items.forEach((item) => {
        const coordinates = eventCoordinates(item.event);
        if (!coordinates) return;
        const cached = placements.get(item.instanceId);
        const point = map.project(coordinates as LngLatLike);
        if (point.x < -80 || point.y < -80 || point.x > width + 80 || point.y > height + 80) {
          // 滑出可视区，仍保留 placement（重新进入时位置不变）；只是这一帧不渲染
          return;
        }
        if (cached) {
          // 用缓存的相对偏移 + 当前锚点
          const x = point.x + cached.offsetX;
          const y = point.y + cached.offsetY;
          placed.push({
            item,
            point: { x: point.x, y: point.y },
            callout: { x, y, width: CALLOUT_WIDTH, height: CALLOUT_HEIGHT, placeLeft: cached.placeLeft }
          });
        } else {
          newItems.push(item);
        }
      });

      // 再处理新卡片：与所有已记忆位置（包含 exiting）避让
      newItems.forEach((item) => {
        const coordinates = eventCoordinates(item.event);
        if (!coordinates) return;
        const point = map.project(coordinates as LngLatLike);
        if (point.x < -80 || point.y < -80 || point.x > width + 80 || point.y > height + 80) {
          return;
        }
        const placeLeft = point.x + CALLOUT_WIDTH + 34 > width - EDGE_PADDING;
        const rawX = placeLeft ? point.x - CALLOUT_WIDTH - 28 : point.x + 28;
        const rawY = point.y - 78;
        let x = Math.min(Math.max(rawX, EDGE_PADDING), Math.max(EDGE_PADDING, width - CALLOUT_WIDTH - EDGE_PADDING));
        let y = Math.min(Math.max(rawY, 74), Math.max(74, height - CALLOUT_HEIGHT - 96));

        let finalPlaceLeft = placeLeft;
        for (let attempt = 0; attempt < 8; attempt += 1) {
          const blocker = collidesAny(x, y);
          if (!blocker) break;
          const tryDown = blocker.callout.y + blocker.callout.height + gap;
          if (tryDown + CALLOUT_HEIGHT <= height - 96) {
            y = tryDown;
            continue;
          }
          const tryUp = blocker.callout.y - CALLOUT_HEIGHT - gap;
          if (tryUp >= 74) {
            y = tryUp;
            continue;
          }
          // 上下没空间：换边
          finalPlaceLeft = !finalPlaceLeft;
          x = finalPlaceLeft
            ? Math.max(EDGE_PADDING, point.x - CALLOUT_WIDTH - 28)
            : Math.min(width - CALLOUT_WIDTH - EDGE_PADDING, point.x + 28);
          y = Math.min(Math.max(rawY, 74), Math.max(74, height - CALLOUT_HEIGHT - 96));
        }

        // 记忆该新卡的偏移（相对锚点点 point.x/y），后续地图平移缩放时按相对偏移复算 x/y
        placements.set(item.instanceId, {
          lng: coordinates[0],
          lat: coordinates[1],
          placeLeft: finalPlaceLeft,
          offsetX: x - point.x,
          offsetY: y - point.y
        });

        placed.push({
          item,
          point: { x: point.x, y: point.y },
          callout: { x, y, width: CALLOUT_WIDTH, height: CALLOUT_HEIGHT, placeLeft: finalPlaceLeft }
        });
      });

      setProjected(placed);
    };

    update();
    map.on("move", update);
    map.on("zoom", update);
    map.on("resize", update);
    window.addEventListener("resize", update);
    return () => {
      map.off("move", update);
      map.off("zoom", update);
      map.off("resize", update);
      window.removeEventListener("resize", update);
    };
  }, [map, items]);

  const connectors = useMemo(
    () =>
      // 连接线也保留 exiting 项让其随 callout 一起淡出（CSS 控制 stroke-opacity）
      projected.map(({ item, point, callout }) => {
        const targetX = callout.placeLeft ? callout.x + callout.width : callout.x;
        const targetY = callout.y + 45;
        return { id: item.instanceId, status: item.status, x1: point.x, y1: point.y, x2: targetX, y2: targetY };
      }),
    [projected]
  );

  if (!projected.length) return null;

  return (
    <div className="map-event-overlay" aria-hidden="false">
      <svg className="map-event-connectors" aria-hidden="true">
        {connectors.map((line) => (
          <line
            key={line.id}
            className={`map-event-connector map-event-connector--${line.status}`}
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
          />
        ))}
      </svg>
      {projected.map(({ item, point, callout }) => {
        const event = item.event;
        const coordinates = eventCoordinates(event);
        const colorClass = eventColorClass(event);
        const historicalName = event.location?.historical_name || event.location_historical_name || event.location_name;
        const modernName = event.location?.modern_name || event.location_modern_name || event.location_name;
        const metaLabel = [stageLabel(event), coverageLabel(event)].filter(Boolean).join(" · ");
        return (
          <div key={item.instanceId} className={`map-event-layer map-event-layer--${item.status} ${colorClass}`}>
            <button
              type="button"
              className="map-event-pulse"
              style={{ left: point.x, top: point.y }}
              aria-label={`${event.date_label} ${event.title}`}
              onClick={() => {
                if (coordinates) onFlyToEvent?.(coordinates[0], coordinates[1]);
              }}
              tabIndex={item.status === "exiting" ? -1 : 0}
            >
              <span />
            </button>
            {/* callout 始终渲染；状态变化只切 CSS 类，opacity/transform 由 transition 接管 */}
            <article
              className={`map-event-callout ${callout.placeLeft ? "map-event-callout--left" : "map-event-callout--right"}`}
              style={{ left: callout.x, top: callout.y }}
              aria-hidden={item.status === "exiting"}
            >
              <div className="map-event-callout__meta">
                <span>{event.date_label}</span>
                <span>{metaLabel}</span>
              </div>
              <h3>{event.title}</h3>
              <p>{event.description}</p>
              <div className="map-event-callout__place">
                <span>{historicalName}</span>
                <span>{modernName}</span>
              </div>
            </article>
          </div>
        );
      })}
    </div>
  );
}
