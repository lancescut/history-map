import type {
  AliasIndex,
  CapitalsData,
  CountyUnitProperties,
  DatasetId,
  HistoricalAnecdotesData,
  HistoricalContextsData,
  HistoricalEventsData,
  IssuesData,
  Metadata,
  MythologyData,
  PolityCountyIndex,
  StrategicLocationsData,
  StoryPresetsData,
  TerritoryFeatureProperties,
  TerritoryHatchFeatureProperties,
  ValidationData,
  YearData
} from "./types";

const jsonCache = new Map<string, Promise<unknown>>();

const DEFAULT_DATASET: DatasetId = "v03";

function dataPath(datasetId: DatasetId, subpath: string): string {
  return `/data/${datasetId}/${subpath}`;
}

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

export function getMetadata(datasetId: DatasetId = DEFAULT_DATASET): Promise<Metadata> {
  return fetchJson<Metadata>(dataPath(datasetId, "metadata.json"));
}

export function getCapitals(datasetId: DatasetId = DEFAULT_DATASET): Promise<CapitalsData> {
  return fetchJson<CapitalsData>(dataPath(datasetId, "capitals.json"));
}

export function getAliasIndex(datasetId: DatasetId = DEFAULT_DATASET): Promise<AliasIndex> {
  return fetchJson<AliasIndex>(dataPath(datasetId, "alias_index.json"));
}

export function getTerritories(
  datasetId: DatasetId = DEFAULT_DATASET
): Promise<GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties>> {
  return fetchJson<GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties>>(
    dataPath(datasetId, "territories/approx_polities.geojson")
  );
}

export function getTerritoryInfluenceHatches(
  datasetId: DatasetId = DEFAULT_DATASET
): Promise<GeoJSON.FeatureCollection<GeoJSON.LineString, TerritoryHatchFeatureProperties>> {
  return fetchJson<GeoJSON.FeatureCollection<GeoJSON.LineString, TerritoryHatchFeatureProperties>>(
    dataPath(datasetId, "territories/territory_influence_hatches.geojson")
  );
}

export function getModernAdminUnits(
  datasetId: DatasetId = DEFAULT_DATASET
): Promise<GeoJSON.FeatureCollection> {
  return fetchJson<GeoJSON.FeatureCollection>(
    dataPath(datasetId, "territories/modern_admin_units.geojson")
  );
}

export function getCountyUnits(
  datasetId: DatasetId = DEFAULT_DATASET
): Promise<GeoJSON.FeatureCollection<GeoJSON.Geometry, CountyUnitProperties>> {
  return fetchJson<GeoJSON.FeatureCollection<GeoJSON.Geometry, CountyUnitProperties>>(
    dataPath(datasetId, "territories/county_units.geojson")
  );
}

export function getPolityCountyIndex(
  datasetId: DatasetId = DEFAULT_DATASET
): Promise<PolityCountyIndex> {
  return fetchJson<PolityCountyIndex>(dataPath(datasetId, "territories/polity_county_index.json"));
}

export function getYearData(year: number, datasetId: DatasetId = DEFAULT_DATASET): Promise<YearData> {
  return fetchJson<YearData>(dataPath(datasetId, `years/${year}.json`));
}

export function getIssues(datasetId: DatasetId = DEFAULT_DATASET): Promise<IssuesData> {
  return fetchJson<IssuesData>(dataPath(datasetId, "issues.json"));
}

export function getValidation(datasetId: DatasetId = DEFAULT_DATASET): Promise<ValidationData> {
  return fetchJson<ValidationData>(dataPath(datasetId, "validation.json"));
}

export function getHistoricalEvents(
  datasetId: DatasetId = DEFAULT_DATASET
): Promise<HistoricalEventsData> {
  return fetchJson<HistoricalEventsData>(dataPath(datasetId, "events.json"));
}

export function getHistoricalAnecdotes(
  datasetId: DatasetId = DEFAULT_DATASET
): Promise<HistoricalAnecdotesData> {
  return fetchJson<HistoricalAnecdotesData>(dataPath(datasetId, "anecdotes.json"));
}

export function getHistoricalContexts(
  datasetId: DatasetId = DEFAULT_DATASET
): Promise<HistoricalContextsData> {
  return fetchJson<HistoricalContextsData>(dataPath(datasetId, "contexts.json"));
}

export function getStoryPresets(
  datasetId: DatasetId = DEFAULT_DATASET
): Promise<StoryPresetsData> {
  return fetchJson<StoryPresetsData>(dataPath(datasetId, "story_presets.json"));
}

export function getStrategicLocations(
  datasetId: DatasetId = DEFAULT_DATASET
): Promise<StrategicLocationsData> {
  return fetchJson<StrategicLocationsData>(dataPath(datasetId, "strategic_locations.json"));
}

export function getMythology(datasetId: DatasetId = DEFAULT_DATASET): Promise<MythologyData> {
  return fetchJson<MythologyData>(dataPath(datasetId, "mythology.json"));
}

export interface DatasetBundle {
  datasetId: DatasetId;
  metadata: Metadata;
  capitals: CapitalsData | null;
  aliasIndex: AliasIndex | null;
  territories: GeoJSON.FeatureCollection<GeoJSON.MultiPolygon, TerritoryFeatureProperties> | null;
  territoryHatches: GeoJSON.FeatureCollection<GeoJSON.LineString, TerritoryHatchFeatureProperties> | null;
  modernAdminUnits: GeoJSON.FeatureCollection | null;
  countyUnits: GeoJSON.FeatureCollection<GeoJSON.Geometry, CountyUnitProperties> | null;
  polityCountyIndex: PolityCountyIndex | null;
  issues: IssuesData | null;
  validation: ValidationData | null;
  events: HistoricalEventsData | null;
  anecdotes: HistoricalAnecdotesData | null;
  contexts: HistoricalContextsData | null;
  storyPresets: StoryPresetsData | null;
  strategicLocations: StrategicLocationsData | null;
  mythology: MythologyData | null;
}

// 把单源 Promise.all 收敛为一次调用；non-critical 资源缺失（404 / fallback）走 null。
// metadata 是 dataset 的最小可用前提，缺失则整个 bundle reject。
export async function loadDataset(datasetId: DatasetId): Promise<DatasetBundle> {
  const optional = <T>(promise: Promise<T>): Promise<T | null> => promise.catch(() => null);
  const [
    metadata,
    capitals,
    aliasIndex,
    territories,
    territoryHatches,
    modernAdminUnits,
    countyUnits,
    polityCountyIndex,
    issues,
    validation,
    events,
    anecdotes,
    contexts,
    storyPresets,
    strategicLocations,
    mythology
  ] = await Promise.all([
    getMetadata(datasetId),
    optional(getCapitals(datasetId)),
    optional(getAliasIndex(datasetId)),
    optional(getTerritories(datasetId)),
    optional(getTerritoryInfluenceHatches(datasetId)),
    optional(getModernAdminUnits(datasetId)),
    optional(getCountyUnits(datasetId)),
    optional(getPolityCountyIndex(datasetId)),
    optional(getIssues(datasetId)),
    optional(getValidation(datasetId)),
    optional(getHistoricalEvents(datasetId)),
    optional(getHistoricalAnecdotes(datasetId)),
    optional(getHistoricalContexts(datasetId)),
    optional(getStoryPresets(datasetId)),
    optional(getStrategicLocations(datasetId)),
    optional(getMythology(datasetId))
  ]);
  return {
    datasetId,
    metadata,
    capitals,
    aliasIndex,
    territories,
    territoryHatches,
    modernAdminUnits,
    countyUnits,
    polityCountyIndex,
    issues,
    validation,
    events,
    anecdotes,
    contexts,
    storyPresets,
    strategicLocations,
    mythology
  };
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

// round-robin 合并多源数组：按 order 顺序逐位取，空源跳过。
// 例：order=["v03","vIndian"], 输入 {v03:[a,b,c], vIndian:[X,Y]} → [a,X,b,Y,c]
export function roundRobinInterleave<T>(
  perDataset: Partial<Record<DatasetId, T[]>>,
  order: readonly DatasetId[]
): T[] {
  const result: T[] = [];
  const maxLen = Math.max(0, ...order.map((id) => perDataset[id]?.length ?? 0));
  for (let i = 0; i < maxLen; i++) {
    for (const id of order) {
      const arr = perDataset[id];
      if (arr && i < arr.length) result.push(arr[i]);
    }
  }
  return result;
}
