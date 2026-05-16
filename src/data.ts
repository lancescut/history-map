import type { AliasIndex, CapitalsData, Metadata, TerritoryFeatureProperties, YearData } from "./types";

const jsonCache = new Map<string, Promise<unknown>>();

async function fetchJson<T>(path: string): Promise<T> {
  if (!jsonCache.has(path)) {
    jsonCache.set(
      path,
      fetch(path).then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to load ${path}: ${response.status}`);
        }
        return response.json() as Promise<T>;
      })
    );
  }
  return jsonCache.get(path) as Promise<T>;
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

export function getYearData(year: number): Promise<YearData> {
  return fetchJson<YearData>(`/data/v03/years/${year}.json`);
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
