#!/usr/bin/env python3
"""Generate browser-ready vIndian data assets.

vIndian schema is v03-compatible (see input/vIndian/dataset_manifest_vIndian.json).
Rather than retrofit scripts/generate_public_data.py (3000+ lines of Chinese-specific
logic — neighbor borders, nomadic classification, republic-period adjustments), this
script focuses on producing the minimum set of files the frontend loader needs:

- metadata.json
- events.json / anecdotes.json / mythology.json
- contexts.json (empty if no contexts csv yet)
- capitals.json
- alias_index.json
- strategic_locations.json (+ geojson stub)
- issues.json / validation.json
- years/{Y}.json
- story_presets.json (empty)
- territories/*.geojson + polity_county_index.json (empty stubs; Phase 1.1 will populate)

Run:
    python scripts/build_vindian_public_data.py
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "input" / "vIndian"
OUT_DIR = ROOT / "public" / "data" / "vIndian"
YEARS_DIR = OUT_DIR / "years"
TERRITORIES_DIR = OUT_DIR / "territories"
ADMIN_BOUNDARY_DIR = INPUT_DIR / "admin_boundaries"

DATA_VERSION = "vIndian"


def read_csv(path: Path) -> list[dict[str, Any]]:
    """utf-8-sig handles BOM that bootstrap_vindian_dataset.py leaves on row 1."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def write_json(path: Path, payload: Any, *, compact: bool = False) -> None:
    """Write JSON payload. Use `compact=True` for large machine-consumed files
    (territory geojsons, per-year payloads) to avoid spending megabytes on
    pretty-print whitespace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        if compact:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(payload, f, ensure_ascii=False, indent=2)


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def int_opt(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def float_opt(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def pipe_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    return [item.strip() for item in str(value).split("|") if item.strip()]


def normalize_key(value: Any) -> str:
    """Search/lookup key shared by alias index and territory text matching."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[\s_\-()/,;:]+", "", text.lower())
    return text


def normalize_search_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text.lower()).strip()


def unique_list(values: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    out: list[Any] = []
    for value in values:
        if value is None or value == "" or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def year_label(year: int) -> str:
    if year < 0:
        return f"前{abs(year)}年"
    return f"{year}年"


def normalize_context_row(row: dict[str, Any]) -> dict[str, Any]:
    """Map historical_contexts_vIndian.csv row to the HistoricalContext shape the frontend expects.

    跨度年份 start_year / end_year 是关键字段。year 字段在前端运行时被覆盖为 currentPlaybackYear，
    保留 start_year 作为锚点；progress_ratio 由前端按当年位置计算。
    """
    context_id = (row.get("context_id") or "").strip()
    if not context_id:
        return {}
    start_year = int_opt(row.get("start_year"))
    end_year = int_opt(row.get("end_year"))
    if start_year is None or end_year is None:
        return {}
    lng = float_opt(row.get("longitude"))
    lat = float_opt(row.get("latitude"))
    return {
        "context_id": context_id,
        "year": start_year,
        "year_label": (row.get("start_label") or year_label(start_year)).strip(),
        "current_year": start_year,
        "title": (row.get("title") or "").strip(),
        "description": (row.get("description") or "").strip(),
        "start_year": start_year,
        "end_year": end_year,
        "start_label": (row.get("start_label") or year_label(start_year)).strip(),
        "end_label": (row.get("end_label") or year_label(end_year)).strip(),
        "progress_ratio": 0.0,
        "sort_order": int_opt(row.get("sort_order")) or 0,
        "display_priority": int_opt(row.get("display_priority")) or 500,
        "longitude": lng,
        "latitude": lat,
        "location_name": (row.get("location_name") or "").strip(),
        "source_titles": (row.get("source_titles") or "").strip(),
        "source_urls": pipe_list(row.get("source_urls")),
        "source_type": (row.get("source_type") or "synthesized_secondary").strip(),
        "confidence_score": float_opt(row.get("confidence_score")),
        "confidence_note": (row.get("confidence_note") or "").strip(),
    }


def normalize_event_row(row: dict[str, Any], default_kind: str = "event") -> dict[str, Any]:
    """Map CSV row to the HistoricalEvent shape the frontend expects."""
    year_val = int_opt(row.get("year"))
    if year_val is None:
        return {}
    event_id = (row.get("event_id") or row.get("anecdote_id") or "").strip()
    if not event_id:
        return {}
    lng = float_opt(row.get("longitude"))
    lat = float_opt(row.get("latitude"))
    is_anecdote = default_kind == "anecdote"
    return {
        "event_id": event_id,
        "year": year_val,
        "year_label": (row.get("year_label") or year_label(year_val)).strip(),
        "sort_order": int_opt(row.get("sort_order")) or 0,
        "date_label": (row.get("date_label") or "").strip(),
        "date_precision": (row.get("date_precision") or "year").strip(),
        "coverage_role": (row.get("coverage_role") or ("anecdote" if is_anecdote else "primary")).strip(),
        "coverage_start_year": int_opt(row.get("coverage_start_year")) or year_val,
        "coverage_end_year": int_opt(row.get("coverage_end_year")) or year_val,
        "coverage_group_id": (row.get("coverage_group_id") or "").strip(),
        "item_kind": "anecdote" if is_anecdote else (row.get("item_kind") or "event").strip(),
        "event_type": (row.get("event_type") or ("allusion" if is_anecdote else "other")).strip(),
        "title": (row.get("title") or "").strip(),
        "description": (row.get("description") or row.get("short_description") or "").strip(),
        "significance": (row.get("significance") or "").strip(),
        "primary_education_stage": (row.get("primary_education_stage") or "").strip(),
        "education_stage_tags": pipe_list(row.get("education_stage_tags")),
        "curriculum_basis": (row.get("curriculum_basis") or "").strip(),
        "importance_level": int_opt(row.get("importance_level")) or 3,
        "display_priority": int_opt(row.get("display_priority")) or 500,
        "longitude": lng,
        "latitude": lat,
        "related_polity_ids": pipe_list(row.get("related_polity_ids")),
        "related_people": pipe_list(row.get("related_people")),
        "location_name": (row.get("location_name") or row.get("location_historical_name") or "").strip(),
        "location_historical_name": (row.get("location_historical_name") or "").strip() or None,
        "location_modern_name": (row.get("location_modern_name") or "").strip() or None,
        "location_modern_admin_id": (row.get("location_modern_admin_id") or "").strip() or None,
        "location_precision": (row.get("location_precision") or "").strip() or None,
        "location_confidence_score": float_opt(row.get("location_confidence_score")),
        "location_source_titles": (row.get("location_source_titles") or "").strip() or None,
        "location_source_urls": pipe_list(row.get("location_source_urls")) or None,
        "location_note": (row.get("location_note") or "").strip() or None,
        "source_titles": (row.get("source_titles") or row.get("source_title") or "").strip(),
        "source_urls": pipe_list(row.get("source_urls") or row.get("source_url")),
        "source_type": (row.get("source_type") or "").strip(),
        "confidence_score": float_opt(row.get("confidence_score")),
        "confidence_note": (row.get("confidence_note") or "").strip(),
        "fact_review_status": (row.get("fact_review_status") or row.get("review_status") or "").strip() or None,
        "review_note": (row.get("review_note") or "").strip() or None,
        # anecdote-only
        "anecdote_id": (row.get("anecdote_id") or "").strip() or None,
        "anecdote_type": (row.get("anecdote_type") or "").strip() or None,
        "dynasty_name": (row.get("dynasty_name") or "").strip() or None,
        "macro_period": (row.get("macro_period") or "").strip() or None,
        "phrase": (row.get("phrase") or "").strip() or None,
        "story_text": (row.get("story_text") or "").strip() or None,
        "source_title": (row.get("source_title") or "").strip() or None,
        "source_section": (row.get("source_section") or "").strip() or None,
        "source_url": (row.get("source_url") or "").strip() or None,
        "source_note": (row.get("source_note") or "").strip() or None,
        "is_anecdote": is_anecdote or None,
    }


def normalize_myth_row(row: dict[str, Any]) -> dict[str, Any]:
    """Map a mythological_timeline row into the HistoricalAnecdote shape with
    anecdote_type='mythological' so the frontend stream renders it like a story
    card. Skip rows without a usable `year` (the playback timeline is purely numeric).
    """
    year_val = int_opt(row.get("year")) or int_opt(row.get("traditional_year"))
    if year_val is None:
        return {}
    myth_id = (row.get("myth_id") or "").strip()
    if not myth_id:
        return {}
    title = (row.get("title") or "").strip()
    summary = (row.get("summary") or "").strip()
    historicity = (row.get("historicity_status") or "").strip()
    description = summary
    if historicity:
        description = f"{summary}（{historicity}）" if summary else f"（{historicity}）"
    lng = float_opt(row.get("longitude"))
    lat = float_opt(row.get("latitude"))
    return {
        "event_id": f"myth_{myth_id}",
        "year": year_val,
        "year_label": (row.get("year_label") or year_label(year_val)).strip(),
        "sort_order": int_opt(row.get("relative_sequence")) or 0,
        "date_label": (row.get("calendar_note") or row.get("year_label") or "").strip(),
        "date_precision": (row.get("date_precision") or "approx").strip(),
        "coverage_role": "anecdote",
        "coverage_start_year": int_opt(row.get("coverage_start_year")) or year_val,
        "coverage_end_year": int_opt(row.get("coverage_end_year")) or year_val,
        "coverage_group_id": (row.get("mythic_cycle") or "").strip(),
        "item_kind": "anecdote",
        "event_type": "allusion",
        "title": title or myth_id,
        "description": description,
        "significance": (row.get("cultural_significance") or "").strip(),
        "primary_education_stage": "",
        "education_stage_tags": [],
        "curriculum_basis": "",
        "importance_level": 2,
        "display_priority": 800,
        "longitude": lng,
        "latitude": lat,
        "related_polity_ids": pipe_list(row.get("related_historical_polity_ids")),
        "related_people": pipe_list(row.get("related_people_or_deities")),
        "location_name": (row.get("location_name") or "").strip(),
        "source_titles": (row.get("source_titles") or "").strip(),
        "source_urls": pipe_list(row.get("source_urls")),
        "source_type": (row.get("source_type") or "").strip(),
        "confidence_score": float_opt(row.get("confidence_score")),
        "confidence_note": (row.get("confidence_note") or "").strip(),
        "anecdote_id": myth_id,
        "anecdote_type": "mythological",
        "dynasty_name": (row.get("tradition_name") or "").strip() or None,
        "macro_period": (row.get("tradition_type") or "").strip() or None,
        "is_anecdote": True,
    }


def normalize_capital_event(row: dict[str, Any], polity_name_by_id: dict[str, str] | None = None) -> dict[str, Any]:
    polity_id = (row.get("polity_id") or "").strip()
    polity_name = (polity_name_by_id or {}).get(polity_id, "")
    return {
        "capital_event_id": (row.get("capital_event_id") or "").strip(),
        "polity_id": polity_id,
        "polity_name": polity_name,
        "polity_display_name": polity_name,
        "capital_event_type": (row.get("capital_event_type") or "initial_capital").strip(),
        "event_type": (row.get("capital_event_type") or "initial_capital").strip(),
        "capital_name_historical": (row.get("capital_name_historical") or "").strip(),
        "capital_name_modern": (row.get("capital_name_modern") or "").strip(),
        "valid_from_year": int_opt(row.get("valid_from_year")),
        "valid_from_label": year_label(int_opt(row.get("valid_from_year")) or 0),
        "valid_to_year": int_opt(row.get("valid_to_year")),
        "valid_to_label": year_label(int_opt(row.get("valid_to_year")) or 0),
        "longitude": float_opt(row.get("longitude")),
        "latitude": float_opt(row.get("latitude")),
        "is_primary": True,
        "is_disputed": False,
        "location_precision": (row.get("location_precision") or "city").strip(),
        "location_modern_admin_id": (row.get("location_modern_admin_id") or "").strip(),
        "source_titles": (row.get("source_titles") or "").strip(),
        "source_urls": pipe_list(row.get("source_urls")),
        "source_raw": (row.get("source_raw") or "").strip(),
        "confidence_score": float_opt(row.get("confidence_score")) or 75,
        "confidence_note": (row.get("confidence_note") or "").strip(),
    }


def normalize_strategic_location(row: dict[str, Any]) -> dict[str, Any]:
    start_year = int_opt(row.get("start_year"))
    end_year = int_opt(row.get("end_year"))
    importance_level = int_opt(row.get("importance_level")) or 3
    display_priority = int_opt(row.get("display_priority")) or 500
    active_year_ranges: list[dict[str, int]] = []
    if start_year is not None and end_year is not None:
        active_year_ranges.append({"start_year": start_year, "end_year": end_year})
    return {
        "location_id": (row.get("location_id") or "").strip(),
        "name": (row.get("name") or "").strip(),
        "aliases": pipe_list(row.get("aliases")),
        "category": (row.get("category") or "").strip(),
        "icon_key": (row.get("icon_key") or "place").strip(),
        "importance_level": importance_level,
        "display_priority": display_priority,
        "start_year": start_year,
        "end_year": end_year,
        "active_years_raw": (row.get("active_years_raw") or "").strip(),
        "active_years": [],
        "active_year_ranges": active_year_ranges,
        "related_event_ids": pipe_list(row.get("related_event_ids")),
        "related_anecdote_ids": pipe_list(row.get("related_anecdote_ids")),
        "related_polity_ids": pipe_list(row.get("related_polity_ids")),
        "related_people": pipe_list(row.get("related_people")),
        "historical_name": (row.get("historical_name") or "").strip(),
        "modern_name": (row.get("modern_name") or "").strip(),
        "modern_admin_units_raw": (row.get("modern_admin_units_raw") or "").strip(),
        "longitude": float_opt(row.get("longitude")),
        "latitude": float_opt(row.get("latitude")),
        "location_precision": (row.get("location_precision") or "approximate").strip(),
        "location_confidence_score": float_opt(row.get("location_confidence_score")) or 0,
        "strategic_summary": (row.get("strategic_summary") or "").strip(),
        "historical_significance": (row.get("historical_significance") or "").strip(),
        "source_titles": pipe_list(row.get("source_titles")),
        "source_urls": pipe_list(row.get("source_urls")),
        "source_type": (row.get("source_type") or "").strip(),
        "confidence_note": (row.get("confidence_note") or "").strip(),
        "review_status": (row.get("review_status") or "").strip(),
        "review_note": (row.get("review_note") or "").strip(),
        "default_visible": (row.get("review_status") or "").strip() == "verified" and importance_level <= 2,
        "is_high_importance": importance_level <= 2,
    }


def build_alias_index(polities: list[dict[str, Any]], rulers: list[dict[str, Any]],
                      capitals: list[dict[str, Any]], strategic_locations: list[dict[str, Any]]) -> dict[str, Any]:
    """Frontend search index for polities, rulers, capitals, and strategic locations."""
    entries: list[dict[str, Any]] = []

    def add_entry(alias: str, entity_type: str, entity_id: str, **extra: Any) -> None:
        alias = (alias or "").strip()
        if not alias:
            return
        entries.append(
            {
                "alias": alias,
                "normalized": normalize_search_text(alias),
                "label": extra.pop("label", alias),
                "entity_type": entity_type,
                "entity_id": entity_id or alias,
                **extra,
            }
        )

    polity_name_by_id = {
        (p.get("polity_id") or "").strip(): (p.get("polity_display_name") or p.get("polity_name") or "").strip()
        for p in polities
        if (p.get("polity_id") or "").strip()
    }

    for p in polities:
        polity_id = (p.get("polity_id") or "").strip()
        if not polity_id:
            continue
        primary = (p.get("polity_display_name") or p.get("polity_name") or "").strip()
        aliases = unique_list(([primary] if primary else []) + pipe_list(p.get("polity_aliases")))
        start = int_opt(p.get("polity_start_year"))
        end = int_opt(p.get("polity_end_year"))
        for alias in aliases:
            add_entry(
                alias,
                "polity",
                polity_id,
                polity_id=polity_id,
                polity_display_name=primary,
                label=primary or alias,
                start_year=start,
                end_year=end,
            )
    for r in rulers:
        ruler_id = (r.get("ruler_id") or "").strip()
        polity_id = (r.get("polity_id") or "").strip()
        names = []
        for field in ("ruler_name", "ruler_personal_name", "ruler_temple_name", "ruler_posthumous_name", "ruler_era_name", "ruler_display_name"):
            val = (r.get(field) or "").strip()
            if val and val not in names:
                names.append(val)
        start = int_opt(r.get("ruler_reign_start_year") or r.get("reign_start_year"))
        end = int_opt(r.get("ruler_reign_end_year") or r.get("reign_end_year"))
        polity_name = polity_name_by_id.get(polity_id, "")
        for alias in names:
            add_entry(
                alias,
                "ruler",
                ruler_id or alias,
                polity_id=polity_id or None,
                polity_display_name=polity_name or None,
                label=f"{alias} · {polity_name}" if polity_name else alias,
                start_year=start,
                end_year=end,
            )
    for cap in capitals:
        for field in ("capital_name_historical", "capital_name_modern"):
            val = (cap.get(field) or "").strip()
            if not val:
                continue
            add_entry(
                val,
                "capital",
                cap.get("capital_event_id") or val,
                polity_id=cap.get("polity_id"),
                polity_display_name=cap.get("polity_name"),
                longitude=cap.get("longitude"),
                latitude=cap.get("latitude"),
                start_year=cap.get("valid_from_year"),
                end_year=cap.get("valid_to_year"),
            )
    for loc in strategic_locations:
        name = (loc.get("name") or "").strip()
        if not name:
            continue
        for alias in unique_list([name] + list(loc.get("aliases") or [])):
            add_entry(
                alias,
                "strategic_location",
                loc.get("location_id") or alias,
                strategic_location_id=loc.get("location_id"),
                longitude=loc.get("longitude"),
                latitude=loc.get("latitude"),
                label=name,
                start_year=loc.get("start_year"),
                end_year=loc.get("end_year"),
            )
    return {"data_version": DATA_VERSION, "entries": entries}


def empty_feature_collection() -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": []}


# ---------- Territory build ----------
#
# 输入：input/vIndian/admin_boundaries/india_adm1_normalized.geojson（36 邦/UT 几何，admin_id=IN-XX）。
# 输入：input/vIndian/territory_overrides_vIndian.csv 的 admin_ids 列（pipe-sep IN-XX）。
# 输出：public/data/vIndian/territories/approx_polities.geojson —— 每个政权对应一个 MultiPolygon，
#       几何为它命中的 ADM1 几何的并集（这里采用最简单的"全部追加为 MultiPolygon"，跨邦边界
#       不做真实 union 化简，前端 fill 层会自然合并视觉）。
# 输出：public/data/vIndian/territories/polity_county_index.json —— polity_id → admin_ids 索引。
# 输出：public/data/vIndian/territories/county_units.geojson —— ADM1 features 复用为"county_units"
#       命名空间，方便前端复用 v03 的图层加载逻辑（虽然印度粒度是邦不是县）。


def geometry_to_multipolygon_coords(geometry: dict[str, Any]) -> list[Any]:
    gtype = geometry.get("type")
    if gtype == "Polygon":
        return [geometry.get("coordinates", [])]
    if gtype == "MultiPolygon":
        return list(geometry.get("coordinates", []))
    return []


def union_multipolygon(geometries: list[dict[str, Any]]) -> dict[str, Any]:
    """简化版 union：把每个 ADM1 的 polygon/multipolygon 都追加到一个 MultiPolygon 中。
    不做真实几何 union（避免依赖 shapely/turf）；视觉上 fill 层会自然合并相邻 polygon。"""
    coords: list[Any] = []
    for g in geometries:
        coords.extend(geometry_to_multipolygon_coords(g))
    return {"type": "MultiPolygon", "coordinates": coords}


def load_admin_boundaries() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """加载 ADM1 normalized geojson；返回 (admin_by_id, ordered_features)。"""
    path = ADMIN_BOUNDARY_DIR / "india_adm1_normalized.geojson"
    if not path.exists():
        print(f"  warn: {path} not found; territory output will be empty stubs.")
        return {}, []
    data = read_json(path) or {}
    features = data.get("features") or []
    by_id = {f["properties"]["admin_id"]: f for f in features if f.get("properties", {}).get("admin_id")}
    return by_id, features


def load_neighbor_polygons() -> dict[str, dict[str, Any]]:
    """加载邻国 ADM0 geojson；返回 {ISO3 → feature}。键示例 'PAK', 'BGD', 'NPL', 'AFG', 'BTN', 'LKA', 'MMR', 'CHN', 'IRN'。
    territory_overrides_vIndian.csv 的 admin_ids 列中可直接用 3 字母 ISO 表示跨境疆域：
        admin_ids = "IN-UP|IN-BR|PAK|BGD|AFG" → 印度+巴+孟+阿 union 几何。
    """
    path = ADMIN_BOUNDARY_DIR / "neighbor_adm0.geojson"
    if not path.exists():
        return {}
    data = read_json(path) or {}
    out: dict[str, dict[str, Any]] = {}
    for f in data.get("features", []):
        iso = (f.get("properties", {}).get("iso_a3") or "").upper()
        if iso and len(iso) == 3:
            out[iso] = f
    return out


COUNTRY_TOKEN_TO_ISO = {
    "pk": "PAK",
    "pak": "PAK",
    "pakistan": "PAK",
    "bd": "BGD",
    "bgd": "BGD",
    "bangladesh": "BGD",
    "afg": "AFG",
    "afghanistan": "AFG",
    "npl": "NPL",
    "nepal": "NPL",
    "btn": "BTN",
    "bhutan": "BTN",
    "lk": "LKA",
    "lka": "LKA",
    "srilanka": "LKA",
    "ceylon": "LKA",
    "mmr": "MMR",
    "myanmar": "MMR",
    "burma": "MMR",
    "chn": "CHN",
    "china": "CHN",
    "irn": "IRN",
    "iran": "IRN",
}

ADMIN_TOKEN_ALIASES = {
    # The 2020 merged union territory is IN-DH in the normalized geojson.
    "IN-DD": "IN-DH",
    "IN-DN": "IN-DH",
}

NORTHWESTERN_INDIA_IDS = ["IN-PB", "IN-HR", "IN-RJ", "IN-GJ", "IN-JK", "IN-LA"]


def build_admin_alias_index(admin_by_id: dict[str, dict[str, Any]]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for admin_id, feature in admin_by_id.items():
        props = feature.get("properties", {})
        names = [admin_id, props.get("name"), props.get("source_shape_name")]
        names.extend(pipe_list(props.get("aliases")))
        for name in names:
            key = normalize_key(name)
            if key:
                aliases[key] = admin_id
    manual_aliases = {
        "jammuandkashmir": "IN-JK",
        "kashmir": "IN-JK",
        "ladakh": "IN-LA",
        "dadraandnagarhaveli": "IN-DH",
        "damananddiu": "IN-DH",
        "bengal": "IN-WB",
        "westbengal": "IN-WB",
        "orissa": "IN-OR",
        "odisha": "IN-OR",
        "uttarpradesh": "IN-UP",
        "madhyapradesh": "IN-MP",
        "andhrapradesh": "IN-AP",
        "tamilnadu": "IN-TN",
    }
    aliases.update({k: v for k, v in manual_aliases.items() if v in admin_by_id})
    return aliases


def clean_region_token(token: str) -> str:
    token = token.strip()
    token = re.sub(r"\bbefore\s+\d+\b", "", token, flags=re.IGNORECASE)
    token = re.sub(r"\bparts?\b", "", token, flags=re.IGNORECASE)
    token = re.sub(r"\bmodern\s+location\b", "", token, flags=re.IGNORECASE)
    token = re.sub(r"\brequires\s+item-level\s+review\b", "", token, flags=re.IGNORECASE)
    token = re.sub(r"\bhistorical\s+south\s+asia\b", "", token, flags=re.IGNORECASE)
    token = re.sub(r"\bmodern\s+country/adm1\b", "", token, flags=re.IGNORECASE)
    token = re.sub(r"\s+", " ", token)
    return token.strip(" ;,.")


def split_region_tokens(raw: str) -> list[str]:
    tokens: list[str] = []
    for token in pipe_list(raw):
        token = clean_region_token(token)
        if not token:
            continue
        if "disputed Himalayan region" in token or "disputed himalayan region" in token.lower():
            tokens.append(token)
            continue
        tokens.extend(clean_region_token(part) for part in re.split(r"/", token) if clean_region_token(part))
    return tokens


def resolve_region_token(
    token: str,
    admin_by_id: dict[str, dict[str, Any]],
    neighbor_by_iso: dict[str, dict[str, Any]],
    admin_alias_index: dict[str, str],
) -> list[str]:
    token = clean_region_token(token)
    if not token:
        return []
    if "disputed Himalayan region" in token or "disputed himalayan region" in token.lower():
        return [v for v in ["IN-JK", "IN-LA", "PAK", "CHN"] if v in admin_by_id or v in neighbor_by_iso]

    mapped_admin = ADMIN_TOKEN_ALIASES.get(token, token)
    if mapped_admin.startswith("IN-"):
        return [mapped_admin] if mapped_admin in admin_by_id else []

    upper_token = token.upper()
    if upper_token == "IND":
        return sorted(admin_by_id)
    if len(upper_token) == 3 and upper_token in neighbor_by_iso:
        return [upper_token]
    if upper_token in ("PK", "BD", "LK"):
        iso = COUNTRY_TOKEN_TO_ISO[upper_token.lower()]
        return [iso] if iso in neighbor_by_iso else []

    key = normalize_key(token)
    if key in ("india", "republicofindia", "dominionofindia"):
        return sorted(admin_by_id)
    if key == "northwesternindia":
        return [admin_id for admin_id in NORTHWESTERN_INDIA_IDS if admin_id in admin_by_id]

    if token.lower().startswith("india "):
        rest = token[6:].strip()
        if not rest:
            return sorted(admin_by_id)
        matched: list[str] = []
        for part in re.split(r"[,/]", rest):
            part_key = normalize_key(part)
            if part_key in admin_alias_index:
                matched.append(admin_alias_index[part_key])
        if matched:
            return unique_list(matched)

    for country_key, iso in COUNTRY_TOKEN_TO_ISO.items():
        if country_key in key and iso in neighbor_by_iso:
            return [iso]

    if key in admin_alias_index:
        return [admin_alias_index[key]]
    return []


def resolve_admin_ids(
    raw: str,
    admin_by_id: dict[str, dict[str, Any]],
    neighbor_by_iso: dict[str, dict[str, Any]],
    admin_alias_index: dict[str, str],
) -> list[str]:
    resolved: list[str] = []
    for token in split_region_tokens(raw):
        resolved.extend(resolve_region_token(token, admin_by_id, neighbor_by_iso, admin_alias_index))
    return unique_list(resolved)


def load_territory_overrides() -> dict[str, dict[str, Any]]:
    """polity_id → {admin_ids: list[str], valid_from_year, valid_to_year, confidence_score, ...}

    admin_ids 列接受：
    - 'IN-XX'：印度 ADM1 邦/UT 编码。
    - 'IN-ADM2-XXX'：印度 ADM2 区编码（目前 build_polity_territories 仍按 ADM1 命中，ADM2 后续启用）。
    - 3 字母大写 ISO：邻国 ADM0 编码（PAK / BGD / NPL / AFG / BTN / LKA / MMR / CHN / IRN）。
    - IND：展开为全部印度 ADM1，用于共和国/英属印度等大范围近似。
    """
    out: dict[str, dict[str, Any]] = {}
    for row in read_csv(INPUT_DIR / "territory_overrides_vIndian.csv"):
        polity_id = (row.get("polity_id") or "").strip()
        if not polity_id:
            continue
        admin_ids_raw = (row.get("admin_ids") or "").strip()
        out[polity_id] = {
            "admin_ids_raw": admin_ids_raw,
            "valid_from_year": int_opt(row.get("valid_from_year")),
            "valid_to_year": int_opt(row.get("valid_to_year")),
            "confidence_score": float_opt(row.get("confidence_score")),
            "match_source": (row.get("match_source") or "manual_override").strip(),
            "note": (row.get("note") or "").strip(),
            "source_titles": (row.get("source_titles") or "").strip(),
        }
    return out


def build_polity_territories(polities: list[dict[str, Any]], admin_by_id: dict[str, dict[str, Any]], neighbor_by_iso: dict[str, dict[str, Any]], overrides: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """返回 (approx_features, polity_county_index_entries)。
    admin_ids 可同时含：
    - IN-XX  → 印度 ADM1 几何
    - 3-letter ISO（PAK/BGD/NPL...）→ 邻国 ADM0 几何
    """
    features: list[dict[str, Any]] = []
    index_entries: dict[str, dict[str, Any]] = {}
    admin_alias_index = build_admin_alias_index(admin_by_id)
    matched = 0
    for polity in polities:
        polity_id = (polity.get("polity_id") or "").strip()
        if not polity_id:
            continue
        override = overrides.get(polity_id)
        source_raw = override["admin_ids_raw"] if override else (polity.get("modern_admin_units_raw") or "")
        admin_ids = resolve_admin_ids(source_raw, admin_by_id, neighbor_by_iso, admin_alias_index)
        # 命中的几何：ADM1 + 邻国 ADM0
        admin_geometries = []
        matched_admin_ids: list[str] = []
        for admin_id in admin_ids:
            if admin_id.startswith("IN-"):
                feature = admin_by_id.get(admin_id)
            elif len(admin_id) == 3 and admin_id.isupper():
                feature = neighbor_by_iso.get(admin_id)
            else:
                feature = None
            if feature is None:
                continue
            admin_geometries.append(feature["geometry"])
            matched_admin_ids.append(admin_id)

        index_entries[polity_id] = {
            "polity_id": polity_id,
            "county_ids": matched_admin_ids,
            "summary_admin_ids": matched_admin_ids,
            "county_count": len(matched_admin_ids),
            "matched_resolution": (
                "ADM1_ADM0"
                if any(not admin_id.startswith("IN-") for admin_id in matched_admin_ids) and any(admin_id.startswith("IN-") for admin_id in matched_admin_ids)
                else "ADM0"
                if matched_admin_ids and all(not admin_id.startswith("IN-") for admin_id in matched_admin_ids)
                else "ADM1"
                if matched_admin_ids
                else "missing"
            ),
            "match_source": override["match_source"] if override else "modern_admin_units_raw_fallback",
            "match_confidence": override["confidence_score"] if override else None,
            "note": override["note"] if override else "",
            "valid_from_year": override["valid_from_year"] if override else None,
            "valid_to_year": override["valid_to_year"] if override else None,
        }

        if not admin_geometries:
            # 未匹配上的政权不出 feature；前端 territory 层显示空。
            continue

        geometry = union_multipolygon(admin_geometries)
        # 简单算 bbox
        all_points: list[tuple[float, float]] = []
        for polygon in geometry["coordinates"]:
            for ring in polygon:
                for point in ring:
                    if isinstance(point, list) and len(point) >= 2:
                        all_points.append((point[0], point[1]))
        if all_points:
            lons = [p[0] for p in all_points]
            lats = [p[1] for p in all_points]
            bbox = [min(lons), min(lats), max(lons), max(lats)]
        else:
            bbox = [0, 0, 0, 0]

        polity_name = (polity.get("polity_display_name") or polity.get("polity_name") or polity_id).strip()
        polity_start = int_opt(polity.get("polity_start_year"))
        polity_end = int_opt(polity.get("polity_end_year"))
        macro_period = (polity.get("macro_period") or "").strip()
        dynasty_name = (polity.get("dynasty_name") or "").strip()
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "polity_id": polity_id,
                    "polity_name": polity_name,
                    "polity_display_name": polity_name,
                    "macro_period": macro_period,
                    "dynasty_name": dynasty_name,
                    "polity_start_year": polity_start,
                    "polity_end_year": polity_end,
                    "matched_admin_ids": matched_admin_ids,
                    "match_confidence": override["confidence_score"] if override else None,
                    "territory_status": "approximate",
                    "match_source": override["match_source"] if override else "modern_admin_units_raw_fallback",
                    "bbox": bbox,
                    "is_nomadic": False,
                    "is_steppe_origin": False,
                    "control_type": "direct",
                    "feature_id": polity_id,
                },
            }
        )
        matched += 1
    return features, index_entries


def adm1_features_to_county_units(adm1_features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """ADM1 feature 直接复用为 county_units，统一字段名以匹配前端 TypeScript 的 CountyUnitProperties。"""
    out: list[dict[str, Any]] = []
    for f in adm1_features:
        p = f.get("properties", {})
        out.append(
            {
                "type": "Feature",
                "geometry": f["geometry"],
                "properties": {
                    "admin_id": p["admin_id"],
                    "name": p.get("name", ""),
                    "aliases": p.get("aliases", ""),
                    "admin_level": p.get("admin_level", "state"),
                    "parent_admin_ids": [],
                    "source_shape_name": p.get("source_shape_name", ""),
                    "source_shape_id": p.get("source_shape_id", ""),
                    "bbox": p.get("bbox"),
                    "centroid": p.get("centroid"),
                    "coordinate_count": p.get("coordinate_count", 0),
                },
            }
        )
    return out


def main() -> None:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    manifest = read_json(INPUT_DIR / "dataset_manifest_vIndian.json") or {}
    year_min = int(manifest.get("year_min") or -3300)
    year_max = int(manifest.get("year_max") or 1990)

    polities = read_csv(INPUT_DIR / "indian_history_polities_master_vIndian.csv")
    rulers = read_csv(INPUT_DIR / "indian_history_rulers_master_vIndian.csv")
    yearly_rows = read_csv(INPUT_DIR / "indian_history_polities_yearly_vIndian.csv")
    issues = read_csv(INPUT_DIR / "indian_history_unresolved_or_disputed_vIndian.csv")
    validation = read_csv(INPUT_DIR / "indian_history_validation_report_vIndian.csv")
    capital_raw = read_csv(INPUT_DIR / "capital_events_vIndian.csv")
    events_raw = read_csv(INPUT_DIR / "historical_events_vIndian.csv")
    anecdotes_raw = read_csv(INPUT_DIR / "historical_anecdotes_vIndian.csv")
    myth_raw = read_csv(INPUT_DIR / "mythological_timeline_vIndian.csv")
    strategic_locations_raw = read_csv(INPUT_DIR / "strategic_locations_vIndian.csv")
    contexts_raw = read_csv(INPUT_DIR / "historical_contexts_vIndian.csv")
    story_presets_raw = read_json(INPUT_DIR / "story_presets_vIndian.json") or {"data_version": DATA_VERSION, "presets": []}

    events = [e for e in (normalize_event_row(r, "event") for r in events_raw) if e]
    anecdotes = [e for e in (normalize_event_row(r, "anecdote") for r in anecdotes_raw) if e]
    myths = [e for e in (normalize_myth_row(r) for r in myth_raw) if e]
    polity_name_by_id = {
        (p.get("polity_id") or "").strip(): (p.get("polity_display_name") or p.get("polity_name") or "").strip()
        for p in polities
        if (p.get("polity_id") or "").strip()
    }
    capitals_normalized = [
        normalize_capital_event(r, polity_name_by_id)
        for r in capital_raw
        if (r.get("polity_id") or "").strip()
    ]
    strategic_locations = [
        loc
        for loc in (normalize_strategic_location(r) for r in strategic_locations_raw if (r.get("location_id") or "").strip())
        if loc.get("review_status") == "verified" and loc.get("longitude") is not None and loc.get("latitude") is not None
    ]
    contexts = [c for c in (normalize_context_row(r) for r in contexts_raw) if c]

    # actual_min/max from data — drives metadata if manifest stale
    data_years: list[int] = []
    data_years.extend(int_opt(e.get("year")) for e in events)
    data_years.extend(int_opt(e.get("year")) for e in anecdotes)
    data_years.extend(int_opt(e.get("year")) for e in myths)
    data_years.extend(int_opt(r.get("year")) for r in yearly_rows)
    data_years = [y for y in data_years if y is not None]
    if data_years:
        year_min = min(year_min, min(data_years))
        year_max = max(year_max, max(data_years))

    # capitals.json: by_polity + all_events
    capitals_by_polity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cap in capitals_normalized:
        capitals_by_polity[cap["polity_id"]].append(cap)
    for pid, lst in capitals_by_polity.items():
        lst.sort(key=lambda c: (c.get("valid_from_year") or 0, c.get("capital_event_id") or ""))

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    YEARS_DIR.mkdir(parents=True, exist_ok=True)
    TERRITORIES_DIR.mkdir(parents=True, exist_ok=True)

    playable_years = [y for y in range(year_min, year_max + 1) if y != 0]

    # 先构 territories（metadata 的 territory_polity_count 需要这个）。下方 main 末尾会写文件。
    admin_by_id, adm1_features = load_admin_boundaries()
    neighbor_by_iso = load_neighbor_polygons()
    overrides = load_territory_overrides()
    polity_features, polity_index = build_polity_territories(polities, admin_by_id, neighbor_by_iso, overrides)
    territory_polity_count = len(polity_features)

    # metadata
    write_json(
        OUT_DIR / "metadata.json",
        {
            "data_version": DATA_VERSION,
            "generated_at": generated_at,
            "year_min": year_min,
            "year_max": year_max,
            "year_count": len(playable_years),
            "has_year_zero": False,
            "polity_count": len(polities),
            "ruler_count": len(rulers),
            "yearly_row_count": len(yearly_rows),
            "capital_event_count": len(capitals_normalized),
            "capital_polity_count": len(capitals_by_polity),
            "capital_migration_count": 0,
            "capital_migration_years": [],
            "territory_polity_count": territory_polity_count,
            "territory_missing_count": len(polities) - territory_polity_count,
            "territory_low_confidence_count": 0,
            "historical_event_count": len(events),
            "historical_anecdote_count": len(anecdotes) + len(myths),
            "strategic_location_count": len(strategic_locations),
            "admin_boundary_source": "geoBoundaries gbOpen/IND",
            "admin_boundary_license": "Open Data Commons Open Database License 1.0",
        },
    )

    # polities / rulers / issues / validation (passthroughs)
    write_json(OUT_DIR / "polities.json", {"data_version": DATA_VERSION, "polities": polities})
    write_json(OUT_DIR / "rulers.json", {"data_version": DATA_VERSION, "rulers": rulers})
    write_json(OUT_DIR / "issues.json", {"data_version": DATA_VERSION, "issues": issues})
    write_json(OUT_DIR / "validation.json", {"data_version": DATA_VERSION, "checks": validation})

    # events / anecdotes / mythology
    write_json(
        OUT_DIR / "events.json",
        {
            "data_version": DATA_VERSION,
            "generated_at": generated_at,
            "event_count": len(events),
            "covered_year_count": len({e["year"] for e in events}),
            "marker_count": len(events),
            "events": events,
        },
    )
    write_json(
        OUT_DIR / "anecdotes.json",
        {
            "data_version": DATA_VERSION,
            "generated_at": generated_at,
            "anecdote_count": len(anecdotes),
            "marker_count": len(anecdotes),
            "covered_year_count": len({e["year"] for e in anecdotes}),
            "by_dynasty": {},
            "anecdotes": anecdotes,
        },
    )
    write_json(
        OUT_DIR / "mythology.json",
        {
            "data_version": DATA_VERSION,
            "generated_at": generated_at,
            "anecdote_count": len(myths),
            "marker_count": len(myths),
            "covered_year_count": len({e["year"] for e in myths}),
            "anecdotes": myths,
        },
    )

    # contexts.json：从 historical_contexts_vIndian.csv 读
    context_years_set = set()
    for c in contexts:
        for y in range(int(c["start_year"]), int(c["end_year"]) + 1):
            if y == 0:
                continue
            context_years_set.add(y)
    write_json(
        OUT_DIR / "contexts.json",
        {
            "data_version": DATA_VERSION,
            "generated_at": generated_at,
            "context_count": len(contexts),
            "covered_year_count": len(context_years_set),
            "full_year_coverage": False,
            "context_years": sorted(context_years_set),
            "contexts": contexts,
        },
    )

    # capitals.json：字段名对齐前端 CapitalsData 类型（capital_events / capital_migrations / migrations_by_year）。
    # 旧 all_events / migrations 字段名是初版疏忽，Phase 8.2 多源合并按 capital_events 取，需匹配。
    write_json(
        OUT_DIR / "capitals.json",
        {
            "data_version": DATA_VERSION,
            "generated_at": generated_at,
            "by_polity": dict(capitals_by_polity),
            "capital_events": capitals_normalized,
            "capital_migrations": [],
            "migrations_by_year": {},
        },
    )

    # strategic locations + geojson stub
    write_json(
        OUT_DIR / "strategic_locations.json",
        {
            "data_version": DATA_VERSION,
            "generated_at": generated_at,
            "location_count": len(strategic_locations),
            "category_counts": dict(sorted({
                category: sum(1 for loc in strategic_locations if loc.get("category") == category)
                for category in {loc.get("category") for loc in strategic_locations}
            }.items())),
            "locations": strategic_locations,
        },
    )
    sl_geojson_features = []
    for loc in strategic_locations:
        if loc.get("longitude") is None or loc.get("latitude") is None:
            continue
        sl_geojson_features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [loc["longitude"], loc["latitude"]]},
                "properties": loc,
            }
        )
    write_json(
        OUT_DIR / "strategic_locations.geojson",
        {"type": "FeatureCollection", "features": sl_geojson_features},
    )

    # alias_index
    write_json(OUT_DIR / "alias_index.json", build_alias_index(polities, rulers, capitals_normalized, strategic_locations))

    # story presets：从 input/vIndian/story_presets_vIndian.json 读取，注入 dataset_id 与 generated_at/preset_count。
    presets_in = list(story_presets_raw.get("presets", []) or [])
    for p in presets_in:
        p["dataset_id"] = DATA_VERSION  # 强制覆盖防止人工 JSON 漏填
    write_json(
        OUT_DIR / "story_presets.json",
        {
            "data_version": DATA_VERSION,
            "generated_at": generated_at,
            "preset_count": len(presets_in),
            "comment": story_presets_raw.get("comment", ""),
            "presets": presets_in,
        },
    )

    # territories：从 ADM1 + 邻国 ADM0 + territory_overrides 拼；无 override 的核心政权按 modern_admin_units_raw 近似解析。
    matched_polities = len(polity_features)
    total_polities = len(polities)

    write_json(
        OUT_DIR / "territories/approx_polities.geojson",
        {"type": "FeatureCollection", "features": polity_features},
        compact=True,
    )
    # influence hatches 在 vIndian 阶段一不区分实控/羁縻，输出空集合。
    write_json(OUT_DIR / "territories/territory_influence_hatches.geojson", empty_feature_collection())
    # modern_admin_units = ADM1 features（用作"现代行政摘要"图层，对应 v03 的 modern_admin_units.geojson）。
    write_json(
        OUT_DIR / "territories/modern_admin_units.geojson",
        {"type": "FeatureCollection", "features": adm1_features},
        compact=True,
    )
    # county_units = ADM1 复用（vIndian 粒度只到邦级）。
    write_json(
        OUT_DIR / "territories/county_units.geojson",
        {"type": "FeatureCollection", "features": adm1_features_to_county_units(adm1_features)},
        compact=True,
    )
    write_json(
        OUT_DIR / "territories/polity_county_index.json",
        {
            "data_version": DATA_VERSION,
            "generated_at": generated_at,
            "source": "territory_overrides_vIndian.csv + india_adm1_normalized.geojson",
            "polities": polity_index,
        },
    )

    # years/{Y}.json — per-year payload (lightweight: events + anecdotes + mythology + polities listed in yearly)
    events_by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for e in events:
        events_by_year[e["year"]].append(e)
    anecdotes_by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for e in anecdotes:
        anecdotes_by_year[e["year"]].append(e)
    myths_by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for e in myths:
        myths_by_year[e["year"]].append(e)
    yearly_by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in yearly_rows:
        y = int_opt(r.get("year"))
        if y is None:
            continue
        yearly_by_year[y].append(r)

    for y in playable_years:
        polities_by_id: dict[str, dict[str, Any]] = {}
        for row in yearly_by_year.get(y, []):
            polity_id = (row.get("polity_id") or "").strip()
            if not polity_id:
                continue
            if polity_id not in polities_by_id:
                territory_entry = polity_index.get(polity_id, {})
                has_territory = bool(territory_entry.get("county_count"))
                active_caps = [
                    cap
                    for cap in capitals_by_polity.get(polity_id, [])
                    if (cap.get("valid_from_year") is None or cap["valid_from_year"] <= y)
                    and (cap.get("valid_to_year") is None or y <= cap["valid_to_year"])
                ]
                polities_by_id[polity_id] = {
                    "polity_id": polity_id,
                    "polity_name": row.get("polity_name") or row.get("polity_display_name") or "",
                    "polity_aliases": row.get("polity_aliases") or "",
                    "polity_display_name": row.get("polity_display_name") or row.get("polity_name") or "",
                    "polity_name_disambiguation": row.get("polity_name_disambiguation") or "",
                    "polity_name_review_status": row.get("polity_name_review_status") or "",
                    "polity_name_risk_flags": row.get("polity_name_risk_flags") or "",
                    "polity_type": row.get("polity_type") or "",
                    "macro_period": row.get("macro_period") or "",
                    "dynasty_name": row.get("dynasty_name") or "",
                    "polity_start_year": int_opt(row.get("polity_start_year")),
                    "polity_end_year": int_opt(row.get("polity_end_year")),
                    "modern_admin_units_raw": row.get("modern_admin_units_raw") or "",
                    "capital_historical_raw": row.get("capital_historical") or "",
                    "capital_modern_raw": row.get("capital_modern") or "",
                    "ruling_family_or_clan": row.get("ruling_family_or_clan") or "",
                    "ethnicity_or_group": row.get("ethnicity_or_group") or "",
                    "founder": row.get("founder") or "",
                    "last_ruler": row.get("last_ruler") or "",
                    "destroyed_by_or_successor": row.get("destroyed_by_or_successor") or "",
                    "polity_source_titles": row.get("polity_source_titles") or "",
                    "polity_source_urls": row.get("polity_source_urls") or "",
                    "polity_source_raw": row.get("polity_source_raw") or "",
                    "is_nomadic": False,
                    "is_steppe_origin": False,
                    "capitals": active_caps,
                    "active_capital_event_ids": [cap.get("capital_event_id") for cap in active_caps if cap.get("capital_event_id")],
                    "has_capital_migration_in_year": False,
                    "capital_quality": {
                        "status": "present" if active_caps else "missing",
                        "label": "present" if active_caps else "missing",
                        "has_dispute": False,
                        "lowest_confidence_score": min((cap.get("confidence_score") or 100 for cap in active_caps), default=None),
                        "location_precision": active_caps[0].get("location_precision") if active_caps else "",
                        "source_status": "present" if active_caps else "missing",
                    },
                    "territory": {
                        "geometry_ref": polity_id if has_territory else None,
                        "territory_status": "matched" if has_territory else "missing",
                        "territory_method": "modern_admin_approximation",
                        "approx_area_km2": None,
                        "match_confidence": (territory_entry.get("match_confidence") or 70) if has_territory else 0,
                    },
                    "rulers": [],
                    "confidence_score": float_opt(row.get("confidence_score")),
                    "quality": {
                        "confidence_score": float_opt(row.get("confidence_score")),
                        "has_dispute": "disputed" in (row.get("confidence_note") or "").lower(),
                        "has_unmatched_ruler": False,
                    },
                }
            if row.get("row_granularity") == "year_polity_unmatched_ruler":
                polities_by_id[polity_id]["quality"]["has_unmatched_ruler"] = True
            ruler_id = (row.get("ruler_id") or "").strip()
            if ruler_id and not any(r.get("ruler_id") == ruler_id for r in polities_by_id[polity_id]["rulers"]):
                polities_by_id[polity_id]["rulers"].append(
                    {
                        "ruler_id": ruler_id,
                        "ruler_name": row.get("ruler_name") or "",
                        "ruler_title": row.get("ruler_title") or "",
                        "ruler_temple_name": row.get("ruler_temple_name") or "",
                        "ruler_posthumous_name": row.get("ruler_posthumous_name") or "",
                        "ruler_personal_name": row.get("ruler_personal_name") or "",
                        "era_names": row.get("era_names") or "",
                        "ruler_reign_start_year": int_opt(row.get("ruler_reign_start_year")),
                        "ruler_reign_end_year": int_opt(row.get("ruler_reign_end_year")),
                        "ruler_source_title": row.get("ruler_source_title") or "",
                        "ruler_source_url": row.get("ruler_source_url") or "",
                        "ruler_confidence_score": float_opt(row.get("ruler_confidence_score")),
                    }
                )
        polities_in_year = list(polities_by_id.values())
        write_json(
            YEARS_DIR / f"{y}.json",
            {
                "year": y,
                "year_label": year_label(y),
                "polity_count": len(polities_in_year),
                "polities": polities_in_year,
                "capital_migrations": [],
                "historical_events": events_by_year.get(y, []),
                "historical_anecdotes": anecdotes_by_year.get(y, []) + myths_by_year.get(y, []),
                "historical_contexts": [],
            },
            compact=True,
        )

    print(
        f"[vIndian] wrote {len(events)} events, {len(anecdotes)} anecdotes, {len(myths)} myths, "
        f"{len(contexts)} contexts, {len(presets_in)} story presets, "
        f"{len(capitals_normalized)} capital events, {len(strategic_locations)} strategic locations, "
        f"{len(playable_years)} year files, {matched_polities}/{total_polities} polities with territory → {OUT_DIR}"
    )


if __name__ == "__main__":
    main()
