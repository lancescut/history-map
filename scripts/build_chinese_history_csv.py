#!/usr/bin/env python3
"""Build a source-grounded yearly China historical polity CSV.

The output is intentionally conservative. Fields that cannot be supported by
the parsed sources are left blank, and raw source text is carried alongside
parsed years so downstream users can audit uncertain cases.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import urllib3
from bs4 import BeautifulSoup


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = ROOT / "input" / "chinese_history_polities_yearly.csv"
UNRESOLVED_CSV = ROOT / "input" / "chinese_history_polities_unresolved_metadata.csv"
SCOPE_START_YEAR = -1046
SCOPE_END_YEAR = 1912

HEADERS = {"User-Agent": "Mozilla/5.0 history-map research bot; source-audited CSV build"}

SOURCES = {
    "china_dynasties_wiki": {
        "title": "中国朝代 - 维基百科",
        "url": "https://zh.wikipedia.org/wiki/%E4%B8%AD%E5%9B%BD%E6%9C%9D%E4%BB%A3",
        "confidence": 72,
    },
    "zhou_states_wiki": {
        "title": "周代诸侯国列表 - 维基百科",
        "url": "https://zh.wikipedia.org/wiki/%E5%91%A8%E4%BB%A3%E8%AB%B8%E4%BE%AF%E5%9C%8B%E5%88%97%E8%A1%A8",
        "confidence": 55,
    },
    "zhou_rulers_wiki": {
        "title": "周朝君主列表 - 维基百科",
        "url": "https://zh.wikipedia.org/wiki/%E5%91%A8%E6%9C%9D%E5%90%9B%E4%B8%BB%E5%88%97%E8%A1%A8",
        "confidence": 70,
    },
    "zhou_vassal_rulers_wiki": {
        "title": "周朝诸侯国君主列表 - 维基百科",
        "url": "https://zh.wikipedia.org/wiki/%E5%91%A8%E6%9C%9D%E8%AB%B8%E4%BE%AF%E5%9C%8B%E5%90%9B%E4%B8%BB%E5%88%97%E8%A1%A8",
        "confidence": 45,
    },
    "moe_emperors": {
        "title": "教育部《重编国语辞典修订本》中国历代帝王年表",
        "url": "https://dict.revised.moe.edu.tw/appendix.jsp?ID=2&la=0&page={page}&powerMode=0",
        "confidence": 86,
    },
    "five_hu_wiki": {
        "title": "五胡十六国 - 维基百科",
        "url": "https://zh.wikipedia.org/wiki/%E4%BA%94%E8%83%A1%E5%8D%81%E5%85%AD%E5%9B%BD",
        "confidence": 70,
    },
    "five_hu_rulers_wiki": {
        "title": "五胡十六国君主列表 - 维基百科",
        "url": "https://zh.wikipedia.org/wiki/%E4%BA%94%E8%83%A1%E5%8D%81%E5%85%AD%E5%9B%BD%E5%90%9B%E4%B8%BB%E5%88%97%E8%A1%A8",
        "confidence": 65,
    },
    "five_dynasties_wiki": {
        "title": "五代十国 - 维基百科",
        "url": "https://zh.wikipedia.org/wiki/%E4%BA%94%E4%BB%A3%E5%8D%81%E5%9B%BD",
        "confidence": 70,
    },
    "five_dynasties_rulers_wiki": {
        "title": "五代十国君主列表 - 维基百科",
        "url": "https://zh.wikipedia.org/wiki/%E4%BA%94%E4%BB%A3%E5%8D%81%E5%9B%BD%E5%90%9B%E4%B8%BB%E5%88%97%E8%A1%A8",
        "confidence": 65,
    },
    "northern_southern_wiki": {
        "title": "南北朝 - 维基百科",
        "url": "https://zh.wikipedia.org/wiki/%E5%8D%97%E5%8C%97%E6%9C%9D",
        "confidence": 70,
    },
    "northern_southern_rulers_wiki": {
        "title": "南北朝君主列表 - 维基百科",
        "url": "https://zh.wikipedia.org/wiki/%E5%8D%97%E5%8C%97%E6%9C%9D%E5%90%9B%E4%B8%BB%E5%88%97%E8%A1%A8",
        "confidence": 65,
    },
    "three_kingdoms_wiki": {
        "title": "三国 - 维基百科",
        "url": "https://zh.wikipedia.org/wiki/%E4%B8%89%E5%9B%BD",
        "confidence": 70,
    },
    "cbdb_dynasties": {
        "title": "CBDB DYNASTIES code table",
        "url": "https://input.cbdb.fas.harvard.edu/codes/DYNASTIES",
        "confidence": 88,
    },
    "chgis": {
        "title": "China Historical GIS, Harvard Center for Geographic Analysis",
        "url": "https://gis.harvard.edu/china-historical-gis",
        "confidence": 90,
    },
}

TRAD_TO_COMMON = str.maketrans(
    {
        "國": "国",
        "齊": "齐",
        "漢": "汉",
        "趙": "赵",
        "後": "后",
        "涼": "凉",
        "遼": "辽",
        "晉": "晋",
        "陳": "陈",
        "吳": "吴",
        "東": "东",
        "閩": "闽",
        "荊": "荆",
        "馬": "马",
        "劉": "刘",
        "蕭": "萧",
        "魏": "魏",
        "週": "周",
        "寶": "宝",
        "顯": "显",
        "統": "统",
        "謚": "谥",
        "諡": "谥",
        "廟": "庙",
        "諱": "讳",
        "稱": "称",
        "領": "领",
        "嶺": "岭",
        "長": "长",
        "廣": "广",
        "臺": "台",
        "臺": "台",
    }
)

AGGREGATE_NAMES = {
    "周朝",
    "汉朝",
    "三国",
    "晋朝",
    "十六国",
    "北朝",
    "南朝",
    "五代",
    "十国",
    "宋朝",
}

MOE_POLITY_MAP = {
    ("周", "東周"): "東周",
    ("秦", "秦"): "秦朝",
    ("漢", "西漢"): "西漢",
    ("漢", "新"): "新朝",
    ("漢", "東漢"): "東漢",
    ("三國", "魏"): "曹魏",
    ("三國", "蜀"): "蜀漢",
    ("三國", "吳"): "東吳",
    ("晉", "西晉"): "西晉",
    ("晉", "東晉"): "東晉",
    ("南北朝", "宋"): "劉宋",
    ("南北朝", "齊"): "南齊",
    ("南北朝", "梁"): "梁朝",
    ("南北朝", "陳"): "陳朝",
    ("南北朝", "北魏"): "北魏",
    ("南北朝", "東魏"): "東魏",
    ("南北朝", "西魏"): "西魏",
    ("南北朝", "北齊"): "北齊",
    ("南北朝", "北周"): "北周",
    ("隋", "隋"): "隋朝",
    ("唐", "唐"): "唐朝",
    ("五代", "後梁"): "後梁",
    ("五代", "後唐"): "後唐",
    ("五代", "後晉"): "後晉",
    ("五代", "後漢"): "後漢",
    ("五代", "後周"): "後周",
    ("宋", "北宋"): "北宋",
    ("宋", "南宋"): "南宋",
    ("遼", "遼"): "遼朝",
    ("金", "金"): "金朝",
    ("元", "元"): "元朝",
    ("西夏", "西夏"): "西夏",
    ("明", "明"): "明朝",
    ("清", "清"): "清朝",
}

ALIAS_CANONICAL = {
    "辽": "辽朝",
    "遼": "遼朝",
    "金": "金朝",
    "元": "元朝",
    "明": "明朝",
    "清": "清朝",
    "蕭梁": "梁朝",
    "萧梁": "梁朝",
    "南陳": "陳朝",
    "南陈": "陈朝",
    "劉宋": "劉宋",
    "刘宋": "劉宋",
    "南齊": "南齊",
    "南齐": "南齊",
    "楊吳": "楊吳",
    "杨吴": "楊吳",
    "吳": "楊吳",
    "吴": "楊吳",
    "楚": "馬楚",
    "马楚": "馬楚",
    "漢趙": "漢趙",
    "汉赵": "漢趙",
    "胡夏": "胡夏",
    "夏": "胡夏",
    "代": "代國",
}


def fetch(url: str, verify: bool = True) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30, verify=verify)
    response.raise_for_status()
    return response.text


def clean_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value)
    text = re.sub(r"\[[^\]]*?\]", "", text)
    text = re.sub(r"【[^】]*?】", "", text)
    text = text.replace("\xa0", " ").replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_notes(value: str) -> str:
    text = clean_text(value)
    text = re.sub(r"\s*\(.*?\)\s*", "", text)
    text = re.sub(r"\s*（.*?）\s*", "", text)
    return text.strip()


def common_key(value: str) -> str:
    text = clean_text(value).translate(TRAD_TO_COMMON)
    text = re.sub(r"[\s·・,，、／/()（）\[\]［］「」『』《》<>〈〉\-—－:：;；]", "", text)
    text = re.sub(r"\d+年.*$", "", text)
    text = text.replace("史称", "")
    return text


def canonical_display_name(name: str) -> str:
    raw = clean_text(name)
    if not raw:
        return ""
    if "史称西周" in raw:
        return "西周"
    if "史称东周" in raw or "史称東周" in raw:
        return "東周"
    if "初稱唐" in raw or "初称唐" in raw:
        return "晉國"
    raw = re.split(r"[（(]", raw)[0].strip()
    raw = raw.replace(" ", "")
    return ALIAS_CANONICAL.get(raw, raw)


def canon_key(name: str) -> str:
    display = canonical_display_name(name)
    display = ALIAS_CANONICAL.get(display, display)
    return common_key(display)


def date_precision(raw: str) -> str:
    text = clean_text(raw)
    if not text:
        return ""
    markers = ["约", "約", "？", "或", "世纪", "世紀", "时期", "時期", "商代", "周代", "春秋", "战国", "戰國", "不详", "不詳"]
    return "approx_or_uncertain" if any(m in text for m in markers) else "year"


def extract_years(raw: str) -> list[int]:
    text = clean_text(raw)
    if not text:
        return []
    text = text.replace("B.C.", "前")
    years: list[int] = []
    for m in re.finditer(r"(公元前|前)\s*(\d{1,4})(?!\d)(?!\s*(?:世纪|世紀))\s*年?", text):
        years.append(-int(m.group(2)))
    masked = re.sub(r"(公元前|前)\s*\d{1,4}\s*年?", " ", text)
    for m in re.finditer(r"(?:公元)?\s*(\d{1,4})\s*年", masked):
        years.append(int(m.group(1)))
    if not years:
        compact = re.findall(r"\d{3,4}", text)
        if len(compact) >= 2:
            years.extend([int(compact[0]), int(compact[1])])
    return years


def parse_range(raw: str) -> tuple[int | None, int | None, str]:
    years = extract_years(raw)
    if len(years) >= 2:
        return years[0], years[1], date_precision(raw)
    if len(years) == 1:
        if re.search(r"^[^－—\-~～至]*[－—\-~～至]", clean_text(raw)):
            return None, years[0], "partial"
        return years[0], None, "partial"
    return None, None, ""


def year_label(year: int | None) -> str:
    if year is None:
        return ""
    return f"前{abs(year)}年" if year < 0 else f"{year}年"


def iter_years(start: int | None, end: int | None) -> list[int]:
    if start is None or end is None:
        return []
    if start > end:
        start, end = end, start
    return [y for y in range(start, end + 1) if y != 0]


def iter_scope_years(start: int | None, end: int | None) -> list[int]:
    if start is None or end is None:
        return []
    return iter_years(max(start, SCOPE_START_YEAR), min(end, SCOPE_END_YEAR))


def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            "|".join(clean_text(part) for part in col if clean_text(part) and not str(part).startswith("Unnamed"))
            for col in df.columns
        ]
    else:
        df.columns = [clean_text(col) for col in df.columns]
    return df


def row_get(row: pd.Series, candidates: list[str]) -> str:
    for wanted in candidates:
        for col in row.index:
            if wanted in str(col):
                value = clean_text(row[col])
                if value:
                    return value
    return ""


def macro_for(name: str, start: int | None = None) -> str:
    key = common_key(name)
    if key in {"西周", "东周"} or key.endswith("国") and start is not None and start < -221:
        return "周"
    if key in {"秦朝", "西汉", "新朝", "东汉"}:
        return "秦汉"
    if key in {"曹魏", "蜀汉", "东吴"}:
        return "三国"
    if key in {"西晋", "东晋"}:
        return "两晋"
    if start is not None and 304 <= start <= 589:
        return "魏晋南北朝"
    if key in {"隋朝", "唐朝", "武周"}:
        return "隋唐"
    if key in {"后梁", "后唐", "后晋", "后汉", "后周", "杨吴", "前蜀", "吴越", "闽", "南汉", "荆南", "后蜀", "南唐", "北汉", "马楚"}:
        return "五代十国"
    if key in {"北宋", "南宋", "辽朝", "西辽", "西夏", "金朝"}:
        return "宋辽金夏"
    if key in {"元朝", "北元", "明朝", "南明", "后金", "清朝"}:
        return "元明清"
    if start is not None and 907 <= start <= 979:
        return "五代十国"
    return ""


def dynasty_for(name: str, start: int | None = None) -> str:
    key = common_key(name)
    if key.endswith("国") and start is not None and start < -221:
        return "周代诸侯国"
    if key in {"西周", "东周"}:
        return "周朝"
    if key in {"曹魏", "蜀汉", "东吴"}:
        return "三国"
    if start is not None and 304 <= start <= 439 and key not in {"东晋"}:
        return "五胡十六国"
    if key in {"刘宋", "南齐", "梁朝", "西梁", "陈朝", "北魏", "东魏", "西魏", "北齐", "北周"}:
        return "南北朝"
    if key in {"后梁", "后唐", "后晋", "后汉", "后周", "杨吴", "前蜀", "吴越", "闽", "南汉", "荆南", "后蜀", "南唐", "北汉", "马楚"}:
        return "五代十国"
    if key in {"北宋", "南宋", "辽朝", "西辽", "西夏", "金朝"}:
        return "宋辽金夏"
    if key in {"元朝", "北元", "明朝", "南明", "后金", "清朝"}:
        return "元明清"
    if start is not None and 907 <= start <= 979:
        return "五代十国"
    return name


SOURCE_CONTEXT = {
    "zhou_vassal_rulers_wiki": ("周", "周代诸侯国"),
    "five_hu_rulers_wiki": ("魏晋南北朝", "五胡十六国"),
    "five_dynasties_rulers_wiki": ("五代十国", "五代十国"),
    "northern_southern_rulers_wiki": ("魏晋南北朝", "南北朝"),
}


def contextual_polity_key(
    name: str,
    *,
    macro_period: str = "",
    dynasty_name: str = "",
    start_year: int | None = None,
    source_key: str = "",
) -> str:
    display = canonical_display_name(name)
    source_macro, source_dynasty = SOURCE_CONTEXT.get(source_key, ("", ""))
    effective_dynasty = dynasty_name or source_dynasty or dynasty_for(display, start_year)
    effective_macro = macro_period or source_macro or macro_for(display, start_year)
    context = common_key(effective_dynasty or effective_macro or "未分组")
    return f"{context}::{canon_key(display)}"


@dataclass
class Polity:
    key: str
    name: str
    aliases: set[str] = field(default_factory=set)
    macro_period: str = ""
    dynasty_name: str = ""
    polity_type: str = ""
    start_year: int | None = None
    end_year: int | None = None
    date_raw: set[str] = field(default_factory=set)
    date_precision: set[str] = field(default_factory=set)
    historical_geography: set[str] = field(default_factory=set)
    modern_admin_units: set[str] = field(default_factory=set)
    capital_historical: set[str] = field(default_factory=set)
    capital_modern: set[str] = field(default_factory=set)
    ruling_family: set[str] = field(default_factory=set)
    ethnicity: set[str] = field(default_factory=set)
    founder: set[str] = field(default_factory=set)
    last_ruler: set[str] = field(default_factory=set)
    destroyer: set[str] = field(default_factory=set)
    source_titles: set[str] = field(default_factory=set)
    source_urls: set[str] = field(default_factory=set)
    source_raw: set[str] = field(default_factory=set)
    confidence_scores: list[int] = field(default_factory=list)
    confidence_notes: set[str] = field(default_factory=set)


@dataclass
class Ruler:
    polity_key: str
    polity_name: str
    ruler_name: str
    ruler_title: str = ""
    temple_name: str = ""
    posthumous_name: str = ""
    personal_name: str = ""
    reign_start_year: int | None = None
    reign_end_year: int | None = None
    reign_raw: str = ""
    reign_precision: str = ""
    era_names: str = ""
    source_title: str = ""
    source_url: str = ""
    source_section: str = ""
    confidence_score: int = 0
    confidence_note: str = ""


polities: dict[str, Polity] = {}
rulers: list[Ruler] = []


def add_polity(
    name: str,
    source_key: str,
    *,
    aliases: str = "",
    macro_period: str = "",
    dynasty_name: str = "",
    polity_type: str = "",
    start_year: int | None = None,
    end_year: int | None = None,
    date_raw: str = "",
    precision: str = "",
    historical_geography: str = "",
    modern_admin_units: str = "",
    capital_historical: str = "",
    capital_modern: str = "",
    ruling_family: str = "",
    ethnicity: str = "",
    founder: str = "",
    last_ruler: str = "",
    destroyer: str = "",
    source_raw: str = "",
    confidence_note: str = "",
) -> str:
    display = canonical_display_name(name)
    if not display:
        return ""
    source_macro, source_dynasty = SOURCE_CONTEXT.get(source_key, ("", ""))
    effective_macro = macro_period or source_macro or macro_for(display, start_year)
    effective_dynasty = dynasty_name or source_dynasty or dynasty_for(display, start_year)
    key = contextual_polity_key(
        display,
        macro_period=effective_macro,
        dynasty_name=effective_dynasty,
        start_year=start_year,
        source_key=source_key,
    )
    source = SOURCES[source_key]
    if key not in polities:
        polities[key] = Polity(
            key=key,
            name=display,
            macro_period=effective_macro,
            dynasty_name=effective_dynasty,
            polity_type=polity_type,
        )
    item = polities[key]
    if item.name != display:
        item.aliases.add(display)
    if aliases and aliases != display:
        item.aliases.add(clean_text(aliases))
    if effective_macro and not item.macro_period:
        item.macro_period = effective_macro
    if effective_dynasty and not item.dynasty_name:
        item.dynasty_name = effective_dynasty
    if polity_type and not item.polity_type:
        item.polity_type = polity_type
    if start_year is not None:
        item.start_year = start_year if item.start_year is None else min(item.start_year, start_year)
    if end_year is not None:
        item.end_year = end_year if item.end_year is None else max(item.end_year, end_year)
    for attr, value in [
        ("date_raw", date_raw),
        ("date_precision", precision),
        ("historical_geography", historical_geography),
        ("modern_admin_units", modern_admin_units),
        ("capital_historical", capital_historical),
        ("capital_modern", capital_modern),
        ("ruling_family", ruling_family),
        ("ethnicity", ethnicity),
        ("founder", founder),
        ("last_ruler", last_ruler),
        ("destroyer", destroyer),
        ("source_raw", source_raw),
        ("confidence_notes", confidence_note),
    ]:
        if value:
            getattr(item, attr).add(clean_text(value))
    item.source_titles.add(source["title"])
    item.source_urls.add(source["url"].format(page="*"))
    item.confidence_scores.append(int(source["confidence"]))
    return key


def add_ruler(
    polity_name: str,
    source_key: str,
    *,
    ruler_name: str,
    macro_period: str = "",
    dynasty_name: str = "",
    ruler_title: str = "",
    temple_name: str = "",
    posthumous_name: str = "",
    personal_name: str = "",
    reign_raw: str = "",
    era_names: str = "",
    section: str = "",
    confidence_note: str = "",
) -> None:
    ruler_name = clean_text(ruler_name)
    if not ruler_name or "失考" in ruler_name or ruler_name in {"—", "-", "nan"}:
        return
    start, end, precision = parse_range(reign_raw)
    if start is None or end is None:
        return
    default_macro, default_dynasty = SOURCE_CONTEXT.get(source_key, ("", ""))
    source_macro = macro_period or default_macro
    source_dynasty = dynasty_name or default_dynasty
    polity_exists = (
        contextual_polity_key(
            polity_name,
            macro_period=source_macro,
            dynasty_name=source_dynasty,
            start_year=start,
            source_key=source_key,
        )
        in polities
    )
    source = SOURCES[source_key]
    key = add_polity(
        polity_name,
        source_key,
        macro_period=source_macro,
        dynasty_name=source_dynasty,
        polity_type="政权/国家",
        start_year=None if polity_exists else start,
        end_year=None if polity_exists else end,
        date_raw="",
        precision="",
        confidence_note="国家起止由君主在位上下限临时补足，需用政权表复核" if not polity_exists else "",
    )
    rulers.append(
        Ruler(
            polity_key=key,
            polity_name=canonical_display_name(polity_name),
            ruler_name=ruler_name,
            ruler_title=clean_text(ruler_title),
            temple_name=clean_text(temple_name),
            posthumous_name=clean_text(posthumous_name),
            personal_name=clean_text(personal_name),
            reign_start_year=start,
            reign_end_year=end,
            reign_raw=clean_text(reign_raw),
            reign_precision=precision,
            era_names=clean_text(era_names),
            source_title=source["title"],
            source_url=source["url"].format(page="*"),
            source_section=clean_text(section),
            confidence_score=int(source["confidence"]),
            confidence_note=confidence_note,
        )
    )


def load_main_dynasties() -> None:
    aggregate_keys = {common_key(name) for name in AGGREGATE_NAMES}
    html = fetch(SOURCES["china_dynasties_wiki"]["url"])
    tables = pd.read_html(StringIO(html))
    df = flatten_columns(tables[5])
    for _, row in df.iterrows():
        name = strip_notes(row_get(row, ["朝代"]))
        if not name or common_key(name) in {"夏朝", "商朝"} or common_key(name) in aggregate_keys:
            continue
        start_raw = row_get(row, ["建立"])
        end_raw = row_get(row, ["滅亡", "灭亡"])
        start_years = extract_years(start_raw)
        end_years = extract_years(end_raw)
        start = start_years[0] if start_years else None
        end = end_years[0] if end_years else None
        raw = f"建立:{start_raw}; 滅亡:{end_raw}"
        add_polity(
            name,
            "china_dynasties_wiki",
            macro_period=macro_for(name, start),
            dynasty_name=dynasty_for(name, start),
            polity_type="王朝/政权",
            start_year=start,
            end_year=end,
            date_raw=raw,
            precision=date_precision(raw),
            ruling_family=row_get(row, ["國姓", "国姓"]),
            ethnicity=row_get(row, ["民族"]),
            founder=row_get(row, ["起始之君"]),
            last_ruler=row_get(row, ["亡國之君", "亡国之君"]),
            source_raw=raw,
        )


def load_zhou_state_metadata() -> None:
    html = fetch(SOURCES["zhou_states_wiki"]["url"])
    for df in pd.read_html(StringIO(html)):
        df = flatten_columns(df)
        cols = "".join(map(str, df.columns))
        if "國名" not in cols or "起迄年" not in cols:
            continue
        for _, row in df.iterrows():
            raw_name = row_get(row, ["國名", "国名"])
            if not raw_name:
                continue
            date_raw = row_get(row, ["起迄年"])
            start, end, precision = parse_range(date_raw)
            add_polity(
                raw_name,
                "zhou_states_wiki",
                aliases=raw_name,
                macro_period="周",
                dynasty_name="周代诸侯国",
                polity_type="诸侯国/古国",
                start_year=start,
                end_year=end,
                date_raw=date_raw,
                precision=precision,
                modern_admin_units=row_get(row, ["今地"]),
                ruling_family=row_get(row, ["姓氏"]),
                destroyer=row_get(row, ["滅國者", "灭国者"]),
                source_raw=f"國名:{raw_name}; 今地:{row_get(row, ['今地'])}; 起迄年:{date_raw}; 出處:{row_get(row, ['出處', '出处'])}",
                confidence_note="周代诸侯国列表条目本身标注需要补充来源；已保留原始出处字段供复核",
            )


def load_five_hu_metadata() -> None:
    html = fetch(SOURCES["five_hu_wiki"]["url"])
    tables = pd.read_html(StringIO(html))
    for idx in [2, 3]:
        df = flatten_columns(tables[idx])
        for _, row in df.iterrows():
            raw_name = row_get(row, ["國名", "国名"])
            date_raw = row_get(row, ["国祚", "國祚"])
            start, end, precision = parse_range(date_raw)
            add_polity(
                raw_name,
                "five_hu_wiki",
                macro_period="魏晋南北朝",
                dynasty_name="五胡十六国" if idx == 2 else "五胡十六国外政权",
                polity_type="割据政权/国家",
                start_year=start,
                end_year=end,
                date_raw=date_raw,
                precision=precision,
                modern_admin_units=row_get(row, ["领土范围", "領土範圍"]),
                ethnicity=row_get(row, ["民族"]),
                founder=row_get(row, ["首任君主"]),
                last_ruler=row_get(row, ["末任君主"]),
                destroyer=row_get(row, ["亡于"]),
                capital_historical=row_get(row, ["国都", "國都"]),
                source_raw="; ".join([f"{c}:{clean_text(row[c])}" for c in df.columns if clean_text(row[c])]),
            )


def load_five_dynasties_metadata() -> None:
    html = fetch(SOURCES["five_dynasties_wiki"]["url"])
    df = flatten_columns(pd.read_html(StringIO(html))[0])
    blocks = [(0, 7, "五代"), (10, 16, "十国"), (17, 22, "十国")]
    for start_row, end_row, dynasty in blocks:
        labels = [clean_text(df.iloc[r, 0]) for r in range(start_row, end_row + 1)]
        for col in df.columns[1:]:
            values = {labels[i]: clean_text(df.loc[start_row + i, col]) for i in range(len(labels))}
            name = values.get("國家") or values.get("国家")
            if not name:
                continue
            date_raw = f"{values.get('成立', '')}－{values.get('灭亡', '')}"
            start, end, precision = parse_range(date_raw)
            add_polity(
                name,
                "five_dynasties_wiki",
                macro_period="五代十国",
                dynasty_name=dynasty,
                polity_type="王朝/割据政权",
                start_year=start,
                end_year=end,
                date_raw=date_raw,
                precision=precision,
                capital_historical=values.get("首都", ""),
                ruling_family=values.get("國君士族", ""),
                source_raw="; ".join([f"{k}:{v}" for k, v in values.items() if v]),
            )


def load_northern_southern_metadata() -> None:
    html = fetch(SOURCES["northern_southern_wiki"]["url"])
    df = flatten_columns(pd.read_html(StringIO(html))[0])
    blocks = [(0, 6, "北朝"), (9, 15, "南朝")]
    for start_row, end_row, dynasty in blocks:
        labels = [clean_text(df.iloc[r, 0]) for r in range(start_row, end_row + 1)]
        for col in df.columns[1:]:
            values = {labels[i]: clean_text(df.loc[start_row + i, col]) for i in range(len(labels))}
            name = values.get("國家") or values.get("国家")
            if not name:
                continue
            date_raw = f"{values.get('成立', '')}－{values.get('灭亡', values.get('滅亡', ''))}"
            start, end, precision = parse_range(date_raw)
            add_polity(
                name,
                "northern_southern_wiki",
                macro_period="魏晋南北朝",
                dynasty_name="南北朝",
                polity_type="王朝/政权",
                start_year=start,
                end_year=end,
                date_raw=date_raw,
                precision=precision,
                capital_historical=values.get("首都", ""),
                ruling_family=values.get("國君士族", values.get("國君 士族", "")),
                source_raw="; ".join([f"{k}:{v}" for k, v in values.items() if v]),
            )


def load_three_kingdoms_geo() -> None:
    html = fetch(SOURCES["three_kingdoms_wiki"]["url"])
    tables = pd.read_html(StringIO(html))
    df = flatten_columns(tables[0])
    if len(df) >= 3:
        for col in df.columns[1:4]:
            name = clean_text(df.loc[0, col])
            if name:
                add_polity(
                    name,
                    "three_kingdoms_wiki",
                    macro_period="三国",
                    dynasty_name="三国",
                    polity_type="政权/国家",
                    capital_historical=clean_text(df.loc[2, col]),
                    ruling_family=clean_text(df.loc[1, col]),
                    source_raw=f"國家:{name}; 國君士族:{clean_text(df.loc[1, col])}; 首都:{clean_text(df.loc[2, col])}",
                )
    df2 = flatten_columns(tables[2])
    force_map = {"曹操": "曹魏", "刘备": "蜀漢", "孙权": "東吳"}
    for _, row in df2.iterrows():
        force = row_get(row, ["势力"])
        if force in force_map:
            add_polity(
                force_map[force],
                "three_kingdoms_wiki",
                historical_geography=row_get(row, ["统治州郡"]),
                source_raw=f"东汉末势力:{force}; 统治州郡:{row_get(row, ['统治州郡'])}",
                confidence_note="三国地域字段取自东汉朝廷授予曹孙刘最终官职表，代表建国前后势力范围线索，非精确边界",
            )


def load_zhou_kings() -> None:
    html = fetch(SOURCES["zhou_rulers_wiki"]["url"])
    tables = pd.read_html(StringIO(html))
    west = flatten_columns(tables[2])
    chronology_col = next((c for c in west.columns if "夏商周斷代工程" in c), "")
    for _, row in west.iterrows():
        title = row_get(row, ["諡號", "谥号"])
        if title in {"周文王", ""}:
            continue
        raw = clean_text(row.get(chronology_col, ""))
        add_ruler(
            "西周",
            "zhou_rulers_wiki",
            ruler_name=title,
            ruler_title=title,
            personal_name=row_get(row, ["本名"]),
            reign_raw=raw,
            section="西周君主：夏商周断代工程年表",
            confidence_note="西周共和以前纪年存在学术争议，本字段采用条目中夏商周断代工程列",
        )
    east = flatten_columns(tables[4])
    for _, row in east.iterrows():
        title = row_get(row, ["谥号", "諡號"])
        if not title or "时期君主" in title:
            continue
        add_ruler(
            "東周",
            "zhou_rulers_wiki",
            ruler_name=title,
            ruler_title=title,
            personal_name=row_get(row, ["本名"]),
            reign_raw=row_get(row, ["在位时间"]),
            section="东周君主",
        )


def load_moe_rulers() -> None:
    for page in [1, 2, 3]:
        url = SOURCES["moe_emperors"]["url"].format(page=page)
        html = fetch(url, verify=False)
        soup = BeautifulSoup(html, "html.parser")
        for tr in soup.select("tr"):
            cells = [clean_text(c.get_text(" ", strip=True)) for c in tr.find_all(["td", "th"])]
            if len(cells) != 3 or cells[0] == "年代 朝代":
                continue
            parts = cells[0].split()
            if len(parts) == 1:
                macro, sub = parts[0], parts[0]
            else:
                macro, sub = parts[0], parts[-1]
            if (macro, sub) == ("周", "西周"):
                continue
            polity = MOE_POLITY_MAP.get((macro, sub))
            if not polity:
                continue
            emperor = re.sub(r"[〔［\[](.*?)[〕］\]]", "", cells[1]).strip()
            if (macro, sub) == ("清", "清") and emperor == "太祖":
                add_ruler(
                    "後金",
                    "moe_emperors",
                    ruler_name=emperor,
                    ruler_title=emperor,
                    reign_raw=cells[2],
                    section=f"page={page}; {macro}>{sub}; 后金阶段归并",
                )
                continue
            if (macro, sub) == ("清", "清") and emperor == "太宗":
                add_ruler(
                    "後金",
                    "moe_emperors",
                    ruler_name=emperor,
                    ruler_title=emperor,
                    reign_raw="1626 1636",
                    section=f"page={page}; {macro}>{sub}; 后金阶段拆分",
                    confidence_note="教育部年表列太宗1626-1643；此处按后金至1636、清朝自1636分段展开",
                )
            add_ruler(
                polity,
                "moe_emperors",
                ruler_name=emperor,
                ruler_title=emperor,
                reign_raw=cells[2],
                section=f"page={page}; {macro}>{sub}",
            )


def parse_monarch_page(source_key: str, *, include_sections: set[str] | None = None, base_conf_note: str = "") -> None:
    html = fetch(SOURCES[source_key]["url"])
    soup = BeautifulSoup(html, "html.parser")
    current: list[tuple[int, str]] = []
    for el in soup.select("h2,h3,h4,table"):
        if el.name in {"h2", "h3", "h4"}:
            level = {"h2": 0, "h3": 1, "h4": 2}[el.name]
            text = clean_text(el.get_text(" ", strip=True).replace("[编辑]", ""))
            current = [c for c in current if c[0] < level]
            current.append((level, text))
            continue
        if "wikitable" not in " ".join(el.get("class", [])):
            continue
        try:
            df = flatten_columns(pd.read_html(StringIO(str(el)))[0])
        except Exception:
            continue
        path = [x[1] for x in current]
        if include_sections and not include_sections.intersection(path):
            continue
        if not path:
            continue
        polity = path[-1]
        if polity in {"魏氏領袖", "魏国君主", "魏國君主"} and len(path) >= 2:
            polity = path[-2]
        if polity in {"淝水戰前政權", "淝水戰後政權", "十六國外政權", "五代", "十国", "南朝", "北朝", "其他", "十二诸侯和五霸七雄"}:
            continue
        ruler_macro = ""
        ruler_dynasty = ""
        if source_key == "five_hu_rulers_wiki":
            ruler_macro = "魏晋南北朝"
            ruler_dynasty = "五胡十六国外政权" if "十六國外政權" in path else "五胡十六国"
        section = " > ".join(path)
        for _, row in df.iterrows():
            reign_raw = row_get(row, ["在位时间", "在位時間", "统治时间", "統治時間", "在位年份", "在位時间"])
            if not reign_raw:
                continue
            name = row_get(row, ["名讳", "名諱", "姓名", "國君姓名", "国君姓名", "國君本名", "国君本名", "領袖姓名", "领袖姓名", "名"])
            title = row_get(row, ["称号", "稱號", "国君名号", "國君名號", "諡號", "谥号", "汗號", "尊號", "國君"])
            if not name:
                name = title
            if not name or "年－" in name or "年—" in name:
                continue
            add_ruler(
                polity,
                source_key,
                ruler_name=name,
                macro_period=ruler_macro,
                dynasty_name=ruler_dynasty,
                ruler_title=title,
                temple_name=row_get(row, ["庙号", "廟號"]),
                posthumous_name=row_get(row, ["谥号", "謚號", "諡號"]),
                personal_name=name,
                reign_raw=reign_raw,
                era_names=row_get(row, ["年号", "年號", "年号及使用时间", "年號及使用時間"]),
                section=section,
                confidence_note=base_conf_note,
            )


def dedupe_rulers() -> None:
    best: dict[tuple[str, str, int | None, int | None], Ruler] = {}
    for ruler in rulers:
        key = (ruler.polity_key, common_key(ruler.ruler_name), ruler.reign_start_year, ruler.reign_end_year)
        existing = best.get(key)
        if not existing or ruler.confidence_score > existing.confidence_score:
            best[key] = ruler
        elif existing and ruler.source_url not in existing.source_url:
            existing.source_title += f" | {ruler.source_title}"
            existing.source_url += f" | {ruler.source_url}"
    rulers[:] = list(best.values())


def build_rows() -> list[dict[str, Any]]:
    dedupe_rulers()
    by_polity: dict[str, list[Ruler]] = defaultdict(list)
    for ruler in rulers:
        by_polity[ruler.polity_key].append(ruler)

    rows: list[dict[str, Any]] = []
    row_id = 1
    for key, polity in sorted(polities.items(), key=lambda kv: (kv[1].start_year if kv[1].start_year is not None else 9999, kv[1].name)):
        polity_rulers = sorted(by_polity.get(key, []), key=lambda r: (r.reign_start_year or 9999, r.ruler_name))
        source_titles = " | ".join(sorted(polity.source_titles))
        source_urls = " | ".join(sorted(polity.source_urls))
        source_raw = " || ".join(sorted(polity.source_raw))
        confidence = round(sum(polity.confidence_scores) / len(polity.confidence_scores)) if polity.confidence_scores else 0
        meta = {
            "macro_period": polity.macro_period,
            "dynasty_name": polity.dynasty_name or dynasty_for(polity.name, polity.start_year),
            "polity_name": polity.name,
            "polity_aliases": " | ".join(sorted(polity.aliases)),
            "polity_type": polity.polity_type,
            "polity_start_year": polity.start_year if polity.start_year is not None else "",
            "polity_start_label": year_label(polity.start_year),
            "polity_end_year": polity.end_year if polity.end_year is not None else "",
            "polity_end_label": year_label(polity.end_year),
            "polity_date_raw": " | ".join(sorted(polity.date_raw)),
            "polity_date_precision": " | ".join(sorted(polity.date_precision)),
            "historical_geography_raw": " | ".join(sorted(polity.historical_geography)),
            "modern_admin_units_raw": " | ".join(sorted(polity.modern_admin_units)),
            "capital_historical": " | ".join(sorted(polity.capital_historical)),
            "capital_modern": " | ".join(sorted(polity.capital_modern)),
            "ruling_family_or_clan": " | ".join(sorted(polity.ruling_family)),
            "ethnicity_or_group": " | ".join(sorted(polity.ethnicity)),
            "founder": " | ".join(sorted(polity.founder)),
            "last_ruler": " | ".join(sorted(polity.last_ruler)),
            "destroyed_by_or_successor": " | ".join(sorted(polity.destroyer)),
            "polity_source_titles": source_titles,
            "polity_source_urls": source_urls,
            "polity_source_raw": source_raw,
            "confidence_score": confidence,
            "confidence_note": " | ".join(sorted(polity.confidence_notes)),
            "calendar_system_note": "BCE years are negative integers; there is no year 0; ranges are expanded inclusively when start and end years are parseable.",
        }
        if polity_rulers:
            covered_years: set[int] = set()
            for ruler in polity_rulers:
                clipped_start = ruler.reign_start_year
                clipped_end = ruler.reign_end_year
                if clipped_start is not None and polity.start_year is not None:
                    clipped_start = max(clipped_start, polity.start_year)
                if clipped_end is not None and polity.end_year is not None:
                    clipped_end = min(clipped_end, polity.end_year)
                if clipped_start is not None and clipped_end is not None and clipped_start > clipped_end:
                    continue
                years = iter_scope_years(clipped_start, clipped_end)
                if not years:
                    years = [None]  # type: ignore[list-item]
                for y in years:
                    row = {
                        "row_id": row_id,
                        "row_granularity": "year_polity_ruler" if y is not None else "polity_ruler_metadata",
                        "year": y if y is not None else "",
                        "year_label": year_label(y) if y is not None else "",
                        **meta,
                        "ruler_name": ruler.ruler_name,
                        "ruler_title": ruler.ruler_title,
                        "ruler_temple_name": ruler.temple_name,
                        "ruler_posthumous_name": ruler.posthumous_name,
                        "ruler_personal_name": ruler.personal_name,
                        "ruler_reign_start_year": ruler.reign_start_year if ruler.reign_start_year is not None else "",
                        "ruler_reign_start_label": year_label(ruler.reign_start_year),
                        "ruler_reign_end_year": ruler.reign_end_year if ruler.reign_end_year is not None else "",
                        "ruler_reign_end_label": year_label(ruler.reign_end_year),
                        "ruler_reign_raw": ruler.reign_raw,
                        "ruler_reign_precision": ruler.reign_precision,
                        "era_names": ruler.era_names,
                        "ruler_source_title": ruler.source_title,
                        "ruler_source_url": ruler.source_url,
                        "ruler_source_section": ruler.source_section,
                        "ruler_confidence_score": ruler.confidence_score,
                        "ruler_confidence_note": ruler.confidence_note,
                    }
                    rows.append(row)
                    if y is not None:
                        covered_years.add(y)
                    row_id += 1
            for y in iter_scope_years(polity.start_year, polity.end_year):
                if y in covered_years:
                    continue
                row = {
                    "row_id": row_id,
                    "row_granularity": "year_polity_unmatched_ruler",
                    "year": y,
                    "year_label": year_label(y),
                    **meta,
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
                    "ruler_confidence_note": "该年度在政权存在期内，但未匹配到可解析君主年表；按国家年度行保留",
                }
                rows.append(row)
                row_id += 1
        else:
            years = iter_scope_years(polity.start_year, polity.end_year)
            if not years:
                years = [None]  # type: ignore[list-item]
            for y in years:
                row = {
                    "row_id": row_id,
                    "row_granularity": "year_polity" if y is not None else "polity_metadata",
                    "year": y if y is not None else "",
                    "year_label": year_label(y) if y is not None else "",
                    **meta,
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
                    "ruler_confidence_note": "",
                }
                rows.append(row)
                row_id += 1
    return rows


def main() -> None:
    load_main_dynasties()
    load_zhou_state_metadata()
    load_five_hu_metadata()
    load_five_dynasties_metadata()
    load_northern_southern_metadata()
    load_three_kingdoms_geo()
    load_zhou_kings()
    load_moe_rulers()
    parse_monarch_page("five_hu_rulers_wiki")
    parse_monarch_page("five_dynasties_rulers_wiki")
    parse_monarch_page("northern_southern_rulers_wiki")
    parse_monarch_page(
        "zhou_vassal_rulers_wiki",
        base_conf_note="该条目页面标注没有列出参考或来源；仅保留有可解析在位年份的条目",
    )

    rows = build_rows()
    yearly_rows = [row for row in rows if row["year"] != ""]
    unresolved_rows = [row for row in rows if row["year"] == ""]
    yearly_rows.sort(
        key=lambda row: (
            int(row["year"]),
            row["macro_period"],
            row["dynasty_name"],
            row["polity_name"],
            row["ruler_reign_start_year"] if row["ruler_reign_start_year"] != "" else "9999",
            row["ruler_name"],
        )
    )
    unresolved_rows.sort(
        key=lambda row: (
            row["macro_period"],
            row["dynasty_name"],
            row["polity_name"],
            row["polity_date_raw"],
        )
    )
    for i, row in enumerate(yearly_rows, start=1):
        row["row_id"] = i
    for i, row in enumerate(unresolved_rows, start=1):
        row["row_id"] = i
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(yearly_rows[0].keys()))
        writer.writeheader()
        writer.writerows(yearly_rows)
    if unresolved_rows:
        with UNRESOLVED_CSV.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(unresolved_rows[0].keys()))
            writer.writeheader()
            writer.writerows(unresolved_rows)
    print(
        f"Wrote {len(yearly_rows)} yearly rows, {len(unresolved_rows)} unresolved metadata rows, "
        f"{len(polities)} polities, {len(rulers)} ruler records to {OUT_CSV}"
    )


if __name__ == "__main__":
    main()
