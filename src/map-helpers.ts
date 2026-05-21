import maplibregl, { LngLatBoundsLike } from "maplibre-gl";
import polylabel from "polylabel";
import type {
  AppState,
  CapitalEvent,
  StrategicLocation,
  StrategicLocationFeatureProperties,
  TerritoryFeatureProperties,
  TerritoryHatchFeatureProperties,
  YearData,
  YearPolity
} from "./types";

// 物理底图配色：陆地浅米，海洋蓝灰，统一处理避免政治化染色（MRD §6.1 MAP-002）
export const LAND_FILL = "#e6dcc4";
export const LAND_OUTLINE = "rgba(120, 110, 90, 0.42)";
export const OCEAN_FILL = "#a8c6dd";
export const LAKE_FILL = "#b9d6ea";
export const RIVER_LINE = "#7aa5c8";
export const GLACIER_FILL = "#f4f8fb";

export interface GraticuleLineProperties {
  graticule_type: "meridian" | "parallel";
  value: number;
  label: string;
  is_major: boolean;
}

export interface GraticuleLabelProperties {
  label: string;
  graticule_type: "longitude" | "latitude";
  value: number;
}

export function formatLongitude(value: number): string {
  if (value === 0) return "0°";
  return `${Math.abs(value)}°${value < 0 ? "W" : "E"}`;
}

export function formatLatitude(value: number): string {
  if (value === 0) return "0°";
  return `${Math.abs(value)}°${value < 0 ? "S" : "N"}`;
}

export function formatCoordinatePair(lng: number, lat: number): string {
  return `${formatLongitude(Number(lng.toFixed(2)))} / ${formatLatitude(Number(lat.toFixed(2)))}`;
}

export function buildGraticule(): {
  lines: GeoJSON.FeatureCollection<GeoJSON.LineString, GraticuleLineProperties>;
  labels: GeoJSON.FeatureCollection<GeoJSON.Point, GraticuleLabelProperties>;
} {
  const lineFeatures: GeoJSON.Feature<GeoJSON.LineString, GraticuleLineProperties>[] = [];
  const labelFeatures: GeoJSON.Feature<GeoJSON.Point, GraticuleLabelProperties>[] = [];
  for (let longitude = -180; longitude <= 180; longitude += 10) {
    const isMajor = longitude % 20 === 0;
    const label = formatLongitude(longitude);
    lineFeatures.push({
      type: "Feature",
      geometry: {
        type: "LineString",
        coordinates: [
          [longitude, -80],
          [longitude, 85]
        ]
      },
      properties: {
        graticule_type: "meridian",
        value: longitude,
        label,
        is_major: isMajor
      }
    });
    if (isMajor && longitude !== -180 && longitude !== 180) {
      labelFeatures.push({
        type: "Feature",
        geometry: { type: "Point", coordinates: [longitude, 18] },
        properties: { label, graticule_type: "longitude", value: longitude }
      });
    }
  }
  for (let latitude = -80; latitude <= 80; latitude += 10) {
    const isMajor = latitude % 20 === 0;
    const label = formatLatitude(latitude);
    lineFeatures.push({
      type: "Feature",
      geometry: {
        type: "LineString",
        coordinates: [
          [-180, latitude],
          [180, latitude]
        ]
      },
      properties: {
        graticule_type: "parallel",
        value: latitude,
        label,
        is_major: isMajor
      }
    });
    if (isMajor) {
      labelFeatures.push({
        type: "Feature",
        geometry: { type: "Point", coordinates: [142, latitude] },
        properties: { label, graticule_type: "latitude", value: latitude }
      });
    }
  }
  return {
    lines: { type: "FeatureCollection", features: lineFeatures },
    labels: { type: "FeatureCollection", features: labelFeatures }
  };
}

export const BASEMAP_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    "ne-ocean": { type: "geojson", data: "/data/basemap/ne_110m_ocean.geojson" },
    "ne-land": { type: "geojson", data: "/data/basemap/ne_110m_land.geojson" },
    "ne-coastline": { type: "geojson", data: "/data/basemap/ne_110m_coastline.geojson" },
    "ne-lakes": { type: "geojson", data: "/data/basemap/ne_110m_lakes.geojson" },
    "ne-rivers": { type: "geojson", data: "/data/basemap/ne_110m_rivers_lake_centerlines.geojson" },
    "ne-glaciers": { type: "geojson", data: "/data/basemap/ne_110m_glaciated_areas.geojson" },
    "ne-geographic-lines": { type: "geojson", data: "/data/basemap/ne_110m_geographic_lines.geojson" },
    "ne-modern-borders": {
      type: "geojson",
      data: "/data/basemap/ne_110m_admin_0_boundary_lines_land.geojson"
    },
    "cn-borders": {
      type: "geojson",
      data: "/data/basemap/cn_standard_world_borders.geojson"
    }
  },
  layers: [
    { id: "background", type: "background", paint: { "background-color": OCEAN_FILL } },
    {
      id: "ne-ocean-fill",
      type: "fill",
      source: "ne-ocean",
      paint: { "fill-color": OCEAN_FILL, "fill-opacity": 1 }
    },
    {
      id: "ne-land-fill",
      type: "fill",
      source: "ne-land",
      paint: { "fill-color": LAND_FILL, "fill-opacity": 0.97 }
    },
    {
      id: "ne-coastline",
      type: "line",
      source: "ne-coastline",
      paint: {
        "line-color": "rgba(98, 88, 70, 0.7)",
        "line-width": ["interpolate", ["linear"], ["zoom"], 1, 0.4, 5, 0.9]
      }
    },
    {
      id: "ne-lakes-fill",
      type: "fill",
      source: "ne-lakes",
      paint: { "fill-color": LAKE_FILL, "fill-opacity": 0.92 }
    },
    {
      id: "ne-lakes-outline",
      type: "line",
      source: "ne-lakes",
      paint: { "line-color": "rgba(70, 110, 140, 0.5)", "line-width": 0.4 }
    },
    {
      id: "ne-rivers",
      type: "line",
      source: "ne-rivers",
      paint: {
        "line-color": RIVER_LINE,
        "line-width": ["interpolate", ["linear"], ["zoom"], 1, 0.4, 5, 1.1],
        "line-opacity": 0.85
      }
    },
    {
      id: "ne-glaciers-fill",
      type: "fill",
      source: "ne-glaciers",
      paint: { "fill-color": GLACIER_FILL, "fill-opacity": 0.85 }
    },
    {
      id: "ne-geographic-lines",
      type: "line",
      source: "ne-geographic-lines",
      layout: { visibility: "none" },
      paint: {
        "line-color": "rgba(120, 110, 90, 0.35)",
        "line-width": 0.5,
        "line-dasharray": [3, 3]
      }
    },
    {
      id: "ne-modern-borders",
      type: "line",
      source: "ne-modern-borders",
      paint: {
        "line-color": LAND_OUTLINE,
        "line-width": ["interpolate", ["linear"], ["zoom"], 1, 0.3, 5, 0.7],
        "line-dasharray": [2, 2],
        "line-opacity": 0.7
      }
    },
    {
      // 国界（中国官方标准对齐）—— 深灰加重虚线
      // 数据由 scripts/prepare_cn_standard_borders.py 生成（echarts world.json + 九段线）
      // 默认 visibility:none，由 state.layers.cn_border_overlay + applyPhysicalBasemapVisibility 控制
      // App.tsx 在 mapReady 后会 moveLayer 把该层提到 territory-fill 之上、territory-labels 之下
      id: "cn-borders-line",
      type: "line",
      source: "cn-borders",
      layout: { visibility: "none" },
      paint: {
        "line-color": "#3a3a3a",
        "line-width": ["interpolate", ["linear"], ["zoom"], 1, 0.7, 5, 1.4],
        "line-dasharray": [4, 3],
        "line-opacity": 0.88
      }
    }
  ]
};

export function polityDisplayName(polity: Pick<YearPolity, "polity_name" | "polity_display_name">): string {
  return polity.polity_display_name || polity.polity_name;
}

export const EXTERNAL_TERRITORY_MARKERS = [
  "蒙古国",
  "俄罗斯",
  "哈萨克",
  "吉尔吉斯",
  "塔吉克",
  "乌兹别克",
  "中亚",
  "西伯利亚",
  "库页岛",
  "越南",
  "缅甸",
  "老挝",
  "朝鲜半岛"
];

// 政权配色策略：每个 polity_id 在整个色轮上获得一个稳定的色相（用黄金角散布让相邻
// polity_id 的颜色也尽可能拉开），饱和度与亮度同样由 hash 决定。这样：
//   - 同一 polity 跨所有年份始终是同一颜色（hash(polity_id) 是纯函数）
//   - 不同 polity 之间最大化色相区分度，便于在同年并存时辨认
// 历史版本基于 macro_period 共享 base hue 的设计，会让同期政权颜色过近（如隋唐期间
// 唐/吐蕃/南诏/回鹘/渤海全部挤在金黄色窄带里），已弃用。macroPeriod 参数仅作 sat
// 微调以保留一点"时期气质"。
export const MACRO_PERIOD_SAT_BIAS: Record<string, number> = {
  周: -4,
  秦汉: 0,
  三国: 4,
  两晋: 0,
  魏晋南北朝: 4,
  隋唐: 0,
  五代十国: 4,
  宋辽金夏: -4,
  元明清: 0
};

function stableHash(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash;
}

// MurmurHash3 finalizer：把可能相邻的 hash（来自 "polity_0026" / "polity_0131" 这种
// 共前缀+连续编号的字符串）充分打散到 32 位空间。否则黄金角乘法对相邻 hash 不敏感，
// 会产生肉眼相同的色相（北宋 polity_0026 vs 西夏 polity_0131 此前 Δ=0.4°，实测撞色）。
function mixHash(h: number): number {
  h = Math.imul(h ^ (h >>> 16), 0x85ebca6b);
  h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35);
  return (h ^ (h >>> 16)) >>> 0;
}

// Okabe-Ito (Wong) 色盲安全调色板。学界经典 8 色（含黑，但黑在浅底图上对比太强，仅保留 7 色）。
// 参考 Wong, B. (2011) Color blindness, Nature Methods 8(6):441.
// 顺序保留视觉差异最大原则：橙 / 天蓝 / 蓝绿 / 黄 / 蓝 / 朱红 / 红紫
const OKABE_ITO_PALETTE = [
  "#E69F00", // orange
  "#56B4E9", // sky blue
  "#009E73", // bluish green
  "#F0E442", // yellow
  "#0072B2", // blue
  "#D55E00", // vermillion
  "#CC79A7", // reddish purple
  "#7E5BAA"  // purple（补 1 色，进一步降低同年冲突概率）
];

export type ColorPalette = "default" | "colorblind";

// 多源场景下让印度政权与中国政权视觉分簇：
//   v03 = 全色相均匀分布（默认值，不动既有色彩）
//   vIndian = 偏暖色区间（hue 主要落在 10-100 / 320-360，红橙黄棕系），与印度文化的暖色直觉一致
const DATASET_HUE_RANGE: Record<string, { offset: number; range: number }> = {
  v03: { offset: 0, range: 360 },
  vIndian: { offset: -25, range: 130 }
};

export function macroPeriodColor(
  macroPeriod: string,
  polityId: string,
  palette: ColorPalette = "default",
  datasetId?: string
): string {
  const mixed = mixHash(stableHash(polityId));
  if (palette === "colorblind") {
    // Okabe-Ito 8 色 + macro_period 偏移，降低同时代撞色概率。
    const periodShift = MACRO_PERIOD_SHIFT[macroPeriod] ?? 0;
    const index = (mixed + periodShift) % OKABE_ITO_PALETTE.length;
    return OKABE_ITO_PALETTE[index];
  }
  // 默认调色板：用 mixed hash 直接 [0,1) → [0,360) 均匀分布。
  // 多源场景给印度一个偏暖色色带，与中国全色相区分。
  const range = DATASET_HUE_RANGE[datasetId ?? "v03"] ?? DATASET_HUE_RANGE.v03;
  const normalized = (mixed >>> 0) / 4294967296;
  const hue = (range.offset + normalized * range.range + 360) % 360;
  const baseSat = 60 + ((mixed >> 4) % 22); // 60-81
  const light = 44 + ((mixed >> 12) % 16); // 44-59
  const satBias = MACRO_PERIOD_SAT_BIAS[macroPeriod] ?? 0;
  const sat = Math.max(50, Math.min(86, baseSat + satBias));
  return `hsl(${hue.toFixed(1)}, ${sat}%, ${light}%)`;
}


// 给每个 macro_period 一个素数偏移，使同时代多政权落到不同 palette 槽位（降低近邻撞色）。
const MACRO_PERIOD_SHIFT: Record<string, number> = {
  夏商西周: 0,
  春秋战国: 3,
  秦汉: 1,
  魏晋南北朝: 5,
  隋唐五代: 2,
  宋辽金夏: 7,
  元明清: 4
};

// ----- 颜色感知一致性：图例 swatch 要显示「地图上实际看到的颜色」 -----
//
// 地图 territory-fill-current 的 fill-opacity 是 0.84(选中) / 0.48(游牧) / 0.68(普通)，
// 叠加在浅米色 LAND_FILL (#e6dcc4) 上。图例若用 100% 不透明源色，肉眼会觉得"图例更鲜艳"。
// 这里做一次 alpha 合成：return effective_rgb = base * α + land * (1-α)

const LAND_RGB = { r: 0xe6, g: 0xdc, b: 0xc4 };

function parseHslColor(s: string): { h: number; sat: number; light: number } | null {
  const m = /hsl\(([\d.]+),\s*([\d.]+)%,\s*([\d.]+)%\)/i.exec(s);
  if (!m) return null;
  return { h: parseFloat(m[1]), sat: parseFloat(m[2]), light: parseFloat(m[3]) };
}

function hslToRgb(h: number, sat: number, light: number): { r: number; g: number; b: number } {
  const s = sat / 100;
  const l = light / 100;
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  let r = 0;
  let g = 0;
  let b = 0;
  if (h < 60) [r, g, b] = [c, x, 0];
  else if (h < 120) [r, g, b] = [x, c, 0];
  else if (h < 180) [r, g, b] = [0, c, x];
  else if (h < 240) [r, g, b] = [0, x, c];
  else if (h < 300) [r, g, b] = [x, 0, c];
  else [r, g, b] = [c, 0, x];
  return {
    r: Math.round((r + m) * 255),
    g: Math.round((g + m) * 255),
    b: Math.round((b + m) * 255)
  };
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const m = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex.trim());
  if (!m) return null;
  return { r: parseInt(m[1], 16), g: parseInt(m[2], 16), b: parseInt(m[3], 16) };
}

function colorToRgb(color: string): { r: number; g: number; b: number } {
  if (color.startsWith("#")) {
    const rgb = hexToRgb(color);
    if (rgb) return rgb;
  }
  const hsl = parseHslColor(color);
  if (hsl) return hslToRgb(hsl.h, hsl.sat, hsl.light);
  return { r: 0, g: 0, b: 0 };
}

function blendOverLand(color: string, opacity: number): string {
  const rgb = colorToRgb(color);
  const r = Math.round(rgb.r * opacity + LAND_RGB.r * (1 - opacity));
  const g = Math.round(rgb.g * opacity + LAND_RGB.g * (1 - opacity));
  const b = Math.round(rgb.b * opacity + LAND_RGB.b * (1 - opacity));
  return `rgb(${r}, ${g}, ${b})`;
}

// 公开 API：返回地图上实际看到的政权疆域填色（图例/选中标识等 UI 应用该值，
// 与地图 territory-fill-current 的 fill-opacity 表达式保持同步：
//   - 普通 / 选中政权：1.0 不透明 → 直接返回源色（不与 land 混合）
//   - 游牧政权：0.55 半透明 → 与 land 做 alpha 合成
// 这样图例 swatch RGB 与地图 canvas 像素 RGB 严格一致。
export function effectiveTerritoryColor(
  macroPeriod: string,
  polityId: string,
  isNomadic: boolean,
  options: { palette?: ColorPalette; selected?: boolean; datasetId?: string } = {}
): string {
  void options.selected; // selected 不影响 fill 色（已改用 outline 区分）
  const baseColor = macroPeriodColor(macroPeriod, polityId, options.palette ?? "default", options.datasetId);
  if (!isNomadic) return baseColor;
  return blendOverLand(baseColor, 0.55);
}

export function isPolityNomadic(polity: YearPolity): boolean {
  if (typeof polity.is_nomadic === "boolean") return polity.is_nomadic;
  // 多源场景下 vIndian polity 缺 ethnicity_or_group / ruling_family_or_clan 字段，全程用 ?? 兜底
  const haystack = `${polity.polity_type ?? ""}${polity.ethnicity_or_group ?? ""}${polity.ruling_family_or_clan ?? ""}`;
  return /游牧|匈奴|鲜卑|柔然|突厥|回鹘|丁零|高车|敕勒|乌孙|月氏|乌桓|吐谷浑/.test(haystack);
}

export function hasExternalTerritoryText(sourceText: string): boolean {
  return EXTERNAL_TERRITORY_MARKERS.some((marker) => sourceText.includes(marker));
}

export function emptyTerritoryCollection(): GeoJSON.FeatureCollection<
  GeoJSON.MultiPolygon,
  TerritoryFeatureProperties
> {
  return { type: "FeatureCollection", features: [] };
}

export function emptyHatchCollection(): GeoJSON.FeatureCollection<
  GeoJSON.LineString,
  TerritoryHatchFeatureProperties
> {
  return { type: "FeatureCollection", features: [] };
}

export function emptyLabelCollection(): GeoJSON.FeatureCollection<GeoJSON.Point> {
  return { type: "FeatureCollection", features: [] };
}

export function emptyFeatureCollection(): GeoJSON.FeatureCollection {
  return { type: "FeatureCollection", features: [] };
}

export function emptyStrategicLocationCollection(): GeoJSON.FeatureCollection<
  GeoJSON.Point,
  StrategicLocationFeatureProperties
> {
  return { type: "FeatureCollection", features: [] };
}

export function isStrategicLocationActive(location: StrategicLocation, year: number): boolean {
  if (location.active_years.includes(year)) return true;
  if (location.start_year != null && location.end_year != null && location.start_year === year && location.end_year === year) {
    return true;
  }
  return location.active_year_ranges.some((range) => year >= range.start_year && year <= range.end_year);
}

export function strategicLocationFeatureCollection(
  locations: StrategicLocation[] | null,
  year: number,
  options: { includeNonDefault?: boolean } = {}
): GeoJSON.FeatureCollection<GeoJSON.Point, StrategicLocationFeatureProperties> {
  if (!locations?.length) return emptyStrategicLocationCollection();
  const includeNonDefault = options.includeNonDefault ?? false;
  return {
    type: "FeatureCollection",
    features: locations
      .filter((location) => includeNonDefault || location.default_visible)
      .map((location) => {
        const activeNow = isStrategicLocationActive(location, year);
        return {
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [location.longitude, location.latitude]
          },
          properties: {
            location_id: location.location_id,
            name: location.name,
            aliases: location.aliases.join("|"),
            category: location.category,
            icon_key: location.icon_key,
            importance_level: location.importance_level,
            display_priority: location.display_priority,
            start_year: location.start_year,
            end_year: location.end_year,
            active_years_raw: location.active_years_raw,
            active_years: location.active_years.join("|"),
            active_year_ranges: location.active_year_ranges
              .map((range) => `${range.start_year}:${range.end_year}`)
              .join("|"),
            related_event_ids: location.related_event_ids.join("|"),
            related_anecdote_ids: location.related_anecdote_ids.join("|"),
            related_polity_ids: location.related_polity_ids.join("|"),
            related_people: location.related_people.join("|"),
            historical_name: location.historical_name,
            modern_name: location.modern_name,
            modern_admin_units_raw: location.modern_admin_units_raw,
            location_precision: location.location_precision,
            location_confidence_score: location.location_confidence_score,
            strategic_summary: location.strategic_summary,
            historical_significance: location.historical_significance,
            source_titles: location.source_titles.join("|"),
            source_urls: location.source_urls.join("|"),
            source_type: location.source_type,
            confidence_note: location.confidence_note,
            review_status: location.review_status,
            review_note: location.review_note,
            default_visible: location.default_visible,
            is_high_importance: location.is_high_importance,
            active_now: activeNow
          }
        };
      })
  };
}

// 标签内点缓存：按 polity_id 算一次"难达极点"，比 centroid 更可靠地落在多边形内部
// （非凸/狭长形态时 centroid 可能掉到领土外，例如赵国细长走廊或南匈奴的环形覆盖区）。
const innerLabelPointCache = new Map<string, [number, number]>();

function ringSignedArea(ring: number[][]): number {
  let area = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    area += (ring[j][0] + ring[i][0]) * (ring[j][1] - ring[i][1]);
  }
  return area / 2;
}

function computeInnerPoint(
  polityId: string,
  features: GeoJSON.Feature<GeoJSON.MultiPolygon, TerritoryFeatureProperties>[],
  fallback: [number, number] | null
): [number, number] | null {
  const cached = innerLabelPointCache.get(polityId);
  if (cached) return cached;
  // 在该政权所有 MultiPolygon 子多边形里挑面积最大者，再 polylabel 求内点
  let bestRings: number[][][] | null = null;
  let bestArea = 0;
  for (const feature of features) {
    if (feature.geometry.type !== "MultiPolygon") continue;
    for (const polygon of feature.geometry.coordinates) {
      if (!polygon.length) continue;
      const outerRing = polygon[0];
      const area = Math.abs(ringSignedArea(outerRing));
      if (area > bestArea) {
        bestArea = area;
        bestRings = polygon;
      }
    }
  }
  if (!bestRings) {
    if (fallback) innerLabelPointCache.set(polityId, fallback);
    return fallback;
  }
  try {
    const result = polylabel(bestRings, 1.0);
    const point: [number, number] = [result[0], result[1]];
    innerLabelPointCache.set(polityId, point);
    return point;
  } catch {
    if (fallback) innerLabelPointCache.set(polityId, fallback);
    return fallback;
  }
}

export function migrationFeatureCollection(
  yearData: YearData | null
): GeoJSON.FeatureCollection<GeoJSON.LineString> {
  return {
    type: "FeatureCollection",
    features:
      yearData?.capital_migrations.map((migration) => ({
        type: "Feature",
        geometry: {
          type: "LineString",
          coordinates: [migration.from_coordinates, migration.to_coordinates]
        },
        properties: {
          migration_id: migration.migration_id,
          label: migration.label,
          is_disputed: migration.is_disputed
        }
      })) ?? []
  };
}

export function applyPhysicalBasemapVisibility(map: maplibregl.Map, layers: AppState["layers"]): void {
  const setVis = (layerId: string, visible: boolean) => {
    if (map.getLayer(layerId)) {
      map.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
    }
  };
  setVis("ne-rivers", layers.physical_rivers);
  setVis("ne-lakes-fill", layers.physical_lakes);
  setVis("ne-lakes-outline", layers.physical_lakes);
  setVis("ne-glaciers-fill", layers.physical_glaciers);
  setVis("ne-geographic-lines", layers.geographic_lines);
  setVis("ne-modern-borders", layers.modern_country_boundaries);
  setVis("cn-borders-line", layers.cn_border_overlay);
}

export function territoryCollections(
  yearData: YearData | null,
  territoryGeoJSON: GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties> | null,
  hatchGeoJSON: GeoJSON.FeatureCollection<GeoJSON.LineString, TerritoryHatchFeatureProperties> | null,
  state: AppState,
  palette: ColorPalette = "default"
): {
  territories: GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties>;
  hatches: GeoJSON.FeatureCollection<GeoJSON.LineString, TerritoryHatchFeatureProperties>;
  labels: GeoJSON.FeatureCollection<GeoJSON.Point>;
  badges: GeoJSON.FeatureCollection<GeoJSON.Point>;
} {
  if (!yearData || !territoryGeoJSON || !state.layers.territories) {
    return {
      territories: emptyTerritoryCollection(),
      hatches: emptyHatchCollection(),
      labels: emptyLabelCollection(),
      badges: emptyLabelCollection()
    };
  }
  const polityById = new Map(yearData.polities.map((polity) => [polity.polity_id, polity]));
  const features: GeoJSON.Feature<GeoJSON.MultiPolygon, TerritoryFeatureProperties>[] = [];
  const hatchFeatures: GeoJSON.Feature<GeoJSON.LineString, TerritoryHatchFeatureProperties>[] = [];
  const labelFeatures: GeoJSON.Feature<GeoJSON.Point>[] = [];
  const coverageByPolity = new Map<string, Set<string>>();

  // 预先按 polity_id 聚合 raw features，便于 polylabel 在最大子多边形上计算
  const rawFeaturesByPolity = new Map<
    string,
    GeoJSON.Feature<GeoJSON.MultiPolygon, TerritoryFeatureProperties>[]
  >();
  territoryGeoJSON.features.forEach((feature) => {
    const id = feature.properties.polity_id;
    const list = rawFeaturesByPolity.get(id) ?? [];
    list.push(feature);
    rawFeaturesByPolity.set(id, list);
  });

  const labeledPolities = new Set<string>();
  territoryGeoJSON.features.forEach((feature) => {
    const polity = polityById.get(feature.properties.polity_id);
    // 多源场景：feature 来自非 v03 数据源时（如 vIndian），其对应 polity 不在 v03 yearData.polities
    // 中，但 feature.properties 自己携带 polity_start_year / polity_end_year / polity_name，
    // 因此可以直接用 properties 走快速渲染路径。
    if (!polity) {
      const fp = feature.properties;
      const zStart = fp.zone_start_year ?? fp.polity_start_year ?? yearData.year;
      const zEnd = fp.zone_end_year ?? fp.polity_end_year ?? yearData.year;
      if (yearData.year < zStart || yearData.year > zEnd) return;
      if (state.filters.polity_types.length && fp.polity_type && !state.filters.polity_types.includes(fp.polity_type)) return;
      if (state.filters.territory_status === "missing") return;
      const color = macroPeriodColor(fp.macro_period ?? "", fp.polity_id, palette, fp.dataset_id);
      const selected = fp.polity_id === state.selection.selected_polity_id;
      features.push({
        ...feature,
        properties: {
          ...fp,
          color,
          selected,
          is_nomadic: Boolean(fp.is_nomadic)
        }
      });
      return;
    }
    const zoneStart = feature.properties.zone_start_year ?? polity.polity_start_year ?? yearData.year;
    const zoneEnd = feature.properties.zone_end_year ?? polity.polity_end_year ?? yearData.year;
    if (yearData.year < zoneStart || yearData.year > zoneEnd) return;
    if (state.filters.polity_types.length && !state.filters.polity_types.includes(polity.polity_type)) return;
    if (state.filters.territory_status === "has_territory" && polity.territory.territory_status === "missing")
      return;
    if (state.filters.territory_status === "missing") return;
    if ((polity.confidence_score ?? 0) < state.filters.min_confidence_score) return;
    if (!state.filters.show_disputed && polity.quality.has_dispute) return;
    if (!state.filters.show_unmatched_ruler && polity.quality.has_unmatched_ruler) return;

    const color = macroPeriodColor(polity.macro_period, polity.polity_id, palette);
    const selected = polity.polity_id === state.selection.selected_polity_id;
    const displayName = polityDisplayName(polity);
    const properties = {
      ...polity.territory,
      ...feature.properties,
      polity_id: polity.polity_id,
      polity_name: polity.polity_name,
      polity_display_name: displayName,
      polity_name_disambiguation: polity.polity_name_disambiguation,
      polity_name_review_status: polity.polity_name_review_status,
      polity_name_risk_flags: polity.polity_name_risk_flags,
      macro_period: polity.macro_period,
      dynasty_name: polity.dynasty_name,
      polity_type: polity.polity_type,
      color,
      selected,
      is_nomadic: isPolityNomadic(polity)
    } as TerritoryFeatureProperties & { is_nomadic: boolean };
    features.push({ ...feature, properties });
    coverageByPolity.set(polity.polity_id, new Set(polity.territory.matched_admin_ids));
    if (
      state.layers.territory_labels &&
      !labeledPolities.has(polity.polity_id)
    ) {
      const polityFeatures = rawFeaturesByPolity.get(polity.polity_id) ?? [];
      const innerPoint = computeInnerPoint(
        polity.polity_id,
        polityFeatures,
        polity.territory.centroid ?? null
      );
      if (innerPoint) {
        labeledPolities.add(polity.polity_id);
        labelFeatures.push({
          type: "Feature",
          geometry: { type: "Point", coordinates: innerPoint },
          properties: {
            polity_id: polity.polity_id,
            polity_name: polity.polity_name,
            polity_display_name: displayName,
            size_rank: polity.territory.approx_area_km2 ?? 0,
            selected
          }
        });
      }
    }
  });

  hatchGeoJSON?.features.forEach((feature) => {
    const polity = polityById.get(feature.properties.polity_id);
    if (!polity) return;
    const zoneStart = feature.properties.zone_start_year ?? polity.polity_start_year ?? yearData.year;
    const zoneEnd = feature.properties.zone_end_year ?? polity.polity_end_year ?? yearData.year;
    if (yearData.year < zoneStart || yearData.year > zoneEnd) return;
    if (state.filters.polity_types.length && !state.filters.polity_types.includes(polity.polity_type)) return;
    if (state.filters.territory_status === "has_territory" && polity.territory.territory_status === "missing")
      return;
    if (state.filters.territory_status === "missing") return;
    if ((polity.confidence_score ?? 0) < state.filters.min_confidence_score) return;
    if (!state.filters.show_disputed && polity.quality.has_dispute) return;
    if (!state.filters.show_unmatched_ruler && polity.quality.has_unmatched_ruler) return;
    const color = macroPeriodColor(polity.macro_period, polity.polity_id, palette);
    const selected = polity.polity_id === state.selection.selected_polity_id;
    hatchFeatures.push({
      ...feature,
      properties: {
        ...polity.territory,
        ...feature.properties,
        polity_id: polity.polity_id,
        polity_name: polity.polity_name,
        polity_display_name: polityDisplayName(polity),
        polity_name_disambiguation: polity.polity_name_disambiguation,
        polity_name_review_status: polity.polity_name_review_status,
        polity_name_risk_flags: polity.polity_name_risk_flags,
        macro_period: polity.macro_period,
        dynasty_name: polity.dynasty_name,
        polity_type: polity.polity_type,
        color,
        selected,
        is_nomadic: isPolityNomadic(polity)
      }
    });
  });

  // 渲染顺序：大政权先画 → 小政权画在上层（visible）；选中政权强制最顶。
  // MapLibre 按 features 数组顺序绘制 (后绘制在上)。
  features.sort((a, b) => {
    const aSel = a.properties.selected ? 1 : 0;
    const bSel = b.properties.selected ? 1 : 0;
    if (aSel !== bSel) return aSel - bSel; // 选中放最后
    const aArea = a.properties.approx_area_km2 ?? 0;
    const bArea = b.properties.approx_area_km2 ?? 0;
    return bArea - aArea; // 面积大的先（在下层），小的后（在上层）
  });

  const badgeFeatures: GeoJSON.Feature<GeoJSON.Point>[] = features.flatMap((feature) => {
    const polity = polityById.get(feature.properties.polity_id);
    const centroid = polity?.territory.centroid;
    const coverage = coverageByPolity.get(feature.properties.polity_id);
    if (!polity || !centroid || !coverage?.size) return [];
    const overlapCount =
      features.filter((candidate) => {
        if (candidate.properties.polity_id === polity.polity_id) return false;
        const candidateCoverage = coverageByPolity.get(candidate.properties.polity_id);
        return candidateCoverage ? [...coverage].some((adminId) => candidateCoverage.has(adminId)) : false;
      }).length + 1;
    if (overlapCount < 2) return [];
    return [
      {
        type: "Feature",
        geometry: { type: "Point", coordinates: centroid },
        properties: {
          polity_id: polity.polity_id,
          polity_name: polity.polity_name,
          polity_display_name: polityDisplayName(polity),
          overlap_count: overlapCount,
          selected: polity.polity_id === state.selection.selected_polity_id
        }
      }
    ];
  });

  return {
    territories: { type: "FeatureCollection", features },
    hatches: { type: "FeatureCollection", features: hatchFeatures },
    labels: { type: "FeatureCollection", features: labelFeatures },
    badges: { type: "FeatureCollection", features: badgeFeatures }
  };
}

export function fitMigrationBounds(map: maplibregl.Map, yearData: YearData): void {
  if (!yearData.capital_migrations.length) return;
  const points = yearData.capital_migrations.flatMap((migration) => [
    migration.from_coordinates,
    migration.to_coordinates
  ]);
  const bounds = points.reduce(
    (current, point) => current.extend(point),
    new maplibregl.LngLatBounds(points[0], points[0])
  );
  map.fitBounds(bounds as LngLatBoundsLike, { padding: 120, maxZoom: 5.8, duration: 800 });
}

export function territoryBounds(
  collection: GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties>
): maplibregl.LngLatBounds | null {
  const coordinates = collection.features.flatMap((feature) =>
    feature.geometry.coordinates.flatMap((polygon) => polygon.flatMap((ring) => ring))
  );
  if (!coordinates.length) return null;
  return coordinates.reduce(
    (bounds, coordinate) => bounds.extend(coordinate as [number, number]),
    new maplibregl.LngLatBounds(coordinates[0] as [number, number], coordinates[0] as [number, number])
  );
}

/**
 * 取面积排序后累计达到 cumulativeThreshold（默认 0.85）的主要政权 features。
 * 避免春秋战国 54 国并存时镜头被微型政权拉到整个东亚视角。
 */
export function mainPolityFeatures(
  collection: GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties>,
  cumulativeThreshold = 0.85
): GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties> {
  if (collection.features.length <= 4) return collection;
  const sorted = [...collection.features].sort(
    (a, b) => (b.properties.approx_area_km2 ?? 0) - (a.properties.approx_area_km2 ?? 0)
  );
  const totalArea = sorted.reduce((sum, feature) => sum + (feature.properties.approx_area_km2 ?? 0), 0);
  if (totalArea <= 0) return { type: "FeatureCollection", features: sorted.slice(0, 5) };
  let accumulated = 0;
  const picked: typeof sorted = [];
  for (const feature of sorted) {
    accumulated += feature.properties.approx_area_km2 ?? 0;
    picked.push(feature);
    if (accumulated / totalArea >= cumulativeThreshold) break;
  }
  // 同时至少保留 top 3（避免极端情况下只取一个）
  while (picked.length < Math.min(3, sorted.length)) {
    picked.push(sorted[picked.length]);
  }
  return { type: "FeatureCollection", features: picked };
}

export function fitTerritoryBounds(
  map: maplibregl.Map,
  collection: GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties>,
  options: { focusMainOnly?: boolean } = {}
): void {
  const target = options.focusMainOnly ? mainPolityFeatures(collection) : collection;
  const bounds = territoryBounds(target);
  if (!bounds) return;
  map.fitBounds(bounds as LngLatBoundsLike, {
    padding: {
      top: 96,
      bottom: 96,
      left: 96,
      right: window.innerWidth >= 980 ? 520 : 96
    },
    maxZoom: 5.2,
    duration: 700
  });
}

export interface SnapshotOptions {
  yearLabel: string;
  polityCount: number;
  withTerritory: number;
  dataVersion: string;
  attribution: string;
}

export async function exportMapSnapshot(map: maplibregl.Map, options: SnapshotOptions): Promise<void> {
  // 触发一次渲染保证 framebuffer 是最新的，然后立即取像素
  await new Promise<void>((resolve) => {
    map.once("idle", () => resolve());
    map.triggerRepaint();
  });
  const mapCanvas = map.getCanvas();
  const width = mapCanvas.width;
  const height = mapCanvas.height;
  const footerHeight = Math.round(height * 0.07); // 底部水印条高度
  const output = document.createElement("canvas");
  output.width = width;
  output.height = height + footerHeight;
  const ctx = output.getContext("2d");
  if (!ctx) {
    throw new Error("无法创建 2D 绘图上下文");
  }
  ctx.drawImage(mapCanvas, 0, 0, width, height);

  // 底部水印条
  const grad = ctx.createLinearGradient(0, height, 0, height + footerHeight);
  grad.addColorStop(0, "rgba(20, 24, 32, 0.85)");
  grad.addColorStop(1, "rgba(20, 24, 32, 0.96)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, height, width, footerHeight);

  const dpr = window.devicePixelRatio || 1;
  const bigFont = Math.max(18, Math.floor(footerHeight * 0.42 / dpr));
  const smallFont = Math.max(12, Math.floor(footerHeight * 0.22 / dpr));
  const paddingX = Math.max(24, Math.floor(width * 0.018));
  const baselineY = height + footerHeight * 0.42;
  const subBaselineY = height + footerHeight * 0.78;

  ctx.fillStyle = "rgba(255, 244, 194, 0.96)";
  ctx.font = `700 ${bigFont * dpr}px "PingFang SC", "Helvetica Neue", system-ui, sans-serif`;
  ctx.textBaseline = "alphabetic";
  ctx.fillText(options.yearLabel, paddingX, baselineY);

  ctx.fillStyle = "rgba(236, 240, 248, 0.85)";
  ctx.font = `500 ${smallFont * dpr}px "PingFang SC", "Helvetica Neue", system-ui, sans-serif`;
  const meta = `${options.polityCount} 个政权 · ${options.withTerritory} 有疆域 · data ${options.dataVersion}`;
  ctx.fillText(meta, paddingX, subBaselineY);

  ctx.fillStyle = "rgba(184, 218, 255, 0.85)";
  ctx.font = `500 ${smallFont * dpr}px "PingFang SC", "Helvetica Neue", system-ui, sans-serif`;
  ctx.textAlign = "right";
  ctx.fillText("中国朝代更迭地图 · 现代行政区近似，非历史精确边界", width - paddingX, baselineY);
  ctx.fillStyle = "rgba(184, 200, 220, 0.7)";
  ctx.fillText(options.attribution, width - paddingX, subBaselineY);
  ctx.textAlign = "left";

  const blob: Blob | null = await new Promise((resolve) => output.toBlob((value) => resolve(value), "image/png"));
  if (!blob) {
    throw new Error("截图生成失败");
  }
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const safeYear = options.yearLabel.replace(/[^\w一-龥-]/g, "_");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  link.href = url;
  link.download = `history-map-${safeYear}-${stamp}.png`;
  link.click();
  URL.revokeObjectURL(url);
}

export function capitalEventTypeLabel(event: CapitalEvent): string {
  const labels: Record<string, string> = {
    initial_capital: "初始都城",
    relocation: "迁都",
    co_capital: "陪都",
    temporary_capital: "临时都城",
    disputed: "争议迁都"
  };
  return labels[event.event_type] ?? event.event_type;
}
