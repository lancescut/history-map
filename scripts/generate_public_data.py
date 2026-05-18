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
YEAR_MAX = 1949

CAPITAL_EVENT_TYPES = {
    "initial_capital",
    "relocation",
    "co_capital",
    "temporary_capital",
    "disputed",
}

LOCATION_PRECISIONS = {"exact", "city", "region", "approximate", "unknown"}

# 游牧政权识别：基于族属/家族字段，避免硬编码 polity_name。
# 命中即标记 is_nomadic=true（MRD §6.3 POLITY-002：游牧政权使用虚线 + 羽化）
NOMADIC_ETHNIC_KEYWORDS = (
    "匈奴", "鲜卑", "羯", "氐", "羌",
    "柔然", "突厥", "回鹘", "丁零", "高车", "敕勒",
    "室韦", "乌孙", "月氏", "乌桓",
    "吐谷浑", "铁勒", "薛延陀",
)
# 已大幅定居的游牧出身王朝：保持 is_nomadic=false，但以 is_steppe_origin=true 单列
STEPPE_ORIGIN_BUT_SETTLED_POLITY_IDS = {
    # 这些由 master 表中 macro_period 已经记入"宋辽金夏""元明清"，建有稳定都城
    # 辽朝、金朝、西夏、元朝、北元、后金、清朝、西辽
}
STEPPE_ORIGIN_ETHNICITY_KEYWORDS = ("契丹", "女真", "蒙古", "满洲", "满族", "党项")


def classify_polity_steppe(polity_row: dict[str, str]) -> tuple[bool, bool]:
    """Return (is_nomadic, is_steppe_origin).

    - is_nomadic=True 表示该政权缺乏稳定定居核心，应在地图上以虚线+羽化呈现。
    - is_steppe_origin=True 表示游牧出身但已大幅定居（辽/金/夏/元/清），仍用实线，但供 UI 标注。
    """
    eth = polity_row.get("ethnicity_or_group", "") or ""
    clan = polity_row.get("ruling_family_or_clan", "") or ""
    polity_type = polity_row.get("polity_type", "") or ""
    macro = polity_row.get("macro_period", "") or ""
    haystack = f"{eth} {clan} {polity_type}"

    is_steppe_origin = any(k in haystack for k in STEPPE_ORIGIN_ETHNICITY_KEYWORDS)
    is_nomadic = any(k in haystack for k in NOMADIC_ETHNIC_KEYWORDS)

    # 已定居王朝排除（即使 ethnicity 命中纯游牧关键词也不算）
    polity_id = polity_row.get("polity_id") or ""
    if polity_id in STEPPE_ORIGIN_BUT_SETTLED_POLITY_IDS:
        is_nomadic = False
        is_steppe_origin = True

    # macro_period=元明清/宋辽金夏 中的契丹/女真/蒙古/满洲出身政权 → 视为已定居
    if macro in ("元明清", "宋辽金夏") and is_steppe_origin:
        is_nomadic = False

    # polity_type 含"游牧"显式标注
    if "游牧" in polity_type:
        is_nomadic = True

    return is_nomadic, is_steppe_origin


TERRITORY_LABEL = "现代县级行政边界索引，聚合面为现代行政边界近似，非历史精确边界"
ADMIN_SUMMARY_BOUNDARY_PATH = ADMIN_BOUNDARY_DIR / "china_adm1_normalized.geojson"
ADMIN_COUNTY_BOUNDARY_PATH = ADMIN_BOUNDARY_DIR / "china_adm3_normalized.geojson"
ADMIN_BOUNDARY_PATH = ADMIN_COUNTY_BOUNDARY_PATH
ADMIN_BOUNDARY_MANIFEST_PATH = ADMIN_BOUNDARY_DIR / "admin_boundary_source_manifest.json"
NEIGHBOR_ADM0_PATH = ADMIN_BOUNDARY_DIR / "neighbor_adm0.geojson"
NEIGHBOR_ADM1_PATH = ADMIN_BOUNDARY_DIR / "neighbor_adm1.geojson"

# 跨境关键字 → (level, target_ids)
# level="adm1": ADM1 ID 列表（精细，优先）；level="adm0": ADM0 ISO-A3 列表（fallback，整国）
NEIGHBOR_KEYWORD_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    # 俄罗斯 ADM1 精细化（释放 release_note batch19a 中的"已收敛"表述）
    ("外满洲", "adm1", ("RU-KHABAROVSK", "RU-PRIMORSKY", "RU-AMUR", "RU-JEWISH")),
    ("外兴安岭", "adm1", ("RU-AMUR", "RU-KHABAROVSK")),
    ("库页岛", "adm1", ("RU-SAKHALIN",)),
    ("萨哈林", "adm1", ("RU-SAKHALIN",)),
    ("唐努乌梁海", "adm1", ("RU-TUVA",)),
    ("图瓦", "adm1", ("RU-TUVA",)),
    ("贝加尔", "adm1", ("RU-BURYATIA", "RU-IRKUTSK", "RU-ZABAYKAL")),
    ("滨海边疆", "adm1", ("RU-PRIMORSKY",)),
    ("阿穆尔", "adm1", ("RU-AMUR",)),
    (
        "远东",
        "adm1",
        ("RU-KHABAROVSK", "RU-PRIMORSKY", "RU-AMUR", "RU-JEWISH", "RU-SAKHALIN", "RU-MAGADAN"),
    ),
    (
        "西伯利亚",
        "adm1",
        (
            "RU-TOMSK", "RU-NOVOSIBIRSK", "RU-OMSK", "RU-KEMEROVO", "RU-ALTAI-REP",
            "RU-KHAKASSIA", "RU-IRKUTSK", "RU-BURYATIA", "RU-ZABAYKAL", "RU-KRASNOYARSK",
            "RU-TUVA",
        ),
    ),
    # 邻国 ADM0 fallback
    ("蒙古国", "adm0", ("MNG",)),
    ("外蒙古", "adm0", ("MNG",)),
    ("外蒙", "adm0", ("MNG",)),
    ("俄罗斯", "adm0", ("RUS",)),
    ("哈萨克斯坦", "adm0", ("KAZ",)),
    ("哈萨克", "adm0", ("KAZ",)),
    ("巴尔喀什", "adm0", ("KAZ",)),
    ("吉尔吉斯", "adm0", ("KGZ",)),
    ("塔吉克", "adm0", ("TJK",)),
    ("乌兹别克", "adm0", ("UZB",)),
    ("土库曼", "adm0", ("TKM",)),
    ("阿富汗", "adm0", ("AFG",)),
    ("帕米尔", "adm0", ("TJK", "AFG")),
    ("巴基斯坦", "adm0", ("PAK",)),
    ("印度", "adm0", ("IND",)),
    ("尼泊尔", "adm0", ("NPL",)),
    ("不丹", "adm0", ("BTN",)),
    ("孟加拉", "adm0", ("BGD",)),
    ("缅甸", "adm0", ("MMR",)),
    ("老挝", "adm0", ("LAO",)),
    ("越南", "adm0", ("VNM",)),
    ("交趾", "adm0", ("VNM",)),
    ("安南", "adm0", ("VNM",)),
    ("象郡", "adm0", ("VNM",)),
    ("泰国", "adm0", ("THA",)),
    ("柬埔寨", "adm0", ("KHM",)),
    ("朝鲜半岛", "adm0", ("PRK", "KOR")),
    ("朝鲜", "adm0", ("PRK",)),
    ("汉四郡", "adm0", ("PRK",)),
    ("韩国", "adm0", ("KOR",)),
    ("日本", "adm0", ("JPN",)),
    ("台湾", "adm0", ("TWN",)),
]

# ADM1 ID → ISO 映射，用于"若已有 ADM1 命中同 ISO 则跳过 ADM0"
ADM1_ID_TO_ISO = {
    **{f"RU-{suffix}": "RUS" for suffix in [
        "PRIMORSKY", "KHABAROVSK", "AMUR", "JEWISH", "SAKHALIN", "TUVA", "BURYATIA",
        "IRKUTSK", "ZABAYKAL", "SAKHA", "CHUKOT", "MAGADAN", "KAMCHATKA", "ALTAI-REP",
        "KEMEROVO", "TOMSK", "NOVOSIBIRSK", "OMSK", "KRASNOYARSK", "KHAKASSIA",
    ]},
    **{f"KZ-{suffix}": "KAZ" for suffix in ["ALMATY", "EAST", "ZHAMBYL", "KYZYLORDA", "SOUTH", "KARAGANDA"]},
    **{f"KG-{suffix}": "KGZ" for suffix in ["NARYN", "ISSYK", "OSH"]},
    **{f"VN-{suffix}": "VNM" for suffix in ["LANGSON", "HAGIANG", "CAOBANG", "LAICHAU", "DIENBIEN"]},
    **{f"MM-{suffix}": "MMR" for suffix in ["KACHIN", "SHAN"]},
}

NEIGHBOR_ISO_NAMES = {
    "MNG": "蒙古国",
    "RUS": "俄罗斯",
    "KAZ": "哈萨克斯坦",
    "KGZ": "吉尔吉斯斯坦",
    "TJK": "塔吉克斯坦",
    "UZB": "乌兹别克斯坦",
    "TKM": "土库曼斯坦",
    "AFG": "阿富汗",
    "PAK": "巴基斯坦",
    "IND": "印度",
    "NPL": "尼泊尔",
    "BTN": "不丹",
    "BGD": "孟加拉国",
    "MMR": "缅甸",
    "LAO": "老挝",
    "VNM": "越南",
    "THA": "泰国",
    "KHM": "柬埔寨",
    "PRK": "朝鲜",
    "KOR": "韩国",
    "JPN": "日本",
    "TWN": "台湾",
}

DOMESTIC_ADMIN_ID_TO_NEIGHBOR_ISO = {
    "CN-TW": "TWN",
}

# 宽泛中国区域词 → 现代省级近似。仅作为 modern_admin_units_raw 中
# “中国南部 / 中原 / 长江中下游”等非行政区文本的兜底索引，仍标低置信度。
DOMESTIC_REGION_RULES: list[tuple[str, tuple[str, ...]]] = [
    (
        "中国南部及东南部",
        ("CN-JS", "CN-SH", "CN-ZJ", "CN-AH", "CN-JX", "CN-FJ", "CN-HB", "CN-HN", "CN-GD", "CN-GX", "CN-SC", "CN-CQ"),
    ),
    (
        "中国南部及西南部",
        ("CN-JS", "CN-SH", "CN-ZJ", "CN-AH", "CN-JX", "CN-FJ", "CN-HB", "CN-HN", "CN-GD", "CN-GX", "CN-SC", "CN-CQ", "CN-GZ", "CN-YN"),
    ),
    (
        "中国北方及中原",
        ("CN-BJ", "CN-TJ", "CN-HE", "CN-SX", "CN-NM", "CN-LN", "CN-SN", "CN-GS", "CN-NX", "CN-HA", "CN-SD", "CN-AH", "CN-JS", "CN-HB", "CN-HN"),
    ),
    (
        "黄河以北至辽东",
        ("CN-BJ", "CN-TJ", "CN-HE", "CN-SX", "CN-LN", "CN-HA", "CN-SD"),
    ),
    (
        "黄河以北及长江以北",
        ("CN-BJ", "CN-TJ", "CN-HE", "CN-SX", "CN-LN", "CN-HA", "CN-SD", "CN-AH", "CN-JS", "CN-HB"),
    ),
    (
        "中国西北及中原",
        ("CN-SN", "CN-GS", "CN-NX", "CN-QH", "CN-HA", "CN-SX", "CN-HB", "CN-HN", "CN-SC", "CN-CQ"),
    ),
    (
        "中国西北",
        ("CN-SN", "CN-GS", "CN-NX", "CN-QH", "CN-XJ"),
    ),
    (
        "长江中下游地区",
        ("CN-JS", "CN-SH", "CN-ZJ", "CN-AH", "CN-JX", "CN-HB", "CN-HN"),
    ),
    (
        "辽东塞外",
        ("CN-LN", "CN-JL", "CN-NM"),
    ),
    (
        "中国中原地区及江淮地区",
        ("CN-HA", "CN-SD", "CN-SX", "CN-HE", "CN-SN", "CN-AH", "CN-JS", "CN-HB"),
    ),
    (
        "中国中原地区",
        ("CN-HA", "CN-SD", "CN-SX", "CN-HE", "CN-SN", "CN-AH", "CN-JS", "CN-HB"),
    ),
    (
        "江淮地区",
        ("CN-JS", "CN-AH"),
    ),
]


def load_neighbor_polygons() -> dict[str, dict]:
    if not NEIGHBOR_ADM0_PATH.exists():
        return {}
    payload = json.loads(NEIGHBOR_ADM0_PATH.read_text(encoding="utf-8"))
    result: dict[str, dict] = {}
    for feature in payload.get("features", []):
        iso = feature.get("properties", {}).get("iso_a3")
        if isinstance(iso, str):
            result[iso.upper()] = feature
    return result


def load_neighbor_adm1_polygons() -> dict[str, dict]:
    if not NEIGHBOR_ADM1_PATH.exists():
        return {}
    payload = json.loads(NEIGHBOR_ADM1_PATH.read_text(encoding="utf-8"))
    result: dict[str, dict] = {}
    for feature in payload.get("features", []):
        admin_id = feature.get("properties", {}).get("admin_id")
        if isinstance(admin_id, str):
            result[admin_id] = feature
    return result


def match_neighbor_targets(raw_text: str) -> tuple[list[str], list[str], list[str]]:
    """Return (adm1_ids, adm0_isos, country_names) hit by raw_text.

    ADM1 命中优先：若某 ISO 已经在 ADM1 命中，则跳过同 ISO 的 ADM0（避免整国吞并）。
    """
    if not raw_text:
        return [], [], []
    seen_adm1: set[str] = set()
    ordered_adm1: list[str] = []
    seen_adm0: set[str] = set()
    ordered_adm0: list[str] = []
    for keyword, level, targets in NEIGHBOR_KEYWORD_RULES:
        if keyword not in raw_text:
            continue
        if level == "adm1":
            for adm1_id in targets:
                if adm1_id in seen_adm1:
                    continue
                seen_adm1.add(adm1_id)
                ordered_adm1.append(adm1_id)
        else:  # adm0
            for iso in targets:
                if iso in seen_adm0:
                    continue
                seen_adm0.add(iso)
                ordered_adm0.append(iso)
    # 移除已有 ADM1 覆盖的 ADM0
    skipped_isos = {ADM1_ID_TO_ISO[adm1_id] for adm1_id in ordered_adm1 if adm1_id in ADM1_ID_TO_ISO}
    ordered_adm0 = [iso for iso in ordered_adm0 if iso not in skipped_isos]
    names: list[str] = [NEIGHBOR_ISO_NAMES.get(iso, iso) for iso in ordered_adm0]
    return ordered_adm1, ordered_adm0, names


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
        "區": "区",
    }
)


def clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\ufeff", "").strip())


def polity_display_name(row: dict[str, Any]) -> str:
    return clean(row.get("polity_display_name")) or clean(row.get("polity_name"))


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


def pipe_list(value: Any) -> list[str]:
    return [item.strip() for item in clean(value).split("|") if item.strip()]


def int_event_optional(value: Any) -> int | None:
    value = clean(value)
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def float_event_optional(value: Any) -> float | None:
    value = clean(value)
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


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
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
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


def normalize_parent_ids(value: Any) -> list[str]:
    if isinstance(value, list):
        return [clean(item) for item in value if clean(item)]
    return split_list(clean(value))


def load_admin_boundaries() -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, list[str]],
]:
    summary_payload = read_json(ADMIN_SUMMARY_BOUNDARY_PATH)
    county_payload = read_json(ADMIN_COUNTY_BOUNDARY_PATH)
    summary_features = summary_payload["features"]
    county_features = county_payload["features"]
    summary_by_id = {feature["properties"]["admin_id"]: feature for feature in summary_features}
    county_by_id = {feature["properties"]["admin_id"]: feature for feature in county_features}
    county_ids_by_parent: dict[str, list[str]] = defaultdict(list)
    for feature in county_features:
        county_id = feature["properties"]["admin_id"]
        for parent_id in normalize_parent_ids(feature["properties"].get("parent_admin_ids", [])):
            county_ids_by_parent[parent_id].append(county_id)
    for parent_id in county_ids_by_parent:
        county_ids_by_parent[parent_id].sort()
    return summary_features, summary_by_id, county_features, county_by_id, county_ids_by_parent


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
            for suffix in [
                "省",
                "市",
                "自治区",
                "壮族自治区",
                "回族自治区",
                "维吾尔自治区",
                "县",
                "区",
                "旗",
                "自治县",
                "County",
                "District",
                "City",
                "Banner",
                "AutonomousCounty",
                "AutonomousBanner",
                "Qu",
                "Xian",
                "Shi",
                "Qi",
            ]:
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


def match_domestic_region_units(
    raw_text: str,
    summary_admin_by_id: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, str]], list[str]]:
    haystack = compact_text(raw_text)
    if not haystack:
        return [], []
    matched: dict[str, dict[str, str]] = {}
    matched_rules: list[str] = []
    for keyword, admin_ids in DOMESTIC_REGION_RULES:
        normalized_keyword = compact_text(keyword)
        if normalized_keyword not in haystack:
            continue
        if normalized_keyword == compact_text("中国北方及中原") and (
            compact_text("黄河以北至辽东") in haystack or compact_text("黄河以北及长江以北") in haystack
        ):
            continue
        if normalized_keyword == compact_text("中国西北") and compact_text("中国西北及中原") in haystack:
            continue
        matched_rules.append(keyword)
        for admin_id in admin_ids:
            feature = summary_admin_by_id.get(admin_id)
            if not feature:
                continue
            matched[admin_id] = {
                "admin_id": admin_id,
                "name": feature["properties"]["name"],
                "matched_alias": keyword,
            }
    return sorted(matched.values(), key=lambda item: item["admin_id"]), matched_rules


def dedupe_sorted(values: list[str]) -> list[str]:
    return sorted(set(values))


def county_ids_for_admin_ids(
    admin_ids: list[str],
    county_by_id: dict[str, dict[str, Any]],
    county_ids_by_parent: dict[str, list[str]],
) -> list[str]:
    county_ids: list[str] = []
    for admin_id in admin_ids:
        if admin_id in county_by_id:
            county_ids.append(admin_id)
        else:
            county_ids.extend(county_ids_by_parent.get(admin_id, []))
    return dedupe_sorted(county_ids)


def summarize_county_parents(
    county_ids: list[str],
    county_by_id: dict[str, dict[str, Any]],
    summary_admin_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    matches: dict[str, dict[str, str]] = {}
    for county_id in county_ids:
        feature = county_by_id.get(county_id)
        if not feature:
            continue
        for parent_id in normalize_parent_ids(feature["properties"].get("parent_admin_ids", [])):
            parent = summary_admin_by_id.get(parent_id)
            if parent:
                matches[parent_id] = {
                    "admin_id": parent_id,
                    "name": parent["properties"]["name"],
                    "matched_alias": parent["properties"]["name"],
                }
    return sorted(matches.values(), key=lambda item: item["admin_id"])


def confidence_for_match(raw_text: str, match_count: int, override: dict[str, Any] | None, matched_resolution: str) -> int:
    low_confidence_markers = ["部分", "一带", "一帶", "曾经", "曾經", "达到", "達到", "后扩张", "中心"]
    if override:
        confidence = override["confidence_score"]
    elif matched_resolution in {"county_text_match", "manual_county_override"}:
        confidence = 88
    elif "domestic_region" in matched_resolution:
        confidence = 58
    else:
        confidence = 78
    if match_count > 4 and not override:
        confidence -= 10
    if any(marker in raw_text for marker in low_confidence_markers):
        confidence -= 14
    return max(45, min(100, confidence))


def coarse_fallback_reason_for_resolution(matched_resolution: str, raw_text: str) -> str:
    if matched_resolution in {"manual_county_override", "county_text_match"}:
        return ""
    if "domestic_region" in matched_resolution:
        return "命中宽泛国内区域词，按现代省级近似展开为县级索引。"
    if matched_resolution in {"manual_province_expanded_to_county", "province_expanded_to_county"}:
        return "仅命中现代省级/直辖市/自治区摘要，已展开为其下所有现代县级单元。"
    if matched_resolution in {"manual_province_only", "province_only"}:
        return "仅命中现代省级/直辖市/自治区摘要，且该行政区没有可用县级子单元，使用省级几何。"
    if not raw_text:
        return "缺少 modern_admin_units_raw 或人工 override。"
    return "未命中可索引的现代县级或省级行政区。"


def build_polity_territories(
    polities: list[dict[str, str]],
    summary_admin_features: list[dict[str, Any]],
    summary_admin_by_id: dict[str, dict[str, Any]],
    county_features: list[dict[str, Any]],
    county_by_id: dict[str, dict[str, Any]],
    county_ids_by_parent: dict[str, list[str]],
    territory_overrides: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    summary_aliases = build_admin_aliases(summary_admin_features)
    county_aliases = build_admin_aliases(county_features)
    neighbor_features = load_neighbor_polygons()
    neighbor_adm1_features = load_neighbor_adm1_polygons()
    territories: dict[str, dict[str, Any]] = {}
    polity_county_index: dict[str, Any] = {}
    report_rows: list[dict[str, Any]] = []
    features: list[dict[str, Any]] = []
    admin_unit_features: list[dict[str, Any]] = []
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()

    for polity in polities:
        polity_id = polity["polity_id"]
        raw_text = polity.get("modern_admin_units_raw", "")
        matches: list[dict[str, str]] = []
        county_ids: list[str] = []
        override = territory_overrides.get(polity_id)
        match_source = "modern_admin_units_raw"
        matched_resolution = "missing"
        confidence_note = ""
        domestic_region_rules: list[str] = []
        if override:
            county_ids = county_ids_for_admin_ids(override["admin_ids"], county_by_id, county_ids_by_parent)
            direct_county_override = any(admin_id in county_by_id for admin_id in override["admin_ids"])
            summary_matches = [
                {
                    "admin_id": admin_id,
                    "name": summary_admin_by_id[admin_id]["properties"]["name"],
                    "matched_alias": summary_admin_by_id[admin_id]["properties"]["name"],
                }
                for admin_id in override["admin_ids"]
                if admin_id in summary_admin_by_id
            ]
            parent_matches = summarize_county_parents(county_ids, county_by_id, summary_admin_by_id)
            matches_by_id = {match["admin_id"]: match for match in [*summary_matches, *parent_matches]}
            matches = sorted(matches_by_id.values(), key=lambda item: item["admin_id"])
            raw_text = raw_text or override["source_raw"] or f"{polity['polity_name']} v1 人工维护王朝级现代行政区近似 override"
            match_source = override["match_source"]
            matched_resolution = "manual_county_override" if direct_county_override else "manual_province_expanded_to_county"
            confidence_note = override["note"]
        else:
            county_matches = match_admin_units(raw_text, county_aliases)
            if county_matches:
                county_ids = county_ids_for_admin_ids([match["admin_id"] for match in county_matches], county_by_id, county_ids_by_parent)
                matches = summarize_county_parents(county_ids, county_by_id, summary_admin_by_id)
                if not matches:
                    matches = county_matches
                matched_resolution = "county_text_match"
            else:
                matches = match_admin_units(raw_text, summary_aliases)
                county_ids = county_ids_for_admin_ids([match["admin_id"] for match in matches], county_by_id, county_ids_by_parent)
                if matches:
                    matched_resolution = "province_expanded_to_county"
            region_matches, domestic_region_rules = match_domestic_region_units(raw_text, summary_admin_by_id)
            if region_matches:
                matches_by_id = {match["admin_id"]: match for match in [*matches, *region_matches]}
                matches = sorted(matches_by_id.values(), key=lambda item: item["admin_id"])
                county_ids = county_ids_for_admin_ids([match["admin_id"] for match in matches], county_by_id, county_ids_by_parent)
                matched_resolution = (
                    "domestic_region_expanded_to_county"
                    if matched_resolution == "missing"
                    else f"{matched_resolution}+domestic_region"
                )
                confidence_note = "宽泛国内区域词近似展开：" + "、".join(domestic_region_rules)
        if matches and not county_ids and matched_resolution in {"manual_province_expanded_to_county", "province_expanded_to_county"}:
            matched_resolution = "manual_province_only" if override else "province_only"
        matched_ids = [match["admin_id"] for match in matches]
        matched_names = [match["name"] for match in matches]
        county_index_ref = f"territories/polity_county_index.json#{polity_id}" if county_ids else None
        coarse_fallback_reason = coarse_fallback_reason_for_resolution(matched_resolution, raw_text)
        polity_county_index[polity_id] = {
            "polity_id": polity_id,
            "polity_name": polity["polity_name"],
            "polity_display_name": polity_display_name(polity),
            "county_ids": county_ids,
            "county_count": len(county_ids),
            "summary_admin_ids": matched_ids,
            "summary_admin_units": matched_names,
            "matched_resolution": matched_resolution,
            "match_source": match_source,
            "source_text": raw_text,
        }
        if not county_ids and not matches:
            # 无国内匹配，但 raw_text 可能命中邻国关键字 → 走纯跨境分支
            if neighbor_features or neighbor_adm1_features:
                neighbor_adm1_ids, neighbor_only_isos, neighbor_names = match_neighbor_targets(raw_text)
            else:
                neighbor_adm1_ids, neighbor_only_isos, neighbor_names = [], [], []
            if neighbor_adm1_ids or neighbor_only_isos:
                neighbor_polygons: list[Any] = []
                neighbor_bboxes: list[tuple[float, float, float, float]] = []
                neighbor_area = 0.0
                neighbor_coord_count = 0
                # 先加 ADM1（精细）
                for adm1_id in neighbor_adm1_ids:
                    feature = neighbor_adm1_features.get(adm1_id)
                    if not feature:
                        continue
                    geom = feature["geometry"]
                    if geom["type"] == "Polygon":
                        neighbor_polygons.append(geom["coordinates"])
                        bbox = polygon_bbox(geom["coordinates"])
                    elif geom["type"] == "MultiPolygon":
                        neighbor_polygons.extend(geom["coordinates"])
                        bbox = polygon_bbox(geom["coordinates"])
                    else:
                        continue
                    neighbor_bboxes.append(bbox)
                    neighbor_area += geometry_area_km2(geom)
                    neighbor_coord_count += geometry_coordinate_count(geom)
                # 再加 ADM0（fallback）
                for iso in neighbor_only_isos:
                    feature = neighbor_features.get(iso)
                    if not feature:
                        continue
                    geom = feature["geometry"]
                    if geom["type"] == "Polygon":
                        neighbor_polygons.append(geom["coordinates"])
                        bbox = polygon_bbox(geom["coordinates"])
                    elif geom["type"] == "MultiPolygon":
                        neighbor_polygons.extend(geom["coordinates"])
                        bbox = polygon_bbox(geom["coordinates"])
                    else:
                        continue
                    neighbor_bboxes.append(bbox)
                    neighbor_area += geometry_area_km2(geom)
                    neighbor_coord_count += geometry_coordinate_count(geom)
                if neighbor_polygons:
                    min_lon = min(bbox[0] for bbox in neighbor_bboxes)
                    min_lat = min(bbox[1] for bbox in neighbor_bboxes)
                    max_lon = max(bbox[2] for bbox in neighbor_bboxes)
                    max_lat = max(bbox[3] for bbox in neighbor_bboxes)
                    centroid = [(min_lon + max_lon) / 2, (min_lat + max_lat) / 2]
                    has_adm1 = bool(neighbor_adm1_ids)
                    resolution = "cross_border_adm1+adm0" if has_adm1 and neighbor_only_isos else (
                        "cross_border_adm1_only" if has_adm1 else "cross_border_adm0_only"
                    )
                    territory = {
                        "geometry_ref": f"territories/approx_polities.geojson#{polity_id}",
                        "territory_status": "matched_low_confidence",
                        "territory_method": "modern_admin_approximation",
                        "approx_area_km2": round(neighbor_area, 1),
                        "match_confidence": 55 if has_adm1 else 50,
                        "matched_admin_ids": [],
                        "matched_admin_units": [],
                        "matched_county_count": 0,
                        "county_index_ref": None,
                        "boundary_level": "country" if not has_adm1 else "province",
                        "match_resolution": resolution,
                        "coarse_fallback_reason": "国内未匹配，全部以邻国 ADM0/ADM1 近似拼合。",
                        "source_text": raw_text,
                        "geometry_source": str(NEIGHBOR_ADM0_PATH.relative_to(ROOT)),
                        "geometry_source_license": "Public domain (CC0)",
                        "geometry_source_attribution": "Natural Earth admin_0/admin_1",
                        "county_geometry_source": "",
                        "match_source": match_source,
                        "confidence_note": "跨境近似边界，精度为现代国家/省级",
                        "geometry_coordinate_count": neighbor_coord_count,
                        "generated_at": generated_at,
                        "label": TERRITORY_LABEL,
                        "centroid": centroid,
                        "cross_border_iso_codes": neighbor_only_isos,
                        "cross_border_country_names": neighbor_names,
                        "cross_border_adm1_ids": neighbor_adm1_ids,
                    }
                    territories[polity_id] = territory
                    polity_is_nomadic, polity_is_steppe_origin = classify_polity_steppe(polity)
                    features.append(
                        {
                            "type": "Feature",
                            "geometry": {"type": "MultiPolygon", "coordinates": neighbor_polygons},
                            "properties": {
                                "polity_id": polity_id,
                                "polity_name": polity["polity_name"],
                                "polity_display_name": polity_display_name(polity),
                                "polity_name_disambiguation": clean(polity.get("polity_name_disambiguation", "")),
                                "polity_name_review_status": clean(polity.get("polity_name_review_status", "")),
                                "polity_name_risk_flags": clean(polity.get("polity_name_risk_flags", "")),
                                "macro_period": polity["macro_period"],
                                "dynasty_name": polity["dynasty_name"],
                                "polity_type": polity["polity_type"],
                                "is_nomadic": polity_is_nomadic,
                                "is_steppe_origin": polity_is_steppe_origin,
                                **territory,
                            },
                        }
                    )
                    polity_county_index[polity_id] = {
                        "polity_id": polity_id,
                        "polity_name": polity["polity_name"],
                        "polity_display_name": polity_display_name(polity),
                        "county_ids": [],
                        "county_count": 0,
                        "summary_admin_ids": [],
                        "summary_admin_units": [],
                        "matched_resolution": "cross_border_adm0_only",
                        "match_source": match_source,
                        "source_text": raw_text,
                    }
                    report_rows.append(
                        {
                            "polity_id": polity_id,
                            "polity_name": polity["polity_name"],
                            "territory_status": "matched_low_confidence",
                            "matched_admin_ids": "",
                            "matched_admin_units": "",
                            "matched_resolution": "cross_border_adm0_only",
                            "county_count": 0,
                            "county_index_ref": "",
                            "coarse_fallback_reason": "国内未匹配，全部以邻国 ADM0 近似拼合。",
                            "match_source": match_source,
                            "match_confidence": 50,
                            "confidence_note": "跨境近似边界，精度为现代国家级",
                            "approx_area_km2": round(neighbor_area, 1),
                            "source_text": raw_text,
                            "note": f"cross_border_adm0_only: {', '.join(neighbor_names)}",
                        }
                    )
                    continue
            territories[polity_id] = {
                "geometry_ref": None,
                "territory_status": "missing",
                "territory_method": "modern_admin_approximation",
                "approx_area_km2": None,
                "match_confidence": 0,
                "matched_admin_ids": [],
                "matched_admin_units": [],
                "matched_county_count": 0,
                "county_index_ref": None,
                "boundary_level": "missing",
                "match_resolution": "missing",
                "coarse_fallback_reason": coarse_fallback_reason,
                "source_text": raw_text,
                "match_source": match_source,
                "confidence_note": confidence_note,
                "label": TERRITORY_LABEL,
                "cross_border_iso_codes": [],
                "cross_border_country_names": [],
            }
            report_rows.append(
                {
                    "polity_id": polity_id,
                    "polity_name": polity["polity_name"],
                    "territory_status": "missing",
                    "matched_admin_ids": "",
                    "matched_admin_units": "",
                    "matched_resolution": "missing",
                    "county_count": 0,
                    "county_index_ref": "",
                    "coarse_fallback_reason": coarse_fallback_reason,
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
        summary_geometry_ids = [admin_id for admin_id in matched_ids if admin_id in summary_admin_by_id]
        summary_geometry_is_detailed = all(
            geometry_coordinate_count(summary_admin_by_id[admin_id]["geometry"]) > 20
            for admin_id in summary_geometry_ids
        )
        use_county_geometry = bool(county_ids) and (not summary_geometry_ids or not summary_geometry_is_detailed)
        geometry_ids = county_ids if use_county_geometry else summary_geometry_ids
        geometry_by_id = county_by_id if use_county_geometry else summary_admin_by_id
        geometry_source_path = ADMIN_COUNTY_BOUNDARY_PATH if use_county_geometry else ADMIN_SUMMARY_BOUNDARY_PATH
        boundary_level = "county" if county_ids else "province"
        if use_county_geometry:
            matched_resolution = f"{matched_resolution}+county_geometry"
        for admin_id in geometry_ids:
            admin_feature = geometry_by_id[admin_id]
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
                        "matched_resolution": matched_resolution,
                        "county_count": len(county_ids),
                        "county_index_ref": county_index_ref,
                    },
                }
            )

        # 跨境邻国 ADM1+ADM0 合并（MRD §6.4 + batch19 邻国扩展；ADM1 优先避免整国吞并）
        cross_border_adm1_ids: list[str] = []
        cross_border_isos: list[str] = []
        cross_border_names: list[str] = []
        if neighbor_features or neighbor_adm1_features:
            cross_border_adm1_ids, cross_border_isos, cross_border_names = match_neighbor_targets(raw_text)
            domestic_neighbor_isos = {
                iso for admin_id in matched_ids if (iso := DOMESTIC_ADMIN_ID_TO_NEIGHBOR_ISO.get(admin_id))
            }
            if domestic_neighbor_isos:
                cross_border_isos = [iso for iso in cross_border_isos if iso not in domestic_neighbor_isos]
                cross_border_names = [NEIGHBOR_ISO_NAMES.get(iso, iso) for iso in cross_border_isos]
            for adm1_id in cross_border_adm1_ids:
                feature = neighbor_adm1_features.get(adm1_id)
                if not feature:
                    continue
                geom = feature["geometry"]
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
            for iso in cross_border_isos:
                feature = neighbor_features.get(iso)
                if not feature:
                    continue
                geom = feature["geometry"]
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

        confidence = confidence_for_match(raw_text, len(matches), override, matched_resolution)
        territory_status = "matched_low_confidence" if confidence < 70 else "matched"
        if cross_border_adm1_ids and cross_border_isos:
            matched_resolution = f"{matched_resolution}+cross_border_adm1+adm0"
        elif cross_border_adm1_ids:
            matched_resolution = f"{matched_resolution}+cross_border_adm1"
        elif cross_border_isos:
            matched_resolution = f"{matched_resolution}+cross_border_adm0"
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
            "matched_county_count": len(county_ids),
            "county_index_ref": county_index_ref,
            "boundary_level": boundary_level,
            "match_resolution": matched_resolution,
            "coarse_fallback_reason": coarse_fallback_reason,
            "source_text": raw_text,
            "geometry_source": str(geometry_source_path.relative_to(ROOT)),
            "geometry_source_license": county_features[0]["properties"].get("source_license", ""),
            "geometry_source_attribution": county_features[0]["properties"].get("source_attribution", ""),
            "county_geometry_source": str(ADMIN_COUNTY_BOUNDARY_PATH.relative_to(ROOT)),
            "match_source": match_source,
            "confidence_note": confidence_note,
            "geometry_coordinate_count": coordinate_count,
            "generated_at": generated_at,
            "label": TERRITORY_LABEL,
            "centroid": centroid,
            "cross_border_iso_codes": cross_border_isos,
            "cross_border_country_names": cross_border_names,
            "cross_border_adm1_ids": cross_border_adm1_ids,
        }
        territories[polity_id] = territory
        polity_is_nomadic, polity_is_steppe_origin = classify_polity_steppe(polity)
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "MultiPolygon", "coordinates": polygons},
                "properties": {
                    "polity_id": polity_id,
                    "polity_name": polity["polity_name"],
                    "polity_display_name": polity_display_name(polity),
                    "polity_name_disambiguation": clean(polity.get("polity_name_disambiguation", "")),
                    "polity_name_review_status": clean(polity.get("polity_name_review_status", "")),
                    "polity_name_risk_flags": clean(polity.get("polity_name_risk_flags", "")),
                    "macro_period": polity["macro_period"],
                    "dynasty_name": polity["dynasty_name"],
                    "polity_type": polity["polity_type"],
                    "is_nomadic": polity_is_nomadic,
                    "is_steppe_origin": polity_is_steppe_origin,
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
                "matched_resolution": matched_resolution,
                "county_count": len(county_ids),
                "county_index_ref": county_index_ref or "",
                "coarse_fallback_reason": coarse_fallback_reason,
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
    return territories, feature_collection, admin_unit_collection, report_rows, polity_county_index


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
                "polity_display_name": polity_display_name(polity),
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
                    "polity_display_name": current.get("polity_display_name", current["polity_name"]),
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
        label = polity_display_name(polity)
        add(polity["polity_name"], "polity", polity["polity_id"], label, {
            "polity_id": polity["polity_id"],
            "polity_display_name": label,
            "start_year": int_optional(polity.get("polity_start_year", "")),
            "end_year": int_optional(polity.get("polity_end_year", "")),
        })
        for alias in split_list(polity.get("polity_aliases", "")):
            add(alias, "polity", polity["polity_id"], label, {
                "polity_id": polity["polity_id"],
                "polity_display_name": label,
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
        key = (entry["normalized"], entry["entity_type"], entry["entity_id"])
        if key not in dedup:
            dedup[key] = entry
    return {"entries": sorted(dedup.values(), key=lambda item: (item["normalized"], item["entity_type"]))}


def main() -> None:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()

    polities = read_csv(INPUT_DIR / "chinese_history_polities_master_v03.csv")
    rulers = read_csv(INPUT_DIR / "chinese_history_rulers_master_v03.csv")
    yearly_rows = read_csv(INPUT_DIR / "chinese_history_polities_yearly_v03.csv")
    issues = read_csv(INPUT_DIR / "chinese_history_unresolved_or_disputed_v03.csv")
    validation = read_csv(INPUT_DIR / "chinese_history_validation_report_v03.csv")
    capital_raw = read_csv(INPUT_DIR / "capital_events_v03.csv")
    events_path = INPUT_DIR / "historical_events_v03.csv"
    historical_events_raw = read_csv(events_path) if events_path.exists() else []
    anecdotes_path = INPUT_DIR / "historical_anecdotes_v03.csv"
    historical_anecdotes_raw = read_csv(anecdotes_path) if anecdotes_path.exists() else []
    story_presets_path = INPUT_DIR / "story_presets_v03.json"
    story_presets_payload = read_json(story_presets_path) if story_presets_path.exists() else {"data_version": DATA_VERSION, "presets": []}
    (
        summary_admin_features,
        summary_admin_by_id,
        county_features,
        county_by_id,
        county_ids_by_parent,
    ) = load_admin_boundaries()
    admin_boundary_manifest = read_json(ADMIN_BOUNDARY_MANIFEST_PATH)
    territory_overrides = load_territory_overrides()

    polities_by_id = {row["polity_id"]: row for row in polities}
    steppe_flags_by_id: dict[str, tuple[bool, bool]] = {
        row["polity_id"]: classify_polity_steppe(row) for row in polities
    }
    for row in polities:
        is_nomadic, is_steppe_origin = steppe_flags_by_id[row["polity_id"]]
        row["is_nomadic"] = "true" if is_nomadic else "false"
        row["is_steppe_origin"] = "true" if is_steppe_origin else "false"
    issues_by_polity: dict[str, list[dict[str, str]]] = defaultdict(list)
    for issue in issues:
        polity = polities_by_id.get(issue["polity_id"])
        if polity:
            issue["polity_display_name"] = polity_display_name(polity)
        issues_by_polity[issue["polity_id"]].append(issue)

    capital_events = validate_and_normalize_capitals(capital_raw, polities_by_id)
    events_by_polity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in capital_events:
        events_by_polity[event["polity_id"]].append(event)

    migrations = build_capital_migrations(events_by_polity)
    migrations_by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for migration in migrations:
        migrations_by_year[migration["year"]].append(migration)

    yearly_by_year: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in yearly_rows:
        yearly_by_year[int(row["year"])].append(row)
    all_years = sorted(yearly_by_year)

    (
        polity_territories,
        territory_geojson,
        admin_units_by_polity_geojson,
        territory_report_rows,
        polity_county_index,
    ) = build_polity_territories(
        polities,
        summary_admin_features,
        summary_admin_by_id,
        county_features,
        county_by_id,
        county_ids_by_parent,
        territory_overrides,
    )

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    YEARS_DIR.mkdir(parents=True, exist_ok=True)

    write_json(OUT_DIR / "polities.json", {"data_version": DATA_VERSION, "polities": polities})
    write_json(OUT_DIR / "rulers.json", {"data_version": DATA_VERSION, "rulers": rulers})
    write_json(OUT_DIR / "issues.json", {"data_version": DATA_VERSION, "issues": issues})
    write_json(OUT_DIR / "validation.json", {"data_version": DATA_VERSION, "checks": validation})

    # 历史事件层：events.json 只保留真实事件/编年事实/政权起灭。
    # range_anchor 不再作为事件进入播放足迹，而是拆到 historical_contexts。
    historical_events: list[dict[str, Any]] = []
    historical_contexts_by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    historical_contexts_by_id: dict[str, dict[str, Any]] = {}
    for row in historical_events_raw:
        if not row.get("event_id") or not row.get("year"):
            continue
        if row.get("fact_review_status", "verified").strip() != "verified":
            continue
        try:
            year = int(row["year"])
        except ValueError:
            continue
        sort_order = int_event_optional(row.get("sort_order")) or 9999
        importance_level = int_event_optional(row.get("importance_level")) or 3
        display_priority = int_event_optional(row.get("display_priority")) or 3
        item_kind = row.get("item_kind", "").strip() or "core_event"
        coverage_role = row.get("coverage_role", "").strip() or "exact_year_event"
        coverage_start_year = int_event_optional(row.get("coverage_start_year")) or year
        coverage_end_year = int_event_optional(row.get("coverage_end_year")) or year
        coverage_group_id = row.get("coverage_group_id", "").strip() or row["event_id"]
        source_titles = row.get("source_titles", "")
        source_urls = pipe_list(row.get("source_urls", ""))
        longitude = float_event_optional(row.get("longitude"))
        latitude = float_event_optional(row.get("latitude"))
        location = {
            "historical_name": row.get("location_historical_name", ""),
            "modern_name": row.get("location_modern_name", ""),
            "modern_admin_id": row.get("location_modern_admin_id", ""),
            "precision": row.get("location_precision", ""),
            "confidence_score": int_event_optional(row.get("location_confidence_score")),
            "source_titles": row.get("location_source_titles", ""),
            "source_urls": pipe_list(row.get("location_source_urls", "")),
            "note": row.get("location_note", ""),
            "longitude": longitude,
            "latitude": latitude,
        }
        if coverage_role == "range_anchor" or item_kind == "range_anchor":
            context_id = coverage_group_id or row["event_id"]
            span = max(1, abs(coverage_end_year - coverage_start_year))
            progress_ratio = 1 if coverage_start_year == coverage_end_year else (
                (year - coverage_start_year) / span
            )
            progress_ratio = max(0, min(1, progress_ratio))
            context = {
                "context_id": context_id,
                "year": year,
                "year_label": year_label(year),
                "current_year": year,
                "title": row.get("title", ""),
                "description": row.get("description", ""),
                "start_year": coverage_start_year,
                "end_year": coverage_end_year,
                "start_label": year_label(coverage_start_year),
                "end_label": year_label(coverage_end_year),
                "progress_ratio": round(progress_ratio, 4),
                "sort_order": sort_order,
                "display_priority": display_priority,
                "longitude": longitude,
                "latitude": latitude,
                "location_name": row.get("location_name", ""),
                "location_historical_name": row.get("location_historical_name", ""),
                "location_modern_name": row.get("location_modern_name", ""),
                "location_precision": row.get("location_precision", ""),
                "location": location,
                "source_titles": source_titles,
                "source_urls": source_urls,
                "source_type": row.get("source_type", ""),
                "confidence_score": int_event_optional(row.get("confidence_score")),
                "confidence_note": row.get("confidence_note", ""),
            }
            historical_contexts_by_year[year].append(context)
            if context_id not in historical_contexts_by_id:
                historical_contexts_by_id[context_id] = {
                    **context,
                    "year": coverage_start_year,
                    "year_label": year_label(coverage_start_year),
                    "current_year": coverage_start_year,
                    "progress_ratio": 0,
                    "year_count": len(iter_years(coverage_start_year, coverage_end_year)),
                }
            continue
        historical_events.append(
            {
                "event_id": row["event_id"],
                "year": year,
                "year_label": year_label(year),
                "sort_order": sort_order,
                "date_label": row.get("date_label") or year_label(year),
                "date_precision": row.get("date_precision", "year") or "year",
                "coverage_role": coverage_role,
                "coverage_start_year": coverage_start_year,
                "coverage_end_year": coverage_end_year,
                "coverage_group_id": coverage_group_id,
                "item_kind": item_kind,
                "event_type": row.get("event_type", "event"),
                "title": row.get("title", ""),
                "description": row.get("description", ""),
                "significance": row.get("significance", ""),
                "primary_education_stage": row.get("primary_education_stage", ""),
                "education_stage_tags": pipe_list(row.get("education_stage_tags", "")),
                "curriculum_basis": row.get("curriculum_basis", ""),
                "importance_level": importance_level,
                "display_priority": display_priority,
                "related_polity_ids": [
                    value.strip() for value in row.get("related_polity_ids", "").split("|") if value.strip()
                ],
                "related_people": pipe_list(row.get("related_people", "")),
                "location_name": row.get("location_name", ""),
                "longitude": longitude,
                "latitude": latitude,
                "location_historical_name": row.get("location_historical_name", ""),
                "location_modern_name": row.get("location_modern_name", ""),
                "location_modern_admin_id": row.get("location_modern_admin_id", ""),
                "location_precision": row.get("location_precision", ""),
                "location_confidence_score": int_event_optional(row.get("location_confidence_score")),
                "location_source_titles": row.get("location_source_titles", ""),
                "location_source_urls": pipe_list(row.get("location_source_urls", "")),
                "location_note": row.get("location_note", ""),
                "location": location,
                "source_titles": source_titles,
                "source_urls": source_urls,
                "source_type": row.get("source_type", ""),
                "confidence_score": int_event_optional(row.get("confidence_score")),
                "confidence_note": row.get("confidence_note", ""),
                "fact_review_status": row.get("fact_review_status", "verified"),
                "review_note": row.get("review_note", ""),
            }
        )
    historical_events.sort(key=lambda event: (event["year"], event["sort_order"], event["event_id"]))
    historical_events_by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for event in historical_events:
        historical_events_by_year[event["year"]].append(event)
    for year in all_years:
        if historical_contexts_by_year.get(year):
            continue
        event_rows = historical_events_by_year.get(year, [])
        if not event_rows:
            continue
        primary = sorted(
            event_rows,
            key=lambda event: (event["display_priority"], -event["importance_level"], event["sort_order"], event["event_id"]),
        )[0]
        context_id = f"context:activity_{year}"
        context = {
            "context_id": context_id,
            "year": year,
            "year_label": year_label(year),
            "current_year": year,
            "title": primary["title"],
            "description": primary["description"],
            "start_year": year,
            "end_year": year,
            "start_label": year_label(year),
            "end_label": year_label(year),
            "progress_ratio": 1,
            "sort_order": primary["sort_order"],
            "display_priority": primary["display_priority"],
            "longitude": primary["longitude"],
            "latitude": primary["latitude"],
            "location_name": primary["location_name"],
            "location_historical_name": primary.get("location_historical_name", ""),
            "location_modern_name": primary.get("location_modern_name", ""),
            "location_precision": primary.get("location_precision", ""),
            "location": primary.get("location"),
            "source_titles": primary.get("source_titles", ""),
            "source_urls": primary.get("source_urls", []),
            "source_type": primary.get("source_type", ""),
            "confidence_score": primary.get("confidence_score"),
            "confidence_note": "本年有真实事件，脉络卡跟随该关键节点刷新。",
        }
        historical_contexts_by_year[year].append(context)
        historical_contexts_by_id[context_id] = {**context, "year_count": 1}
    historical_event_markers = list(historical_events)
    historical_event_years = sorted({event["year"] for event in historical_events})
    historical_contexts = sorted(
        historical_contexts_by_id.values(),
        key=lambda context: (context["start_year"], context["sort_order"], context["context_id"]),
    )
    historical_context_years = sorted(historical_contexts_by_year)
    write_json(
        OUT_DIR / "events.json",
        {
            "data_version": DATA_VERSION,
            "generated_at": generated_at,
            "event_count": len(historical_events),
            "covered_year_count": len(historical_event_years),
            "full_year_coverage": len(historical_event_years) == len(all_years),
            "marker_count": len(historical_event_markers),
            "events": historical_event_markers,
        },
    )
    write_json(
        OUT_DIR / "contexts.json",
        {
            "data_version": DATA_VERSION,
            "generated_at": generated_at,
            "context_count": len(historical_contexts),
            "covered_year_count": len(historical_context_years),
            "full_year_coverage": len(historical_context_years) == len(all_years),
            "context_years": historical_context_years,
            "contexts": historical_contexts,
        },
    )

    # 历史典故层：独立于正式事件库。前端默认不播放，用户开启“播放典故”后
    # 才把这些 event-like 条目合入年份流与地图脉冲。
    anecdote_types = {"chengyu", "historical_story", "literary_allusion", "folk_tale"}
    anecdote_source_types = {
        "classic_text",
        "official_history",
        "literary_collection",
        "folk_tradition",
        "secondary_reference",
    }
    historical_anecdotes: list[dict[str, Any]] = []
    seen_anecdote_ids: set[str] = set()
    for row in historical_anecdotes_raw:
        anecdote_id = row.get("anecdote_id", "").strip()
        if not anecdote_id or anecdote_id in seen_anecdote_ids:
            continue
        seen_anecdote_ids.add(anecdote_id)
        if row.get("review_status", "verified").strip() != "verified":
            continue
        try:
            year = int(row["year"])
        except (KeyError, ValueError):
            continue
        if year == 0:
            continue
        longitude = float_event_optional(row.get("longitude"))
        latitude = float_event_optional(row.get("latitude"))
        if longitude is None or latitude is None:
            continue
        anecdote_type = row.get("anecdote_type", "").strip()
        source_type = row.get("source_type", "").strip()
        if anecdote_type not in anecdote_types or source_type not in anecdote_source_types:
            continue
        source_url = row.get("source_url", "").strip()
        source_urls = pipe_list(source_url)
        coverage_start_year = int_event_optional(row.get("coverage_start_year")) or year
        coverage_end_year = int_event_optional(row.get("coverage_end_year")) or year
        if coverage_start_year > coverage_end_year:
            coverage_start_year, coverage_end_year = coverage_end_year, coverage_start_year
        sort_order = int_event_optional(row.get("sort_order")) or 7000
        display_priority = int_event_optional(row.get("display_priority")) or 6
        primary_stage = row.get("primary_education_stage", "").strip() or "初中"
        source_title = row.get("source_title", "").strip()
        source_section = row.get("source_section", "").strip()
        title = row.get("title", "").strip()
        short_description = row.get("short_description", "").strip()
        story_text = row.get("story_text", "").strip()
        location = {
            "historical_name": row.get("location_historical_name", ""),
            "modern_name": row.get("location_modern_name", ""),
            "modern_admin_id": "",
            "precision": row.get("location_precision", ""),
            "confidence_score": 86,
            "source_titles": "CHGIS中国历史地理信息系统|中国历史地图集体系",
            "source_urls": [
                "https://chgis.fas.harvard.edu/pages/intro/",
                "https://east.library.utoronto.ca/internet-resource/chinese-civilization-time-and-space",
            ],
            "note": "典故主发生点按故事核心地点或最常见叙事地点落点。",
            "longitude": longitude,
            "latitude": latitude,
        }
        source_label = source_title
        if source_section:
            source_label = f"{source_title}·{source_section}"
        historical_anecdotes.append(
            {
                "event_id": anecdote_id,
                "anecdote_id": anecdote_id,
                "year": year,
                "year_label": year_label(year),
                "sort_order": sort_order,
                "date_label": row.get("date_label") or year_label(year),
                "date_precision": row.get("date_precision", "year") or "year",
                "coverage_role": "anecdote",
                "coverage_start_year": coverage_start_year,
                "coverage_end_year": coverage_end_year,
                "coverage_group_id": f"anecdote:{anecdote_id}",
                "item_kind": "anecdote",
                "event_type": "allusion",
                "title": title,
                "description": short_description,
                "significance": story_text,
                "primary_education_stage": primary_stage,
                "education_stage_tags": pipe_list(row.get("education_stage_tags", "")) or [primary_stage],
                "curriculum_basis": "历史文化常识与成语典故拓展",
                "importance_level": 2,
                "display_priority": display_priority,
                "related_polity_ids": [
                    value.strip() for value in row.get("related_polity_ids", "").split("|") if value.strip()
                ],
                "related_people": pipe_list(row.get("related_people", "")),
                "location_name": row.get("location_historical_name") or row.get("location_modern_name", ""),
                "longitude": longitude,
                "latitude": latitude,
                "location_historical_name": row.get("location_historical_name", ""),
                "location_modern_name": row.get("location_modern_name", ""),
                "location_modern_admin_id": "",
                "location_precision": row.get("location_precision", ""),
                "location_confidence_score": 86,
                "location_source_titles": "CHGIS中国历史地理信息系统|中国历史地图集体系",
                "location_source_urls": location["source_urls"],
                "location_note": location["note"],
                "location": location,
                "source_titles": source_label,
                "source_urls": source_urls,
                "source_type": source_type,
                "confidence_score": 88,
                "confidence_note": row.get("review_note", ""),
                "fact_review_status": "verified",
                "review_note": row.get("review_note", ""),
                "anecdote_type": anecdote_type,
                "dynasty_name": row.get("dynasty_name", ""),
                "macro_period": row.get("macro_period", ""),
                "phrase": row.get("phrase", ""),
                "story_text": story_text,
                "source_title": source_title,
                "source_section": source_section,
                "source_url": source_url,
                "source_note": row.get("source_note", ""),
                "is_anecdote": True,
            }
        )
    historical_anecdotes.sort(key=lambda event: (event["year"], event["sort_order"], event["event_id"]))
    historical_anecdotes_by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    anecdote_count_by_dynasty: dict[str, int] = defaultdict(int)
    for anecdote in historical_anecdotes:
        historical_anecdotes_by_year[anecdote["year"]].append(anecdote)
        anecdote_count_by_dynasty[anecdote.get("dynasty_name") or "未分期"] += 1
    historical_anecdote_years = sorted({anecdote["year"] for anecdote in historical_anecdotes})
    write_json(
        OUT_DIR / "anecdotes.json",
        {
            "data_version": DATA_VERSION,
            "generated_at": generated_at,
            "anecdote_count": len(historical_anecdotes),
            "covered_year_count": len(historical_anecdote_years),
            "marker_count": len(historical_anecdotes),
            "by_dynasty": dict(sorted(anecdote_count_by_dynasty.items())),
            "anecdotes": historical_anecdotes,
        },
    )

    for rows in historical_contexts_by_year.values():
        rows.sort(key=lambda context: (context["display_priority"], context["sort_order"], context["context_id"]))

    # 播放活跃度报告：真实事件/典故稀疏的年份由脉络层补足，不再把 range_anchor 当事件刷屏。
    activity_report_path = INPUT_DIR / "historical_activity_gaps_report_v03.csv"
    real_activity_years = sorted(set(historical_event_years) | set(historical_anecdote_years))
    with activity_report_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "year",
            "year_label",
            "historical_event_count",
            "historical_anecdote_count",
            "historical_context_count",
            "has_real_activity",
            "has_context",
            "previous_real_activity_year",
            "next_real_activity_year",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        previous_activity: int | None = None
        activity_index = 0
        for year in all_years:
            while activity_index < len(real_activity_years) and real_activity_years[activity_index] <= year:
                if real_activity_years[activity_index] == year:
                    break
                activity_index += 1
            next_activity = next((candidate for candidate in real_activity_years if candidate > year), None)
            event_count = len(historical_events_by_year.get(year, []))
            anecdote_count = len(historical_anecdotes_by_year.get(year, []))
            has_real_activity = bool(event_count or anecdote_count)
            if has_real_activity:
                previous_activity = year
            writer.writerow(
                {
                    "year": year,
                    "year_label": year_label(year),
                    "historical_event_count": event_count,
                    "historical_anecdote_count": anecdote_count,
                    "historical_context_count": len(historical_contexts_by_year.get(year, [])),
                    "has_real_activity": "true" if has_real_activity else "false",
                    "has_context": "true" if historical_contexts_by_year.get(year) else "false",
                    "previous_real_activity_year": previous_activity if previous_activity is not None else "",
                    "next_real_activity_year": next_activity if next_activity is not None else "",
                }
            )

    # 演示脚本 passthrough（MRD §11.3.3）
    if story_presets_payload.get("presets"):
        write_json(
            OUT_DIR / "story_presets.json",
            {
                "data_version": DATA_VERSION,
                "generated_at": generated_at,
                "preset_count": len(story_presets_payload["presets"]),
                "presets": story_presets_payload["presets"],
            },
        )

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
    write_json(TERRITORIES_DIR / "county_units.geojson", {"type": "FeatureCollection", "features": county_features})
    write_json(
        TERRITORIES_DIR / "polity_county_index.json",
        {
            "data_version": DATA_VERSION,
            "generated_at": generated_at,
            "source": str(ADMIN_COUNTY_BOUNDARY_PATH.relative_to(ROOT)),
            "polities": polity_county_index,
        },
    )
    write_json(TERRITORIES_DIR / "modern_admin_units.geojson", {"type": "FeatureCollection", "features": summary_admin_features})
    write_csv(
        TERRITORIES_DIR / "territory_match_report.csv",
        territory_report_rows,
        [
            "polity_id",
            "polity_name",
            "territory_status",
            "matched_admin_ids",
            "matched_admin_units",
            "matched_resolution",
            "county_count",
            "county_index_ref",
            "coarse_fallback_reason",
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
            is_nomadic_flag, is_steppe_origin_flag = steppe_flags_by_id.get(polity_id, (False, False))
            polities_payload.append(
                {
                    "polity_id": polity_id,
                    "polity_name": first["polity_name"],
                    "polity_aliases": first["polity_aliases"],
                    "polity_display_name": polity_display_name(first),
                    "polity_name_disambiguation": clean(first.get("polity_name_disambiguation", "")),
                    "polity_name_review_status": clean(first.get("polity_name_review_status", "")),
                    "polity_name_risk_flags": clean(first.get("polity_name_risk_flags", "")),
                    "macro_period": first["macro_period"],
                    "dynasty_name": first["dynasty_name"],
                    "polity_type": first["polity_type"],
                    "is_nomadic": is_nomadic_flag,
                    "is_steppe_origin": is_steppe_origin_flag,
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
                "historical_events": historical_events_by_year.get(year, []),
                "historical_anecdotes": historical_anecdotes_by_year.get(year, []),
                "historical_contexts": historical_contexts_by_year.get(year, [])[:3],
            },
        )

    input_files = [
        INPUT_DIR / "chinese_history_polities_master_v03.csv",
        INPUT_DIR / "chinese_history_rulers_master_v03.csv",
        INPUT_DIR / "chinese_history_polities_yearly_v03.csv",
        INPUT_DIR / "chinese_history_unresolved_or_disputed_v03.csv",
        INPUT_DIR / "chinese_history_validation_report_v03.csv",
        INPUT_DIR / "capital_events_v03.csv",
        INPUT_DIR / "republican_period_sources_v03.csv",
        events_path,
        anecdotes_path,
        activity_report_path,
        INPUT_DIR / "territory_overrides_v03.csv",
        ADMIN_BOUNDARY_DIR / "china_adm1_geoboundaries_raw.geojson",
        ADMIN_SUMMARY_BOUNDARY_PATH,
        ADMIN_BOUNDARY_DIR / "china_adm3_geoboundaries_raw.geojson",
        ADMIN_COUNTY_BOUNDARY_PATH,
        ADMIN_BOUNDARY_MANIFEST_PATH,
        ADMIN_BOUNDARY_DIR / "county_boundary_source_research.md",
        ADMIN_BOUNDARY_DIR / "ODbL-1.0-NOTICE.md",
        ADMIN_BOUNDARY_DIR / "neighbor_adm0.geojson",
        ADMIN_BOUNDARY_DIR / "neighbor_adm0_manifest.json",
        ADMIN_BOUNDARY_DIR / "neighbor_adm1.geojson",
        ADMIN_BOUNDARY_DIR / "neighbor_adm1_manifest.json",
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
        "historical_event_count": len(historical_events),
        "historical_event_years": historical_event_years,
        "historical_event_covered_year_count": len(historical_event_years),
        "historical_event_full_year_coverage": len(historical_event_years) == len(all_years),
        "historical_event_marker_count": len(historical_event_markers),
        "historical_event_marker_years": sorted({event["year"] for event in historical_event_markers}),
        "historical_anecdote_count": len(historical_anecdotes),
        "historical_anecdote_years": historical_anecdote_years,
        "historical_anecdote_marker_count": len(historical_anecdotes),
        "historical_context_count": len(historical_contexts),
        "historical_context_years": historical_context_years,
        "historical_context_covered_year_count": len(historical_context_years),
        "historical_context_full_year_coverage": len(historical_context_years) == len(all_years),
        "territory_polity_count": len(matched_territories),
        "territory_missing_count": len(polities) - len(matched_territories),
        "territory_low_confidence_count": len(low_confidence_territories),
        "territory_coverage_ratio": round(len(matched_territories) / len(polities), 4),
        "territory_label": TERRITORY_LABEL,
        "territory_boundary_level": "county_index_with_admin1_aggregate_fill",
        "admin_boundary_source": admin_boundary_manifest["source"],
        "admin_boundary_source_release": admin_boundary_manifest["source_release"],
        "admin_boundary_license": admin_boundary_manifest["source_license"],
        "admin_boundary_attribution": admin_boundary_manifest["source_attribution"],
        "admin_boundary_feature_count": admin_boundary_manifest["feature_count"],
        "admin_boundary_level": admin_boundary_manifest.get("admin_level", "county"),
        "county_unit_count": len(county_features),
        "county_units_path": "territories/county_units.geojson",
        "county_index_path": "territories/polity_county_index.json",
        "summary_admin_boundary_feature_count": len(summary_admin_features),
        "summary_admin_boundary_path": str(ADMIN_SUMMARY_BOUNDARY_PATH.relative_to(ROOT)),
        "modern_admin_reference_feature_count": len(summary_admin_features),
        "modern_admin_reference_path": "territories/modern_admin_units.geojson",
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
