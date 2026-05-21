#!/usr/bin/env python3
"""Prepare vIndian modern administrative boundary sources.

Mirror of scripts/prepare_admin_boundaries.py (China), but targeting India:
- ADM1: 28 states + 8 union territories (~36 features).
- ADM2: districts (~700 features).

Both layers are modern administrative references (used as a geometry stock for
historical-polity approximation via territory_overrides_vIndian.csv), NOT historical
exact boundaries. ADM IDs are stable hashes:  IN-ADM1-{shapeName_hash} / IN-ADM2-{shapeName_hash}.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_DIR = ROOT / "input" / "vIndian" / "admin_boundaries"

ADM1_RAW_PATH = BOUNDARY_DIR / "india_adm1_geoboundaries_raw.geojson"
ADM1_NORMALIZED_PATH = BOUNDARY_DIR / "india_adm1_normalized.geojson"
ADM2_RAW_PATH = BOUNDARY_DIR / "india_adm2_geoboundaries_raw.geojson"
ADM2_NORMALIZED_PATH = BOUNDARY_DIR / "india_adm2_normalized.geojson"

MANIFEST_PATH = BOUNDARY_DIR / "admin_boundary_source_manifest.json"
ODBL_NOTICE_PATH = BOUNDARY_DIR / "ODbL-1.0-NOTICE.md"

ADM1_API_METADATA_URL = "https://www.geoboundaries.org/api/current/gbOpen/IND/ADM1/"
ADM2_API_METADATA_URL = "https://www.geoboundaries.org/api/current/gbOpen/IND/ADM2/"
SCRIPT_VERSION = "2026-05-20-vindian-state-and-district"

# Map from geoBoundaries shapeName → (admin_id, name_zh, alias_pipe). 28 states + 8 UTs.
# alias_pipe combines English (shapeName), 中文 (常用译名), 罗马转写 variants.
ADM1_NAME_MAP: dict[str, tuple[str, str, str]] = {
    # 28 states
    "Andhra Pradesh": ("IN-AP", "安得拉邦", "Andhra Pradesh|AndhraPradesh|安得拉|安得拉邦"),
    "Arunachal Pradesh": ("IN-AR", "阿鲁纳恰尔邦", "Arunachal Pradesh|阿鲁纳恰尔|阿鲁纳恰尔邦"),
    "Assam": ("IN-AS", "阿萨姆邦", "Assam|阿萨姆|阿萨姆邦"),
    "Bihar": ("IN-BR", "比哈尔邦", "Bihar|比哈尔|比哈尔邦"),
    "Chhattisgarh": ("IN-CT", "恰蒂斯加尔邦", "Chhattisgarh|恰蒂斯加尔|恰蒂斯加尔邦"),
    "Goa": ("IN-GA", "果阿邦", "Goa|果阿|果阿邦"),
    "Gujarat": ("IN-GJ", "古吉拉特邦", "Gujarat|古吉拉特|古吉拉特邦"),
    "Haryana": ("IN-HR", "哈里亚纳邦", "Haryana|哈里亚纳|哈里亚纳邦"),
    "Himachal Pradesh": ("IN-HP", "喜马偕尔邦", "Himachal Pradesh|喜马偕尔|喜马偕尔邦"),
    "Jharkhand": ("IN-JH", "贾坎德邦", "Jharkhand|贾坎德|贾坎德邦"),
    "Karnataka": ("IN-KA", "卡纳塔克邦", "Karnataka|卡纳塔克|卡纳塔克邦|迈索尔"),
    "Kerala": ("IN-KL", "喀拉拉邦", "Kerala|喀拉拉|喀拉拉邦"),
    "Madhya Pradesh": ("IN-MP", "中央邦", "Madhya Pradesh|中央邦|MadhyaPradesh"),
    "Maharashtra": ("IN-MH", "马哈拉施特拉邦", "Maharashtra|马哈拉施特拉|马哈拉施特拉邦"),
    "Manipur": ("IN-MN", "曼尼普尔邦", "Manipur|曼尼普尔|曼尼普尔邦"),
    "Meghalaya": ("IN-ML", "梅加拉亚邦", "Meghalaya|梅加拉亚|梅加拉亚邦"),
    "Mizoram": ("IN-MZ", "米佐拉姆邦", "Mizoram|米佐拉姆|米佐拉姆邦"),
    "Nagaland": ("IN-NL", "那加兰邦", "Nagaland|那加兰|那加兰邦"),
    "Odisha": ("IN-OR", "奥里萨邦", "Odisha|Orissa|奥里萨|奥里萨邦"),
    "Punjab": ("IN-PB", "旁遮普邦", "Punjab|旁遮普|旁遮普邦"),
    "Rajasthan": ("IN-RJ", "拉贾斯坦邦", "Rajasthan|拉贾斯坦|拉贾斯坦邦"),
    "Sikkim": ("IN-SK", "锡金邦", "Sikkim|锡金|锡金邦"),
    "Tamil Nadu": ("IN-TN", "泰米尔纳德邦", "Tamil Nadu|TamilNadu|泰米尔纳德|泰米尔纳德邦"),
    "Telangana": ("IN-TG", "特伦甘纳邦", "Telangana|特伦甘纳|特伦甘纳邦"),
    "Tripura": ("IN-TR", "特里普拉邦", "Tripura|特里普拉|特里普拉邦"),
    "Uttar Pradesh": ("IN-UP", "北方邦", "Uttar Pradesh|UttarPradesh|北方邦|北方"),
    "Uttarakhand": ("IN-UK", "北阿坎德邦", "Uttarakhand|Uttaranchal|北阿坎德|北阿坎德邦"),
    "West Bengal": ("IN-WB", "西孟加拉邦", "West Bengal|WestBengal|西孟加拉|西孟加拉邦"),
    # 8 union territories / NCT
    "Andaman and Nicobar": ("IN-AN", "安达曼-尼科巴群岛", "Andaman and Nicobar|Andaman And Nicobar|安达曼|尼科巴"),
    "Chandigarh": ("IN-CH", "昌迪加尔", "Chandigarh|昌迪加尔"),
    "Dadra and Nagar Haveli and Daman and Diu": ("IN-DH", "达德拉、那加尔、达曼、第乌", "Dadra|Nagar Haveli|Daman|Diu|达德拉|达曼|第乌"),
    "Delhi": ("IN-DL", "德里首都辖区", "Delhi|National Capital Territory|NCT of Delhi|德里"),
    "Jammu and Kashmir": ("IN-JK", "查谟和克什米尔", "Jammu and Kashmir|Jammu|Kashmir|查谟|克什米尔"),
    "Ladakh": ("IN-LA", "拉达克", "Ladakh|拉达克"),
    "Lakshadweep": ("IN-LD", "拉克沙群岛", "Lakshadweep|拉克沙"),
    "Puducherry": ("IN-PY", "本地治里", "Puducherry|Pondicherry|本地治里|朋迪榭里"),
}

# 与 prepare_admin_boundaries.py 完全一致的字段集，便于 generate_public_data 复用同模式。
ADM1_SOURCE_METADATA = {
    "source": "geoBoundaries",
    "source_release": "gbOpen",
    "source_layer": "IND ADM1 simplified",
    "source_url": "https://www.geoboundaries.org/",
    "api_metadata_url": ADM1_API_METADATA_URL,
    "source_license": "Open Data Commons Open Database License 1.0",
    "source_attribution": "geoBoundaries / Wikimedia Commons",
    "crs": "WGS84",
}

# 与 v03 同步采用 9469f09 提交的 release data，保证可复现构建。若元数据 API 不可达，
# 这些 fallback 提供直接 GitHub raw 下载链接。
GEOBOUNDARIES_PINNED_COMMIT = "9469f09"

ADM2_METADATA_FALLBACK = {
    "admUnitCount": "713",
    "boundaryISO": "IND",
    "boundaryLicense": "Open Data Commons Open Database License 1.0",
    "boundaryName": "India",
    "boundarySource": "geoBoundaries",
    "boundarySourceURL": "https://www.geoboundaries.org/",
    "boundaryType": "ADM2",
    "buildDate": "",
    "gjDownloadURL": f"https://github.com/wmgeolab/geoBoundaries/raw/{GEOBOUNDARIES_PINNED_COMMIT}/releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2.geojson",
    "simplifiedGeometryGeoJSON": f"https://github.com/wmgeolab/geoBoundaries/raw/{GEOBOUNDARIES_PINNED_COMMIT}/releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2_simplified.geojson",
}

ADM1_METADATA_FALLBACK = {
    "admUnitCount": "36",
    "boundaryISO": "IND",
    "boundaryLicense": "Open Data Commons Open Database License 1.0",
    "boundaryName": "India",
    "boundarySource": "geoBoundaries",
    "boundarySourceURL": "https://www.geoboundaries.org/",
    "boundaryType": "ADM1",
    "buildDate": "",
    "gjDownloadURL": f"https://github.com/wmgeolab/geoBoundaries/raw/{GEOBOUNDARIES_PINNED_COMMIT}/releaseData/gbOpen/IND/ADM1/geoBoundaries-IND-ADM1.geojson",
    "simplifiedGeometryGeoJSON": f"https://github.com/wmgeolab/geoBoundaries/raw/{GEOBOUNDARIES_PINNED_COMMIT}/releaseData/gbOpen/IND/ADM1/geoBoundaries-IND-ADM1_simplified.geojson",
}


# ---------- IO helpers (copied from prepare_admin_boundaries.py) ----------


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
        with urllib.request.urlopen(url, timeout=45) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: could not fetch {url}: {exc}; using pinned fallback metadata.")
        return dict(fallback)


def download_if_missing(url: str, path: Path) -> bool:
    if path.exists() and path.stat().st_size > 0:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    print(f"Downloading {url} -> {path.relative_to(ROOT)}")
    with urllib.request.urlopen(url, timeout=180) as response:  # noqa: S310
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


# Geometry comes from geoBoundaries with 14-digit precision (`93.89017692426908`),
# which is wasted on a continent-scale historical map. Rounding to 5 decimals leaves
# ~1.1 m precision at the equator — enough for state-level rendering — and roughly
# halves the on-disk size of the normalized GeoJSON files.
COORD_PRECISION = 5


def round_coords(value: Any) -> Any:
    if isinstance(value, list):
        if value and isinstance(value[0], (int, float)) and len(value) in (2, 3):
            return [round(float(component), COORD_PRECISION) for component in value]
        return [round_coords(item) for item in value]
    return value


def round_geometry(geometry: dict[str, Any]) -> dict[str, Any]:
    if "coordinates" not in geometry:
        return geometry
    return {**geometry, "coordinates": round_coords(geometry["coordinates"])}


def round_bbox(bbox: list[float]) -> list[float]:
    return [round(float(component), COORD_PRECISION) for component in bbox]


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


def adm2_aliases(shape_name: str) -> str:
    aliases = [shape_name]
    suffixes = [" District", " Districts", " Tehsil", " Taluk", " City"]
    for suffix in suffixes:
        if shape_name.endswith(suffix):
            aliases.append(shape_name[: -len(suffix)])
    return "|".join(unique(aliases))


def adm_source_metadata(metadata: dict[str, Any], layer: str, api_url: str) -> dict[str, Any]:
    # Prefer the simplified release to keep boundary files at the same order of magnitude
    # as China ADM1 (which hardcodes the `_simplified.geojson` URL). Full-resolution
    # IND ADM1 weighs in around 46 MB raw / 99 MB normalized; the simplified release is
    # roughly 5% of that and remains accurate enough for state-level historical map rendering.
    download_url = metadata.get("simplifiedGeometryGeoJSON") or metadata.get("gjDownloadURL")
    source = metadata.get("boundarySource") or "geoBoundaries"
    source_url = metadata.get("boundarySourceURL") or "https://www.geoboundaries.org/"
    return {
        "source": "geoBoundaries",
        "source_release": "gbOpen",
        "source_layer": f"IND {layer} simplified",
        "source_url": "https://www.geoboundaries.org/",
        "download_url": download_url,
        "api_metadata_url": api_url,
        "source_license": metadata.get("boundaryLicense", "Open Data Commons Open Database License 1.0"),
        "source_attribution": f"geoBoundaries / {source}",
        "source_boundary_url": source_url,
        "source_build_date": metadata.get("buildDate", ""),
        "source_data_update_date": metadata.get("sourceDataUpdateDate", ""),
        "source_boundary_year_represented": metadata.get("boundaryYearRepresented", ""),
        "crs": "WGS84",
    }


# ---------- ADM1 ----------


def normalize_adm1_boundaries() -> list[dict[str, Any]]:
    metadata = fetch_metadata(ADM1_API_METADATA_URL, ADM1_METADATA_FALLBACK)
    source_metadata = adm_source_metadata(metadata, "ADM1", ADM1_API_METADATA_URL)
    download_url = source_metadata["download_url"]
    if not download_url:
        raise SystemExit("geoBoundaries IND ADM1 metadata did not include a GeoJSON download URL")
    download_if_missing(download_url, ADM1_RAW_PATH)

    raw = read_json(ADM1_RAW_PATH)
    features: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    unknown_names: list[str] = []

    # 副本 NAME_MAP，键多包含 NFKD 折叠后的纯 ASCII 形式（如 "Bihar"），
    # 用于匹配 geoBoundaries 含变音符号的 shapeName（如 "Bihār"）。
    def fold(name: str) -> str:
        no_marks = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
        return re.sub(r"\s+", " ", no_marks).strip().lower()

    name_lookup: dict[str, tuple[str, str, str]] = {}
    for key, value in ADM1_NAME_MAP.items():
        name_lookup[fold(key)] = value
    # 额外别名：geoBoundaries 用 "Andaman and Nicobar Islands"（带 Islands），手册键无 Islands。
    extra_aliases: dict[str, str] = {
        "andaman and nicobar islands": "Andaman and Nicobar",
        "national capital territory of delhi": "Delhi",
    }
    for fold_key, canonical in extra_aliases.items():
        if canonical in ADM1_NAME_MAP:
            name_lookup[fold_key] = ADM1_NAME_MAP[canonical]

    for feature in raw.get("features", []):
        shape_name = (feature.get("properties", {}).get("shapeName") or "").strip()
        mapped = name_lookup.get(fold(shape_name))
        if not mapped:
            unknown_names.append(shape_name)
            continue
        admin_id, name, aliases = mapped
        if admin_id in seen_ids:
            raise SystemExit(f"duplicate admin_id after IND ADM1 normalization: {admin_id}")
        seen_ids.add(admin_id)
        geometry = feature["geometry"]
        if geometry["type"] not in {"Polygon", "MultiPolygon"}:
            raise SystemExit(f"{shape_name} has unsupported geometry {geometry['type']}")
        geometry = round_geometry(geometry)
        bbox = round_bbox(geometry_bbox(geometry))
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "admin_id": admin_id,
                    "name": name,
                    "aliases": aliases,
                    "admin_level": "state",
                    "source_shape_name": shape_name,
                    "source_shape_id": feature.get("properties", {}).get("shapeID", ""),
                    **{k: v for k, v in source_metadata.items() if k != "download_url"},
                    "coordinate_count": coordinate_count(geometry),
                    "bbox": bbox,
                    "centroid": bbox_centroid(bbox),
                },
                "geometry": geometry,
            }
        )

    if unknown_names:
        # 不致命：列出未匹配名称，但继续。便于发现 shapeName 与映射表的拼写差异。
        print("Warning: unmapped IND ADM1 names: " + ", ".join(sorted(set(unknown_names))))

    features.sort(key=lambda item: item["properties"]["admin_id"])
    normalized = {
        "type": "FeatureCollection",
        "name": "india_adm1_normalized_geoboundaries_vindian",
        "description": "Modern IND ADM1 (state + UT) boundaries normalized for vIndian territory approximation. Modern administrative references, not historical territory boundaries.",
        "properties": ADM1_SOURCE_METADATA,
        "features": features,
    }
    write_json(ADM1_NORMALIZED_PATH, normalized, compact=True)
    return features


# ---------- ADM2 ----------


def assign_adm1_parent(child_feature: dict[str, Any], adm1_features: list[dict[str, Any]]) -> dict[str, Any] | None:
    geometry = child_feature["geometry"]
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


def normalize_adm2_boundaries(adm1_features: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metadata = fetch_metadata(ADM2_API_METADATA_URL, ADM2_METADATA_FALLBACK)
    source_metadata = adm_source_metadata(metadata, "ADM2", ADM2_API_METADATA_URL)
    download_url = source_metadata["download_url"] or metadata.get("simplifiedGeometryGeoJSON")
    if not download_url:
        raise SystemExit("geoBoundaries IND ADM2 metadata did not include a GeoJSON download URL")
    source_metadata["download_url"] = download_url
    download_if_missing(download_url, ADM2_RAW_PATH)

    raw = read_json(ADM2_RAW_PATH)
    raw_features = raw.get("features", [])
    expected_count = int(metadata.get("admUnitCount") or 0)

    features: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    parent_match_count = 0
    for index, feature in enumerate(raw_features, start=1):
        geometry = feature.get("geometry")
        if not geometry or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            continue
        props = feature.get("properties", {})
        shape_name = str(props.get("shapeName") or props.get("shapeISO") or f"ADM2 {index}").strip()
        raw_shape_id = str(props.get("shapeID") or "").strip()
        shape_id = re.sub(r"[^A-Za-z0-9_-]", "", raw_shape_id) or hashlib.sha1(  # noqa: S324
            f"{shape_name}-{index}".encode("utf-8")
        ).hexdigest()[:12]
        admin_id = f"IN-ADM2-{shape_id}"
        if admin_id in seen_ids:
            admin_id = f"{admin_id}-{index}"
        seen_ids.add(admin_id)

        geometry = round_geometry(geometry)
        bbox = round_bbox(geometry_bbox(geometry))
        parent = assign_adm1_parent({**feature, "geometry": geometry}, adm1_features)
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
                    "aliases": adm2_aliases(shape_name),
                    "admin_level": "district",
                    "source_shape_name": shape_name,
                    "source_shape_id": raw_shape_id,
                    "parent_admin_ids": parent_ids,
                    "parent_admin_names": parent_names,
                    **{k: v for k, v in source_metadata.items() if k != "download_url"},
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
        "name": "india_adm2_normalized_geoboundaries_vindian",
        "description": "Modern IND ADM2 (district) boundaries normalized for vIndian territory indexes. Modern administrative references, not historical territory boundaries.",
        "properties": source_metadata,
        "features": features,
    }
    write_json(ADM2_NORMALIZED_PATH, normalized, compact=True)
    stats = {
        "expected_feature_count": expected_count,
        "feature_count": len(features),
        "metadata_feature_count_discrepancy": expected_count - len(features) if expected_count else 0,
        "parent_match_count": parent_match_count,
        "parent_unmatched_count": len(features) - parent_match_count,
    }
    return features, {**source_metadata, **stats, "metadata": metadata}


def write_odbl_notice(adm2_info: dict[str, Any]) -> None:
    payload = f"""# ODbL 1.0 Notice for vIndian Boundary Data

This project includes derived state-level and district-level boundary data from
geoBoundaries `gbOpen/IND/ADM1` and `gbOpen/IND/ADM2`.

- Source: geoBoundaries
- ADM1 layer: IND ADM1
- ADM2 layer: IND ADM2
- ADM1 metadata: {ADM1_API_METADATA_URL}
- ADM2 metadata: {ADM2_API_METADATA_URL}
- ADM2 download URL: {adm2_info["download_url"]}
- License: {adm2_info["source_license"]}
- License text: https://opendatacommons.org/licenses/odbl/1-0/
- Attribution: {adm2_info["source_attribution"]}

Derived files in this repository include:

- `input/vIndian/admin_boundaries/india_adm1_geoboundaries_raw.geojson`
- `input/vIndian/admin_boundaries/india_adm1_normalized.geojson`
- `input/vIndian/admin_boundaries/india_adm2_geoboundaries_raw.geojson`
- `input/vIndian/admin_boundaries/india_adm2_normalized.geojson`
- `public/data/vIndian/territories/county_units.geojson` (Phase 1.6+ when generator wired)
- `public/data/vIndian/territories/polity_county_index.json` (Phase 1.6+)

The normalized data adds stable project IDs, parent ADM1 references, bbox/centroid metadata,
coordinate counts, and vIndian indexing fields. Boundaries are modern administrative references
and are NOT historical exact territory boundaries. No endorsement by geoBoundaries or its
upstream sources is implied.
"""
    write_text(ODBL_NOTICE_PATH, payload)


def build_manifest(adm1_features: list[dict[str, Any]], adm2_features: list[dict[str, Any]], adm2_info: dict[str, Any]) -> dict[str, Any]:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    adm2_counts = [feature["properties"]["coordinate_count"] for feature in adm2_features]
    adm1_counts = [feature["properties"]["coordinate_count"] for feature in adm1_features]
    return {
        "source": adm2_info["source"],
        "source_release": adm2_info["source_release"],
        "source_layer": adm2_info["source_layer"],
        "source_url": adm2_info["source_url"],
        "download_url": adm2_info["download_url"],
        "api_metadata_url": ADM2_API_METADATA_URL,
        "source_license": adm2_info["source_license"],
        "source_attribution": adm2_info["source_attribution"],
        "source_boundary_url": adm2_info["source_boundary_url"],
        "source_build_date": adm2_info.get("source_build_date", ""),
        "source_data_update_date": adm2_info.get("source_data_update_date", ""),
        "source_boundary_year_represented": adm2_info.get("source_boundary_year_represented", ""),
        "crs": adm2_info["crs"],
        "admin_level": "district",
        "generated_at": generated_at,
        "build_date": generated_at,
        "cleaning_script_version": SCRIPT_VERSION,
        "cleaning_script_path": str(Path(__file__).relative_to(ROOT)),
        "cleaning_script_sha256": file_sha256(Path(__file__)),
        "raw_path": str(ADM2_RAW_PATH.relative_to(ROOT)),
        "normalized_path": str(ADM2_NORMALIZED_PATH.relative_to(ROOT)),
        "raw_sha256": file_sha256(ADM2_RAW_PATH) if ADM2_RAW_PATH.exists() else "",
        "normalized_sha256": file_sha256(ADM2_NORMALIZED_PATH) if ADM2_NORMALIZED_PATH.exists() else "",
        "feature_count": len(adm2_features),
        "expected_feature_count": adm2_info["expected_feature_count"],
        "metadata_feature_count_discrepancy": adm2_info["metadata_feature_count_discrepancy"],
        "parent_match_count": adm2_info["parent_match_count"],
        "parent_unmatched_count": adm2_info["parent_unmatched_count"],
        "license_notice_path": str(ODBL_NOTICE_PATH.relative_to(ROOT)),
        "geometry_quality": {
            "min_coordinate_count": min(adm2_counts) if adm2_counts else 0,
            "max_coordinate_count": max(adm2_counts) if adm2_counts else 0,
            "formal_rect_fixture": False,
        },
        "adm1_reference": {
            "source_layer": ADM1_SOURCE_METADATA["source_layer"],
            "source_license": ADM1_SOURCE_METADATA["source_license"],
            "raw_path": str(ADM1_RAW_PATH.relative_to(ROOT)),
            "normalized_path": str(ADM1_NORMALIZED_PATH.relative_to(ROOT)),
            "raw_sha256": file_sha256(ADM1_RAW_PATH) if ADM1_RAW_PATH.exists() else "",
            "normalized_sha256": file_sha256(ADM1_NORMALIZED_PATH) if ADM1_NORMALIZED_PATH.exists() else "",
            "feature_count": len(adm1_features),
            "geometry_quality": {
                "min_coordinate_count": min(adm1_counts) if adm1_counts else 0,
                "max_coordinate_count": max(adm1_counts) if adm1_counts else 0,
                "formal_rect_fixture": False,
            },
        },
    }


def normalize_boundaries() -> None:
    adm1_features = normalize_adm1_boundaries()
    adm2_features, adm2_info = normalize_adm2_boundaries(adm1_features)
    write_odbl_notice(adm2_info)
    manifest = build_manifest(adm1_features, adm2_features, adm2_info)
    write_json(MANIFEST_PATH, manifest)
    print(f"Normalized {len(adm1_features)} IND ADM1 boundaries -> {ADM1_NORMALIZED_PATH.relative_to(ROOT)}")
    print(f"Normalized {len(adm2_features)} IND ADM2 boundaries -> {ADM2_NORMALIZED_PATH.relative_to(ROOT)}")
    print(f"Wrote manifest -> {MANIFEST_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    normalize_boundaries()
