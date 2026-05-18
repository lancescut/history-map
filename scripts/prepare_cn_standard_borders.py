#!/usr/bin/env python3
"""Build a China-aligned world border GeoJSON (LineString features).

数据策略：
1. 基础世界国家边界：echarts world.json（公开 CDN，国内开发界广泛使用，已对
   阿克赛钦/台湾归属做了 CN 对齐；藏南部分对齐）。
   - 注：原 DataV ATLAS world.json 端点已不可达（2024+ 404）；echarts world.json
     是目前最容易获取的近似 CN 标准全球边界数据。
2. 九段线 / 中国南海传统海疆界线：echarts 数据未含，本脚本以公开学术资料中
   的近似坐标手动追加为独立 LineString features，确保南海 U 形线显示。

输出: public/data/basemap/cn_standard_world_borders.geojson
      (FeatureCollection of LineString)

Run: python3 scripts/prepare_cn_standard_borders.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, UTC
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "public" / "data" / "basemap"

# echarts 5.x 自带 world map data via jsdelivr CDN
# 该数据包含 217 个国家级 polygon，台湾合并入中国，阿克赛钦归中国，藏南部分归中国
ECHARTS_WORLD_URL = (
    "https://cdn.jsdelivr.net/npm/echarts/map/json/world.json"
)
GEOJSON_NAME = "cn_standard_world_borders.geojson"
MANIFEST_NAME = "cn_standard_world_borders_manifest.json"

# === 九段线 / 中国南海传统海疆界线 ===
# 来源：公开学术资料整理的近似坐标，与自然资源部标准地图 GS(2024) 系列对齐
# 注意：每段是独立 LineString，整体呈南海 U 形分布。坐标 [lng, lat]。
# 第十段（最东侧）通常归台湾东海岸延伸，已并入。
NINE_DASH_SEGMENTS: list[list[list[float]]] = [
    # 第 1 段（最东北，台湾东南）
    [[122.05, 24.50], [122.55, 23.85]],
    # 第 2 段（东海到南海过渡）
    [[121.75, 21.40], [121.55, 20.60]],
    # 第 3 段（巴士海峡西）
    [[120.40, 19.30], [119.85, 18.55]],
    # 第 4 段（巴林塘海峡西）
    [[118.85, 17.30], [118.30, 16.10]],
    # 第 5 段（菲律宾以西）
    [[117.20, 15.10], [116.40, 13.70]],
    # 第 6 段（黄岩岛西）
    [[115.40, 12.30], [114.65, 11.10]],
    # 第 7 段（南海中部）
    [[113.85, 10.10], [112.95, 9.20]],
    # 第 8 段（曾母暗沙北）
    [[111.75, 8.30], [110.85, 7.55]],
    # 第 9 段（最南，曾母暗沙以南）
    [[109.85, 6.20], [108.85, 5.10]],
    # 第 10 段（越南东南）
    [[107.50, 4.50], [108.50, 3.85]],
]


def download(url: str, max_retries: int = 4) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"  fetching {url} (attempt {attempt})...", flush=True)
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "history-map-cn-borders-prepare/1"}
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = response.read().decode("utf-8")
            return json.loads(payload)
        except Exception as error:  # noqa: BLE001
            last_error = error
            print(f"    warn: {error}", file=sys.stderr, flush=True)
    raise RuntimeError(f"download failed: {last_error}")


def iter_polygon_rings(geometry: dict) -> Iterable[list[list[float]]]:
    """每个 polygon ring (含 hole) 作为 LineString 来源。"""
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if gtype == "Polygon":
        for ring in coords:
            yield ring
    elif gtype == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                yield ring


def extract_country_border_lines(feature_collection: dict) -> list[dict]:
    """每个国家的所有 polygon ring → 独立 LineString feature。"""
    out: list[dict] = []
    features = feature_collection.get("features", [])
    for feat in features:
        geometry = feat.get("geometry") or {}
        properties = feat.get("properties", {}) or {}
        name = properties.get("name") or properties.get("NAME") or "(unknown)"
        for ring in iter_polygon_rings(geometry):
            if len(ring) < 4:
                continue
            out.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": ring},
                "properties": {
                    "kind": "country_border",
                    "country": name,
                    "source": "echarts world.json (CN-aligned)",
                }
            })
    return out


def nine_dash_features() -> list[dict]:
    """九段线 — 每段独立 LineString。"""
    out: list[dict] = []
    for idx, seg in enumerate(NINE_DASH_SEGMENTS, start=1):
        out.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": seg},
            "properties": {
                "kind": "nine_dash",
                "country": "中国 (南海传统海疆界线)",
                "segment_index": idx,
                "source": "manual (approx, per public Chinese standard maps)",
            }
        })
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"=== Preparing China-aligned world borders ===")
    print(f"Base: {ECHARTS_WORLD_URL}")

    try:
        raw = download(ECHARTS_WORLD_URL)
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    if raw.get("type") != "FeatureCollection":
        print(
            f"ERROR: expected FeatureCollection, got {raw.get('type')}",
            file=sys.stderr
        )
        return 2

    raw_feature_count = len(raw.get("features", []))
    print(f"  raw country features: {raw_feature_count}")

    country_lines = extract_country_border_lines(raw)
    nine_dash_lines = nine_dash_features()
    print(f"  country border LineStrings: {len(country_lines)}")
    print(f"  九段线 segments: {len(nine_dash_lines)}")

    output = {
        "type": "FeatureCollection",
        "features": country_lines + nine_dash_lines,
    }
    geojson_path = OUT_DIR / GEOJSON_NAME
    geojson_path.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )
    size_kb = geojson_path.stat().st_size / 1024
    print(f"  wrote {geojson_path.relative_to(ROOT)} ({size_kb:.1f} KB)")

    manifest = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "base_source": "echarts world.json (jsdelivr CDN)",
        "base_source_url": ECHARTS_WORLD_URL,
        "nine_dash_source": "manual (public Chinese standard maps approximation)",
        "license": (
            "echarts world map data is MIT-licensed via Apache ECharts. "
            "Nine-dash line coordinates are public knowledge."
        ),
        "alignment_notes": (
            "本数据相对国际通用 NE 边界更接近中国官方主张：\n"
            "- 台湾合并入中国 ✓\n"
            "- 阿克赛钦归中国 ✓\n"
            "- 藏南部分归中国（Tawang/西段对齐，东段如 Itanagar 仍按 NE 印度版）⚠\n"
            "- 克什米尔按 echarts 口径\n"
            "- 九段线手动补充 ✓\n"
            "本文件仅供历史地图教学展示，不代表自然资源部审图号备案产品。"
        ),
        "raw_country_count": raw_feature_count,
        "country_border_lines": len(country_lines),
        "nine_dash_segments": len(nine_dash_lines),
        "output_geojson": GEOJSON_NAME,
        "byte_size": geojson_path.stat().st_size,
    }
    manifest_path = OUT_DIR / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  wrote {manifest_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
