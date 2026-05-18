import type {
  AliasIndex,
  CapitalsData,
  CountyUnitProperties,
  HistoricalAnecdotesData,
  HistoricalContextsData,
  HistoricalEventsData,
  IssuesData,
  Metadata,
  PolityCountyIndex,
  StoryPresetsData,
  TerritoryFeatureProperties,
  ValidationData,
  YearData
} from "./types";

const jsonCache = new Map<string, Promise<unknown>>();

async function fetchJson<T>(path: string): Promise<T> {
  let pending = jsonCache.get(path);
  if (!pending) {
    pending = fetch(path).then(async (response) => {
      if (!response.ok) {
        throw new Error(`Failed to load ${path}: ${response.status}`);
      }
      // Vite dev server 会把不存在的静态路径 fallback 到 SPA index.html，content-type
      // 变成 text/html。强校验避免 JSON.parse 抛 "Unexpected token '<'"。
      const contentType = response.headers.get("content-type") ?? "";
      if (!/json|geo\+json/i.test(contentType)) {
        const peek = await response.text();
        if (peek.trimStart().startsWith("<")) {
          throw new Error(
            `Missing data file: ${path} (server returned HTML fallback, file likely does not exist)`
          );
        }
        return JSON.parse(peek) as T;
      }
      return (await response.json()) as T;
    });
    // 失败时把缓存项剔除，避免后续请求一直拿到失败的 promise
    pending.catch(() => {
      if (jsonCache.get(path) === pending) {
        jsonCache.delete(path);
      }
    });
    jsonCache.set(path, pending);
  }
  return pending as Promise<T>;
}

export function getMetadata(): Promise<Metadata> {
  return fetchJson<Metadata>("/data/v03/metadata.json");
}

export function getCapitals(): Promise<CapitalsData> {
  return fetchJson<CapitalsData>("/data/v03/capitals.json");
}

export function getAliasIndex(): Promise<AliasIndex> {
  return fetchJson<AliasIndex>("/data/v03/alias_index.json");
}

export function getTerritories(): Promise<GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties>> {
  return fetchJson<GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties>>(
    "/data/v03/territories/approx_polities.geojson"
  );
}

export function getModernAdminUnits(): Promise<GeoJSON.FeatureCollection> {
  return fetchJson<GeoJSON.FeatureCollection>("/data/v03/territories/modern_admin_units.geojson");
}

export function getCountyUnits(): Promise<GeoJSON.FeatureCollection<GeoJSON.Geometry, CountyUnitProperties>> {
  return fetchJson<GeoJSON.FeatureCollection<GeoJSON.Geometry, CountyUnitProperties>>(
    "/data/v03/territories/county_units.geojson"
  );
}

export function getPolityCountyIndex(): Promise<PolityCountyIndex> {
  return fetchJson<PolityCountyIndex>("/data/v03/territories/polity_county_index.json");
}

export function getYearData(year: number): Promise<YearData> {
  return fetchJson<YearData>(`/data/v03/years/${year}.json`);
}

export function getIssues(): Promise<IssuesData> {
  return fetchJson<IssuesData>("/data/v03/issues.json");
}

export function getValidation(): Promise<ValidationData> {
  return fetchJson<ValidationData>("/data/v03/validation.json");
}

export function getHistoricalEvents(): Promise<HistoricalEventsData> {
  return fetchJson<HistoricalEventsData>("/data/v03/events.json");
}

export function getHistoricalAnecdotes(): Promise<HistoricalAnecdotesData> {
  return fetchJson<HistoricalAnecdotesData>("/data/v03/anecdotes.json");
}

export function getHistoricalContexts(): Promise<HistoricalContextsData> {
  return fetchJson<HistoricalContextsData>("/data/v03/contexts.json");
}

export function getStoryPresets(): Promise<StoryPresetsData> {
  return fetchJson<StoryPresetsData>("/data/v03/story_presets.json");
}

export function yearLabel(year: number): string {
  return year < 0 ? `前${Math.abs(year)}年` : `${year}年`;
}

export function nextYear(year: number, maxYear: number): number {
  if (year >= maxYear) return maxYear;
  return year === -1 ? 1 : year + 1;
}

export function previousYear(year: number, minYear: number): number {
  if (year <= minYear) return minYear;
  return year === 1 ? -1 : year - 1;
}

export function clampPlayableYear(year: number, minYear: number, maxYear: number): number {
  // 防御 NaN / Infinity：来源可能是 Number("") 或 Number("abc")
  if (!Number.isFinite(year)) return minYear < 0 ? minYear : 1;
  const clamped = Math.min(maxYear, Math.max(minYear, Math.trunc(year)));
  return clamped === 0 ? 1 : clamped;
}

export function normalizeSearch(value: string): string {
  const tradToCommon: Record<string, string> = {
    國: "国",
    後: "后",
    漢: "汉",
    晉: "晋",
    齊: "齐",
    趙: "赵",
    韓: "韩",
    吳: "吴",
    東: "东",
    遼: "辽",
    劉: "刘",
    楊: "杨",
    陳: "陈",
    長: "长",
    陽: "阳",
    臨: "临",
    應: "应",
    會: "会",
    寧: "宁"
  };
  return value
    .trim()
    .split("")
    .map((char) => tradToCommon[char] ?? char)
    .join("")
    .replace(/[\s·・,，、／/()（）[\]［］「」『』《》<>〈〉\-—－:：;；]/g, "")
    .toLowerCase();
}
