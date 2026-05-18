#!/usr/bin/env python3
"""Append the 1912-1949 Republican-period v03 data slice.

The script is intentionally idempotent: it owns a fixed whitelist of IDs,
removes those rows first, then appends the current researched dataset. This
keeps the v03 CSVs reproducible while preserving unrelated user edits.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "input" / "v03"

MASTER = INPUT / "chinese_history_polities_master_v03.csv"
RULERS_CSV = INPUT / "chinese_history_rulers_master_v03.csv"
YEARLY = INPUT / "chinese_history_polities_yearly_v03.csv"
ISSUES_CSV = INPUT / "chinese_history_unresolved_or_disputed_v03.csv"
CAPITALS_CSV = INPUT / "capital_events_v03.csv"
TERRITORY_OVERRIDES = INPUT / "territory_overrides_v03.csv"

MANAGED_POLITY_IDS = {f"polity_{num:04d}" for num in range(183, 214)}
MANAGED_RULER_IDS = {f"ruler_{num:05d}" for num in range(1120, 1158)}
MANAGED_CAPITAL_IDS = {f"capital_{num:04d}" for num in range(58, 96)}
ISSUE_PREFIX = "issue_republic_"

CALENDAR_NOTE = (
    "BCE years are negative integers; there is no year 0; ranges are expanded "
    "inclusively when start and end years are parseable."
)

SOURCE_PAIRS = {
    "republic": (
        "Encyclopaedia Britannica: Republican China 1911-49|Office of the Historian: The Chinese Revolution of 1949",
        "https://www.britannica.com/place/China/Republican-China-1911-49|https://history.state.gov/milestones/1945-1952/chinese-rev",
    ),
    "civil_war": (
        "Encyclopaedia Britannica: Chinese Civil War|Office of the Historian: The Chinese Revolution of 1949",
        "https://www.britannica.com/event/Chinese-Civil-War|https://history.state.gov/milestones/1945-1952/chinese-rev",
    ),
    "war_japan": (
        "Encyclopaedia Britannica: Second Sino-Japanese War|Office of the Historian: Japan Surrenders and World War II Ends",
        "https://www.britannica.com/event/Second-Sino-Japanese-War|https://history.state.gov/milestones/1937-1945/japan-surrender",
    ),
    "manchukuo": (
        "Encyclopaedia Britannica: Manchukuo|Encyclopaedia Britannica: Mukden Incident",
        "https://www.britannica.com/place/Manchukuo|https://www.britannica.com/event/Mukden-Incident",
    ),
    "treaties": (
        "Avalon Project: Cairo Communique 1943|Avalon Project: Potsdam Declaration 1945",
        "https://avalon.law.yale.edu/wwii/cairo.asp|https://avalon.law.yale.edu/20th_century/decade17.asp",
    ),
    "hongkong": (
        "Encyclopaedia Britannica: Hong Kong History|Office of the Historian: Japan Surrenders and World War II Ends",
        "https://www.britannica.com/place/Hong-Kong/History|https://history.state.gov/milestones/1937-1945/japan-surrender",
    ),
    "taiwan": (
        "Encyclopaedia Britannica: Taiwan History|Avalon Project: Cairo Communique 1943",
        "https://www.britannica.com/place/Taiwan/History|https://avalon.law.yale.edu/wwii/cairo.asp",
    ),
    "mongolia": (
        "Encyclopaedia Britannica: Mongolia Between Russia and China|Encyclopaedia Britannica: Mongolia",
        "https://www.britannica.com/place/Mongolia/Between-Russia-and-China|https://www.britannica.com/place/Mongolia",
    ),
    "tibet": (
        "Encyclopaedia Britannica: Tibet since 1900|Encyclopaedia Britannica: Tibet",
        "https://www.britannica.com/place/Tibet/Tibet-since-1900|https://www.britannica.com/place/Tibet",
    ),
    "xinjiang": (
        "Encyclopaedia Britannica: Xinjiang|Encyclopaedia Britannica: China",
        "https://www.britannica.com/place/Xinjiang|https://www.britannica.com/place/China",
    ),
    "leases": (
        "Encyclopaedia Britannica: Shanghai History|Encyclopaedia Britannica: Tianjin History",
        "https://www.britannica.com/place/Shanghai/History|https://www.britannica.com/place/Tianjin/History",
    ),
    "qingdao_weihai": (
        "Encyclopaedia Britannica: Qingdao|Encyclopaedia Britannica: Weihai",
        "https://www.britannica.com/place/Qingdao|https://www.britannica.com/place/Weihai",
    ),
    "guangzhouwan_kwantung": (
        "Encyclopaedia Britannica: Zhanjiang|Encyclopaedia Britannica: Liaodong Peninsula",
        "https://www.britannica.com/place/Zhanjiang|https://www.britannica.com/place/Liaodong-Peninsula",
    ),
    "puppet": (
        "Encyclopaedia Britannica: Wang Ching-wei|Encyclopaedia Britannica: Second Sino-Japanese War",
        "https://www.britannica.com/biography/Wang-Ching-wei|https://www.britannica.com/event/Second-Sino-Japanese-War",
    ),
    "long_march": (
        "Encyclopaedia Britannica: Long March|Encyclopaedia Britannica: Chinese Civil War",
        "https://www.britannica.com/event/Long-March|https://www.britannica.com/event/Chinese-Civil-War",
    ),
}


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = [(field or "").lstrip("\ufeff") for field in (reader.fieldnames or [])]
        rows = [
            {(key or "").lstrip("\ufeff"): (value or "") for key, value in row.items()}
            for row in reader
        ]
    return fields, rows


def write_rows(path: Path, fields: list[str], rows: list[dict[str, Any]], encoding: str = "utf-8") -> None:
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def year_label(year: int) -> str:
    return f"前{abs(year)}年" if year < 0 else f"{year}年"


def iter_years(start: int, end: int) -> list[int]:
    lo, hi = min(start, end), max(start, end)
    return [year for year in range(lo, hi + 1) if year != 0]


def source_pair(key: str) -> tuple[str, str]:
    return SOURCE_PAIRS[key]


def polity(
    num: int,
    name: str,
    polity_type: str,
    start: int,
    end: int,
    historical_geo: str,
    modern_units: str,
    capital_historical: str,
    capital_modern: str,
    *,
    source: str,
    confidence: int,
    note: str,
    aliases: str = "",
    disambiguation: str = "",
    risk_flags: str = "",
    macro_period: str = "民国",
    dynasty_name: str = "中华民国",
    ruling_family: str = "",
    ethnicity: str = "",
    founder: str = "",
    last_ruler: str = "",
    successor: str = "",
) -> dict[str, Any]:
    titles, urls = source_pair(source)
    years = iter_years(start, end)
    return {
        "polity_id": f"polity_{num:04d}",
        "macro_period": macro_period,
        "dynasty_name": dynasty_name,
        "polity_name": name,
        "polity_aliases": aliases,
        "polity_display_name": name,
        "polity_name_disambiguation": disambiguation,
        "polity_name_review_status": "verified",
        "polity_name_risk_flags": risk_flags,
        "polity_type": polity_type,
        "polity_start_year": str(start),
        "polity_start_label": year_label(start),
        "polity_end_year": str(end),
        "polity_end_label": year_label(end),
        "polity_date_raw": f"{year_label(start)}－{year_label(end)}",
        "polity_date_precision": "year",
        "historical_geography_raw": historical_geo,
        "modern_admin_units_raw": modern_units,
        "capital_historical": capital_historical,
        "capital_modern": capital_modern,
        "ruling_family_or_clan": ruling_family,
        "ethnicity_or_group": ethnicity,
        "founder": founder,
        "last_ruler": last_ruler,
        "destroyed_by_or_successor": successor,
        "polity_source_titles": titles,
        "polity_source_urls": urls,
        "polity_source_raw": f"republican_period_sources_v03.csv#{source}",
        "confidence_score": str(confidence),
        "confidence_note": note,
        "calendar_system_note": CALENDAR_NOTE,
        "v02_row_count": "0",
        "v02_actual_min_year": str(start),
        "v02_actual_max_year": str(end),
        "v02_actual_years": ";".join(str(year) for year in years),
        "merged_from_v02_contexts": "",
    }


def ruler(
    num: int,
    pid: str,
    polity_name: str,
    ruler_name: str,
    title: str,
    start: int,
    end: int,
    *,
    source: str,
    note: str = "",
    confidence: int = 80,
) -> dict[str, Any]:
    titles, urls = source_pair(source)
    return {
        "ruler_id": f"ruler_{num:05d}",
        "polity_id": pid,
        "polity_name": polity_name,
        "ruler_name": ruler_name,
        "ruler_title": title,
        "ruler_temple_name": "",
        "ruler_posthumous_name": "",
        "ruler_personal_name": ruler_name,
        "ruler_reign_start_year": str(start),
        "ruler_reign_start_label": year_label(start),
        "ruler_reign_end_year": str(end),
        "ruler_reign_end_label": year_label(end),
        "ruler_reign_raw": f"{year_label(start)}－{year_label(end)}",
        "ruler_reign_precision": "year",
        "era_names": "",
        "ruler_source_title": titles,
        "ruler_source_url": urls,
        "ruler_source_section": "republican_period_sources_v03.csv",
        "ruler_confidence_score": str(confidence),
        "ruler_confidence_note": note,
        "merged_from_v02_rows": "",
    }


def capital(
    num: int,
    pid: str,
    historical: str,
    modern: str,
    start: int,
    end: int,
    lon: float,
    lat: float,
    *,
    source: str,
    primary: bool = True,
    event_type: str = "initial_capital",
    precision: str = "city",
    confidence: int = 80,
    note: str = "",
) -> dict[str, Any]:
    titles, urls = source_pair(source)
    return {
        "capital_event_id": f"capital_{num:04d}",
        "polity_id": pid,
        "capital_name_historical": historical,
        "capital_name_modern": modern,
        "valid_from_year": str(start),
        "valid_to_year": str(end),
        "longitude": f"{lon:.4f}",
        "latitude": f"{lat:.4f}",
        "is_primary": "true" if primary else "false",
        "event_type": event_type,
        "location_precision": precision,
        "source_titles": titles,
        "source_urls": urls,
        "source_raw": "republican_period_sources_v03.csv",
        "confidence_score": str(confidence),
        "confidence_note": note,
    }


def territory(
    pid: str,
    name: str,
    admin_ids: list[str],
    start: int,
    end: int,
    confidence: int,
    note: str,
) -> dict[str, Any]:
    return {
        "polity_id": pid,
        "polity_name": name,
        "admin_ids": "|".join(admin_ids),
        "valid_from_year": str(start),
        "valid_to_year": str(end),
        "match_source": "manual_republican_period_v03_override",
        "confidence_score": str(confidence),
        "note": note,
        "source_titles": "republican_period_sources_v03.csv",
        "source_raw": "现代省级边界近似；用于双层法理/实控模型，不代表精确历史边界。",
    }


def issue(
    suffix: str,
    issue_type: str,
    pid: str,
    name: str,
    field: str,
    selected: str,
    alternatives: str,
    source: str,
    note: str,
) -> dict[str, Any]:
    titles, urls = source_pair(source)
    return {
        "issue_id": f"{ISSUE_PREFIX}{suffix}",
        "issue_type": issue_type,
        "entity_type": "polity",
        "polity_id": pid,
        "polity_name": name,
        "field_name": field,
        "selected_value": selected,
        "alternative_values": alternatives,
        "source_titles": titles,
        "source_urls": urls,
        "note": note,
        "action_in_v03": "modeled as separate nominal/effective-control polities and documented in confidence_note",
    }


POLITIES = [
    polity(183, "中华民国临时政府", "中央政权/实际控制区", 1912, 1912, "1912年南京临时政府成立，实际依托响应辛亥革命的南方与中部各省；同年清帝退位、袁世凯接任临时大总统后政治中心转往北京。", "江苏省、上海市、浙江省、安徽省、江西省、湖北省、湖南省、广东省、广西壮族自治区、福建省、山东省等革命响应区", "南京；北京", "江苏省南京市；北京市", source="republic", confidence=88, note="仅表示1912年临时政府及革命响应区，不等同于同年全国各地即时实控。", aliases="南京临时政府|中华民国南京临时政府", disambiguation="1912年短期临时中央政权。", risk_flags="short_lived|nominal_effective_control_split", founder="孙中山", successor="中华民国北京政府"),
    polity(184, "中华民国北京政府", "中央政权/名义层", 1912, 1928, "北京政府在国际外交上长期代表中华民国，但国内军阀分裂使其直接控制范围随年份变化。", "北京市、天津市、河北省、山东省、河南省、山西省、辽宁省、吉林省、黑龙江省、内蒙古自治区、陕西省、甘肃省等北方及东北承认或受北洋体系影响地区", "北京", "北京市", source="republic", confidence=84, note="本条为名义中央层；实际控制由北洋军阀实际控制区和地方势力事件补充说明。", aliases="北洋政府|北京政府|中华民国北洋政府", disambiguation="1912-1928年以北京为政治中心的中华民国中央政府。", risk_flags="nominal_effective_control_split", founder="袁世凯", successor="中华民国国民政府"),
    polity(185, "北洋军阀实际控制区", "实际控制区/军阀势力范围", 1916, 1928, "袁世凯死后，皖系、直系、奉系等军阀围绕北京政府、华北、东北和长江中下游展开争夺，实际控制范围多次变化。", "北京市、天津市、河北省、山东省、河南省、山西省、辽宁省、吉林省、黑龙江省、内蒙古自治区、江苏省、安徽省、湖北省等军阀争夺区", "北京、天津、沈阳等", "北京市、天津市、辽宁省沈阳市", source="republic", confidence=70, note="这是省级粗粒度势力范围层，战线和派系变化通过事件记录表达，不作逐县逐月控制。", aliases="北洋军阀|皖系|直系|奉系", disambiguation="军阀割据时期北洋派系实际控制区的概括层。", risk_flags="coarse_effective_control|dynamic_frontline", successor="东北易帜后国民政府名义统一"),
    polity(186, "广州护法军政府", "地方中央对抗政权/实际控制区", 1917, 1925, "护法运动后，孙中山等在广州建立与北京政府对立的军政府和大元帅府，依托广东及西南部分势力。", "广东省、广西壮族自治区、云南省、湖南省、福建省等护法及南方革命势力影响区", "广州", "广东省广州市", source="republic", confidence=76, note="广州政权组织形态数次变化，v03 合并为护法到国民政府成立前的实际政治中心层。", aliases="护法军政府|广州军政府|陆海军大元帅大本营", disambiguation="1917-1925年南方护法/革命政权。", risk_flags="coarse_effective_control", founder="孙中山", successor="中华民国国民政府"),
    polity(187, "中华民国国民政府（名义层）", "中央政权/名义层", 1925, 1949, "国民政府先后以广州、武汉、南京、重庆、南京为政治中心，1928年东北易帜后取得国内外较广泛承认；抗战和内战期间其法理宣称与实际控制差异显著。", "中国大陆各省、台湾省；对外蒙古、西藏等仍有法理主张但实际控制不同", "广州、武汉、南京、重庆、台北", "广东省广州市、湖北省武汉市、江苏省南京市、重庆市、台湾省台北市", source="republic", confidence=86, note="本条保留中华民国中央政府法统/名义疆域；实际控制区、日占区、傀儡政权和边疆事实自治另列。1949为本数据集截断点，不表示中华民国政权灭亡。", aliases="国民政府|南京国民政府|重庆国民政府|中华民国政府", disambiguation="1925-1949年国民政府中央名义层。", risk_flags="nominal_effective_control_split|sensitive_sovereignty|continues_after_1949", founder="中国国民党", successor="1949年中央政府迁台；中国大陆政权更替为中华人民共和国"),
    polity(188, "国民政府实际控制区", "实际控制区", 1928, 1949, "1928年后国民政府形成以南京为中心的国统区；抗战时期收缩至西南、西北与若干前线地区，战后接收东北、台湾等地，内战中又迅速缩小。", "江苏省、上海市、浙江省、安徽省、江西省、湖北省、湖南省、福建省、广东省、广西壮族自治区、海南省、四川省、重庆市、贵州省、云南省、陕西省、甘肃省、宁夏回族自治区、青海省、台湾省等国统区核心和战后接收区", "南京、重庆、广州、台北等", "江苏省南京市、重庆市、广东省广州市、台湾省台北市", source="republic", confidence=72, note="实控区随战争剧烈变化；本条用省级概括配合年度事件，避免误作静态精确边界。1949为大陆时期截断点。", aliases="国统区|国民党控制区", disambiguation="国民政府在大陆时期的实际控制区粗粒度层。", risk_flags="coarse_effective_control|dynamic_frontline|continues_after_1949"),
    polity(189, "中华苏维埃共和国", "革命根据地/实际控制区", 1931, 1937, "1931年在江西瑞金成立，中央苏区及其他苏区分布于赣、闽、粤、湘、鄂、豫、皖、川陕等地；长征后政治中心转向陕北。", "江西省、福建省、广东省、湖南省、湖北省、安徽省、河南省、四川省、陕西省等苏区和转移路线涉及地区", "瑞金；保安", "江西省瑞金市；陕西省志丹县", source="long_march", confidence=80, note="苏区分散且动态变化，本条记录中央苏区及主要根据地的概括层。", aliases="中华苏维埃临时中央政府|中央苏区", disambiguation="1931-1937年中共苏维埃政权。", risk_flags="coarse_effective_control|dynamic_frontline", founder="中国共产党", successor="陕甘宁边区与中共抗日根据地"),
    polity(190, "陕甘宁边区与中共抗日根据地", "边区/抗日根据地/实际控制区", 1937, 1945, "第二次国共合作后，陕甘宁边区成为中共中央所在地；华北、华中、华南敌后根据地逐步形成。", "陕西省、甘肃省、宁夏回族自治区、山西省、河北省、山东省、河南省、湖北省、江苏省、安徽省、广东省等敌后根据地", "延安", "陕西省延安市", source="war_japan", confidence=78, note="敌后根据地范围随军事形势变化，采用省级近似并由事件细化。", aliases="陕甘宁边区|抗日根据地|延安时期", disambiguation="1937-1945年中共边区与敌后根据地。", risk_flags="coarse_effective_control|dynamic_frontline", successor="中国共产党解放区"),
    polity(191, "中国共产党解放区", "解放区/实际控制区", 1945, 1949, "抗战后中共控制区由华北、东北、华东等地扩展，内战后期通过三大战役和渡江战役取得大陆多数地区控制。", "黑龙江省、吉林省、辽宁省、内蒙古自治区、河北省、山西省、山东省、河南省、陕西省、甘肃省、宁夏回族自治区、北京市、天津市、江苏省、安徽省、上海市、浙江省、湖北省、湖南省、江西省、福建省等解放区", "延安、西柏坡、北平", "陕西省延安市、河北省平山县、北京市", source="civil_war", confidence=78, note="1945-1949年控制区扩张很快，本条按年度事件表达关键城市与战役造成的变化。", aliases="解放区|中共控制区", disambiguation="1945-1949年国共内战中共控制区。", risk_flags="coarse_effective_control|dynamic_frontline", successor="中华人民共和国"),
    polity(192, "满洲国", "日本扶植傀儡政权/实际控制区", 1932, 1945, "九一八事变后日本在东北扶植满洲国，范围大致包括东北三省和热河等地。", "辽宁省、吉林省、黑龙江省、内蒙古自治区东部", "新京", "吉林省长春市", source="manchukuo", confidence=88, note="作为日本扶植的傀儡政权列为实控层，不等同于中华民国法理承认。", aliases="伪满洲国|满洲帝国|Manchukuo", disambiguation="1932-1945年日本扶植的东北傀儡政权。", risk_flags="puppet_state|occupation|sensitive_sovereignty", founder="日本关东军", last_ruler="溥仪", successor="苏军进东北与国共接收/争夺"),
    polity(193, "中华民国临时政府（华北）", "日本扶植傀儡政权/实际控制区", 1937, 1940, "七七事变后日本在北平扶植华北临时政府，1940年并入汪精卫南京政权体系。", "北京市、天津市、河北省、山西省、山东省、河南省等华北日占区", "北平", "北京市", source="puppet", confidence=76, note="日本占领区下的傀儡政权，记录实控/占领层。", aliases="华北临时政府|伪临时政府", disambiguation="1937-1940年华北日占区傀儡政权。", risk_flags="puppet_state|occupation", founder="日本华北方面军", successor="汪精卫南京国民政府"),
    polity(194, "中华民国维新政府", "日本扶植傀儡政权/实际控制区", 1938, 1940, "日本在南京扶植维新政府，管辖江浙皖等日占区名义行政，1940年并入汪精卫政权。", "江苏省、上海市、浙江省、安徽省等华中日占区", "南京", "江苏省南京市", source="puppet", confidence=76, note="日本占领区下的傀儡政权，记录实控/占领层。", aliases="伪维新政府", disambiguation="1938-1940年华中日占区傀儡政权。", risk_flags="puppet_state|occupation", successor="汪精卫南京国民政府"),
    polity(195, "汪精卫南京国民政府", "日本扶植傀儡政权/实际控制区", 1940, 1945, "汪精卫在南京建立日本扶植的改组国民政府，名义管辖华北、华中、华南若干日占区。", "江苏省、上海市、浙江省、安徽省、湖北省、湖南省、广东省、山东省、河南省、河北省、北京市、天津市等日占区", "南京", "江苏省南京市", source="puppet", confidence=82, note="傀儡政权/占领区层；不代表中华民国重庆国民政府承认其合法性。", aliases="汪伪政权|南京国民政府（汪精卫）|改组国民政府", disambiguation="1940-1945年日本扶植的南京政权。", risk_flags="puppet_state|occupation|sensitive_sovereignty", founder="汪精卫", last_ruler="陈公博", successor="日本投降后结束"),
    polity(196, "蒙疆联合自治政府", "日本扶植傀儡政权/实际控制区", 1939, 1945, "日本在察哈尔、绥远及邻近地区扶植蒙疆联合自治政府，作为华北占领体系一部分。", "内蒙古自治区中西部、河北省北部、山西省北部", "张家口", "河北省张家口市", source="puppet", confidence=76, note="蒙疆范围以现代省级近似表达，避免误作民族或主权判断。", aliases="蒙疆|蒙古联合自治政府", disambiguation="1939-1945年日本扶植的蒙疆傀儡政权。", risk_flags="puppet_state|occupation|coarse_effective_control", founder="德王", successor="日本投降后结束"),
    polity(197, "日本台湾总督府", "殖民管治区", 1895, 1945, "《马关条约》后台湾、澎湖由日本殖民统治，1945年日本投降后由中华民国接收。", "台湾省、澎湖列岛", "台北", "台湾省台北市", source="taiwan", confidence=90, note="1895-1945为日本殖民管治层；1945接收另以事件和国民政府实控层表达。", aliases="日治台湾|台湾总督府", disambiguation="1895-1945年日本在台湾的殖民统治机构。", risk_flags="colonial_rule|cession|retrocession_sensitive", dynasty_name="日本殖民管治", successor="中华民国接收台湾澎湖"),
    polity(198, "日本关东州租借地", "外国租借地/殖民管治区", 1905, 1945, "日俄战争后日本取得旅顺、大连一带关东州租借权益，并与南满铁路附属地、关东军体系共同影响东北。", "辽宁省大连市旅顺口区、大连市区一带", "旅顺、大连", "辽宁省大连市", source="guangzhouwan_kwantung", confidence=78, note="关东州为租借地/殖民管治层，和满洲国范围、东北日占区有关但不完全相同。", aliases="关东州|旅大租借地|Kwantung Leased Territory", disambiguation="1905-1945年日本在辽东半岛南端的租借地。", risk_flags="foreign_lease|occupation|sensitive_sovereignty", dynasty_name="外国租借/占领"),
    polity(199, "英租威海卫", "外国租借地", 1898, 1930, "英国1898年租借威海卫，1930年归还中国。", "山东省威海市", "威海卫", "山东省威海市", source="qingdao_weihai", confidence=82, note="租借地层；1930年归还事件单独记录。", aliases="威海卫租借地|British Weihaiwei", disambiguation="1898-1930年英国租借地。", risk_flags="foreign_lease|retrocession_sensitive", dynasty_name="外国租借/占领"),
    polity(200, "法租广州湾", "外国租借地", 1898, 1945, "法国租借广州湾，范围约今广东湛江一带，1945年归还中国。", "广东省湛江市", "广州湾", "广东省湛江市", source="guangzhouwan_kwantung", confidence=80, note="租借地层；1945年归还中国与战后接收并列记录。", aliases="广州湾租借地|Kouang-Tcheou-Wan|Zhanjiang lease", disambiguation="1898-1945年法国租借地。", risk_flags="foreign_lease|retrocession_sensitive", dynasty_name="外国租借/占领"),
    polity(201, "日本占领胶澳青岛", "外国占领区/租借地", 1914, 1922, "第一次世界大战中日本夺取德国胶澳租借地，1922年青岛与胶济铁路权益归还中国。", "山东省青岛市", "青岛", "山东省青岛市", source="qingdao_weihai", confidence=80, note="1914-1922年日本占领/租借权益层；1922年归还事件单独记录。", aliases="日占青岛|胶澳租借地", disambiguation="一战后至华盛顿会议安排下归还前的日本青岛占领层。", risk_flags="foreign_lease|occupation|retrocession_sensitive", dynasty_name="外国租借/占领"),
    polity(202, "上海公共租界", "外国租界", 1863, 1943, "上海公共租界由英美等侨民机构管理，1943年英美等放弃在华治外法权后名义结束。", "上海市黄浦区、虹口区、静安区等中心城区一带", "上海", "上海市", source="leases", confidence=78, note="租界边界以现代上海市近似，不表示整个上海被租界覆盖。", aliases="上海英美公共租界|Shanghai International Settlement", disambiguation="1863-1943年上海公共租界。", risk_flags="foreign_concession|coarse_boundary", dynasty_name="外国租借/占领"),
    polity(203, "上海法租界", "外国租界", 1849, 1943, "上海法租界由法国管辖，1943年维希法国同汪伪政权移交，战后中法协议确认租界终止。", "上海市黄浦区、徐汇区等中心城区一带", "上海", "上海市", source="leases", confidence=76, note="以1943年日占体系下移交作为实控终止点；战后外交确认另见说明。", aliases="上海法国租界|French Concession", disambiguation="1849-1943年上海法租界。", risk_flags="foreign_concession|coarse_boundary|sensitive_sovereignty", dynasty_name="外国租借/占领"),
    polity(204, "天津租界群", "外国租界", 1860, 1946, "天津曾有英、法、日、德、俄、意、奥、比等多国租界；不同租界终止时间不同，1940年代陆续收回。", "天津市中心城区和海河两岸一带", "天津", "天津市", source="leases", confidence=68, note="合并为租界群层，因各国租界起止年不同，事件与 issue 说明差异。", aliases="天津各国租界|Tianjin concessions", disambiguation="1860-1946年天津多国租界合并展示层。", risk_flags="foreign_concession|merged_multiple_entities|coarse_boundary", dynasty_name="外国租借/占领"),
    polity(205, "英属香港", "殖民管治区", 1842, 1941, "香港岛、九龙及新界先后纳入英国殖民管治；1941年香港沦陷前由英国管治。", "香港特别行政区", "香港", "香港特别行政区", source="hongkong", confidence=88, note="殖民管治层；1941-1945日占香港另列，1945后英方恢复管治另列。", aliases="英国香港|British Hong Kong", disambiguation="1842-1941年英属香港。", risk_flags="colonial_rule|cession|lease|sensitive_sovereignty", dynasty_name="英国殖民管治"),
    polity(206, "日占香港", "外国占领区", 1941, 1945, "1941年12月香港战役后日本占领香港，1945年日本投降后结束。", "香港特别行政区", "香港", "香港特别行政区", source="hongkong", confidence=88, note="日本军事占领层，区别于英属香港战前/战后殖民管治。", aliases="日本占领香港|香港日占时期", disambiguation="1941-1945年日本占领香港。", risk_flags="occupation|colonial_rule|sensitive_sovereignty", dynasty_name="日本占领"),
    polity(207, "英属香港（战后恢复）", "殖民管治区", 1945, 1949, "1945年日本投降后英国恢复在香港的殖民管治，延续至民国大陆时期结束。", "香港特别行政区", "香港", "香港特别行政区", source="hongkong", confidence=86, note="战后英方恢复管治层，不等同于中华民国实际控制；1949为本数据集截断点。", aliases="战后英属香港|British Hong Kong postwar", disambiguation="1945-1949年英方恢复管治阶段。", risk_flags="colonial_rule|sensitive_sovereignty|continues_after_1949", dynasty_name="英国殖民管治"),
    polity(208, "葡属澳门", "殖民管治区", 1887, 1949, "1887年中葡条约后澳门由葡萄牙长期管治；民国时期不属中国政府实际控制。", "澳门特别行政区", "澳门", "澳门特别行政区", source="leases", confidence=82, note="殖民管治层，保留法理与实际控制差异；1949为本数据集截断点。", aliases="葡萄牙澳门|Portuguese Macau", disambiguation="1887-1949年葡萄牙管治澳门。", risk_flags="colonial_rule|sensitive_sovereignty|continues_after_1949", dynasty_name="葡萄牙殖民管治"),
    polity(209, "外蒙古/蒙古人民共和国", "边疆事实独立政权", 1911, 1949, "外蒙古1911年后事实脱离清朝继承政权控制，1924年成立蒙古人民共和国；1945年公投后中华民国政府承认其独立。", "蒙古国（外蒙古）", "库伦；乌兰巴托", "蒙古国乌兰巴托", source="mongolia", confidence=80, note="法理主张与实际控制长期分离；1945-1946承认外蒙古独立另列事件和 issue。1949为本数据集截断点。", aliases="外蒙古|蒙古人民共和国|蒙古人民共和國", disambiguation="1911-1949年外蒙古事实独立/蒙古人民共和国层。", risk_flags="sensitive_sovereignty|nominal_effective_control_split|continues_after_1949", dynasty_name="蒙古地方/蒙古人民共和国", successor="蒙古人民共和国"),
    polity(210, "西藏噶厦政权", "边疆事实自治政权", 1912, 1949, "清朝驻藏机构瓦解后，拉萨噶厦长期维持事实自治；中华民国保留法理主张但实际控制有限。", "西藏自治区及邻近藏区核心", "拉萨", "西藏自治区拉萨市", source="tibet", confidence=78, note="事实自治与中华民国法理宣称并列呈现，避免将二者混同。1949为本数据集截断点。", aliases="噶厦|西藏地方政府|Ganden Phodrang", disambiguation="1912-1949年拉萨噶厦事实自治层。", risk_flags="sensitive_sovereignty|nominal_effective_control_split|continues_after_1949", dynasty_name="西藏地方政权"),
    polity(211, "新疆省地方军政", "边疆地方政权/实际控制区", 1912, 1949, "民国时期新疆由杨增新、金树仁、盛世才及战后国民政府省政当局先后控制，中央直接控制程度有限。", "新疆维吾尔自治区", "迪化", "新疆维吾尔自治区乌鲁木齐市", source="xinjiang", confidence=76, note="新疆省名义属中华民国，地方军政独立性强；三区革命另列。", aliases="新疆省|迪化政权|盛世才政权", disambiguation="1912-1949年新疆省地方军政层。", risk_flags="borderland_autonomy|nominal_effective_control_split", successor="1949年新疆和平解放"),
    polity(212, "新疆三区革命政权", "边疆地方政权/实际控制区", 1944, 1949, "1944年伊犁、塔城、阿山三区形成反国民政府地方政权，1949年与新疆和平解放进程衔接。", "新疆维吾尔自治区伊犁哈萨克自治州、塔城地区、阿勒泰地区", "伊宁", "新疆维吾尔自治区伊宁市", source="xinjiang", confidence=74, note="三区范围以北疆省级/地区级近似表达，具体县域控制不在首批展开。", aliases="三区革命|东突厥斯坦共和国（1944）|伊犁临时政府", disambiguation="1944-1949年新疆三区地方政权。", risk_flags="sensitive_sovereignty|coarse_effective_control", successor="新疆和平解放"),
    polity(213, "中华人民共和国（1949年成立）", "中央政权/实际控制区", 1949, 1949, "1949年10月1日中华人民共和国中央人民政府成立；同年中国大陆主要地区陆续由中共/解放军控制，台湾、香港、澳门、西藏等状态另有差异。", "北京市、天津市、河北省、山西省、内蒙古自治区、辽宁省、吉林省、黑龙江省、上海市、江苏省、浙江省、安徽省、福建省、江西省、山东省、河南省、湖北省、湖南省、广东省、广西壮族自治区、重庆市、四川省、贵州省、云南省、陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区等1949年底已控制或进入接收进程地区", "北京", "北京市", source="civil_war", confidence=82, note="本条仅为1949年起点层；因 v03 当前截断到1949，不展开1950年以后控制变化。", aliases="新中国|中央人民政府|PRC", disambiguation="1949年中华人民共和国成立起点。", risk_flags="year_endpoint|dynamic_frontline", macro_period="中华人民共和国", dynasty_name="中华人民共和国", founder="中国共产党", successor=""),
]

RULERS = [
    ruler(1120, "polity_0183", "中华民国临时政府", "孙中山", "临时大总统", 1912, 1912, source="republic", note="1912年1月至3月南京临时政府。", confidence=88),
    ruler(1121, "polity_0183", "中华民国临时政府", "袁世凯", "临时大总统", 1912, 1912, source="republic", note="1912年3月后临时大总统，政治中心转北京。", confidence=86),
    ruler(1122, "polity_0184", "中华民国北京政府", "袁世凯", "临时大总统/大总统", 1912, 1916, source="republic", confidence=86),
    ruler(1123, "polity_0184", "中华民国北京政府", "北京政府历任大总统及执政", "中央政府首脑", 1916, 1928, source="republic", note="合并黎元洪、冯国璋、徐世昌、曹锟、段祺瑞、张作霖等阶段以保证年度覆盖。", confidence=72),
    ruler(1124, "polity_0185", "北洋军阀实际控制区", "皖系、直系、奉系等北洋派系", "实际军事政治控制者", 1916, 1928, source="republic", note="势力范围动态变化，作为聚合控制层。", confidence=66),
    ruler(1125, "polity_0186", "广州护法军政府", "孙中山及南方护法军政府", "非常大总统/大元帅", 1917, 1925, source="republic", confidence=76),
    ruler(1126, "polity_0187", "中华民国国民政府（名义层）", "国民政府委员会及国民政府主席", "中央政府首脑", 1925, 1949, source="republic", note="聚合汪精卫、谭延闿、蒋介石、林森、蒋中正、李宗仁等阶段。", confidence=76),
    ruler(1127, "polity_0188", "国民政府实际控制区", "国民政府军事委员会及行政院", "国统区军政机关", 1928, 1949, source="republic", confidence=72),
    ruler(1128, "polity_0189", "中华苏维埃共和国", "中华苏维埃临时中央政府", "中央执行委员会", 1931, 1937, source="long_march", confidence=80),
    ruler(1129, "polity_0190", "陕甘宁边区与中共抗日根据地", "陕甘宁边区政府与中共中央", "边区/根据地领导机关", 1937, 1945, source="war_japan", confidence=78),
    ruler(1130, "polity_0191", "中国共产党解放区", "中共中央与解放区军政机关", "解放区领导机关", 1945, 1949, source="civil_war", confidence=78),
    ruler(1131, "polity_0192", "满洲国", "溥仪", "执政/皇帝", 1932, 1945, source="manchukuo", confidence=88),
    ruler(1132, "polity_0193", "中华民国临时政府（华北）", "王克敏", "行政委员会委员长", 1937, 1940, source="puppet", confidence=76),
    ruler(1133, "polity_0194", "中华民国维新政府", "梁鸿志", "行政院长", 1938, 1940, source="puppet", confidence=76),
    ruler(1134, "polity_0195", "汪精卫南京国民政府", "汪精卫、陈公博", "国民政府主席", 1940, 1945, source="puppet", confidence=80),
    ruler(1135, "polity_0196", "蒙疆联合自治政府", "德王及蒙疆联合自治政府", "主席", 1939, 1945, source="puppet", confidence=74),
    ruler(1136, "polity_0197", "日本台湾总督府", "台湾总督府历任总督", "总督", 1895, 1945, source="taiwan", confidence=82),
    ruler(1137, "polity_0198", "日本关东州租借地", "日本关东州租借地当局", "租借地行政机关", 1905, 1945, source="guangzhouwan_kwantung", confidence=76),
    ruler(1138, "polity_0199", "英租威海卫", "威海卫英方行政长官", "行政长官", 1898, 1930, source="qingdao_weihai", confidence=78),
    ruler(1139, "polity_0200", "法租广州湾", "广州湾法方行政当局", "租借地行政机关", 1898, 1945, source="guangzhouwan_kwantung", confidence=76),
    ruler(1140, "polity_0201", "日本占领胶澳青岛", "日本青岛守备军及民政署", "占领/民政机关", 1914, 1922, source="qingdao_weihai", confidence=76),
    ruler(1141, "polity_0202", "上海公共租界", "上海公共租界工部局", "租界行政机关", 1863, 1943, source="leases", confidence=76),
    ruler(1142, "polity_0203", "上海法租界", "上海法租界公董局", "租界行政机关", 1849, 1943, source="leases", confidence=74),
    ruler(1143, "polity_0204", "天津租界群", "天津各国租界行政机关", "租界行政机关", 1860, 1946, source="leases", confidence=66),
    ruler(1144, "polity_0205", "英属香港", "香港总督", "总督", 1842, 1941, source="hongkong", confidence=84),
    ruler(1145, "polity_0206", "日占香港", "香港占领地总督部", "日本军政机关", 1941, 1945, source="hongkong", confidence=84),
    ruler(1146, "polity_0207", "英属香港（战后恢复）", "香港总督", "总督", 1945, 1949, source="hongkong", confidence=82),
    ruler(1147, "polity_0208", "葡属澳门", "澳门总督", "总督", 1887, 1949, source="leases", confidence=78),
    ruler(1148, "polity_0209", "外蒙古/蒙古人民共和国", "博克多汗政权", "汗/君主", 1911, 1924, source="mongolia", confidence=76),
    ruler(1149, "polity_0209", "外蒙古/蒙古人民共和国", "蒙古人民共和国政府", "国家政权机关", 1924, 1949, source="mongolia", confidence=80),
    ruler(1150, "polity_0210", "西藏噶厦政权", "十三世达赖喇嘛与噶厦", "达赖喇嘛/噶厦", 1912, 1933, source="tibet", confidence=78),
    ruler(1151, "polity_0210", "西藏噶厦政权", "热振摄政及噶厦", "摄政/噶厦", 1934, 1949, source="tibet", confidence=74),
    ruler(1152, "polity_0211", "新疆省地方军政", "杨增新", "新疆都督/省长", 1912, 1928, source="xinjiang", confidence=78),
    ruler(1153, "polity_0211", "新疆省地方军政", "金树仁", "新疆省主席", 1928, 1933, source="xinjiang", confidence=74),
    ruler(1154, "polity_0211", "新疆省地方军政", "盛世才", "新疆省主席", 1933, 1944, source="xinjiang", confidence=78),
    ruler(1155, "polity_0211", "新疆省地方军政", "战后新疆省政府", "省政府", 1944, 1949, source="xinjiang", note="聚合吴忠信、张治中、包尔汉等阶段。", confidence=72),
    ruler(1156, "polity_0212", "新疆三区革命政权", "三区临时政府", "临时政府", 1944, 1949, source="xinjiang", confidence=74),
    ruler(1157, "polity_0213", "中华人民共和国（1949年成立）", "中央人民政府委员会", "中央人民政府", 1949, 1949, source="civil_war", confidence=84),
]

CAPITAL_EVENTS = [
    capital(58, "polity_0183", "南京", "江苏省南京市", 1912, 1912, 118.7969, 32.0603, source="republic", note="南京临时政府所在地。"),
    capital(59, "polity_0183", "北京", "北京市", 1912, 1912, 116.4074, 39.9042, source="republic", primary=False, event_type="relocation", note="袁世凯就任后政治中心转往北京。"),
    capital(60, "polity_0184", "北京", "北京市", 1912, 1928, 116.4074, 39.9042, source="republic"),
    capital(61, "polity_0186", "广州", "广东省广州市", 1917, 1925, 113.2644, 23.1291, source="republic"),
    capital(62, "polity_0187", "广州", "广东省广州市", 1925, 1927, 113.2644, 23.1291, source="republic"),
    capital(63, "polity_0187", "武汉", "湖北省武汉市", 1927, 1927, 114.3054, 30.5928, source="republic", primary=False, event_type="temporary_capital"),
    capital(64, "polity_0187", "南京", "江苏省南京市", 1927, 1937, 118.7969, 32.0603, source="republic", event_type="relocation"),
    capital(65, "polity_0187", "重庆", "重庆市", 1937, 1946, 106.5516, 29.5630, source="war_japan", event_type="temporary_capital", note="抗战时期陪都/战时首都。"),
    capital(66, "polity_0187", "南京", "江苏省南京市", 1946, 1949, 118.7969, 32.0603, source="republic", event_type="relocation"),
    capital(67, "polity_0187", "台北", "台湾省台北市", 1949, 1949, 121.5654, 25.0330, source="taiwan", event_type="relocation", note="1949年中央政府迁台后的政治中心。"),
    capital(68, "polity_0189", "瑞金", "江西省瑞金市", 1931, 1934, 116.0271, 25.8862, source="long_march"),
    capital(69, "polity_0189", "保安", "陕西省志丹县", 1935, 1937, 108.7689, 36.8210, source="long_march", event_type="temporary_capital"),
    capital(70, "polity_0190", "延安", "陕西省延安市", 1937, 1945, 109.4897, 36.5854, source="war_japan"),
    capital(71, "polity_0191", "延安", "陕西省延安市", 1945, 1947, 109.4897, 36.5854, source="civil_war"),
    capital(72, "polity_0191", "西柏坡", "河北省平山县西柏坡", 1948, 1949, 114.1330, 38.3510, source="civil_war", event_type="temporary_capital", precision="region"),
    capital(73, "polity_0192", "新京", "吉林省长春市", 1932, 1945, 125.3245, 43.8868, source="manchukuo"),
    capital(74, "polity_0193", "北平", "北京市", 1937, 1940, 116.4074, 39.9042, source="puppet"),
    capital(75, "polity_0194", "南京", "江苏省南京市", 1938, 1940, 118.7969, 32.0603, source="puppet"),
    capital(76, "polity_0195", "南京", "江苏省南京市", 1940, 1945, 118.7969, 32.0603, source="puppet"),
    capital(77, "polity_0196", "张家口", "河北省张家口市", 1939, 1945, 114.8841, 40.8119, source="puppet"),
    capital(78, "polity_0197", "台北", "台湾省台北市", 1895, 1945, 121.5654, 25.0330, source="taiwan"),
    capital(79, "polity_0198", "旅顺/大连", "辽宁省大连市", 1905, 1945, 121.6147, 38.9140, source="guangzhouwan_kwantung"),
    capital(80, "polity_0199", "威海卫", "山东省威海市", 1898, 1930, 122.1204, 37.5131, source="qingdao_weihai"),
    capital(81, "polity_0200", "广州湾", "广东省湛江市", 1898, 1945, 110.3594, 21.2707, source="guangzhouwan_kwantung"),
    capital(82, "polity_0201", "青岛", "山东省青岛市", 1914, 1922, 120.3826, 36.0671, source="qingdao_weihai"),
    capital(83, "polity_0202", "上海", "上海市", 1863, 1943, 121.4737, 31.2304, source="leases"),
    capital(84, "polity_0203", "上海", "上海市", 1849, 1943, 121.4737, 31.2304, source="leases"),
    capital(85, "polity_0204", "天津", "天津市", 1860, 1946, 117.2000, 39.1333, source="leases"),
    capital(86, "polity_0205", "香港", "香港特别行政区", 1842, 1941, 114.1694, 22.3193, source="hongkong"),
    capital(87, "polity_0206", "香港", "香港特别行政区", 1941, 1945, 114.1694, 22.3193, source="hongkong"),
    capital(88, "polity_0207", "香港", "香港特别行政区", 1945, 1949, 114.1694, 22.3193, source="hongkong"),
    capital(89, "polity_0208", "澳门", "澳门特别行政区", 1887, 1949, 113.5439, 22.1987, source="leases"),
    capital(90, "polity_0209", "库伦/乌兰巴托", "蒙古国乌兰巴托", 1911, 1949, 106.9057, 47.8864, source="mongolia"),
    capital(91, "polity_0210", "拉萨", "西藏自治区拉萨市", 1912, 1949, 91.1172, 29.6469, source="tibet"),
    capital(92, "polity_0211", "迪化", "新疆维吾尔自治区乌鲁木齐市", 1912, 1949, 87.6168, 43.8256, source="xinjiang"),
    capital(93, "polity_0212", "伊宁", "新疆维吾尔自治区伊宁市", 1944, 1949, 81.2777, 43.9080, source="xinjiang"),
    capital(94, "polity_0213", "北京", "北京市", 1949, 1949, 116.4074, 39.9042, source="civil_war"),
]

TERRITORY_ROWS = [
    territory("polity_0183", "中华民国临时政府", ["CN-JS", "CN-SH", "CN-ZJ", "CN-AH", "CN-JX", "CN-HB", "CN-HN", "CN-GD", "CN-GX", "CN-FJ", "CN-SD"], 1912, 1912, 58, "革命响应区省级近似，非1912全年稳定实控。"),
    territory("polity_0184", "中华民国北京政府", ["CN-BJ", "CN-TJ", "CN-HE", "CN-SD", "CN-HA", "CN-SX", "CN-LN", "CN-JL", "CN-HL", "CN-NM", "CN-SN", "CN-GS"], 1912, 1928, 52, "名义中央与北洋体系影响区混合近似。"),
    territory("polity_0185", "北洋军阀实际控制区", ["CN-BJ", "CN-TJ", "CN-HE", "CN-SD", "CN-HA", "CN-SX", "CN-LN", "CN-JL", "CN-HL", "CN-NM", "CN-JS", "CN-AH", "CN-HB"], 1916, 1928, 48, "军阀势力范围动态变化，采用宽泛省级层。"),
    territory("polity_0186", "广州护法军政府", ["CN-GD", "CN-GX", "CN-YN", "CN-HN", "CN-FJ"], 1917, 1925, 50, "南方护法势力范围近似。"),
    territory("polity_0187", "中华民国国民政府（名义层）", ["CN-BJ", "CN-TJ", "CN-HE", "CN-SX", "CN-NM", "CN-LN", "CN-JL", "CN-HL", "CN-SH", "CN-JS", "CN-ZJ", "CN-AH", "CN-FJ", "CN-JX", "CN-SD", "CN-HA", "CN-HB", "CN-HN", "CN-GD", "CN-GX", "CN-HI", "CN-CQ", "CN-SC", "CN-GZ", "CN-YN", "CN-XZ", "CN-SN", "CN-GS", "CN-QH", "CN-NX", "CN-XJ", "CN-TW"], 1925, 1949, 46, "中华民国法理/名义层，明确不代表各地实际控制。"),
    territory("polity_0188", "国民政府实际控制区", ["CN-JS", "CN-SH", "CN-ZJ", "CN-AH", "CN-JX", "CN-HB", "CN-HN", "CN-FJ", "CN-GD", "CN-GX", "CN-HI", "CN-SC", "CN-CQ", "CN-GZ", "CN-YN", "CN-SN", "CN-GS", "CN-NX", "CN-QH", "CN-SD", "CN-HA", "CN-TW"], 1928, 1949, 50, "国统区在抗战与内战中大幅变化，采用核心控制区与战后接收区近似。"),
    territory("polity_0189", "中华苏维埃共和国", ["CN-JX", "CN-FJ", "CN-GD", "CN-HN", "CN-HB", "CN-AH", "CN-HA", "CN-SC", "CN-SN"], 1931, 1937, 48, "多个苏区分散存在，使用省级近似。"),
    territory("polity_0190", "陕甘宁边区与中共抗日根据地", ["CN-SN", "CN-GS", "CN-NX", "CN-SX", "CN-HE", "CN-SD", "CN-HA", "CN-HB", "CN-JS", "CN-AH", "CN-GD"], 1937, 1945, 48, "敌后根据地动态变化，使用省级近似。"),
    territory("polity_0191", "中国共产党解放区", ["CN-HL", "CN-JL", "CN-LN", "CN-NM", "CN-HE", "CN-SX", "CN-SD", "CN-HA", "CN-SN", "CN-GS", "CN-NX", "CN-BJ", "CN-TJ", "CN-JS", "CN-AH", "CN-SH", "CN-ZJ", "CN-HB", "CN-HN", "CN-JX", "CN-FJ"], 1945, 1949, 52, "内战后期快速扩展，按1949年主要控制进程近似。"),
    territory("polity_0192", "满洲国", ["CN-LN", "CN-JL", "CN-HL", "CN-NM"], 1932, 1945, 60, "东北与热河/东蒙相关地区省级近似。"),
    territory("polity_0193", "中华民国临时政府（华北）", ["CN-BJ", "CN-TJ", "CN-HE", "CN-SX", "CN-SD", "CN-HA"], 1937, 1940, 54, "华北日占区傀儡政权省级近似。"),
    territory("polity_0194", "中华民国维新政府", ["CN-JS", "CN-SH", "CN-ZJ", "CN-AH"], 1938, 1940, 56, "华中日占区傀儡政权省级近似。"),
    territory("polity_0195", "汪精卫南京国民政府", ["CN-JS", "CN-SH", "CN-ZJ", "CN-AH", "CN-HB", "CN-HN", "CN-GD", "CN-SD", "CN-HA", "CN-HE", "CN-BJ", "CN-TJ"], 1940, 1945, 52, "汪伪政权名义辖区与日军实际占领交错，采用省级近似。"),
    territory("polity_0196", "蒙疆联合自治政府", ["CN-NM", "CN-HE", "CN-SX"], 1939, 1945, 54, "察绥及邻近地区省级近似。"),
    territory("polity_0197", "日本台湾总督府", ["CN-TW"], 1895, 1945, 72, "台湾及澎湖按现代台湾省近似。"),
    territory("polity_0198", "日本关东州租借地", ["CN-LN"], 1905, 1945, 48, "旅大局部租借地以辽宁省近似，边界明显粗化。"),
    territory("polity_0199", "英租威海卫", ["CN-SD"], 1898, 1930, 48, "威海卫局部租借地以山东省近似，边界明显粗化。"),
    territory("polity_0200", "法租广州湾", ["CN-GD"], 1898, 1945, 48, "广州湾局部租借地以广东省近似，边界明显粗化。"),
    territory("polity_0201", "日本占领胶澳青岛", ["CN-SD"], 1914, 1922, 48, "青岛/胶澳局部占领区以山东省近似。"),
    territory("polity_0202", "上海公共租界", ["CN-SH"], 1863, 1943, 48, "租界局部区域以上海市近似。"),
    territory("polity_0203", "上海法租界", ["CN-SH"], 1849, 1943, 48, "租界局部区域以上海市近似。"),
    territory("polity_0204", "天津租界群", ["CN-TJ"], 1860, 1946, 46, "多国租界局部区域以天津市近似。"),
    territory("polity_0205", "英属香港", ["CN-HK"], 1842, 1941, 70, "香港按现代香港特别行政区边界近似。"),
    territory("polity_0206", "日占香港", ["CN-HK"], 1941, 1945, 70, "香港日占期按现代香港特别行政区边界近似。"),
    territory("polity_0207", "英属香港（战后恢复）", ["CN-HK"], 1945, 1949, 70, "战后英属香港按现代香港特别行政区边界近似。"),
    territory("polity_0208", "葡属澳门", ["CN-MO"], 1887, 1949, 70, "澳门按现代澳门特别行政区边界近似。"),
    territory("polity_0210", "西藏噶厦政权", ["CN-XZ"], 1912, 1949, 58, "噶厦事实控制区以西藏自治区近似，未展开藏区边缘差异。"),
    territory("polity_0211", "新疆省地方军政", ["CN-XJ"], 1912, 1949, 62, "新疆省以现代新疆维吾尔自治区近似。"),
    territory("polity_0212", "新疆三区革命政权", ["CN-XJ"], 1944, 1949, 48, "三区局部范围以新疆自治区近似，边界明显粗化。"),
    territory("polity_0213", "中华人民共和国（1949年成立）", ["CN-BJ", "CN-TJ", "CN-HE", "CN-SX", "CN-NM", "CN-LN", "CN-JL", "CN-HL", "CN-SH", "CN-JS", "CN-ZJ", "CN-AH", "CN-FJ", "CN-JX", "CN-SD", "CN-HA", "CN-HB", "CN-HN", "CN-GD", "CN-GX", "CN-CQ", "CN-SC", "CN-GZ", "CN-YN", "CN-SN", "CN-GS", "CN-QH", "CN-NX", "CN-XJ"], 1949, 1949, 54, "1949年底大陆主要控制/接收进程近似，不含台湾、港澳、海南、西藏等差异地区。"),
]

ISSUES = [
    issue("roc_nominal_vs_control", "sovereignty_control_distinction", "polity_0187", "中华民国国民政府（名义层）", "modern_admin_units_raw", "保留中华民国名义/法理层", "实际控制由国统区、日占区、傀儡政权、中共根据地、边疆事实自治政权分列", "republic", "国民政府名义疆域与1928-1949实际控制差异很大，地图必须同时显示双层事实。"),
    issue("beiyang_control", "effective_control_dispute", "polity_0184", "中华民国北京政府", "territory_override", "北洋中央名义层", "皖系、直系、奉系及地方军阀实控区", "republic", "北京政府的国际代表性不等同于全国稳定实控。"),
    issue("civil_war_frontlines", "dynamic_frontline", "polity_0191", "中国共产党解放区", "modern_admin_units_raw", "1945-1949省级近似", "逐县逐月战线变化", "civil_war", "国共内战控制区变化迅速，首批以省级/城市事件表达。"),
    issue("manchukuo", "puppet_state_status", "polity_0192", "满洲国", "polity_type", "日本扶植傀儡政权/实际控制区", "中华民国法理上未承认其主权", "manchukuo", "满洲国作为实控层加入，避免和中华民国名义层混同。"),
    issue("wang_puppet", "puppet_state_status", "polity_0195", "汪精卫南京国民政府", "polity_type", "日本扶植傀儡政权/实际控制区", "重庆国民政府继续代表抗战阵营", "puppet", "汪伪政权仅作为占领体系下的实际行政层呈现。"),
    issue("taiwan_1895_1945", "cession_retrocession", "polity_0197", "日本台湾总督府", "polity_end_year", "1945", "1895割让给日本；1945日本投降后中华民国接收", "taiwan", "台湾、澎湖在1895-1945为日本殖民管治，1945接收事件另列，1949迁台事件另列。"),
    issue("hongkong", "colonial_rule_status", "polity_0205", "英属香港", "polity_type", "殖民管治区", "1941-1945日占；1945后英方恢复管治", "hongkong", "香港在民国时期不属中国政府实际控制，需与中华民国名义层区分。"),
    issue("macao", "colonial_rule_status", "polity_0208", "葡属澳门", "polity_type", "殖民管治区", "中华民国法理关切与葡萄牙实际管治并存", "leases", "澳门以殖民管治区列入，避免误作国民政府实控。"),
    issue("outer_mongolia", "sovereignty_control_distinction", "polity_0209", "外蒙古/蒙古人民共和国", "polity_end_year", "1949", "中华民国1945-1946承认独立；后续政治立场变化不纳入本时段", "mongolia", "外蒙古1911后事实脱离中国中央政府控制，1945公投与承认需用事件说明。"),
    issue("tibet", "sovereignty_control_distinction", "polity_0210", "西藏噶厦政权", "polity_type", "边疆事实自治政权", "中华民国名义主张", "tibet", "西藏1912-1949事实自治与中华民国法理主张并列记录。"),
    issue("xinjiang_three_districts", "effective_control_dispute", "polity_0212", "新疆三区革命政权", "modern_admin_units_raw", "伊犁、塔城、阿山三区", "新疆全省", "xinjiang", "三区革命控制范围是北疆局部，territory override 以全新疆省近似有明显粗化。"),
    issue("kwantung", "foreign_lease_status", "polity_0198", "日本关东州租借地", "modern_admin_units_raw", "旅顺/大连一带", "辽宁省全域", "guangzhouwan_kwantung", "关东州仅为辽东半岛南端租借地，省级边界只是前端兼容近似。"),
    issue("shanghai_tianjin_concessions", "foreign_concession_status", "polity_0202", "上海公共租界", "modern_admin_units_raw", "上海市局部租界", "上海市全域", "leases", "租界为城市局部区域，首批以现代直辖市近似，必须在说明中标低置信度。"),
    issue("prc_1949_endpoint", "year_endpoint_scope", "polity_0213", "中华人民共和国（1949年成立）", "polity_end_year", "1949", "1950年以后疆域与控制变化", "civil_war", "v03 当前只生成到1949，因此中华人民共和国仅作为1949起点层，不延展后续年份。"),
]


def build_yearly_rows(existing_rows: list[dict[str, str]], polities: list[dict[str, Any]], rulers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [row for row in existing_rows if row.get("polity_id") not in MANAGED_POLITY_IDS]
    max_row_id = 0
    for row in rows:
        try:
            max_row_id = max(max_row_id, int(row.get("row_id", "0")))
        except ValueError:
            continue

    rulers_by_polity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in rulers:
        rulers_by_polity[item["polity_id"]].append(item)

    next_row_id = max_row_id + 1
    for item in polities:
        start = int(item["polity_start_year"])
        end = int(item["polity_end_year"])
        for year in iter_years(start, end):
            matched = [
                ruler_row
                for ruler_row in rulers_by_polity.get(item["polity_id"], [])
                if int(ruler_row["ruler_reign_start_year"]) <= year <= int(ruler_row["ruler_reign_end_year"])
            ]
            if not matched:
                matched = [None]
            for ruler_row in matched:
                yearly_row: dict[str, Any] = {
                    "row_id": str(next_row_id),
                    "polity_id": item["polity_id"],
                    "ruler_id": ruler_row["ruler_id"] if ruler_row else "",
                    "row_granularity": "year_polity_ruler" if ruler_row else "year_polity_unmatched_ruler",
                    "year": str(year),
                    "year_label": year_label(year),
                }
                for key in [
                    "macro_period", "dynasty_name", "polity_name", "polity_aliases",
                    "polity_display_name", "polity_name_disambiguation",
                    "polity_name_review_status", "polity_name_risk_flags", "polity_type",
                    "polity_start_year", "polity_start_label", "polity_end_year",
                    "polity_end_label", "polity_date_raw", "polity_date_precision",
                    "historical_geography_raw", "modern_admin_units_raw",
                    "capital_historical", "capital_modern", "ruling_family_or_clan",
                    "ethnicity_or_group", "founder", "last_ruler",
                    "destroyed_by_or_successor", "polity_source_titles",
                    "polity_source_urls", "polity_source_raw", "confidence_score",
                    "confidence_note", "calendar_system_note",
                ]:
                    yearly_row[key] = item.get(key, "")
                for key in [
                    "ruler_name", "ruler_title", "ruler_temple_name",
                    "ruler_posthumous_name", "ruler_personal_name",
                    "ruler_reign_start_year", "ruler_reign_start_label",
                    "ruler_reign_end_year", "ruler_reign_end_label",
                    "ruler_reign_raw", "ruler_reign_precision", "era_names",
                    "ruler_source_title", "ruler_source_url", "ruler_source_section",
                    "ruler_confidence_score", "ruler_confidence_note",
                ]:
                    yearly_row[key] = ruler_row.get(key, "") if ruler_row else ""
                if not ruler_row:
                    yearly_row["ruler_confidence_note"] = "该年度保留政权层，但未配置具体首脑；待后续细化。"
                rows.append(yearly_row)
                next_row_id += 1

    def sort_key(row: dict[str, Any]) -> tuple[int, str, str, int]:
        try:
            year = int(row.get("year", "0"))
        except ValueError:
            year = 0
        try:
            row_id = int(row.get("row_id", "0"))
        except ValueError:
            row_id = 0
        return (year, str(row.get("polity_id", "")), str(row.get("ruler_id", "")), row_id)

    return sorted(rows, key=sort_key)


def main() -> int:
    master_fields, master_rows = read_rows(MASTER)
    ruler_fields, ruler_rows = read_rows(RULERS_CSV)
    yearly_fields, yearly_rows = read_rows(YEARLY)
    issue_fields, issue_rows = read_rows(ISSUES_CSV)
    capital_fields, capital_rows = read_rows(CAPITALS_CSV)
    territory_fields, territory_rows = read_rows(TERRITORY_OVERRIDES)

    master_rows = [row for row in master_rows if row.get("polity_id") not in MANAGED_POLITY_IDS]
    ruler_rows = [
        row for row in ruler_rows
        if row.get("ruler_id") not in MANAGED_RULER_IDS and row.get("polity_id") not in MANAGED_POLITY_IDS
    ]
    issue_rows = [row for row in issue_rows if not row.get("issue_id", "").startswith(ISSUE_PREFIX)]
    capital_rows = [
        row for row in capital_rows
        if row.get("capital_event_id") not in MANAGED_CAPITAL_IDS and row.get("polity_id") not in MANAGED_POLITY_IDS
    ]
    territory_rows = [row for row in territory_rows if row.get("polity_id") not in MANAGED_POLITY_IDS]

    master_rows.extend(POLITIES)
    ruler_rows.extend(RULERS)
    capital_rows.extend(CAPITAL_EVENTS)
    issue_rows.extend(ISSUES)
    territory_rows.extend(TERRITORY_ROWS)
    yearly_rows = build_yearly_rows(yearly_rows, POLITIES, RULERS)

    master_rows.sort(key=lambda row: row.get("polity_id", ""))
    ruler_rows.sort(key=lambda row: row.get("ruler_id", ""))
    capital_rows.sort(key=lambda row: row.get("capital_event_id", ""))
    issue_rows.sort(key=lambda row: row.get("issue_id", ""))
    territory_rows.sort(key=lambda row: row.get("polity_id", ""))

    write_rows(MASTER, master_fields, master_rows)
    write_rows(RULERS_CSV, ruler_fields, ruler_rows)
    write_rows(YEARLY, yearly_fields, yearly_rows)
    write_rows(ISSUES_CSV, issue_fields, issue_rows)
    write_rows(CAPITALS_CSV, capital_fields, capital_rows)
    write_rows(TERRITORY_OVERRIDES, territory_fields, territory_rows)

    print(
        "Added Republican-period v03 slice:",
        f"{len(POLITIES)} polities,",
        f"{len(RULERS)} rulers/government heads,",
        f"{len(CAPITAL_EVENTS)} capital events,",
        f"{len(ISSUES)} issues,",
        f"{len(TERRITORY_ROWS)} territory overrides.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
