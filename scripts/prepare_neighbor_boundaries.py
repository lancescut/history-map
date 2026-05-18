#!/usr/bin/env python3
"""Download Natural Earth 110m admin-0 countries and write a slim邻国 GeoJSON.

跨境疆域近似（MRD §6.4 + release_note batch19）：批次 19 已经把汉/唐/元/清等
大一统王朝的 `modern_admin_units_raw` 扩展到蒙古、俄、中亚、朝鲜半岛、越南
等地区，但当前 generate_public_data.py 只加载中国 ADM1，导致跨境部分被裁剪。
本脚本输出邻国 ADM0 polygon 作为跨境近似几何数据源。

数据：Natural Earth public domain (CC0)，约 250 KiB。
输出：`input/v03/admin_boundaries/neighbor_adm0.geojson`
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "input" / "v03" / "admin_boundaries" / "neighbor_adm0.geojson"
MANIFEST_PATH = ROOT / "input" / "v03" / "admin_boundaries" / "neighbor_adm0_manifest.json"
ADM1_OUT_PATH = ROOT / "input" / "v03" / "admin_boundaries" / "neighbor_adm1.geojson"
ADM1_MANIFEST_PATH = ROOT / "input" / "v03" / "admin_boundaries" / "neighbor_adm1_manifest.json"

SOURCE_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
    "ne_110m_admin_0_countries.geojson"
)
ADM1_SOURCE_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
    "ne_50m_admin_1_states_provinces.geojson"
)

# release_note batch19 涉及的邻国 ISO-A3 列表
# 通过 ADM0_A3/ISO_A3/SOV_A3 任一字段匹配
NEIGHBOR_ISO_CODES = {
    # 内陆亚邻
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
    # 东南
    "MMR": "缅甸",
    "LAO": "老挝",
    "VNM": "越南",
    "THA": "泰国",
    "KHM": "柬埔寨",
    # 东
    "PRK": "朝鲜",
    "KOR": "韩国",
    "JPN": "日本",
    # 北
    "TWN": "台湾",
}


def fetch_json(url: str, label: str, max_retries: int = 4) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"fetching {label} (attempt {attempt})...", flush=True)
            request = urllib.request.Request(
                url, headers={"User-Agent": "history-map-neighbor-prepare/1"}
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = response.read().decode("utf-8")
            return json.loads(payload)
        except Exception as error:  # noqa: BLE001
            last_error = error
            print(f"  warn: {error}", file=sys.stderr, flush=True)
    raise RuntimeError(f"download failed for {label}: {last_error}")


def fetch_countries() -> dict:
    return fetch_json(SOURCE_URL, "ne_110m_admin_0_countries")


# 邻国关注的 ADM1。键是稳定 admin_id（自造），值是 (中文名, iso_a2, name_en 关键词正则)
# 因为 Natural Earth code_hasc 字段在俄罗斯/中亚普遍错位，这里用 name_en 关键词匹配。
NEIGHBOR_ADM1_TARGETS = {
    # 俄罗斯远东/东西伯利亚
    "RU-PRIMORSKY": ("滨海边疆区", "RU", "Primorsky"),
    "RU-KHABAROVSK": ("哈巴罗夫斯克边疆区", "RU", "Khabarovsk"),
    "RU-AMUR": ("阿穆尔州", "RU", r"^Amur$|Amurskaya"),
    "RU-JEWISH": ("犹太自治州", "RU", "Jewish"),
    "RU-SAKHALIN": ("萨哈林州", "RU", "Sakhalin"),
    "RU-TUVA": ("图瓦共和国", "RU", r"^Tuva$|Tyva"),
    "RU-BURYATIA": ("布里亚特共和国", "RU", "Buryatia"),
    "RU-IRKUTSK": ("伊尔库茨克州", "RU", "Irkutsk"),
    "RU-ZABAYKAL": ("外贝加尔边疆区", "RU", "Zabaykal|Chita"),
    "RU-SAKHA": ("萨哈共和国", "RU", "Sakha|Yakut"),
    "RU-CHUKOT": ("楚科奇自治区", "RU", "Chukot"),
    "RU-MAGADAN": ("马加丹州", "RU", "Magadan"),
    "RU-KAMCHATKA": ("堪察加边疆区", "RU", "Kamchatka"),
    "RU-ALTAI-REP": ("阿尔泰共和国", "RU", "Altay|Altai Republic"),
    "RU-KEMEROVO": ("克麦罗沃州", "RU", "Kemerovo"),
    "RU-TOMSK": ("托木斯克州", "RU", "Tomsk"),
    "RU-NOVOSIBIRSK": ("新西伯利亚州", "RU", "Novosibirsk"),
    "RU-OMSK": ("鄂木斯克州", "RU", "Omsk"),
    "RU-KRASNOYARSK": ("克拉斯诺亚尔斯克边疆区", "RU", "Krasnoyarsk"),
    "RU-KHAKASSIA": ("哈卡斯共和国", "RU", "Khakassia"),
    # 哈萨克斯坦（巴尔喀什以东和南部）
    "KZ-ALMATY": ("阿拉木图州", "KZ", "Almaty"),
    "KZ-EAST": ("东哈萨克斯坦州", "KZ", "East Kazakhstan|Vostochno"),
    "KZ-ZHAMBYL": ("江布尔州", "KZ", "Zhambyl|Jambyl"),
    "KZ-KYZYLORDA": ("克孜勒奥尔达州", "KZ", "Kyzylorda"),
    "KZ-SOUTH": ("南哈萨克斯坦州", "KZ", "South Kazakhstan|Turkistan|Yuzhno"),
    "KZ-KARAGANDA": ("卡拉干达州", "KZ", "Karaganda|Qaraghandy"),
    # 吉尔吉斯
    "KG-NARYN": ("纳伦州", "KG", "Naryn"),
    "KG-ISSYK": ("伊塞克湖州", "KG", "Issyk"),
    "KG-OSH": ("奥什州", "KG", r"^Osh"),
    # 越南北部
    "VN-LANGSON": ("谅山省", "VN", "Lang Son"),
    "VN-HAGIANG": ("河江省", "VN", "Ha Giang"),
    "VN-CAOBANG": ("高平省", "VN", "Cao Bang"),
    "VN-LAICHAU": ("莱州省", "VN", "Lai Chau"),
    "VN-DIENBIEN": ("奠边省", "VN", "Dien Bien"),
    # 缅甸北部
    "MM-KACHIN": ("克钦邦", "MM", "Kachin"),
    "MM-SHAN": ("掸邦", "MM", "Shan"),
}


def fetch_adm1() -> dict:
    return fetch_json(ADM1_SOURCE_URL, "ne_50m_admin_1_states_provinces")


import re as _re


def adm1_name_text(props: dict) -> str:
    parts: list[str] = []
    for key in ("name_en", "name", "name_alt", "woe_name"):
        value = props.get(key)
        if isinstance(value, str) and value:
            parts.append(value)
    return " | ".join(parts)


def slim_adm1(payload: dict) -> tuple[list[dict], list[str]]:
    features: list[dict] = []
    matched_ids: list[str] = []
    used = set()
    compiled: list[tuple[str, str, str, "_re.Pattern[str]"]] = [
        (admin_id, chinese, iso, _re.compile(pattern, _re.IGNORECASE))
        for admin_id, (chinese, iso, pattern) in NEIGHBOR_ADM1_TARGETS.items()
    ]
    for feature in payload.get("features", []):
        props = feature.get("properties", {})
        iso = (props.get("iso_a2") or "").upper()
        haystack = adm1_name_text(props)
        for admin_id, chinese_name, target_iso, pattern in compiled:
            if admin_id in used:
                continue
            if iso != target_iso:
                continue
            if not pattern.search(haystack):
                continue
            features.append(
                {
                    "type": "Feature",
                    "geometry": feature["geometry"],
                    "properties": {
                        "admin_id": admin_id,
                        "name": chinese_name,
                        "name_en": props.get("name_en") or props.get("name") or "",
                        "admin_level": "adm1",
                        "iso_a2": iso,
                        "source": "Natural Earth 50m admin-1 (public domain)",
                    },
                }
            )
            used.add(admin_id)
            matched_ids.append(admin_id)
            break
    return features, matched_ids


def country_iso(props: dict) -> str:
    for key in ("ADM0_A3", "ISO_A3", "SOV_A3"):
        value = props.get(key)
        if isinstance(value, str) and len(value) == 3:
            return value.upper()
    return ""


def main() -> int:
    raw = fetch_countries()
    features_in = raw.get("features", [])
    features_out: list[dict] = []
    seen_iso: set[str] = set()
    for feature in features_in:
        iso = country_iso(feature.get("properties", {}))
        if iso not in NEIGHBOR_ISO_CODES:
            continue
        if iso in seen_iso:
            continue
        seen_iso.add(iso)
        name_zh = NEIGHBOR_ISO_CODES[iso]
        props_in = feature.get("properties", {})
        feature_out = {
            "type": "Feature",
            "geometry": feature["geometry"],
            "properties": {
                "admin_id": f"X-{iso}",
                "iso_a3": iso,
                "name": name_zh,
                "name_en": props_in.get("ADMIN") or props_in.get("NAME_EN") or props_in.get("NAME") or "",
                "admin_level": "country",
                "source": "Natural Earth (CC0) ne_110m_admin_0_countries",
            },
        }
        features_out.append(feature_out)
    collection = {"type": "FeatureCollection", "features": features_out}
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(collection, ensure_ascii=False), encoding="utf-8")
    MANIFEST_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
                "source": "Natural Earth 110m admin_0_countries (public domain)",
                "source_url": SOURCE_URL,
                "license": "Public domain (CC0)",
                "feature_count": len(features_out),
                "countries": sorted(seen_iso),
                "missing": sorted(set(NEIGHBOR_ISO_CODES) - seen_iso),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"Wrote {len(features_out)} neighbor admin-0 polygons "
        f"({OUT_PATH.stat().st_size/1024:.1f} KiB) to {OUT_PATH.relative_to(ROOT)}"
    )
    missing = sorted(set(NEIGHBOR_ISO_CODES) - seen_iso)
    if missing:
        print(f"  warn: missing ISO codes {missing}")

    # ADM1 切片
    try:
        adm1_raw = fetch_adm1()
    except Exception as error:  # noqa: BLE001
        print(f"  ! ADM1 download failed, skipping: {error}", file=sys.stderr)
        return 0
    adm1_features, adm1_matched = slim_adm1(adm1_raw)
    ADM1_OUT_PATH.write_text(
        json.dumps({"type": "FeatureCollection", "features": adm1_features}, ensure_ascii=False),
        encoding="utf-8",
    )
    ADM1_MANIFEST_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
                "source": "Natural Earth 50m admin_1_states_provinces (public domain)",
                "source_url": ADM1_SOURCE_URL,
                "license": "Public domain (CC0)",
                "feature_count": len(adm1_features),
                "matched": adm1_matched,
                "missing": sorted(set(NEIGHBOR_ADM1_TARGETS) - set(adm1_matched)),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"Wrote {len(adm1_features)} neighbor admin-1 polygons "
        f"({ADM1_OUT_PATH.stat().st_size/1024:.1f} KiB) to {ADM1_OUT_PATH.relative_to(ROOT)}"
    )
    missing_adm1 = sorted(set(NEIGHBOR_ADM1_TARGETS) - set(adm1_matched))
    if missing_adm1:
        print(f"  warn: ADM1 codes not found in NE 50m: {missing_adm1}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
