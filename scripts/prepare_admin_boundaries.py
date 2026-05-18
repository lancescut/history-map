#!/usr/bin/env python3
"""Prepare v03 modern administrative boundary sources.

The app keeps modern boundary data local so runtime map playback never depends
on a remote service. ADM1 is retained as the compatibility summary layer, while
ADM3 is the county-level index/reference layer used by v03 territory records.
Both layers are modern administrative references, not historical boundaries.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_DIR = ROOT / "input" / "v03" / "admin_boundaries"

ADM1_RAW_PATH = BOUNDARY_DIR / "china_adm1_geoboundaries_raw.geojson"
ADM1_NORMALIZED_PATH = BOUNDARY_DIR / "china_adm1_normalized.geojson"
ADM3_RAW_PATH = BOUNDARY_DIR / "china_adm3_geoboundaries_raw.geojson"
ADM3_NORMALIZED_PATH = BOUNDARY_DIR / "china_adm3_normalized.geojson"

MANIFEST_PATH = BOUNDARY_DIR / "admin_boundary_source_manifest.json"
RESEARCH_NOTE_PATH = BOUNDARY_DIR / "county_boundary_source_research.md"
ODBL_NOTICE_PATH = BOUNDARY_DIR / "ODbL-1.0-NOTICE.md"

ADM1_API_METADATA_URL = "https://www.geoboundaries.org/api/current/gbOpen/CHN/ADM1/"
ADM3_API_METADATA_URL = "https://www.geoboundaries.org/api/current/gbOpen/CHN/ADM3/"
SCRIPT_VERSION = "2026-05-16-v03-county-boundaries"

ADM1_SOURCE_METADATA = {
    "source": "geoBoundaries",
    "source_release": "gbOpen",
    "source_layer": "CHN ADM1",
    "source_url": "https://www.geoboundaries.org/",
    "download_url": "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/CHN/ADM1/geoBoundaries-CHN-ADM1_simplified.geojson",
    "api_metadata_url": ADM1_API_METADATA_URL,
    "source_license": "Public Domain",
    "source_attribution": "geoBoundaries / Wikimedia Commons",
    "crs": "WGS84",
}

ADM3_METADATA_FALLBACK = {
    "admUnitCount": "2867",
    "boundaryISO": "CHN",
    "boundaryLicense": "Open Data Commons Open Database License 1.0",
    "boundaryName": "China",
    "boundarySource": "geoBoundaries",
    "boundarySourceURL": "https://www.geoboundaries.org/",
    "boundaryType": "ADM3",
    "buildDate": "",
    "gjDownloadURL": "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/CHN/ADM3/geoBoundaries-CHN-ADM3.geojson",
    "simplifiedGeometryGeoJSON": "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/CHN/ADM3/geoBoundaries-CHN-ADM3_simplified.geojson",
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


def write_json(path: Path, payload: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        if compact:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_metadata(url: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=45) as response:  # noqa: S310 - pinned HTTPS source URL.
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - source metadata is mirrored in fallback for reproducible builds.
        print(f"Warning: could not fetch {url}: {exc}; using pinned fallback metadata.")
        return dict(fallback)


def download_if_missing(url: str, path: Path) -> bool:
    if path.exists() and path.stat().st_size > 0:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    print(f"Downloading {url} -> {path.relative_to(ROOT)}")
    with urllib.request.urlopen(url, timeout=180) as response:  # noqa: S310 - pinned HTTPS source URL.
        with tmp_path.open("wb") as handle:
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                handle.write(chunk)
    tmp_path.replace(path)
    return True


def iter_points(value: Any) -> Iterable[tuple[float, float]]:
    if isinstance(value, list) and len(value) >= 2 and isinstance(value[0], (int, float)):
        yield float(value[0]), float(value[1])
    elif isinstance(value, list):
        for item in value:
            yield from iter_points(item)


def geometry_points(geometry: dict[str, Any]) -> list[tuple[float, float]]:
    return list(iter_points(geometry.get("coordinates", [])))


def geometry_bbox(geometry: dict[str, Any]) -> list[float]:
    points = geometry_points(geometry)
    if not points:
        raise ValueError("geometry has no coordinates")
    lons = [point[0] for point in points]
    lats = [point[1] for point in points]
    return [min(lons), min(lats), max(lons), max(lats)]


def bbox_centroid(bbox: list[float]) -> list[float]:
    return [round((bbox[0] + bbox[2]) / 2, 6), round((bbox[1] + bbox[3]) / 2, 6)]


def coordinate_count(geometry: dict[str, Any]) -> int:
    return len(geometry_points(geometry))


def bbox_contains_point(bbox: list[float], point: list[float]) -> bool:
    return bbox[0] <= point[0] <= bbox[2] and bbox[1] <= point[1] <= bbox[3]


def point_in_ring(point: list[float], ring: list[list[float]]) -> bool:
    if len(ring) < 4:
        return False
    x, y = point
    inside = False
    j = len(ring) - 1
    for i, current in enumerate(ring):
        xi, yi = float(current[0]), float(current[1])
        xj, yj = float(ring[j][0]), float(ring[j][1])
        if ((yi > y) != (yj > y)) and x < ((xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_in_polygon(point: list[float], polygon: list[Any]) -> bool:
    if not polygon or not point_in_ring(point, polygon[0]):
        return False
    return not any(point_in_ring(point, hole) for hole in polygon[1:])


def geometry_contains_point(geometry: dict[str, Any], point: list[float]) -> bool:
    if geometry.get("type") == "Polygon":
        return point_in_polygon(point, geometry.get("coordinates", []))
    if geometry.get("type") == "MultiPolygon":
        return any(point_in_polygon(point, polygon) for polygon in geometry.get("coordinates", []))
    return False


def first_geometry_point(geometry: dict[str, Any]) -> list[float] | None:
    for point in iter_points(geometry.get("coordinates", [])):
        return [point[0], point[1]]
    return None


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean = re.sub(r"\s+", " ", str(value).strip())
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result


def county_aliases(shape_name: str) -> str:
    aliases = [shape_name]
    suffixes = [
        " Autonomous County",
        " County",
        " District",
        " City",
        " Banner",
        " Autonomous Banner",
        " Qu",
        " Xian",
        " Shi",
        " Qi",
    ]
    for suffix in suffixes:
        if shape_name.endswith(suffix):
            aliases.append(shape_name[: -len(suffix)])
    return "|".join(unique(aliases))


def adm3_source_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    # The current API metadata reports 2867 ADM3 units, while the simplified
    # GeoJSON endpoint omits a few features. Use the full GeoJSON as the raw
    # source so manifest counts can be checked directly against metadata.
    download_url = metadata.get("gjDownloadURL") or metadata.get("simplifiedGeometryGeoJSON")
    source = metadata.get("boundarySource") or "geoBoundaries"
    source_url = metadata.get("boundarySourceURL") or "https://www.geoboundaries.org/"
    return {
        "source": "geoBoundaries",
        "source_release": "gbOpen",
        "source_layer": "CHN ADM3 simplified",
        "source_url": "https://www.geoboundaries.org/",
        "download_url": download_url,
        "api_metadata_url": ADM3_API_METADATA_URL,
        "source_license": metadata.get("boundaryLicense", "Open Data Commons Open Database License 1.0"),
        "source_attribution": f"geoBoundaries / {source}",
        "source_boundary_url": source_url,
        "source_build_date": metadata.get("buildDate", ""),
        "source_data_update_date": metadata.get("sourceDataUpdateDate", ""),
        "source_boundary_year_represented": metadata.get("boundaryYearRepresented", ""),
        "crs": "WGS84",
    }


def normalize_adm1_boundaries() -> list[dict[str, Any]]:
    raw = read_json(ADM1_RAW_PATH)
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
            raise SystemExit(f"duplicate admin_id after ADM1 normalization: {admin_id}")
        seen_ids.add(admin_id)
        geometry = feature["geometry"]
        if geometry["type"] not in {"Polygon", "MultiPolygon"}:
            raise SystemExit(f"{shape_name} has unsupported geometry {geometry['type']}")
        bbox = geometry_bbox(geometry)
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
                    **ADM1_SOURCE_METADATA,
                    "coordinate_count": coordinate_count(geometry),
                    "bbox": bbox,
                    "centroid": bbox_centroid(bbox),
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
        "description": "Modern ADM1 boundaries normalized for v03 summary matching and territory approximation fallback. These are modern administrative references, not historical territory boundaries.",
        "properties": ADM1_SOURCE_METADATA,
        "features": features,
    }
    write_json(ADM1_NORMALIZED_PATH, normalized)
    return features


def assign_adm1_parent(county_feature: dict[str, Any], adm1_features: list[dict[str, Any]]) -> dict[str, Any] | None:
    geometry = county_feature["geometry"]
    bbox = geometry_bbox(geometry)
    candidate_points: list[list[float]] = [bbox_centroid(bbox)]
    first_point = first_geometry_point(geometry)
    if first_point:
        candidate_points.append(first_point)

    for point in candidate_points:
        for parent in adm1_features:
            parent_bbox = parent["properties"]["bbox"]
            if bbox_contains_point(parent_bbox, point) and geometry_contains_point(parent["geometry"], point):
                return parent
    return None


def normalize_adm3_boundaries(adm1_features: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metadata = fetch_metadata(ADM3_API_METADATA_URL, ADM3_METADATA_FALLBACK)
    source_metadata = adm3_source_metadata(metadata)
    download_url = source_metadata["download_url"]
    if not download_url:
        raise SystemExit("geoBoundaries ADM3 metadata did not include a GeoJSON download URL")
    download_if_missing(download_url, ADM3_RAW_PATH)

    raw = read_json(ADM3_RAW_PATH)
    raw_features = raw.get("features", [])
    expected_count = int(metadata.get("admUnitCount") or 0)
    if expected_count and len(raw_features) != expected_count:
        print(
            "Warning: geoBoundaries ADM3 metadata reports "
            f"{expected_count} features, downloaded GeoJSON contains {len(raw_features)}."
        )

    features: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    parent_match_count = 0
    for index, feature in enumerate(raw_features, start=1):
        geometry = feature.get("geometry")
        if not geometry or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise SystemExit(f"ADM3 feature {index} has unsupported or empty geometry")
        props = feature.get("properties", {})
        shape_name = str(props.get("shapeName") or props.get("shapeISO") or f"ADM3 {index}").strip()
        raw_shape_id = str(props.get("shapeID") or "").strip()
        shape_id = re.sub(r"[^A-Za-z0-9_-]", "", raw_shape_id) or hashlib.sha1(  # noqa: S324 - stable id fallback only.
            f"{shape_name}-{index}".encode("utf-8")
        ).hexdigest()[:12]
        admin_id = f"CN-ADM3-{shape_id}"
        if admin_id in seen_ids:
            admin_id = f"{admin_id}-{index}"
        seen_ids.add(admin_id)

        bbox = geometry_bbox(geometry)
        parent = assign_adm1_parent(feature, adm1_features)
        parent_ids: list[str] = []
        parent_names: list[str] = []
        if parent:
            parent_match_count += 1
            parent_ids = [parent["properties"]["admin_id"]]
            parent_names = [parent["properties"]["name"]]

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "admin_id": admin_id,
                    "name": shape_name,
                    "aliases": county_aliases(shape_name),
                    "admin_level": "county",
                    "source_shape_name": shape_name,
                    "source_shape_id": raw_shape_id,
                    "source_shape_type": props.get("shapeType", ""),
                    "parent_admin_ids": parent_ids,
                    "parent_admin_names": parent_names,
                    "license": source_metadata["source_license"],
                    **source_metadata,
                    "coordinate_count": coordinate_count(geometry),
                    "bbox": bbox,
                    "centroid": bbox_centroid(bbox),
                },
                "geometry": geometry,
            }
        )

    features.sort(key=lambda item: (item["properties"]["parent_admin_ids"], item["properties"]["admin_id"]))
    normalized = {
        "type": "FeatureCollection",
        "name": "china_adm3_normalized_geoboundaries_v03",
        "description": "Modern ADM3 county-level boundaries normalized for v03 territory indexes. These are modern administrative references, not historical territory boundaries.",
        "properties": source_metadata,
        "features": features,
    }
    write_json(ADM3_NORMALIZED_PATH, normalized, compact=True)
    stats = {
        "expected_feature_count": expected_count,
        "feature_count": len(features),
        "metadata_feature_count_discrepancy": expected_count - len(features) if expected_count else 0,
        "parent_match_count": parent_match_count,
        "parent_unmatched_count": len(features) - parent_match_count,
    }
    return features, {**source_metadata, **stats, "metadata": metadata}


def write_research_note(adm3_manifest: dict[str, Any]) -> None:
    payload = f"""# v03 县级边界数据源研究

## 结论

本项目采用 geoBoundaries `gbOpen/CHN/ADM3` simplified GeoJSON 作为 v03 县级现代行政边界源。

## 选择理由

- geoBoundaries 提供固定 API 元数据与 WGS84 GeoJSON，当前元数据记录为 {adm3_manifest["expected_feature_count"]} 个 ADM3 单元；本次下载文件实际包含 {adm3_manifest["feature_count"]} 个 feature，差异已写入 manifest。
- geoBoundaries ADM3 当前许可为 `{adm3_manifest["source_license"]}`，可随公开仓库分发派生数据，但必须保留 ODbL 署名、许可与派生说明。
- GADM 许可不适合作为本项目公开仓库的再分发首选源。
- GeoJSON.cn 县级离线数据需要授权；且 1.6+ 数据为 GCJ-02，不作为当前公开 WGS84 数据流水线源。

## 数据口径

- 当前县级边界是现代行政区近似层，不是历史疆域实测层。
- v03 继续保留 ADM1 摘要匹配，用来兼容旧字段 `matched_admin_ids` / `matched_admin_units`。
- 新增 ADM3 县级事实层与 `polity_county_index.json`，年度记录只保存 `territory.county_index_ref` 和统计字段。
- geoBoundaries 的 CHN ADM3 名称以来源 `shapeName` 为准；中文县级别名后续可通过授权地名表或人工别名表追加，不影响县级索引稳定性。

## 来源

- API metadata: {ADM3_API_METADATA_URL}
- Download URL: {adm3_manifest["download_url"]}
- Note: 当前 API 的 GeoJSON 下载文件返回 feature 数少于 `admUnitCount`；清洗脚本不伪造缺失 feature，manifest 同时记录 metadata count、actual count 与 discrepancy。
- License: {adm3_manifest["source_license"]}
- Source attribution: {adm3_manifest["source_attribution"]}
- Build date: {adm3_manifest.get("source_build_date") or "unknown"}
"""
    write_text(RESEARCH_NOTE_PATH, payload)


def write_odbl_notice(adm3_manifest: dict[str, Any]) -> None:
    payload = f"""# ODbL 1.0 Notice for v03 County Boundary Data

This project includes derived county-level boundary data from geoBoundaries `gbOpen/CHN/ADM3`.

- Source: geoBoundaries
- Source layer: CHN ADM3 GeoJSON
- Source metadata: {ADM3_API_METADATA_URL}
- Download URL: {adm3_manifest["download_url"]}
- License: {adm3_manifest["source_license"]}
- License text: https://opendatacommons.org/licenses/odbl/1-0/
- Attribution: {adm3_manifest["source_attribution"]}

Derived files in this repository include:

- `input/v03/admin_boundaries/china_adm3_geoboundaries_raw.geojson`
- `input/v03/admin_boundaries/china_adm3_normalized.geojson`
- `public/data/v03/territories/county_units.geojson`
- `public/data/v03/territories/polity_county_index.json`

The normalized data adds stable project IDs, parent ADM1 references, bbox/centroid metadata, coordinate counts, and v03 indexing fields. Boundaries are modern administrative references and are not historical exact territory boundaries. No endorsement by geoBoundaries or its upstream sources is implied.
"""
    write_text(ODBL_NOTICE_PATH, payload)


def build_manifest(adm1_features: list[dict[str, Any]], adm3_features: list[dict[str, Any]], adm3_info: dict[str, Any]) -> dict[str, Any]:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    adm3_counts = [feature["properties"]["coordinate_count"] for feature in adm3_features]
    adm1_counts = [feature["properties"]["coordinate_count"] for feature in adm1_features]
    return {
        "source": adm3_info["source"],
        "source_release": adm3_info["source_release"],
        "source_layer": adm3_info["source_layer"],
        "source_url": adm3_info["source_url"],
        "download_url": adm3_info["download_url"],
        "api_metadata_url": ADM3_API_METADATA_URL,
        "source_license": adm3_info["source_license"],
        "source_attribution": adm3_info["source_attribution"],
        "source_boundary_url": adm3_info["source_boundary_url"],
        "source_build_date": adm3_info.get("source_build_date", ""),
        "source_data_update_date": adm3_info.get("source_data_update_date", ""),
        "source_boundary_year_represented": adm3_info.get("source_boundary_year_represented", ""),
        "crs": adm3_info["crs"],
        "admin_level": "county",
        "generated_at": generated_at,
        "build_date": generated_at,
        "cleaning_script_version": SCRIPT_VERSION,
        "cleaning_script_path": str(Path(__file__).relative_to(ROOT)),
        "cleaning_script_sha256": file_sha256(Path(__file__)),
        "raw_path": str(ADM3_RAW_PATH.relative_to(ROOT)),
        "normalized_path": str(ADM3_NORMALIZED_PATH.relative_to(ROOT)),
        "raw_sha256": file_sha256(ADM3_RAW_PATH),
        "normalized_sha256": file_sha256(ADM3_NORMALIZED_PATH),
        "feature_count": len(adm3_features),
        "expected_feature_count": adm3_info["expected_feature_count"],
        "metadata_feature_count_discrepancy": adm3_info["metadata_feature_count_discrepancy"],
        "parent_match_count": adm3_info["parent_match_count"],
        "parent_unmatched_count": adm3_info["parent_unmatched_count"],
        "source_research_note_path": str(RESEARCH_NOTE_PATH.relative_to(ROOT)),
        "license_notice_path": str(ODBL_NOTICE_PATH.relative_to(ROOT)),
        "geometry_quality": {
            "min_coordinate_count": min(adm3_counts),
            "max_coordinate_count": max(adm3_counts),
            "formal_rect_fixture": False,
        },
        "adm1_reference": {
            "source_layer": ADM1_SOURCE_METADATA["source_layer"],
            "source_license": ADM1_SOURCE_METADATA["source_license"],
            "raw_path": str(ADM1_RAW_PATH.relative_to(ROOT)),
            "normalized_path": str(ADM1_NORMALIZED_PATH.relative_to(ROOT)),
            "raw_sha256": file_sha256(ADM1_RAW_PATH),
            "normalized_sha256": file_sha256(ADM1_NORMALIZED_PATH),
            "feature_count": len(adm1_features),
            "geometry_quality": {
                "min_coordinate_count": min(adm1_counts),
                "max_coordinate_count": max(adm1_counts),
                "formal_rect_fixture": False,
            },
        },
    }


def normalize_boundaries() -> None:
    adm1_features = normalize_adm1_boundaries()
    adm3_features, adm3_info = normalize_adm3_boundaries(adm1_features)
    write_research_note(adm3_info)
    write_odbl_notice(adm3_info)
    manifest = build_manifest(adm1_features, adm3_features, adm3_info)
    write_json(MANIFEST_PATH, manifest)
    print(f"Normalized {len(adm1_features)} ADM1 boundaries -> {ADM1_NORMALIZED_PATH.relative_to(ROOT)}")
    print(f"Normalized {len(adm3_features)} ADM3 boundaries -> {ADM3_NORMALIZED_PATH.relative_to(ROOT)}")
    print(f"Wrote manifest -> {MANIFEST_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    normalize_boundaries()
