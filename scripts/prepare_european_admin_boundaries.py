#!/usr/bin/env python3
"""Prepare vEuropean modern administrative boundary sources.

Unlike v03 (single ISO `CHN`) and vIndian (single ISO `IND`), Europe has no
unified geoBoundaries ISO. This script loops over ~47 European country ISO3
codes, pulling each country's `gbOpen/{ISO3}/ADM0_simplified.geojson` from a
pinned geoBoundaries commit, normalizes each feature, and writes one
aggregated `eu_adm0_normalized.geojson`.

For historically-relevant federations (Germany, Italy, Spain, UK, Austria,
Switzerland, Poland, Belgium, Russia, Netherlands), this script additionally
fetches `ADM1_simplified.geojson` and writes per-country
`{iso3_lowercase}_adm1_normalized.geojson` files so that `territory_overrides`
can reference Bavaria, Lombardy, Scotland, etc. by stable admin_id codes.

Output sizes intentionally stay small via three inherited patterns from the
vIndian post-Phase-8 fix:
  1. Prefer `simplifiedGeometryGeoJSON` URLs over `gjDownloadURL`.
  2. Round normalized coordinates to 5 decimals (≈1.1 m precision).
  3. Write normalized geojsons as compact JSON (no `indent`).

Run:
    python3 scripts/prepare_european_admin_boundaries.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_DIR = ROOT / "input" / "vEuropean" / "admin_boundaries"
RAW_DIR = BOUNDARY_DIR / "raw"

ADM0_NORMALIZED_PATH = BOUNDARY_DIR / "eu_adm0_normalized.geojson"
MANIFEST_PATH = BOUNDARY_DIR / "admin_boundary_source_manifest.json"
ODBL_NOTICE_PATH = BOUNDARY_DIR / "ODbL-1.0-NOTICE.md"
ADMIN_ID_REFERENCE_PATH = BOUNDARY_DIR / "ADMIN_ID_REFERENCE.md"

# Pinned commit, identical to v03 / vIndian for reproducibility.
GEOBOUNDARIES_PINNED_COMMIT = "9469f09"

GEOBOUNDARIES_RAW_BASE = (
    f"https://github.com/wmgeolab/geoBoundaries/raw/{GEOBOUNDARIES_PINNED_COMMIT}/releaseData/gbOpen"
)

SCRIPT_VERSION = "2026-05-21-veuropean-multi-iso"


# ---------- Country list ----------
#
# ISO3 → (Chinese name, ISO2). Covers Europe + select transcontinental Russia.
# Micro-states (LIE, MCO, SMR, VAT, AND) are included but get ADM0 only.
# Transcontinental TUR is included; ADM0 polygon is the full country.

ADM0_COUNTRIES: dict[str, tuple[str, str]] = {
    "ALB": ("阿尔巴尼亚", "AL"),
    "AND": ("安道尔", "AD"),
    "AUT": ("奥地利", "AT"),
    "BEL": ("比利时", "BE"),
    "BGR": ("保加利亚", "BG"),
    "BIH": ("波斯尼亚和黑塞哥维那", "BA"),
    "BLR": ("白俄罗斯", "BY"),
    "CHE": ("瑞士", "CH"),
    "CYP": ("塞浦路斯", "CY"),
    "CZE": ("捷克", "CZ"),
    "DEU": ("德国", "DE"),
    "DNK": ("丹麦", "DK"),
    "ESP": ("西班牙", "ES"),
    "EST": ("爱沙尼亚", "EE"),
    "FIN": ("芬兰", "FI"),
    "FRA": ("法国", "FR"),
    "GBR": ("英国", "GB"),
    "GRC": ("希腊", "GR"),
    "HRV": ("克罗地亚", "HR"),
    "HUN": ("匈牙利", "HU"),
    "IRL": ("爱尔兰", "IE"),
    "ISL": ("冰岛", "IS"),
    "ITA": ("意大利", "IT"),
    "LIE": ("列支敦士登", "LI"),
    "LTU": ("立陶宛", "LT"),
    "LUX": ("卢森堡", "LU"),
    "LVA": ("拉脱维亚", "LV"),
    "MCO": ("摩纳哥", "MC"),
    "MDA": ("摩尔多瓦", "MD"),
    "MKD": ("北马其顿", "MK"),
    "MLT": ("马耳他", "MT"),
    "MNE": ("黑山", "ME"),
    "NLD": ("荷兰", "NL"),
    "NOR": ("挪威", "NO"),
    "POL": ("波兰", "PL"),
    "PRT": ("葡萄牙", "PT"),
    "ROU": ("罗马尼亚", "RO"),
    "RUS": ("俄罗斯", "RU"),
    "SMR": ("圣马力诺", "SM"),
    "SRB": ("塞尔维亚", "RS"),
    "SVK": ("斯洛伐克", "SK"),
    "SVN": ("斯洛文尼亚", "SI"),
    "SWE": ("瑞典", "SE"),
    "TUR": ("土耳其", "TR"),
    "UKR": ("乌克兰", "UA"),
    "VAT": ("梵蒂冈", "VA"),
    # Partially-recognized states, geoBoundaries availability uncertain — script
    # tolerates 404s and just lists them as missing in the manifest.
    "XKX": ("科索沃", "XK"),
}

# Federations that get ADM1 in addition to ADM0. Picked for historical depth
# (HRE-relevant Länder, Italian regioni, Spanish comunidades, UK constituent
# countries, Polish voivodeships, Russian federal subjects, etc.).
ADM1_FEDERATIONS: list[str] = [
    "AUT",
    "BEL",
    "CHE",
    "DEU",
    "ESP",
    "GBR",
    "ITA",
    "NLD",
    "POL",
    "RUS",
]


# ---------- IO helpers (mirroring prepare_indian_admin_boundaries.py) ----------


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


def download_if_missing(url: str, path: Path) -> bool:
    """Download `url` to `path` if path is missing or empty. Returns True on
    download, False on cache hit. Raises on 404 / network failures."""
    if path.exists() and path.stat().st_size > 0:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    print(f"  downloading {url}")
    try:
        with urllib.request.urlopen(url, timeout=180) as response:  # noqa: S310
            with tmp_path.open("wb") as handle:
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    handle.write(chunk)
        tmp_path.replace(path)
        return True
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


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


# 5-decimal rounding → ~1.1 m at equator. Inherited from prepare_indian post-fix.
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


def fold(name: str) -> str:
    """NFKD-fold a unicode name for case- and diacritic-insensitive lookup."""
    no_marks = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", no_marks).strip().lower()


def slug(name: str) -> str:
    """Alphanumeric slug for fallback admin_ids when no shapeISO exists."""
    folded = fold(name)
    return re.sub(r"[^a-z0-9]+", "", folded)


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = re.sub(r"\s+", " ", str(value).strip())
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


# ---------- ADM0 ----------


def adm0_url(iso3: str) -> str:
    return f"{GEOBOUNDARIES_RAW_BASE}/{iso3}/ADM0/geoBoundaries-{iso3}-ADM0_simplified.geojson"


def adm0_raw_path(iso3: str) -> Path:
    return RAW_DIR / f"{iso3.lower()}_adm0.geojson"


def normalize_adm0(iso3: str, name_zh: str, iso2: str) -> dict[str, Any] | None:
    """Download + normalize one country's ADM0. Returns the normalized feature,
    or None if the geoBoundaries source is unavailable for that ISO."""
    raw_path = adm0_raw_path(iso3)
    try:
        download_if_missing(adm0_url(iso3), raw_path)
    except Exception as error:  # noqa: BLE001
        print(f"  warn: {iso3} ADM0 download failed: {error}")
        return None
    try:
        raw = read_json(raw_path)
    except Exception as error:  # noqa: BLE001
        print(f"  warn: {iso3} ADM0 invalid JSON: {error}")
        return None
    feats = raw.get("features", [])
    if not feats:
        print(f"  warn: {iso3} ADM0 has no features")
        return None
    feature = feats[0]
    geometry = feature.get("geometry")
    if not geometry or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
        print(f"  warn: {iso3} ADM0 has unsupported geometry")
        return None
    geometry = round_geometry(geometry)
    bbox = round_bbox(geometry_bbox(geometry))
    props_in = feature.get("properties", {}) or {}
    shape_name = (props_in.get("shapeName") or "").strip()
    shape_id = (props_in.get("shapeID") or "").strip()
    aliases = unique([name_zh, shape_name, iso3, iso2])
    return {
        "type": "Feature",
        "properties": {
            "admin_id": iso3,
            "iso_a3": iso3,
            "iso_a2": iso2,
            "name": name_zh,
            "name_en": shape_name,
            "aliases": "|".join(aliases),
            "admin_level": "country",
            "source_shape_name": shape_name,
            "source_shape_id": shape_id,
            "source": "geoBoundaries",
            "source_release": "gbOpen",
            "source_layer": f"{iso3} ADM0 simplified",
            "source_url": "https://www.geoboundaries.org/",
            "source_license": "Open Data Commons Open Database License 1.0",
            "source_attribution": "geoBoundaries",
            "crs": "WGS84",
            "coordinate_count": coordinate_count(geometry),
            "bbox": bbox,
            "centroid": bbox_centroid(bbox),
        },
        "geometry": geometry,
    }


# ---------- ADM1 ----------


def adm1_url(iso3: str) -> str:
    return f"{GEOBOUNDARIES_RAW_BASE}/{iso3}/ADM1/geoBoundaries-{iso3}-ADM1_simplified.geojson"


def adm1_raw_path(iso3: str) -> Path:
    return RAW_DIR / f"{iso3.lower()}_adm1.geojson"


def adm1_normalized_path(iso3: str) -> Path:
    return BOUNDARY_DIR / f"{iso3.lower()}_adm1_normalized.geojson"


def adm1_admin_id(iso2: str, shape_iso: str, shape_name: str, used_ids: set[str]) -> str:
    """Prefer geoBoundaries `shapeISO` (typically `XX-YY` ISO 3166-2 form).
    Fall back to `{ISO2}-{slug-of-name}`. Disambiguate collisions by suffixing."""
    candidate = (shape_iso or "").strip().upper()
    if candidate and re.fullmatch(r"[A-Z]{2}-[A-Z0-9]{1,4}", candidate):
        base = candidate
    else:
        name_slug = slug(shape_name)[:8].upper() or "X"
        base = f"{iso2}-{name_slug}"
    final_id = base
    counter = 2
    while final_id in used_ids:
        final_id = f"{base}-{counter}"
        counter += 1
    return final_id


def normalize_adm1_for_country(iso3: str, name_zh: str, iso2: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Download + normalize ADM1 for one federation. Returns
    (features, stats). On download failure, returns ([], stats with error)."""
    raw_path = adm1_raw_path(iso3)
    stats: dict[str, Any] = {
        "iso3": iso3,
        "name_zh": name_zh,
        "feature_count": 0,
        "raw_sha256": "",
        "normalized_path": str(adm1_normalized_path(iso3).relative_to(ROOT)),
        "download_url": adm1_url(iso3),
        "error": None,
    }
    try:
        download_if_missing(adm1_url(iso3), raw_path)
    except Exception as error:  # noqa: BLE001
        stats["error"] = f"download failed: {error}"
        print(f"  warn: {iso3} ADM1 download failed: {error}")
        return [], stats
    try:
        raw = read_json(raw_path)
    except Exception as error:  # noqa: BLE001
        stats["error"] = f"invalid JSON: {error}"
        print(f"  warn: {iso3} ADM1 invalid JSON: {error}")
        return [], stats
    feats: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    for feature in raw.get("features", []):
        geometry = feature.get("geometry")
        if not geometry or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            continue
        geometry = round_geometry(geometry)
        bbox = round_bbox(geometry_bbox(geometry))
        props_in = feature.get("properties", {}) or {}
        shape_name = (props_in.get("shapeName") or "").strip()
        shape_iso = (props_in.get("shapeISO") or "").strip()
        shape_id = (props_in.get("shapeID") or "").strip()
        admin_id = adm1_admin_id(iso2, shape_iso, shape_name, used_ids)
        used_ids.add(admin_id)
        aliases = unique([shape_name, shape_iso, admin_id])
        feats.append(
            {
                "type": "Feature",
                "properties": {
                    "admin_id": admin_id,
                    "parent_iso_a3": iso3,
                    "parent_iso_a2": iso2,
                    "parent_name": name_zh,
                    "name": shape_name,
                    "aliases": "|".join(aliases),
                    "admin_level": "adm1",
                    "source_shape_name": shape_name,
                    "source_shape_iso": shape_iso,
                    "source_shape_id": shape_id,
                    "source": "geoBoundaries",
                    "source_release": "gbOpen",
                    "source_layer": f"{iso3} ADM1 simplified",
                    "source_license": "Open Data Commons Open Database License 1.0",
                    "source_attribution": "geoBoundaries",
                    "crs": "WGS84",
                    "coordinate_count": coordinate_count(geometry),
                    "bbox": bbox,
                    "centroid": bbox_centroid(bbox),
                },
                "geometry": geometry,
            }
        )
    feats.sort(key=lambda item: item["properties"]["admin_id"])
    stats["feature_count"] = len(feats)
    stats["raw_sha256"] = file_sha256(raw_path) if raw_path.exists() else ""
    return feats, stats


# ---------- Orchestration ----------


def write_odbl_notice(adm0_count: int, adm1_count: int) -> None:
    payload = f"""# ODbL 1.0 Notice for vEuropean Boundary Data

This project includes derived country-level (ADM0) and select first-level
administrative (ADM1) boundary data from geoBoundaries `gbOpen` for {adm0_count}
European countries and {adm1_count} federation-level ADM1 layers.

- Source: geoBoundaries (https://www.geoboundaries.org/)
- Pinned commit: {GEOBOUNDARIES_PINNED_COMMIT}
- License: Open Data Commons Open Database License 1.0
- License text: https://opendatacommons.org/licenses/odbl/1-0/
- Attribution: geoBoundaries

Derived files in this repository include:

- `input/vEuropean/admin_boundaries/eu_adm0_normalized.geojson`
- `input/vEuropean/admin_boundaries/{{iso3}}_adm1_normalized.geojson` (per federation)
- `input/vEuropean/admin_boundaries/raw/{{iso3}}_adm0.geojson` (cached downloads)
- `input/vEuropean/admin_boundaries/raw/{{iso3}}_adm1.geojson` (cached downloads)

The normalized data adds stable project IDs (ISO3 for ADM0, ISO 3166-2 codes
or fallback hashes for ADM1), Chinese display names, bbox/centroid metadata,
coordinate counts, and 5-decimal coordinate rounding. Boundaries are MODERN
administrative references, not historical exact territory boundaries. No
endorsement by geoBoundaries or its upstream sources is implied.
"""
    write_text(ODBL_NOTICE_PATH, payload)


def write_admin_id_reference(adm0_features: list[dict[str, Any]], adm1_features_by_country: dict[str, list[dict[str, Any]]]) -> None:
    lines: list[str] = ["# vEuropean Admin ID Reference", ""]
    lines.append("Stable admin_id codes for use in `territory_overrides_vEuropean.csv`.")
    lines.append("")
    lines.append("## ADM0 (国家)")
    lines.append("")
    lines.append("| admin_id | ISO2 | 中文名 | 英文名 |")
    lines.append("|---|---|---|---|")
    for feat in adm0_features:
        p = feat["properties"]
        lines.append(f"| {p['admin_id']} | {p['iso_a2']} | {p['name']} | {p['name_en']} |")
    for iso3, feats in sorted(adm1_features_by_country.items()):
        if not feats:
            continue
        name_zh, _iso2 = ADM0_COUNTRIES.get(iso3, ("", ""))
        lines.append("")
        lines.append(f"## ADM1: {iso3} ({name_zh})")
        lines.append("")
        lines.append("| admin_id | name | shapeISO |")
        lines.append("|---|---|---|")
        for feat in feats:
            p = feat["properties"]
            lines.append(f"| {p['admin_id']} | {p['name']} | {p.get('source_shape_iso', '')} |")
    write_text(ADMIN_ID_REFERENCE_PATH, "\n".join(lines) + "\n")


def main() -> int:
    BOUNDARY_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    adm0_features: list[dict[str, Any]] = []
    adm0_missing: list[str] = []
    print(f"== ADM0: {len(ADM0_COUNTRIES)} countries ==")
    for iso3, (name_zh, iso2) in sorted(ADM0_COUNTRIES.items()):
        feat = normalize_adm0(iso3, name_zh, iso2)
        if feat is None:
            adm0_missing.append(iso3)
            continue
        adm0_features.append(feat)
    adm0_features.sort(key=lambda item: item["properties"]["admin_id"])
    adm0_collection = {
        "type": "FeatureCollection",
        "name": "eu_adm0_normalized",
        "description": "Aggregated modern ADM0 (country) boundaries for European polities, plus select transcontinental neighbors (Russia, Turkey). Modern administrative references, not historical territory boundaries.",
        "properties": {
            "source": "geoBoundaries gbOpen aggregated",
            "source_release": "gbOpen",
            "pinned_commit": GEOBOUNDARIES_PINNED_COMMIT,
            "source_license": "Open Data Commons Open Database License 1.0",
            "source_attribution": "geoBoundaries",
            "crs": "WGS84",
            "feature_count": len(adm0_features),
        },
        "features": adm0_features,
    }
    write_json(ADM0_NORMALIZED_PATH, adm0_collection, compact=True)
    print(f"  wrote {len(adm0_features)} ADM0 features → {ADM0_NORMALIZED_PATH.relative_to(ROOT)}"
          f" ({ADM0_NORMALIZED_PATH.stat().st_size / 1024:.1f} KiB)")
    if adm0_missing:
        print(f"  missing ADM0: {adm0_missing}")

    adm1_features_by_country: dict[str, list[dict[str, Any]]] = {}
    adm1_stats: list[dict[str, Any]] = []
    print(f"\n== ADM1: {len(ADM1_FEDERATIONS)} federations ==")
    for iso3 in sorted(ADM1_FEDERATIONS):
        name_zh, iso2 = ADM0_COUNTRIES.get(iso3, (iso3, iso3[:2]))
        feats, stats = normalize_adm1_for_country(iso3, name_zh, iso2)
        adm1_features_by_country[iso3] = feats
        adm1_stats.append(stats)
        if not feats:
            continue
        collection = {
            "type": "FeatureCollection",
            "name": f"{iso3.lower()}_adm1_normalized",
            "description": f"Modern {iso3} ADM1 boundaries normalized for vEuropean territory approximation. Modern administrative references, not historical territory boundaries.",
            "properties": {
                "source": "geoBoundaries",
                "source_release": "gbOpen",
                "pinned_commit": GEOBOUNDARIES_PINNED_COMMIT,
                "source_layer": f"{iso3} ADM1 simplified",
                "source_license": "Open Data Commons Open Database License 1.0",
                "source_attribution": "geoBoundaries",
                "crs": "WGS84",
                "feature_count": len(feats),
            },
            "features": feats,
        }
        out_path = adm1_normalized_path(iso3)
        write_json(out_path, collection, compact=True)
        print(f"  wrote {iso3} ADM1: {len(feats)} features → {out_path.relative_to(ROOT)}"
              f" ({out_path.stat().st_size / 1024:.1f} KiB)")

    # Manifest
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    manifest = {
        "source": "geoBoundaries",
        "source_release": "gbOpen",
        "pinned_commit": GEOBOUNDARIES_PINNED_COMMIT,
        "source_url": "https://www.geoboundaries.org/",
        "source_license": "Open Data Commons Open Database License 1.0",
        "source_attribution": "geoBoundaries",
        "crs": "WGS84",
        "admin_id_scheme": (
            "ADM0 admin_id = ISO3 (e.g. FRA, DEU). "
            "ADM1 admin_id = ISO 3166-2 code if shapeISO present (e.g. DE-BY, IT-25), "
            "else `{ISO2}-{8-char alphanumeric slug of shapeName}` with collision suffix."
        ),
        "generated_at": generated_at,
        "build_date": generated_at,
        "cleaning_script_version": SCRIPT_VERSION,
        "cleaning_script_path": str(Path(__file__).relative_to(ROOT)),
        "cleaning_script_sha256": file_sha256(Path(__file__)),
        "adm0": {
            "normalized_path": str(ADM0_NORMALIZED_PATH.relative_to(ROOT)),
            "normalized_sha256": file_sha256(ADM0_NORMALIZED_PATH) if ADM0_NORMALIZED_PATH.exists() else "",
            "feature_count": len(adm0_features),
            "requested_countries": sorted(ADM0_COUNTRIES),
            "missing_countries": adm0_missing,
        },
        "adm1": {
            "federations": ADM1_FEDERATIONS,
            "per_federation": adm1_stats,
        },
        "geometry_quality": {
            "coord_precision_decimals": COORD_PRECISION,
            "min_coordinate_count": min((feat["properties"]["coordinate_count"] for feat in adm0_features), default=0),
            "max_coordinate_count": max((feat["properties"]["coordinate_count"] for feat in adm0_features), default=0),
        },
        "license_notice_path": str(ODBL_NOTICE_PATH.relative_to(ROOT)),
        "admin_id_reference_path": str(ADMIN_ID_REFERENCE_PATH.relative_to(ROOT)),
    }
    write_json(MANIFEST_PATH, manifest)
    write_odbl_notice(adm0_count=len(adm0_features), adm1_count=sum(1 for stats in adm1_stats if stats["feature_count"]))
    write_admin_id_reference(adm0_features, adm1_features_by_country)
    print(f"\nManifest → {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"Admin ID reference → {ADMIN_ID_REFERENCE_PATH.relative_to(ROOT)}")
    print(f"ODbL notice → {ODBL_NOTICE_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
