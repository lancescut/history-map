#!/usr/bin/env python3
"""Normalize the v1 modern administrative boundary source.

The raw input is pinned under input/v03/admin_boundaries so the app never needs
remote boundary services at runtime. This script standardizes property names and
emits a manifest with source/license/hash information for reproducible builds.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_DIR = ROOT / "input" / "v03" / "admin_boundaries"
RAW_PATH = BOUNDARY_DIR / "china_adm1_geoboundaries_raw.geojson"
NORMALIZED_PATH = BOUNDARY_DIR / "china_adm1_normalized.geojson"
MANIFEST_PATH = BOUNDARY_DIR / "admin_boundary_source_manifest.json"

SOURCE_METADATA = {
    "source": "geoBoundaries",
    "source_release": "gbOpen",
    "source_layer": "CHN ADM1",
    "source_url": "https://www.geoboundaries.org/",
    "download_url": "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/CHN/ADM1/geoBoundaries-CHN-ADM1_simplified.geojson",
    "api_metadata_url": "https://www.geoboundaries.org/api/current/gbOpen/CHN/ADM1/",
    "source_license": "Public Domain",
    "source_attribution": "geoBoundaries / Wikimedia Commons",
    "crs": "WGS84",
}

ADM1_NAME_MAP = {
    "Anhui Province": ("CN-AH", "安徽省", "安徽"),
    "Beijing Municipality": ("CN-BJ", "北京市", "北京|京"),
    "Chongqing Municipality": ("CN-CQ", "重庆市", "重庆|重慶"),
    "Fujian Province": ("CN-FJ", "福建省", "福建"),
    "Gansu Province": ("CN-GS", "甘肃省", "甘肃|甘肅"),
    "Guangxi Zhuang Autonomous Region": ("CN-GX", "广西壮族自治区", "广西|廣西"),
    "Guangzhou Province": ("CN-GD", "广东省", "广东|廣東|Guangdong|Guangzhou Province"),
    "Guizhou Province": ("CN-GZ", "贵州省", "贵州|貴州"),
    "Hainan Province": ("CN-HI", "海南省", "海南"),
    "Hebei Province": ("CN-HE", "河北省", "河北"),
    "Heilongjiang Province": ("CN-HL", "黑龙江省", "黑龙江|黑龍江"),
    "Henan Province": ("CN-HA", "河南省", "河南"),
    "Hong Kong Special Administrative Region": ("CN-HK", "香港特别行政区", "香港|Hong Kong"),
    "Hubei Province": ("CN-HB", "湖北省", "湖北"),
    "Hunan Province": ("CN-HN", "湖南省", "湖南"),
    "Inner Mongolia Autonomous Region": ("CN-NM", "内蒙古自治区", "内蒙古|內蒙古"),
    "Jiangsu Province": ("CN-JS", "江苏省", "江苏|江蘇"),
    "Jiangxi Province": ("CN-JX", "江西省", "江西"),
    "Jilin Province": ("CN-JL", "吉林省", "吉林"),
    "Liaoning Province": ("CN-LN", "辽宁省", "辽宁|遼寧"),
    "Macau Special Administrative Region": ("CN-MO", "澳门特别行政区", "澳门|澳門|Macau|Macao"),
    "Ningxia Ningxia Hui Autonomous Region": ("CN-NX", "宁夏回族自治区", "宁夏|寧夏"),
    "Qinghai Province": ("CN-QH", "青海省", "青海"),
    "Shaanxi Province": ("CN-SN", "陕西省", "陕西|陝西"),
    "Shandong Province": ("CN-SD", "山东省", "山东|山東"),
    "Shanghai Municipality": ("CN-SH", "上海市", "上海|沪|滬"),
    "Shanxi Province": ("CN-SX", "山西省", "山西"),
    "Sichuan Province": ("CN-SC", "四川省", "四川"),
    "Taiwan Province": ("CN-TW", "台湾省", "台湾|臺灣|台灣"),
    "Tianjin Municipality": ("CN-TJ", "天津市", "天津"),
    "Tibet Autonomous Region": ("CN-XZ", "西藏自治区", "西藏"),
    "Xinjiang Uyghur Autonomous Region": ("CN-XJ", "新疆维吾尔自治区", "新疆|新疆維吾爾自治區"),
    "Yunnan Province": ("CN-YN", "云南省", "云南|雲南"),
    "Zhejiang Province": ("CN-ZJ", "浙江省", "浙江"),
}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def coordinate_count(geometry: dict[str, Any]) -> int:
    count = 0

    def walk(value: Any) -> None:
        nonlocal count
        if isinstance(value, list) and value and isinstance(value[0], (int, float)):
            count += 1
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(geometry.get("coordinates", []))
    return count


def normalize_boundaries() -> None:
    raw = read_json(RAW_PATH)
    features = []
    seen_ids: set[str] = set()
    unknown_names: list[str] = []

    for feature in raw.get("features", []):
        shape_name = feature.get("properties", {}).get("shapeName", "")
        mapped = ADM1_NAME_MAP.get(shape_name)
        if not mapped:
            unknown_names.append(shape_name)
            continue
        admin_id, name, aliases = mapped
        if admin_id in seen_ids:
            raise SystemExit(f"duplicate admin_id after normalization: {admin_id}")
        seen_ids.add(admin_id)
        geometry = feature["geometry"]
        if geometry["type"] not in {"Polygon", "MultiPolygon"}:
            raise SystemExit(f"{shape_name} has unsupported geometry {geometry['type']}")
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "admin_id": admin_id,
                    "name": name,
                    "aliases": aliases,
                    "admin_level": "province",
                    "source_shape_name": shape_name,
                    "source_shape_id": feature.get("properties", {}).get("shapeID", ""),
                    **SOURCE_METADATA,
                    "coordinate_count": coordinate_count(geometry),
                },
                "geometry": geometry,
            }
        )

    if unknown_names:
        raise SystemExit("unmapped ADM1 names: " + ", ".join(sorted(unknown_names)))
    if len(features) != 34:
        raise SystemExit(f"expected 34 ADM1 features, got {len(features)}")

    features.sort(key=lambda item: item["properties"]["admin_id"])
    normalized = {
        "type": "FeatureCollection",
        "name": "china_adm1_normalized_geoboundaries_v03",
        "description": "Real modern ADM1 boundaries normalized for v1 modern-admin territory approximation. These boundaries are modern administrative references, not historical territory boundaries.",
        "properties": SOURCE_METADATA,
        "features": features,
    }
    write_json(NORMALIZED_PATH, normalized)

    manifest = {
        **SOURCE_METADATA,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "raw_path": str(RAW_PATH.relative_to(ROOT)),
        "normalized_path": str(NORMALIZED_PATH.relative_to(ROOT)),
        "raw_sha256": file_sha256(RAW_PATH),
        "normalized_sha256": file_sha256(NORMALIZED_PATH),
        "feature_count": len(features),
        "admin_ids": [feature["properties"]["admin_id"] for feature in features],
        "geometry_quality": {
            "min_coordinate_count": min(feature["properties"]["coordinate_count"] for feature in features),
            "max_coordinate_count": max(feature["properties"]["coordinate_count"] for feature in features),
            "formal_rect_fixture": False,
        },
    }
    write_json(MANIFEST_PATH, manifest)
    print(f"Normalized {len(features)} ADM1 boundaries -> {NORMALIZED_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    normalize_boundaries()
