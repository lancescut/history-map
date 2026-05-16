#!/usr/bin/env python3
"""Generate browser-ready v03 data assets.

The app treats input/v03 CSV files as the auditable source of truth and emits
small static JSON/GeoJSON files under public/data/v03. Dynamic capitals are
driven only by capital_events_v03.csv; free-text capital fields are retained
for audit display but never used directly for playback.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import shutil
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "input" / "v03"
OUT_DIR = ROOT / "public" / "data" / "v03"
YEARS_DIR = OUT_DIR / "years"
TERRITORIES_DIR = OUT_DIR / "territories"
ADMIN_BOUNDARY_DIR = INPUT_DIR / "admin_boundaries"

DATA_VERSION = "v03"
YEAR_MIN = -1046
YEAR_MAX = 1912

CAPITAL_EVENT_TYPES = {
    "initial_capital",
    "relocation",
    "co_capital",
    "temporary_capital",
    "disputed",
}

LOCATION_PRECISIONS = {"exact", "city", "region", "approximate", "unknown"}

TERRITORY_LABEL = "现代省级行政边界拼合，非历史精确边界"
ADMIN_BOUNDARY_PATH = ADMIN_BOUNDARY_DIR / "china_adm1_normalized.geojson"
ADMIN_BOUNDARY_MANIFEST_PATH = ADMIN_BOUNDARY_DIR / "admin_boundary_source_manifest.json"

TRAD_TO_COMMON = str.maketrans(
    {
        "國": "国",
        "後": "后",
        "漢": "汉",
        "晉": "晋",
        "齊": "齐",
        "趙": "赵",
        "韓": "韩",
        "吳": "吴",
        "東": "东",
        "遼": "辽",
        "劉": "刘",
        "楊": "杨",
        "陳": "陈",
        "長": "长",
        "陽": "阳",
        "臨": "临",
        "應": "应",
        "會": "会",
        "寧": "宁",
        "瀋": "沈",
        "瀋": "沈",
        "臺": "台",
        "灣": "湾",
        "蘇": "苏",
        "魯": "鲁",
        "遼": "辽",
        "寧": "宁",
        "龍": "龙",
        "慶": "庆",
        "貴": "贵",
        "雲": "云",
        "陝": "陕",
        "肅": "肃",
        "廣": "广",
        "東": "东",
        "內": "内",
        "縣": "县",
        "鄉": "乡",
        "為": "为",
        "達": "达",
        "經": "经",
        "帶": "带",
    }
)


def clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\ufeff", "").strip())


def common_key(value: str) -> str:
    text = clean(value).translate(TRAD_TO_COMMON)
    return re.sub(r"[\s·・,，、／/()（）\[\]［］「」『』《》<>〈〉\-—－:：;；]", "", text)


def int_required(row: dict[str, str], field: str) -> int:
    value = clean(row.get(field, ""))
    if not value:
        raise ValueError(f"{field} is required")
    return int(value)


def float_required(row: dict[str, str], field: str) -> float:
    value = clean(row.get(field, ""))
    if not value:
        raise ValueError(f"{field} is required")
    return float(value)


def int_optional(value: Any) -> int | None:
    value = clean(value)
    if not value:
        return None
    return int(value)


def bool_required(row: dict[str, str], field: str) -> bool:
    value = clean(row.get(field, "")).lower()
    if value not in {"true", "false"}:
        raise ValueError(f"{field} must be true or false")
    return value == "true"


def year_label(year: int) -> str:
    return f"前{abs(year)}年" if year < 0 else f"{year}年"


def iter_years(start: int, end: int) -> list[int]:
    return [year for year in range(start, end + 1) if year != 0]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_list(value: str) -> list[str]:
    return [clean(piece) for piece in re.split(r"[|；;、,，]", clean(value)) if clean(piece)]


def compact_text(value: str) -> str:
    text = clean(value).translate(TRAD_TO_COMMON)
    return re.sub(r"[\s·・,，、／/()（）\[\]［］「」『』《》<>〈〉\-—－:：;；]", "", text)


def polygon_bbox(coordinates: list[Any]) -> tuple[float, float, float, float]:
    points: list[tuple[float, float]] = []

    def walk(value: Any) -> None:
        if isinstance(value, list) and value and isinstance(value[0], (int, float)):
            points.append((float(value[0]), float(value[1])))
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(coordinates)
    lons = [point[0] for point in points]
    lats = [point[1] for point in points]
    return min(lons), min(lats), max(lons), max(lats)


def ring_area_km2(ring: list[list[float]]) -> float:
    if len(ring) < 4:
        return 0.0
    radius_km = 6371.0088
    area = 0.0
    for index, point in enumerate(ring):
        next_point = ring[(index + 1) % len(ring)]
        lon1 = math.radians(float(point[0]))
        lat1 = math.radians(float(point[1]))
        lon2 = math.radians(float(next_point[0]))
        lat2 = math.radians(float(next_point[1]))
        area += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
    return abs(area * radius_km * radius_km / 2)


def polygon_area_km2(polygon: list[Any]) -> float:
    if not polygon:
        return 0.0
    exterior = ring_area_km2(polygon[0])
    holes = sum(ring_area_km2(ring) for ring in polygon[1:])
    return max(0.0, exterior - holes)


def geometry_area_km2(geometry: dict[str, Any]) -> float:
    if geometry["type"] == "Polygon":
        return polygon_area_km2(geometry["coordinates"])
    if geometry["type"] == "MultiPolygon":
        return sum(polygon_area_km2(polygon) for polygon in geometry["coordinates"])
    return 0.0


def geometry_coordinate_count(geometry: dict[str, Any]) -> int:
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


def load_admin_boundaries() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    payload = read_json(ADMIN_BOUNDARY_PATH)
    features = payload["features"]
    by_id = {feature["properties"]["admin_id"]: feature for feature in features}
    return features, by_id


def load_territory_overrides() -> dict[str, dict[str, Any]]:
    overrides: dict[str, dict[str, Any]] = {}
    for row in read_csv(INPUT_DIR / "territory_overrides_v03.csv"):
        polity_id = clean(row["polity_id"])
        if not polity_id:
            continue
        overrides[polity_id] = {
            "polity_name": clean(row["polity_name"]),
            "admin_ids": split_list(row["admin_ids"]),
            "valid_from_year": int_optional(row.get("valid_from_year", "")),
            "valid_to_year": int_optional(row.get("valid_to_year", "")),
            "match_source": clean(row.get("match_source", "")) or "manual_v1_override",
            "confidence_score": int(clean(row.get("confidence_score", "")) or 0),
            "note": clean(row.get("note", "")),
            "source_titles": clean(row.get("source_titles", "")),
            "source_raw": clean(row.get("source_raw", "")),
        }
    return overrides


def build_admin_aliases(features: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    aliases: list[tuple[str, str, str]] = []
    for feature in features:
        props = feature["properties"]
        names = [props["name"], *(clean(props.get("aliases", "")).split("|"))]
        for name in names:
            name = clean(name)
            if not name:
                continue
            simplified = compact_text(name)
            aliases.append((simplified, props["admin_id"], props["name"]))
            for suffix in ["省", "市", "自治区", "壮族自治区", "回族自治区", "维吾尔自治区"]:
                if simplified.endswith(suffix):
                    aliases.append((simplified[: -len(suffix)], props["admin_id"], props["name"]))
    aliases.sort(key=lambda item: len(item[0]), reverse=True)
    return aliases


def match_admin_units(raw_text: str, aliases: list[tuple[str, str, str]]) -> list[dict[str, str]]:
    haystack = compact_text(raw_text)
    if not haystack:
        return []
    matched: dict[str, dict[str, str]] = {}
    for alias, admin_id, name in aliases:
        if alias and alias in haystack:
            matched[admin_id] = {"admin_id": admin_id, "name": name, "matched_alias": alias}
    return sorted(matched.values(), key=lambda item: item["admin_id"])


def build_polity_territories(
    polities: list[dict[str, str]],
    admin_features: list[dict[str, Any]],
    admin_by_id: dict[str, dict[str, Any]],
    territory_overrides: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    aliases = build_admin_aliases(admin_features)
    territories: dict[str, dict[str, Any]] = {}
    report_rows: list[dict[str, Any]] = []
    features: list[dict[str, Any]] = []
    admin_unit_features: list[dict[str, Any]] = []
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()

    for polity in polities:
        polity_id = polity["polity_id"]
        raw_text = polity.get("modern_admin_units_raw", "")
        matches = match_admin_units(raw_text, aliases)
        override = territory_overrides.get(polity_id)
        match_source = "modern_admin_units_raw"
        confidence_note = ""
        if override:
            matches = [
                {
                    "admin_id": admin_id,
                    "name": admin_by_id[admin_id]["properties"]["name"],
                    "matched_alias": admin_by_id[admin_id]["properties"]["name"],
                }
                for admin_id in override["admin_ids"]
                if admin_id in admin_by_id
            ]
            raw_text = raw_text or override["source_raw"] or f"{polity['polity_name']} v1 人工维护王朝级现代行政区近似 override"
            match_source = override["match_source"]
            confidence_note = override["note"]
        matched_ids = [match["admin_id"] for match in matches]
        matched_names = [match["name"] for match in matches]
        if not matches:
            territories[polity_id] = {
                "geometry_ref": None,
                "territory_status": "missing",
                "territory_method": "modern_admin_approximation",
                "approx_area_km2": None,
                "match_confidence": 0,
                "matched_admin_ids": [],
                "matched_admin_units": [],
                "source_text": raw_text,
                "match_source": match_source,
                "confidence_note": confidence_note,
                "label": TERRITORY_LABEL,
            }
            report_rows.append(
                {
                    "polity_id": polity_id,
                    "polity_name": polity["polity_name"],
                    "territory_status": "missing",
                    "matched_admin_ids": "",
                    "matched_admin_units": "",
                    "match_source": match_source,
                    "match_confidence": 0,
                    "confidence_note": confidence_note,
                    "approx_area_km2": "",
                    "source_text": raw_text,
                    "note": "无法从 modern_admin_units_raw 匹配现代行政区",
                }
            )
            continue

        polygons: list[Any] = []
        area = 0.0
        bboxes: list[tuple[float, float, float, float]] = []
        coordinate_count = 0
        for admin_id in matched_ids:
            admin_feature = admin_by_id[admin_id]
            geom = admin_feature["geometry"]
            if geom["type"] == "Polygon":
                polygons.append(geom["coordinates"])
                bbox = polygon_bbox(geom["coordinates"])
            elif geom["type"] == "MultiPolygon":
                polygons.extend(geom["coordinates"])
                bbox = polygon_bbox(geom["coordinates"])
            else:
                continue
            bboxes.append(bbox)
            area += geometry_area_km2(geom)
            coordinate_count += geometry_coordinate_count(geom)
            admin_unit_features.append(
                {
                    "type": "Feature",
                    "geometry": geom,
                    "properties": {
                        "polity_id": polity_id,
                        "polity_name": polity["polity_name"],
                        "admin_id": admin_id,
                        "admin_name": admin_feature["properties"]["name"],
                        "match_source": match_source,
                    },
                }
            )

        low_confidence_markers = ["部分", "一带", "一帶", "曾经", "曾經", "达到", "達到", "后扩张", "中心"]
        confidence = override["confidence_score"] if override else 86
        if len(matches) > 4 and not override:
            confidence -= 10
        if any(marker in raw_text for marker in low_confidence_markers):
            confidence -= 14
        confidence = max(45, confidence)
        territory_status = "matched_low_confidence" if confidence < 70 else "matched"
        min_lon = min(bbox[0] for bbox in bboxes)
        min_lat = min(bbox[1] for bbox in bboxes)
        max_lon = max(bbox[2] for bbox in bboxes)
        max_lat = max(bbox[3] for bbox in bboxes)
        centroid = [(min_lon + max_lon) / 2, (min_lat + max_lat) / 2]
        territory = {
            "geometry_ref": f"territories/approx_polities.geojson#{polity_id}",
            "territory_status": territory_status,
            "territory_method": "modern_admin_approximation",
            "approx_area_km2": round(area, 1),
            "match_confidence": confidence,
            "matched_admin_ids": matched_ids,
            "matched_admin_units": matched_names,
            "source_text": raw_text,
            "geometry_source": str(ADMIN_BOUNDARY_PATH.relative_to(ROOT)),
            "geometry_source_license": admin_features[0]["properties"].get("source_license", ""),
            "geometry_source_attribution": admin_features[0]["properties"].get("source_attribution", ""),
            "match_source": match_source,
            "confidence_note": confidence_note,
            "geometry_coordinate_count": coordinate_count,
            "generated_at": generated_at,
            "label": TERRITORY_LABEL,
            "centroid": centroid,
        }
        territories[polity_id] = territory
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "MultiPolygon", "coordinates": polygons},
                "properties": {
                    "polity_id": polity_id,
                    "polity_name": polity["polity_name"],
                    "macro_period": polity["macro_period"],
                    "dynasty_name": polity["dynasty_name"],
                    "polity_type": polity["polity_type"],
                    **territory,
                },
            }
        )
        report_rows.append(
            {
                "polity_id": polity_id,
                "polity_name": polity["polity_name"],
                "territory_status": territory_status,
                "matched_admin_ids": " | ".join(matched_ids),
                "matched_admin_units": " | ".join(matched_names),
                "match_source": match_source,
                "match_confidence": confidence,
                "confidence_note": confidence_note,
                "approx_area_km2": round(area, 1),
                "source_text": raw_text,
                "note": f"{TERRITORY_LABEL}；match_source={match_source}",
            }
        )

    feature_collection = {"type": "FeatureCollection", "features": features}
    admin_unit_collection = {"type": "FeatureCollection", "features": admin_unit_features}
    return territories, feature_collection, admin_unit_collection, report_rows


def validate_and_normalize_capitals(
    raw_rows: list[dict[str, str]],
    polities_by_id: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    events: list[dict[str, Any]] = []
    errors: list[str] = []

    for index, row in enumerate(raw_rows, start=2):
        try:
            event_id = clean(row.get("capital_event_id", ""))
            polity_id = clean(row.get("polity_id", ""))
            if not event_id:
                raise ValueError("capital_event_id is required")
            if event_id in seen:
                raise ValueError(f"duplicate capital_event_id {event_id}")
            seen.add(event_id)
            if polity_id not in polities_by_id:
                raise ValueError(f"unknown polity_id {polity_id}")

            from_year = int_required(row, "valid_from_year")
            to_year = int_required(row, "valid_to_year")
            if from_year == 0 or to_year == 0:
                raise ValueError("capital event cannot include year 0")
            if from_year > to_year:
                raise ValueError("valid_from_year cannot be after valid_to_year")

            polity = polities_by_id[polity_id]
            polity_start = int_required(polity, "polity_start_year")
            polity_end = int_required(polity, "polity_end_year")
            if from_year < polity_start or to_year > polity_end:
                raise ValueError(
                    f"capital range {from_year}..{to_year} outside polity range "
                    f"{polity_start}..{polity_end}"
                )

            event_type = clean(row.get("event_type", ""))
            if event_type not in CAPITAL_EVENT_TYPES:
                raise ValueError(f"invalid event_type {event_type}")
            location_precision = clean(row.get("location_precision", ""))
            if location_precision not in LOCATION_PRECISIONS:
                raise ValueError(f"invalid location_precision {location_precision}")

            longitude = float_required(row, "longitude")
            latitude = float_required(row, "latitude")
            if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
                raise ValueError("longitude/latitude out of range")

            confidence_score = int_required(row, "confidence_score")
            if not 0 <= confidence_score <= 100:
                raise ValueError("confidence_score must be 0..100")

            if not clean(row.get("source_titles", "")):
                raise ValueError("source_titles is required")
            if not clean(row.get("source_raw", "")):
                raise ValueError("source_raw is required")

            event = {
                "capital_event_id": event_id,
                "polity_id": polity_id,
                "polity_name": polity["polity_name"],
                "capital_name_historical": clean(row.get("capital_name_historical", "")),
                "capital_name_modern": clean(row.get("capital_name_modern", "")),
                "valid_from_year": from_year,
                "valid_from_label": year_label(from_year),
                "valid_to_year": to_year,
                "valid_to_label": year_label(to_year),
                "longitude": longitude,
                "latitude": latitude,
                "is_primary": bool_required(row, "is_primary"),
                "event_type": event_type,
                "location_precision": location_precision,
                "source_titles": clean(row.get("source_titles", "")),
                "source_urls": clean(row.get("source_urls", "")),
                "source_raw": clean(row.get("source_raw", "")),
                "confidence_score": confidence_score,
                "confidence_note": clean(row.get("confidence_note", "")),
                "is_disputed": event_type == "disputed" or confidence_score < 60,
            }
            events.append(event)
        except Exception as exc:  # noqa: BLE001 - report every data-row failure together.
            errors.append(f"row {index}: {exc}")

    if errors:
        raise SystemExit("capital_events_v03.csv failed validation:\n" + "\n".join(errors))

    return sorted(events, key=lambda item: (item["polity_id"], item["valid_from_year"], item["capital_event_id"]))


def build_capital_migrations(events_by_polity: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    migrations: list[dict[str, Any]] = []
    for polity_id, events in events_by_polity.items():
        primary_events = [event for event in events if event["is_primary"]]
        primary_events.sort(key=lambda item: (item["valid_from_year"], item["valid_to_year"]))
        for current in primary_events:
            if current["event_type"] not in {"relocation", "disputed"}:
                continue
            previous_candidates = [
                event
                for event in primary_events
                if event["capital_event_id"] != current["capital_event_id"]
                and event["valid_from_year"] < current["valid_from_year"]
            ]
            if not previous_candidates:
                continue
            previous = max(previous_candidates, key=lambda item: item["valid_from_year"])
            migration_id = f"migration_{previous['capital_event_id']}_{current['capital_event_id']}"
            migrations.append(
                {
                    "migration_id": migration_id,
                    "polity_id": polity_id,
                    "polity_name": current["polity_name"],
                    "year": current["valid_from_year"],
                    "year_label": year_label(current["valid_from_year"]),
                    "from_capital_event_id": previous["capital_event_id"],
                    "to_capital_event_id": current["capital_event_id"],
                    "from_capital_name": previous["capital_name_historical"],
                    "to_capital_name": current["capital_name_historical"],
                    "from_coordinates": [previous["longitude"], previous["latitude"]],
                    "to_coordinates": [current["longitude"], current["latitude"]],
                    "is_disputed": current["is_disputed"],
                    "confidence_score": current["confidence_score"],
                    "label": f"迁都：{previous['capital_name_historical']} → {current['capital_name_historical']}",
                }
            )
    return sorted(migrations, key=lambda item: (item["year"], item["polity_id"]))


def active_capitals_for_year(events: list[dict[str, Any]], year: int) -> list[dict[str, Any]]:
    return [
        event
        for event in events
        if event["valid_from_year"] <= year <= event["valid_to_year"]
    ]


def capital_quality(active_events: list[dict[str, Any]], all_events: list[dict[str, Any]]) -> dict[str, Any]:
    if not all_events:
        return {
            "status": "missing",
            "label": "暂无可解析都城资料",
            "has_dispute": False,
            "lowest_confidence_score": None,
            "location_precision": "unknown",
            "source_status": "missing",
        }
    if not active_events:
        return {
            "status": "out_of_range",
            "label": "该年度暂无有效都城事件",
            "has_dispute": False,
            "lowest_confidence_score": None,
            "location_precision": "unknown",
            "source_status": "present",
        }

    has_dispute = any(event["is_disputed"] for event in active_events)
    lowest = min(event["confidence_score"] for event in active_events)
    precision_rank = {"exact": 0, "city": 1, "region": 2, "approximate": 3, "unknown": 4}
    weakest = max(active_events, key=lambda event: precision_rank[event["location_precision"]])
    label = "都城/迁都年份有争议" if has_dispute else "已解析当前有效都城"
    return {
        "status": "disputed" if has_dispute else "present",
        "label": label,
        "has_dispute": has_dispute,
        "lowest_confidence_score": lowest,
        "location_precision": weakest["location_precision"],
        "source_status": "present" if all(event["source_titles"] for event in active_events) else "partial",
    }


def build_alias_index(polities: list[dict[str, str]], rulers: list[dict[str, str]], capitals: list[dict[str, Any]]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []

    def add(alias: str, entity_type: str, entity_id: str, label: str, payload: dict[str, Any]) -> None:
        alias = clean(alias)
        if not alias:
            return
        entries.append(
            {
                "alias": alias,
                "normalized": common_key(alias),
                "entity_type": entity_type,
                "entity_id": entity_id,
                "label": label,
                **payload,
            }
        )

    for polity in polities:
        add(polity["polity_name"], "polity", polity["polity_id"], polity["polity_name"], {
            "polity_id": polity["polity_id"],
            "start_year": int_optional(polity.get("polity_start_year", "")),
            "end_year": int_optional(polity.get("polity_end_year", "")),
        })
        for alias in split_list(polity.get("polity_aliases", "")):
            add(alias, "polity", polity["polity_id"], polity["polity_name"], {
                "polity_id": polity["polity_id"],
                "start_year": int_optional(polity.get("polity_start_year", "")),
                "end_year": int_optional(polity.get("polity_end_year", "")),
            })

    for ruler in rulers:
        for field in ["ruler_name", "ruler_temple_name", "ruler_posthumous_name", "ruler_personal_name"]:
            add(ruler.get(field, ""), "ruler", ruler["ruler_id"], ruler["ruler_name"], {
                "polity_id": ruler["polity_id"],
                "start_year": int_optional(ruler.get("ruler_reign_start_year", "")),
                "end_year": int_optional(ruler.get("ruler_reign_end_year", "")),
            })

    for capital in capitals:
        for field in ["capital_name_historical", "capital_name_modern"]:
            add(capital[field], "capital", capital["capital_event_id"], capital[field], {
                "polity_id": capital["polity_id"],
                "capital_event_id": capital["capital_event_id"],
                "start_year": capital["valid_from_year"],
                "end_year": capital["valid_to_year"],
                "longitude": capital["longitude"],
                "latitude": capital["latitude"],
            })

    dedup: dict[tuple[str, str, str], dict[str, Any]] = {}
    for entry in entries:
        dedup[(entry["normalized"], entry["entity_type"], entry["entity_id"])] = entry
    return {"entries": sorted(dedup.values(), key=lambda item: (item["normalized"], item["entity_type"]))}


def main() -> None:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()

    polities = read_csv(INPUT_DIR / "chinese_history_polities_master_v03.csv")
    rulers = read_csv(INPUT_DIR / "chinese_history_rulers_master_v03.csv")
    yearly_rows = read_csv(INPUT_DIR / "chinese_history_polities_yearly_v03.csv")
    issues = read_csv(INPUT_DIR / "chinese_history_unresolved_or_disputed_v03.csv")
    validation = read_csv(INPUT_DIR / "chinese_history_validation_report_v03.csv")
    capital_raw = read_csv(INPUT_DIR / "capital_events_v03.csv")
    admin_features, admin_by_id = load_admin_boundaries()
    admin_boundary_manifest = read_json(ADMIN_BOUNDARY_MANIFEST_PATH)
    territory_overrides = load_territory_overrides()

    polities_by_id = {row["polity_id"]: row for row in polities}
    issues_by_polity: dict[str, list[dict[str, str]]] = defaultdict(list)
    for issue in issues:
        issues_by_polity[issue["polity_id"]].append(issue)

    capital_events = validate_and_normalize_capitals(capital_raw, polities_by_id)
    events_by_polity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in capital_events:
        events_by_polity[event["polity_id"]].append(event)

    migrations = build_capital_migrations(events_by_polity)
    migrations_by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for migration in migrations:
        migrations_by_year[migration["year"]].append(migration)

    polity_territories, territory_geojson, admin_units_by_polity_geojson, territory_report_rows = build_polity_territories(
        polities,
        admin_features,
        admin_by_id,
        territory_overrides,
    )

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    YEARS_DIR.mkdir(parents=True, exist_ok=True)

    write_json(OUT_DIR / "polities.json", {"data_version": DATA_VERSION, "polities": polities})
    write_json(OUT_DIR / "rulers.json", {"data_version": DATA_VERSION, "rulers": rulers})
    write_json(OUT_DIR / "issues.json", {"data_version": DATA_VERSION, "issues": issues})
    write_json(OUT_DIR / "validation.json", {"data_version": DATA_VERSION, "checks": validation})

    write_json(
        OUT_DIR / "capitals.json",
        {
            "data_version": DATA_VERSION,
            "generated_at": generated_at,
            "capital_events": capital_events,
            "capital_migrations": migrations,
            "by_polity": events_by_polity,
            "migrations_by_year": {str(year): rows for year, rows in migrations_by_year.items()},
        },
    )

    capital_features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [event["longitude"], event["latitude"]]},
            "properties": event,
        }
        for event in capital_events
    ]
    write_json(OUT_DIR / "capital_events.geojson", {"type": "FeatureCollection", "features": capital_features})

    migration_features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [migration["from_coordinates"], migration["to_coordinates"]],
            },
            "properties": migration,
        }
        for migration in migrations
    ]
    write_json(OUT_DIR / "capital_migration_edges.geojson", {"type": "FeatureCollection", "features": migration_features})
    write_json(TERRITORIES_DIR / "approx_polities.geojson", territory_geojson)
    write_json(TERRITORIES_DIR / "admin_units_by_polity.geojson", admin_units_by_polity_geojson)
    write_json(TERRITORIES_DIR / "modern_admin_units.geojson", {"type": "FeatureCollection", "features": admin_features})
    write_csv(
        TERRITORIES_DIR / "territory_match_report.csv",
        territory_report_rows,
        [
            "polity_id",
            "polity_name",
            "territory_status",
            "matched_admin_ids",
            "matched_admin_units",
            "match_source",
            "match_confidence",
            "confidence_note",
            "approx_area_km2",
            "source_text",
            "note",
        ],
    )

    coverage_rows: list[dict[str, Any]] = []
    for polity in polities:
        events = events_by_polity.get(polity["polity_id"], [])
        coverage_rows.append(
            {
                "polity_id": polity["polity_id"],
                "polity_name": polity["polity_name"],
                "has_structured_capital": bool(events),
                "capital_event_count": len(events),
                "has_migration": any(event["event_type"] in {"relocation", "disputed"} for event in events),
                "has_disputed_capital": any(event["is_disputed"] for event in events),
                "capital_modern_raw": polity.get("capital_modern", ""),
                "coverage_note": "structured" if events else "暂无可解析都城资料",
            }
        )
    write_csv(
        OUT_DIR / "capital_coverage_report.csv",
        coverage_rows,
        [
            "polity_id",
            "polity_name",
            "has_structured_capital",
            "capital_event_count",
            "has_migration",
            "has_disputed_capital",
            "capital_modern_raw",
            "coverage_note",
        ],
    )

    write_json(OUT_DIR / "alias_index.json", build_alias_index(polities, rulers, capital_events))

    yearly_by_year: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in yearly_rows:
        yearly_by_year[int(row["year"])].append(row)

    all_years = sorted(yearly_by_year)
    for year in all_years:
        rows = yearly_by_year[year]
        polity_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            polity_groups[row["polity_id"]].append(row)

        year_migrations = migrations_by_year.get(year, [])
        migration_polity_ids = {migration["polity_id"] for migration in year_migrations}
        polities_payload: list[dict[str, Any]] = []
        for polity_id, polity_rows in sorted(polity_groups.items(), key=lambda item: item[1][0]["polity_name"]):
            first = polity_rows[0]
            rulers_payload = [
                {
                    "ruler_id": row["ruler_id"],
                    "ruler_name": row["ruler_name"],
                    "ruler_title": row["ruler_title"],
                    "ruler_temple_name": row["ruler_temple_name"],
                    "ruler_posthumous_name": row["ruler_posthumous_name"],
                    "ruler_personal_name": row["ruler_personal_name"],
                    "era_names": row["era_names"],
                    "ruler_reign_start_year": int(row["ruler_reign_start_year"]) if row["ruler_reign_start_year"] else None,
                    "ruler_reign_end_year": int(row["ruler_reign_end_year"]) if row["ruler_reign_end_year"] else None,
                    "ruler_source_title": row["ruler_source_title"],
                    "ruler_source_url": row["ruler_source_url"],
                    "ruler_confidence_score": int(row["ruler_confidence_score"]) if row["ruler_confidence_score"] else None,
                }
                for row in polity_rows
                if row["ruler_id"]
            ]
            active = active_capitals_for_year(events_by_polity.get(polity_id, []), year)
            all_capitals = events_by_polity.get(polity_id, [])
            territory = polity_territories[polity_id]
            polities_payload.append(
                {
                    "polity_id": polity_id,
                    "polity_name": first["polity_name"],
                    "polity_aliases": first["polity_aliases"],
                    "macro_period": first["macro_period"],
                    "dynasty_name": first["dynasty_name"],
                    "polity_type": first["polity_type"],
                    "polity_start_year": int(first["polity_start_year"]) if first["polity_start_year"] else None,
                    "polity_end_year": int(first["polity_end_year"]) if first["polity_end_year"] else None,
                    "capital_modern_raw": first["capital_modern"],
                    "modern_admin_units_raw": first["modern_admin_units_raw"],
                    "ruling_family_or_clan": first["ruling_family_or_clan"],
                    "ethnicity_or_group": first["ethnicity_or_group"],
                    "founder": first["founder"],
                    "last_ruler": first["last_ruler"],
                    "destroyed_by_or_successor": first["destroyed_by_or_successor"],
                    "polity_source_titles": first["polity_source_titles"],
                    "polity_source_urls": first["polity_source_urls"],
                    "polity_source_raw": first["polity_source_raw"],
                    "confidence_score": int(first["confidence_score"]) if first["confidence_score"] else None,
                    "rulers": rulers_payload,
                    "capitals": active,
                    "active_capital_event_ids": [event["capital_event_id"] for event in active],
                    "has_capital_migration_in_year": polity_id in migration_polity_ids,
                    "capital_quality": capital_quality(active, all_capitals),
                    "territory": territory,
                    "quality": {
                        "confidence_score": int(first["confidence_score"]) if first["confidence_score"] else None,
                        "has_dispute": bool(issues_by_polity.get(polity_id)),
                        "has_unmatched_ruler": any(row["row_granularity"] == "year_polity_unmatched_ruler" for row in polity_rows),
                    },
                }
            )

        write_json(
            YEARS_DIR / f"{year}.json",
            {
                "year": year,
                "year_label": year_label(year),
                "polity_count": len(polities_payload),
                "polities": polities_payload,
                "capital_migrations": year_migrations,
                "has_capital_migration_in_year": bool(year_migrations),
            },
        )

    input_files = [
        INPUT_DIR / "chinese_history_polities_master_v03.csv",
        INPUT_DIR / "chinese_history_rulers_master_v03.csv",
        INPUT_DIR / "chinese_history_polities_yearly_v03.csv",
        INPUT_DIR / "chinese_history_unresolved_or_disputed_v03.csv",
        INPUT_DIR / "chinese_history_validation_report_v03.csv",
        INPUT_DIR / "capital_events_v03.csv",
        INPUT_DIR / "territory_overrides_v03.csv",
        ADMIN_BOUNDARY_DIR / "china_adm1_geoboundaries_raw.geojson",
        ADMIN_BOUNDARY_PATH,
        ADMIN_BOUNDARY_MANIFEST_PATH,
    ]
    matched_territories = [item for item in polity_territories.values() if item["territory_status"] != "missing"]
    low_confidence_territories = [
        item for item in matched_territories if item["territory_status"] == "matched_low_confidence"
    ]
    max_year = max(yearly_by_year, key=lambda item: len(yearly_by_year[item]))
    max_year_polity_ids = {row["polity_id"] for row in yearly_by_year[max_year]}
    max_year_territory_coverage = sum(
        1
        for polity_id in max_year_polity_ids
        if polity_territories[polity_id]["territory_status"] != "missing"
    )
    metadata = {
        "data_version": DATA_VERSION,
        "generated_at": generated_at,
        "year_min": min(all_years),
        "year_max": max(all_years),
        "year_count": len(all_years),
        "has_year_zero": 0 in all_years,
        "polity_count": len(polities),
        "ruler_count": len(rulers),
        "yearly_row_count": len(yearly_rows),
        "issue_count": len(issues),
        "validation_check_count": len(validation),
        "capital_event_count": len(capital_events),
        "capital_polity_count": len(events_by_polity),
        "capital_migration_count": len(migrations),
        "capital_migration_years": sorted({migration["year"] for migration in migrations}),
        "territory_polity_count": len(matched_territories),
        "territory_missing_count": len(polities) - len(matched_territories),
        "territory_low_confidence_count": len(low_confidence_territories),
        "territory_coverage_ratio": round(len(matched_territories) / len(polities), 4),
        "territory_label": TERRITORY_LABEL,
        "admin_boundary_source": admin_boundary_manifest["source"],
        "admin_boundary_source_release": admin_boundary_manifest["source_release"],
        "admin_boundary_license": admin_boundary_manifest["source_license"],
        "admin_boundary_attribution": admin_boundary_manifest["source_attribution"],
        "admin_boundary_feature_count": admin_boundary_manifest["feature_count"],
        "admin_boundary_crs": admin_boundary_manifest["crs"],
        "territory_geometry_quality": admin_boundary_manifest["geometry_quality"],
        "max_concurrent_polities": max(len(rows) for rows in yearly_by_year.values()),
        "max_concurrent_polity_years": [
            year for year, rows in yearly_by_year.items() if len(rows) == max(len(items) for items in yearly_by_year.values())
        ],
        "max_concurrent_territory_coverage": max_year_territory_coverage,
        "input_files": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": file_sha256(path),
            }
            for path in input_files
        ],
    }
    write_json(OUT_DIR / "metadata.json", metadata)

    print(
        "Generated public v03 data:",
        f"{len(all_years)} years,",
        f"{len(capital_events)} capital events,",
        f"{len(migrations)} migrations,",
        f"{len(matched_territories)} territories",
    )


if __name__ == "__main__":
    main()
