#!/usr/bin/env python3
"""Audit and disambiguate v03 polity names.

The public UI can show ancient polity names next to modern basemap labels, so
names that collide with modern country names need an explicit display label.
This script is intentionally idempotent: it normalizes the input v03 CSVs,
writes a full audit report, and leaves searchable aliases intact.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "input" / "v03"

MASTER = INPUT / "chinese_history_polities_master_v03.csv"
YEARLY = INPUT / "chinese_history_polities_yearly_v03.csv"
RULERS = INPUT / "chinese_history_rulers_master_v03.csv"
AUDIT = INPUT / "polity_name_audit_v03.csv"

NEW_POLITY_FIELDS = [
    "polity_display_name",
    "polity_name_disambiguation",
    "polity_name_review_status",
    "polity_name_risk_flags",
]

AUDIT_FIELDS = [
    "polity_id",
    "original_polity_name",
    "canonical_polity_name",
    "suggested_display_name",
    "risk_type",
    "severity",
    "review_status",
    "basis_sources",
    "handling_note",
]

MODERN_COUNTRY_BASELINE_SOURCES = (
    "中华人民共和国外交部“国家和组织”|联合国会员国中文列表"
)
MODERN_COUNTRY_BASELINE_URLS = (
    "https://www.mfa.gov.cn/web/gjhdq_676201/|https://www.un.org/zh/about-us/member-states"
)

MODERN_COUNTRY_NAMES = set(
    """
    中国 美国 英国 法国 德国 意大利 俄罗斯 日本 韩国 朝鲜 越南 老挝 柬埔寨 泰国 缅甸 印度
    巴基斯坦 阿富汗 伊朗 伊拉克 叙利亚 土耳其 埃及 希腊 西班牙 葡萄牙 荷兰 比利时 瑞士
    瑞典 挪威 丹麦 芬兰 波兰 匈牙利 捷克 斯洛伐克 奥地利 乌克兰 白俄罗斯 立陶宛 拉脱维亚
    爱沙尼亚 摩尔多瓦 罗马尼亚 保加利亚 塞尔维亚 克罗地亚 斯洛文尼亚 波黑 黑山 阿尔巴尼亚
    加拿大 墨西哥 巴西 阿根廷 智利 秘鲁 哥伦比亚 澳大利亚 新西兰 南非 摩洛哥 苏丹 利比亚
    突尼斯 以色列 沙特 阿联酋 卡塔尔 巴林 科威特 阿曼 也门 约旦 黎巴嫩 蒙古 尼泊尔 不丹
    孟加拉 斯里兰卡 马来西亚 新加坡 印尼 菲律宾 文莱 东帝汶 哈萨克斯坦 乌兹别克斯坦
    吉尔吉斯斯坦 塔吉克斯坦 土库曼斯坦
    """.split()
)

MODERN_ABBREVIATION_COLLISIONS = {
    "英": "英国/不列颠",
    "韩": "韩国/大韩民国",
    "越": "越南",
}

NAME_OVERRIDES: dict[str, dict[str, str]] = {
    "polity_0119": {
        "canonical_name": "英氏国",
        "display_name": "英氏国",
        "aliases": "英;英氏;古英国;英国（古代诸侯国非近代英国）",
        "disambiguation": "古籍称“英”或“英氏”，这里指周代偃姓英氏诸侯国，不是近代英国。",
        "review_status": "verified",
        "risk_flags": "modern_country_collision|modern_abbreviation_collision|source_mismatch",
        "source_titles": "《史记·楚世家》 | 《春秋左传·僖公十七年》",
        "source_urls": "https://ctext.org/shiji/chu-shi-jia/zh | https://ctext.org/chun-qiu-zuo-zhuan/xi-gong/zh",
        "source_raw": "《史记·楚世家》载楚成王二十六年灭英；《春秋左传·僖公十七年》载齐、徐伐英氏。",
        "confidence_note": "古籍称“英”或“英氏”，本库显示为“英氏国”以避免与近代英国混淆。",
        "severity": "high",
        "handling_note": "改展示和标准名为“英氏国”，保留“英国”作为明确消歧的检索别名。",
    },
    "polity_0161": {
        "display_name": "韩国（战国）",
        "aliases": "韩;韩國;韩国（战国七雄）;战国韩国",
        "disambiguation": "战国七雄之一，姬姓韩氏诸侯国，非现代大韩民国。",
        "review_status": "verified",
        "risk_flags": "modern_country_collision|modern_abbreviation_collision",
        "severity": "high",
        "handling_note": "保留教材常用名“韩国”，前端展示为“韩国（战国）”。",
    },
    "polity_0145": {
        "display_name": "越国",
        "aliases": "越;越國;于越;春秋越国;战国越国",
        "disambiguation": "春秋战国时期越国，非现代越南。",
        "review_status": "verified",
        "risk_flags": "modern_abbreviation_collision",
        "severity": "medium",
        "handling_note": "保留历史通用名，补充消歧说明。",
    },
    "polity_0014": {
        "display_name": "六国（录国）",
        "aliases": "六;录国;錄國;六國（錄國）",
        "disambiguation": "这里是安徽六安一带偃姓古国，又作录国，不是“战国六国”的泛称。",
        "review_status": "verified",
        "risk_flags": "common_term_collision",
        "severity": "medium",
        "handling_note": "前端展示为“六国（录国）”，避免误读成战国六国集合。",
    },
    "polity_0029": {
        "canonical_name": "北虢国",
        "display_name": "北虢国",
        "aliases": "北虢国沛县;北虢國沛縣;东虢国;東虢國",
        "disambiguation": "原字段把现代/整理地点“沛县”混入国名，本轮只保留国名“北虢国”。",
        "review_status": "verified",
        "risk_flags": "location_leak",
        "severity": "high",
        "handling_note": "将“沛县”移出国名语义，保留原串为检索别名。",
    },
    "polity_0108": {
        "canonical_name": "威武军",
        "display_name": "威武军（福州）",
        "aliases": "福州/威武军;福州政权;威武军",
        "disambiguation": "五代十国时期以福州为中心的地方政权，斜杠旧名改为别名。",
        "review_status": "verified",
        "risk_flags": "location_leak",
        "severity": "medium",
        "handling_note": "标准名去掉斜杠，展示名保留福州信息。",
    },
    "polity_0097": {
        "canonical_name": "清源军",
        "display_name": "清源军（平海军）",
        "aliases": "清源军/平海军;平海军;清源軍;平海軍",
        "disambiguation": "五代十国时期泉漳地方政权，斜杠旧名改为别名。",
        "review_status": "verified",
        "risk_flags": "location_leak",
        "severity": "medium",
        "handling_note": "标准名去掉斜杠，展示名保留平海军异名。",
    },
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\ufeff", "").replace("\xa0", " ").strip())


def split_aliases(value: str) -> list[str]:
    return [clean(piece) for piece in re.split(r"[|；;、,，]", clean(value)) if clean(piece)]


def join_unique(values: list[str], sep: str = ";") -> str:
    drop_values = {"英国（古代诸侯国", "非近代英国）"}
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        value = clean(value)
        if value in drop_values:
            continue
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return sep.join(out)


def read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = [(field or "").lstrip("\ufeff") for field in (reader.fieldnames or [])]
        rows = []
        for raw in reader:
            rows.append({(key or "").lstrip("\ufeff"): clean(value) for key, value in raw.items()})
        return rows, fieldnames


def write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def extend_fields(fieldnames: list[str], fields: list[str], after: str = "polity_aliases") -> list[str]:
    out = [field for field in fieldnames if field not in fields]
    try:
        index = out.index(after) + 1
    except ValueError:
        index = len(out)
    return out[:index] + fields + out[index:]


def detect_flags(name: str, row: dict[str, str]) -> set[str]:
    flags: set[str] = set()
    if name in MODERN_COUNTRY_NAMES:
        flags.add("modern_country_collision")
    if name.endswith("国") and name[:-1] in MODERN_ABBREVIATION_COLLISIONS:
        flags.add("modern_abbreviation_collision")
    if re.search(r"[县市省]|一带|/|（|\(|；|;|,|，", name):
        flags.add("location_leak")
    try:
        if int(row.get("confidence_score") or "0") < 70:
            flags.add("low_confidence")
    except ValueError:
        flags.add("low_confidence")
    if row.get("polity_id") == "polity_0119":
        flags.add("source_mismatch")
    return flags


def severity_for(flags: set[str]) -> str:
    if "modern_country_collision" in flags or "location_leak" in flags:
        return "high"
    if "modern_abbreviation_collision" in flags or "common_term_collision" in flags:
        return "medium"
    if "low_confidence" in flags:
        return "low"
    return "none"


def apply_override(row: dict[str, str], override: dict[str, str]) -> None:
    original_name = clean(row.get("polity_name"))
    if override.get("canonical_name"):
        row["polity_name"] = override["canonical_name"]
    existing_aliases = split_aliases(row.get("polity_aliases", ""))
    override_aliases = split_aliases(override.get("aliases", ""))
    row["polity_aliases"] = join_unique([*existing_aliases, original_name, *override_aliases])
    row["polity_display_name"] = override.get("display_name", row.get("polity_name", ""))
    row["polity_name_disambiguation"] = override.get("disambiguation", "")
    row["polity_name_review_status"] = override.get("review_status", "verified")
    row["polity_name_risk_flags"] = override.get("risk_flags", "")
    if override.get("source_titles"):
        row["polity_source_titles"] = override["source_titles"]
    if override.get("source_urls"):
        row["polity_source_urls"] = override["source_urls"]
    if override.get("source_raw"):
        row["polity_source_raw"] = override["source_raw"]
    if override.get("confidence_note"):
        row["confidence_note"] = override["confidence_note"]


def enrich_row(row: dict[str, str], source_by_id: dict[str, dict[str, str]] | None = None) -> None:
    polity_id = clean(row.get("polity_id"))
    source = source_by_id.get(polity_id, {}) if source_by_id else row
    if polity_id in NAME_OVERRIDES:
        apply_override(row, NAME_OVERRIDES[polity_id])
        return
    flags = detect_flags(clean(row.get("polity_name")), source)
    row["polity_display_name"] = row.get("polity_display_name") or row.get("polity_name", "")
    row["polity_name_disambiguation"] = row.get("polity_name_disambiguation", "")
    row["polity_name_review_status"] = "needs_review" if flags else "verified"
    row["polity_name_risk_flags"] = "|".join(sorted(flags))


def build_audit(master_rows: list[dict[str, str]], original_names: dict[str, str]) -> list[dict[str, str]]:
    audit_rows: list[dict[str, str]] = []
    for row in master_rows:
        polity_id = row["polity_id"]
        flags = set(filter(None, row.get("polity_name_risk_flags", "").split("|")))
        override = NAME_OVERRIDES.get(polity_id, {})
        severity = override.get("severity") or severity_for(flags)
        review_status = row.get("polity_name_review_status") or ("needs_review" if flags else "verified")
        basis = MODERN_COUNTRY_BASELINE_SOURCES
        if row.get("polity_source_titles"):
            basis = f"{basis}|{row['polity_source_titles']}"
        audit_rows.append(
            {
                "polity_id": polity_id,
                "original_polity_name": original_names.get(polity_id, row.get("polity_name", "")),
                "canonical_polity_name": row.get("polity_name", ""),
                "suggested_display_name": row.get("polity_display_name", "") or row.get("polity_name", ""),
                "risk_type": "|".join(sorted(flags)) or "none",
                "severity": severity,
                "review_status": review_status,
                "basis_sources": basis,
                "handling_note": override.get("handling_note")
                or (row.get("polity_name_disambiguation", "") if flags else "全量遍历未发现国名误导风险。"),
            }
        )
    return audit_rows


def main() -> int:
    master_rows, master_fields = read_rows(MASTER)
    original_names = {row["polity_id"]: clean(row.get("polity_name")) for row in master_rows}
    master_by_id = {row["polity_id"]: row for row in master_rows}

    for row in master_rows:
        enrich_row(row)

    yearly_rows, yearly_fields = read_rows(YEARLY)
    for row in yearly_rows:
        enrich_row(row, master_by_id)

    ruler_rows, ruler_fields = read_rows(RULERS)
    for row in ruler_rows:
        source = master_by_id.get(row.get("polity_id", ""))
        if source:
            row["polity_name"] = source["polity_name"]

    audit_rows = build_audit(master_rows, original_names)

    write_rows(MASTER, master_rows, extend_fields(master_fields, NEW_POLITY_FIELDS))
    write_rows(YEARLY, yearly_rows, extend_fields(yearly_fields, NEW_POLITY_FIELDS))
    write_rows(RULERS, ruler_rows, ruler_fields)
    write_rows(AUDIT, audit_rows, AUDIT_FIELDS)

    risky = [row for row in audit_rows if row["risk_type"] != "none"]
    unresolved = [row for row in risky if row["review_status"] != "verified"]
    print(
        f"polity name audit complete: {len(master_rows)} polities, "
        f"{len(risky)} flagged, {len(unresolved)} need review"
    )
    print(f"baseline sources: {MODERN_COUNTRY_BASELINE_URLS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
