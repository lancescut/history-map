#!/usr/bin/env python3
"""Generate v03 normalized China historical polity tables from v02.

The v03 build treats v02 as an audited draft, extracts polity-level and
ruler-level master records, then regenerates the yearly table from those
masters. This prevents stale yearly rows from surviving after a polity's
start/end years were corrected.
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "input" / "chinese_history_polities_yearly_v02.csv"
OUT_DIR = ROOT / "input" / "v03"

SCOPE_START_YEAR = -1046
SCOPE_END_YEAR = 1912

YEARLY_V02_FIELDS = [
    "row_id",
    "row_granularity",
    "year",
    "year_label",
    "macro_period",
    "dynasty_name",
    "polity_name",
    "polity_aliases",
    "polity_type",
    "polity_start_year",
    "polity_start_label",
    "polity_end_year",
    "polity_end_label",
    "polity_date_raw",
    "polity_date_precision",
    "historical_geography_raw",
    "modern_admin_units_raw",
    "capital_historical",
    "capital_modern",
    "ruling_family_or_clan",
    "ethnicity_or_group",
    "founder",
    "last_ruler",
    "destroyed_by_or_successor",
    "polity_source_titles",
    "polity_source_urls",
    "polity_source_raw",
    "confidence_score",
    "confidence_note",
    "calendar_system_note",
    "ruler_name",
    "ruler_title",
    "ruler_temple_name",
    "ruler_posthumous_name",
    "ruler_personal_name",
    "ruler_reign_start_year",
    "ruler_reign_start_label",
    "ruler_reign_end_year",
    "ruler_reign_end_label",
    "ruler_reign_raw",
    "ruler_reign_precision",
    "era_names",
    "ruler_source_title",
    "ruler_source_url",
    "ruler_source_section",
    "ruler_confidence_score",
    "ruler_confidence_note",
]

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
        "衞": "卫",
        "衛": "卫",
        "東": "东",
        "遼": "辽",
        "馬": "马",
        "閩": "闽",
        "荊": "荆",
        "楊": "杨",
        "靜": "静",
        "軍": "军",
        "車": "车",
        "涼": "凉",
        "鮮": "鲜",
        "鄧": "邓",
        "濫": "滥",
        "呂": "吕",
        "蔣": "蒋",
        "鄭": "郑",
        "劉": "刘",
        "魯": "鲁",
        "許": "许",
        "溫": "温",
        "畢": "毕",
        "應": "应",
        "陳": "陈",
        "縣": "县",
        "譙": "谯",
        "盧": "卢",
        "餘": "余",
        "鞏": "巩",
        "譚": "谭",
        "頓": "顿",
        "鳩": "鸠",
    }
)

CANONICAL_NAME_ALIASES = {
    "宋": "刘宋",
    "齐": "南齐",
    "梁": "梁朝",
    "陈": "陈朝",
}

FIVE_DYNASTIES = {"后梁", "后唐", "后晋", "后汉", "后周"}
TEN_KINGDOMS = {"杨吴", "前蜀", "吴越", "闽", "南汉", "荆南", "后蜀", "南唐", "北汉", "马楚"}
SOUTHERN_NORTHERN = {"刘宋", "南齐", "梁朝", "陈朝", "西梁", "北魏", "东魏", "西魏", "北齐", "北周"}


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\ufeff", "").replace("\xa0", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def common_text(value: str) -> str:
    return re.sub(r"\s+", "", clean(value).translate(TRAD_TO_COMMON))


def canonical_name(value: str) -> str:
    name = common_text(value)
    return CANONICAL_NAME_ALIASES.get(name, name)


def int_or_none(value: str) -> int | None:
    value = clean(value)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def year_label(year: int | None) -> str:
    if year is None:
        return ""
    return f"前{abs(year)}年" if year < 0 else f"{year}年"


def iter_years(start: int, end: int) -> list[int]:
    low = max(start, SCOPE_START_YEAR)
    high = min(end, SCOPE_END_YEAR)
    if low > high:
        return []
    return [year for year in range(low, high + 1) if year != 0]


def join_unique(values: list[str], sep: str = " | ") -> str:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        value = clean(value)
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return sep.join(out)


def split_aliases(value: str) -> list[str]:
    value = clean(value)
    if not value:
        return []
    pieces = re.split(r"[|；;、,，]", value)
    return [clean(piece) for piece in pieces if clean(piece)]


def choose_text(rows: list[dict[str, str]], field: str) -> str:
    values = [clean(row.get(field, "")) for row in rows if clean(row.get(field, ""))]
    if not values:
        return ""
    return Counter(values).most_common(1)[0][0]


def choose_score(rows: list[dict[str, str]], field: str) -> str:
    scores = [int_or_none(row.get(field, "")) for row in rows]
    scores = [score for score in scores if score is not None]
    if not scores:
        return ""
    return str(max(scores))


def choose_context(name: str, rows: list[dict[str, str]], start: int | None) -> tuple[str, str]:
    if name in {"西周", "东周"}:
        return "周", "周朝"
    if name.endswith("国") and start is not None and start < -221:
        return "周", "周代诸侯国"
    if name in {"秦朝", "西汉", "新朝", "东汉"}:
        return "秦汉", name
    if name in {"曹魏", "蜀汉", "东吴"}:
        return "三国", "三国"
    if name in {"西晋", "东晋"}:
        return "两晋", name
    if name in SOUTHERN_NORTHERN:
        return "魏晋南北朝", "南北朝"
    if name in FIVE_DYNASTIES:
        return "五代十国", "五代"
    if name in TEN_KINGDOMS:
        return "五代十国", "十国"
    if name in {"北宋", "南宋", "辽朝", "西辽", "西夏", "金朝"}:
        return "宋辽金夏", "宋辽金夏"
    if name in {"元朝", "北元", "明朝", "南明", "后金", "清朝"}:
        return "元明清", "元明清"
    macro = choose_text(rows, "macro_period")
    dynasty = choose_text(rows, "dynasty_name")
    return macro, dynasty


def load_v02() -> list[dict[str, str]]:
    with INPUT.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def build_polity_groups(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    by_name: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_name[canonical_name(row["polity_name"])].append(row)

    groups: dict[str, dict[str, Any]] = {}
    for idx, (name, group_rows) in enumerate(sorted(by_name.items()), start=1):
        starts = [int_or_none(row["polity_start_year"]) for row in group_rows]
        ends = [int_or_none(row["polity_end_year"]) for row in group_rows]
        starts = [start for start in starts if start is not None]
        ends = [end for end in ends if end is not None]
        start = min(starts) if starts else None
        end = max(ends) if ends else None
        macro, dynasty = choose_context(name, group_rows, start)

        aliases: list[str] = []
        original_names = sorted({clean(row["polity_name"]) for row in group_rows if clean(row["polity_name"])})
        aliases.extend(original_names)
        for row in group_rows:
            aliases.extend(split_aliases(row.get("polity_aliases", "")))
        aliases = [alias for alias in aliases if common_text(alias) != common_text(name)]

        actual_years = sorted({int_or_none(row["year"]) for row in group_rows if int_or_none(row["year"]) is not None})
        contexts = sorted(
            {
                f"{row['macro_period']}/{row['dynasty_name']}/{row['polity_name']}({row['polity_start_year']}..{row['polity_end_year']})"
                for row in group_rows
            }
        )

        polity_id = f"polity_{idx:04d}"
        groups[name] = {
            "polity_id": polity_id,
            "polity_name": name,
            "polity_aliases": join_unique(aliases, "; "),
            "macro_period": macro,
            "dynasty_name": dynasty,
            "polity_type": choose_text(group_rows, "polity_type"),
            "polity_start_year": "" if start is None else str(start),
            "polity_start_label": year_label(start),
            "polity_end_year": "" if end is None else str(end),
            "polity_end_label": year_label(end),
            "polity_date_raw": join_unique([row.get("polity_date_raw", "") for row in group_rows]),
            "polity_date_precision": choose_text(group_rows, "polity_date_precision"),
            "historical_geography_raw": join_unique([row.get("historical_geography_raw", "") for row in group_rows]),
            "modern_admin_units_raw": join_unique([row.get("modern_admin_units_raw", "") for row in group_rows]),
            "capital_historical": join_unique([row.get("capital_historical", "") for row in group_rows]),
            "capital_modern": join_unique([row.get("capital_modern", "") for row in group_rows]),
            "ruling_family_or_clan": join_unique([row.get("ruling_family_or_clan", "") for row in group_rows]),
            "ethnicity_or_group": join_unique([row.get("ethnicity_or_group", "") for row in group_rows]),
            "founder": join_unique([row.get("founder", "") for row in group_rows]),
            "last_ruler": join_unique([row.get("last_ruler", "") for row in group_rows]),
            "destroyed_by_or_successor": join_unique([row.get("destroyed_by_or_successor", "") for row in group_rows]),
            "polity_source_titles": join_unique([row.get("polity_source_titles", "") for row in group_rows]),
            "polity_source_urls": join_unique([row.get("polity_source_urls", "") for row in group_rows]),
            "polity_source_raw": join_unique([row.get("polity_source_raw", "") for row in group_rows]),
            "confidence_score": choose_score(group_rows, "confidence_score"),
            "confidence_note": join_unique([row.get("confidence_note", "") for row in group_rows]),
            "calendar_system_note": choose_text(group_rows, "calendar_system_note")
            or "BCE years are negative integers; there is no year 0; ranges are expanded inclusively when start and end years are parseable.",
            "v02_row_count": str(len(group_rows)),
            "v02_actual_min_year": "" if not actual_years else str(actual_years[0]),
            "v02_actual_max_year": "" if not actual_years else str(actual_years[-1]),
            "v02_actual_years": ";".join(str(year) for year in actual_years),
            "merged_from_v02_contexts": " | ".join(contexts),
            "_rows": group_rows,
            "_actual_years": actual_years,
        }
    return groups


def build_rulers(groups: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    rulers_by_key: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for group in groups.values():
        for row in group["_rows"]:
            ruler_name = clean(row.get("ruler_name", ""))
            if not ruler_name:
                continue
            key = (
                group["polity_id"],
                common_text(ruler_name),
                clean(row.get("ruler_reign_start_year", "")),
                clean(row.get("ruler_reign_end_year", "")),
            )
            rulers_by_key[key].append(row)

    out: list[dict[str, str]] = []
    for idx, ((polity_id, _ruler_key, start, end), rows) in enumerate(sorted(rulers_by_key.items()), start=1):
        group = next(group for group in groups.values() if group["polity_id"] == polity_id)
        ruler_id = f"ruler_{idx:05d}"
        out.append(
            {
                "ruler_id": ruler_id,
                "polity_id": polity_id,
                "polity_name": group["polity_name"],
                "ruler_name": choose_text(rows, "ruler_name"),
                "ruler_title": choose_text(rows, "ruler_title"),
                "ruler_temple_name": choose_text(rows, "ruler_temple_name"),
                "ruler_posthumous_name": choose_text(rows, "ruler_posthumous_name"),
                "ruler_personal_name": choose_text(rows, "ruler_personal_name"),
                "ruler_reign_start_year": start,
                "ruler_reign_start_label": year_label(int_or_none(start)),
                "ruler_reign_end_year": end,
                "ruler_reign_end_label": year_label(int_or_none(end)),
                "ruler_reign_raw": choose_text(rows, "ruler_reign_raw"),
                "ruler_reign_precision": choose_text(rows, "ruler_reign_precision"),
                "era_names": join_unique([row.get("era_names", "") for row in rows]),
                "ruler_source_title": join_unique([row.get("ruler_source_title", "") for row in rows]),
                "ruler_source_url": join_unique([row.get("ruler_source_url", "") for row in rows]),
                "ruler_source_section": join_unique([row.get("ruler_source_section", "") for row in rows]),
                "ruler_confidence_score": choose_score(rows, "ruler_confidence_score"),
                "ruler_confidence_note": join_unique([row.get("ruler_confidence_note", "") for row in rows]),
                "merged_from_v02_rows": ",".join(row.get("row_id", "") for row in rows if row.get("row_id")),
            }
        )
    return out


def empty_ruler_fields(note: str) -> dict[str, str]:
    return {
        "ruler_id": "",
        "ruler_name": "",
        "ruler_title": "",
        "ruler_temple_name": "",
        "ruler_posthumous_name": "",
        "ruler_personal_name": "",
        "ruler_reign_start_year": "",
        "ruler_reign_start_label": "",
        "ruler_reign_end_year": "",
        "ruler_reign_end_label": "",
        "ruler_reign_raw": "",
        "ruler_reign_precision": "",
        "era_names": "",
        "ruler_source_title": "",
        "ruler_source_url": "",
        "ruler_source_section": "",
        "ruler_confidence_score": "",
        "ruler_confidence_note": note,
    }


def ruler_matches_year(ruler: dict[str, str], year: int) -> bool:
    start = int_or_none(ruler["ruler_reign_start_year"])
    end = int_or_none(ruler["ruler_reign_end_year"])
    if start is None or end is None:
        return False
    return start <= year <= end


def build_yearly(groups: dict[str, dict[str, Any]], rulers: list[dict[str, str]]) -> list[dict[str, str]]:
    rulers_by_polity: dict[str, list[dict[str, str]]] = defaultdict(list)
    for ruler in rulers:
        rulers_by_polity[ruler["polity_id"]].append(ruler)

    out: list[dict[str, str]] = []
    for group in groups.values():
        start = int_or_none(group["polity_start_year"])
        end = int_or_none(group["polity_end_year"])
        if start is not None and end is not None:
            years = iter_years(start, end)
        else:
            years = [year for year in group["_actual_years"] if SCOPE_START_YEAR <= year <= SCOPE_END_YEAR and year != 0]

        polity_rulers = rulers_by_polity.get(group["polity_id"], [])
        for year in years:
            matched = [ruler for ruler in polity_rulers if ruler_matches_year(ruler, year)]
            if not matched:
                note = "该年度在政权存在期内，但未匹配到可解析君主年表；按国家年度行保留"
                row = make_yearly_row(group, year, "year_polity_unmatched_ruler", empty_ruler_fields(note))
                out.append(row)
                continue
            for ruler in matched:
                row = make_yearly_row(group, year, "year_polity_ruler", ruler)
                out.append(row)

    out.sort(key=lambda row: (int(row["year"]), row["macro_period"], row["dynasty_name"], row["polity_name"], row.get("ruler_id", "")))
    for idx, row in enumerate(out, start=1):
        row["row_id"] = str(idx)
    return out


def make_yearly_row(group: dict[str, Any], year: int, granularity: str, ruler: dict[str, str]) -> dict[str, str]:
    row = {
        "row_id": "",
        "polity_id": group["polity_id"],
        "ruler_id": ruler.get("ruler_id", ""),
        "row_granularity": granularity,
        "year": str(year),
        "year_label": year_label(year),
        "macro_period": group["macro_period"],
        "dynasty_name": group["dynasty_name"],
        "polity_name": group["polity_name"],
        "polity_aliases": group["polity_aliases"],
        "polity_type": group["polity_type"],
        "polity_start_year": group["polity_start_year"],
        "polity_start_label": group["polity_start_label"],
        "polity_end_year": group["polity_end_year"],
        "polity_end_label": group["polity_end_label"],
        "polity_date_raw": group["polity_date_raw"],
        "polity_date_precision": group["polity_date_precision"],
        "historical_geography_raw": group["historical_geography_raw"],
        "modern_admin_units_raw": group["modern_admin_units_raw"],
        "capital_historical": group["capital_historical"],
        "capital_modern": group["capital_modern"],
        "ruling_family_or_clan": group["ruling_family_or_clan"],
        "ethnicity_or_group": group["ethnicity_or_group"],
        "founder": group["founder"],
        "last_ruler": group["last_ruler"],
        "destroyed_by_or_successor": group["destroyed_by_or_successor"],
        "polity_source_titles": group["polity_source_titles"],
        "polity_source_urls": group["polity_source_urls"],
        "polity_source_raw": group["polity_source_raw"],
        "confidence_score": group["confidence_score"],
        "confidence_note": group["confidence_note"],
        "calendar_system_note": group["calendar_system_note"],
    }
    row.update({field: ruler.get(field, "") for field in [
        "ruler_name",
        "ruler_title",
        "ruler_temple_name",
        "ruler_posthumous_name",
        "ruler_personal_name",
        "ruler_reign_start_year",
        "ruler_reign_start_label",
        "ruler_reign_end_year",
        "ruler_reign_end_label",
        "ruler_reign_raw",
        "ruler_reign_precision",
        "era_names",
        "ruler_source_title",
        "ruler_source_url",
        "ruler_source_section",
        "ruler_confidence_score",
        "ruler_confidence_note",
    ]})
    return row


def build_unresolved(groups: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    issue_id = 1

    def add(issue_type: str, group: dict[str, Any], field_name: str, selected: str, alternatives: str, note: str, action: str) -> None:
        nonlocal issue_id
        out.append(
            {
                "issue_id": f"issue_{issue_id:04d}",
                "issue_type": issue_type,
                "entity_type": "polity",
                "polity_id": group["polity_id"],
                "polity_name": group["polity_name"],
                "field_name": field_name,
                "selected_value": selected,
                "alternative_values": alternatives,
                "source_titles": group["polity_source_titles"],
                "source_urls": group["polity_source_urls"],
                "note": note,
                "action_in_v03": action,
            }
        )
        issue_id += 1

    groups_by_name = {group["polity_name"]: group for group in groups.values()}
    for group in groups.values():
        if not group["polity_start_year"] or not group["polity_end_year"]:
            add(
                "partial_boundary",
                group,
                "polity_start_year/polity_end_year",
                f"{group['polity_start_year']}..{group['polity_end_year']}",
                "",
                "v02 缺少可解析的完整起止年份；v03 不伪造缺失边界，只保留 v02 已有年度范围。",
                "yearly table generated from existing v02 actual years for this polity",
            )

        contexts = group["merged_from_v02_contexts"].split(" | ") if group["merged_from_v02_contexts"] else []
        if len(contexts) > 1:
            add(
                "merged_v02_contexts",
                group,
                "polity_name/dynasty_name",
                f"{group['macro_period']}/{group['dynasty_name']}/{group['polity_name']}",
                " | ".join(contexts),
                "v02 中存在简繁、异体或泛称/专称重复上下文；v03 合并为一个 polity_id。",
                "merged into one polity master record and regenerated yearly rows once",
            )

    chronology_notes = {
        "后燕": ("polity_end_year", "407", "409", "v02 采用 407 年高云即位建北燕为终点；部分纪年表列 409 年。"),
        "清朝": ("polity_end_year", "1912", "1911", "v03 沿用《清帝逊位诏书》公历 1912-02-12 为终点；部分简表按宣统三年/1911 口径列示。"),
        "元朝": ("polity_start_year", "1271", "1206", "v03 采用大元国号/中原王朝口径；部分资料从 1206 年蒙古建国起算。"),
        "后晋": ("polity_end_year", "947", "946", "后晋灭亡可按契丹入汴与出帝降附事件口径出现 946/947 差异；v03 沿用 v02/release_note 口径。"),
        "后汉": ("polity_end_year", "951", "950", "后汉终年可按年表改元或郭威代汉事件出现 950/951 差异；v03 沿用 v02/release_note 口径。"),
        "荆南": ("polity_end_year", "963", "960", "荆南/南平终年在不同年表中有纳土归宋和传统十国表区间差异；v03 沿用 v02/release_note 口径。"),
        "西夏": ("polity_start_year", "1038", "1032", "西夏起点可按称帝建国或前期政权延续口径不同；v03 沿用 v02/release_note 口径。"),
    }
    for name, (field_name, selected, alternatives, note) in chronology_notes.items():
        group = groups_by_name.get(name)
        if group:
            add("chronology_variant", group, field_name, group.get(field_name, selected), alternatives, note, "selected value retained; issue documented")

    return out


def build_validation(groups: dict[str, dict[str, Any]], rulers: list[dict[str, str]], yearly: list[dict[str, str]]) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []

    def add(check_name: str, status: str, checked_count: int, issue_count: int, details: str) -> None:
        checks.append(
            {
                "check_name": check_name,
                "status": status,
                "checked_count": str(checked_count),
                "issue_count": str(issue_count),
                "details": details,
            }
        )

    boundary_issues = []
    for row in yearly:
        year = int_or_none(row["year"])
        start = int_or_none(row["polity_start_year"])
        end = int_or_none(row["polity_end_year"])
        if year is None or start is None or end is None:
            continue
        if year < max(start, SCOPE_START_YEAR) or year > min(end, SCOPE_END_YEAR):
            boundary_issues.append(f"{row['row_id']}:{row['polity_name']}:{year} not in {start}..{end}")
    add("year_within_polity_range", "PASS" if not boundary_issues else "FAIL", len(yearly), len(boundary_issues), "; ".join(boundary_issues[:20]))

    completeness_issues = []
    yearly_years_by_polity: dict[str, set[int]] = defaultdict(set)
    for row in yearly:
        year = int_or_none(row["year"])
        if year is not None:
            yearly_years_by_polity[row["polity_id"]].add(year)
    for group in groups.values():
        start = int_or_none(group["polity_start_year"])
        end = int_or_none(group["polity_end_year"])
        if start is None or end is None:
            continue
        expected = set(iter_years(start, end))
        missing = sorted(expected - yearly_years_by_polity[group["polity_id"]])
        if missing:
            completeness_issues.append(f"{group['polity_name']} missing {missing[0]}..{missing[-1]} ({len(missing)})")
    add("polity_year_completeness", "PASS" if not completeness_issues else "FAIL", len(groups), len(completeness_issues), "; ".join(completeness_issues[:20]))

    partial = [group["polity_name"] for group in groups.values() if not group["polity_start_year"] or not group["polity_end_year"]]
    add("partial_polity_boundaries", "WARN" if partial else "PASS", len(groups), len(partial), "; ".join(partial))

    row_ids = [row["row_id"] for row in yearly]
    add("duplicate_row_id", "PASS" if len(row_ids) == len(set(row_ids)) else "FAIL", len(row_ids), len(row_ids) - len(set(row_ids)), "")

    polity_ids = {group["polity_id"] for group in groups.values()}
    bad_join = [row["row_id"] for row in yearly if row["polity_id"] not in polity_ids]
    add("yearly_polity_id_join", "PASS" if not bad_join else "FAIL", len(yearly), len(bad_join), ",".join(bad_join[:20]))

    ruler_ids = {ruler["ruler_id"] for ruler in rulers}
    bad_ruler_join = [row["row_id"] for row in yearly if row["ruler_id"] and row["ruler_id"] not in ruler_ids]
    add("yearly_ruler_id_join", "PASS" if not bad_ruler_join else "FAIL", len(yearly), len(bad_ruler_join), ",".join(bad_ruler_join[:20]))

    years = [int(row["year"]) for row in yearly]
    sort_ok = all(a <= b for a, b in zip(years, years[1:]))
    add("year_sort_order", "PASS" if sort_ok else "FAIL", len(years), 0 if sort_ok else 1, "")

    year_zero = [row["row_id"] for row in yearly if row["year"] == "0"]
    add("no_year_zero", "PASS" if not year_zero else "FAIL", len(yearly), len(year_zero), ",".join(year_zero[:20]))

    empty_sources = [group["polity_name"] for group in groups.values() if not group["polity_source_titles"] or not group["polity_source_raw"]]
    add("polity_sources_present", "PASS" if not empty_sources else "WARN", len(groups), len(empty_sources), "; ".join(empty_sources[:30]))

    return checks


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_readme(path: Path, stats: dict[str, int]) -> None:
    path.write_text(
        f"""# 中国历代政权年度数据 v03

本目录是 v03 规范化数据集。v03 的原则是：先维护“政权级事实源”和“君主级事实源”，再从这两张标准表自动生成年度展开主表，避免 v02 中出现的“起止年份已校正，但年度行没有同步删除或补齐”的问题。

## 文件一览

### 1. `chinese_history_polities_master_v03.csv`

政权级标准表。每个政权一个 `polity_id`，记录政权名称、异名、起止年份、版图字段、都城、族属、创建者、灭亡/继承关系、史料出处、置信度、以及从 v02 合并来的上下文。

适合用来回答：

- 某个国家或政权到底从哪一年到哪一年？
- 这个起止年份依据是什么？
- 这个政权有哪些异名或简繁写法？
- 历史地理与现代行政区怎么对应？

### 2. `chinese_history_rulers_master_v03.csv`

君主级标准表。每个君主一个 `ruler_id`，通过 `polity_id` 关联到政权，记录君主名称、庙号、谥号、本名、实际统治起止年、年号、出处和置信度。

适合用来回答：

- 某个政权有哪些君主？
- 某位君主实际统治年份是多少？
- 该君主信息来自哪个来源？

### 3. `chinese_history_polities_yearly_v03.csv`

年度展开主表，也是地图、时间轴、年度查询最应该使用的表。它由政权标准表和君主标准表重新生成，不再直接继承 v02 的旧年度行。

查看方法：

- 查某一年有哪些政权：筛选 `year`。
- 查某个政权完整存在期：筛选 `polity_id` 或 `polity_name`。
- 查某年某国的君主：筛选 `year` + `polity_id`，再看 `ruler_name`。
- `row_granularity = year_polity_ruler` 表示该年匹配到君主。
- `row_granularity = year_polity_unmatched_ruler` 表示该政权这一年存在，但暂未匹配到可解析君主年表；君主字段留空，不代表国家不存在。

### 4. `chinese_history_unresolved_or_disputed_v03.csv`

争议、未定与口径说明表。这里记录不能强行伪造成确定事实的内容，例如：

- 起止年份缺失或只能部分确定。
- v02 中被合并的简繁/异体/重复上下文。
- 后燕、清朝、元朝、西夏等存在不同纪年口径的记录。

查看方法：当你在主表里看到某个年份或政权和其他资料不一致，先到这张表按 `polity_id` 或 `polity_name` 查原因。

### 5. `chinese_history_validation_report_v03.csv`

生成后的质量检查表。它不是历史资料，而是数据工程质检结果。

重点看：

- `year_within_polity_range`: 每一行 `year` 是否都在政权起止范围内。
- `polity_year_completeness`: 每个可解析起止范围的政权，存在期内是否每一年都有至少一行。
- `partial_polity_boundaries`: 哪些政权仍缺少完整起止年份。
- `yearly_polity_id_join` / `yearly_ruler_id_join`: 主表能否正确关联回标准表。

只要 `FAIL` 为 0，说明年度展开结构是干净的；`WARN` 表示需要人工保留说明，但不是生成失败。

## 本次生成规模

- 政权标准项：{stats['polities']} 条
- 君主标准项：{stats['rulers']} 条
- 年度主表行：{stats['yearly']} 行
- 争议/未定说明：{stats['unresolved']} 条
- 校验项：{stats['validation']} 条

## 与 v02 的关系

v02 是人工校正后的大表，但它把政权元数据重复复制到大量年度行里，所以容易出现局部更新后年度行不同步的问题。v03 把 v02 拆成标准表，再重新生成年度主表。

因此，v03 的行数、`row_id` 和部分重复政权的显示方式会和 v02 不同。这是预期变化。需要跨表关联时，请优先使用 `polity_id` 和 `ruler_id`，不要依赖行号。
""",
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_v02()
    groups = build_polity_groups(rows)
    rulers = build_rulers(groups)
    yearly = build_yearly(groups, rulers)
    unresolved = build_unresolved(groups)
    validation = build_validation(groups, rulers, yearly)

    polity_fields = [
        "polity_id",
        "macro_period",
        "dynasty_name",
        "polity_name",
        "polity_aliases",
        "polity_type",
        "polity_start_year",
        "polity_start_label",
        "polity_end_year",
        "polity_end_label",
        "polity_date_raw",
        "polity_date_precision",
        "historical_geography_raw",
        "modern_admin_units_raw",
        "capital_historical",
        "capital_modern",
        "ruling_family_or_clan",
        "ethnicity_or_group",
        "founder",
        "last_ruler",
        "destroyed_by_or_successor",
        "polity_source_titles",
        "polity_source_urls",
        "polity_source_raw",
        "confidence_score",
        "confidence_note",
        "calendar_system_note",
        "v02_row_count",
        "v02_actual_min_year",
        "v02_actual_max_year",
        "v02_actual_years",
        "merged_from_v02_contexts",
    ]
    ruler_fields = [
        "ruler_id",
        "polity_id",
        "polity_name",
        "ruler_name",
        "ruler_title",
        "ruler_temple_name",
        "ruler_posthumous_name",
        "ruler_personal_name",
        "ruler_reign_start_year",
        "ruler_reign_start_label",
        "ruler_reign_end_year",
        "ruler_reign_end_label",
        "ruler_reign_raw",
        "ruler_reign_precision",
        "era_names",
        "ruler_source_title",
        "ruler_source_url",
        "ruler_source_section",
        "ruler_confidence_score",
        "ruler_confidence_note",
        "merged_from_v02_rows",
    ]
    yearly_fields = ["row_id", "polity_id", "ruler_id"] + [field for field in YEARLY_V02_FIELDS if field != "row_id"]
    unresolved_fields = [
        "issue_id",
        "issue_type",
        "entity_type",
        "polity_id",
        "polity_name",
        "field_name",
        "selected_value",
        "alternative_values",
        "source_titles",
        "source_urls",
        "note",
        "action_in_v03",
    ]
    validation_fields = ["check_name", "status", "checked_count", "issue_count", "details"]

    polities = sorted(groups.values(), key=lambda group: (int_or_none(group["polity_start_year"]) if int_or_none(group["polity_start_year"]) is not None else 999999, group["polity_name"]))
    write_csv(OUT_DIR / "chinese_history_polities_master_v03.csv", polities, polity_fields)
    write_csv(OUT_DIR / "chinese_history_rulers_master_v03.csv", rulers, ruler_fields)
    write_csv(OUT_DIR / "chinese_history_polities_yearly_v03.csv", yearly, yearly_fields)
    write_csv(OUT_DIR / "chinese_history_unresolved_or_disputed_v03.csv", unresolved, unresolved_fields)
    write_csv(OUT_DIR / "chinese_history_validation_report_v03.csv", validation, validation_fields)

    write_readme(
        OUT_DIR / "README.md",
        {
            "polities": len(polities),
            "rulers": len(rulers),
            "yearly": len(yearly),
            "unresolved": len(unresolved),
            "validation": len(validation),
        },
    )

    print(f"v03 generated in {OUT_DIR}")
    print(f"polities={len(polities)} rulers={len(rulers)} yearly_rows={len(yearly)} unresolved={len(unresolved)} validation_checks={len(validation)}")


if __name__ == "__main__":
    main()
