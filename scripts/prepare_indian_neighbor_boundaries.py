#!/usr/bin/env python3
"""Download Natural Earth 110m admin-0 country polygons for vIndian neighbors.

Mirror of scripts/prepare_neighbor_boundaries.py for India. Output is used to
draw modern neighbor outlines on the map when vIndian dataset is active, so
historical polities that crossed into Pakistan/Bangladesh/Afghanistan etc. have
a visible canvas. ADM0 only (no ADM1 split) since vIndian polity_overrides
maps to IND ADM1/ADM2 anyway.

Output: input/vIndian/admin_boundaries/neighbor_adm0.geojson
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "input" / "vIndian" / "admin_boundaries" / "neighbor_adm0.geojson"
MANIFEST_PATH = ROOT / "input" / "vIndian" / "admin_boundaries" / "neighbor_adm0_manifest.json"

SOURCE_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
    "ne_110m_admin_0_countries.geojson"
)

# 印度近邻 ISO-A3 列表（不含印度自身，IND 在 admin_boundaries/india_adm1_* 中已有）
NEIGHBOR_ISO_CODES = {
    "PAK": "巴基斯坦",
    "BGD": "孟加拉国",
    "NPL": "尼泊尔",
    "BTN": "不丹",
    "LKA": "斯里兰卡",
    "MMR": "缅甸",
    "AFG": "阿富汗",
    "MDV": "马尔代夫",
    "CHN": "中国",   # 主要呈现西藏/新疆毗邻轮廓
    "IRN": "伊朗",   # 莫卧儿/萨非阿富汗早期相关
}


def fetch_json(url: str, label: str, max_retries: int = 4) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"fetching {label} (attempt {attempt})...", flush=True)
            request = urllib.request.Request(
                url, headers={"User-Agent": "history-map-vindian-neighbor-prepare/1"}
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = response.read().decode("utf-8")
            return json.loads(payload)
        except Exception as error:  # noqa: BLE001
            last_error = error
            print(f"  warn: {error}", file=sys.stderr, flush=True)
    raise RuntimeError(f"download failed for {label}: {last_error}")


def country_iso(props: dict) -> str:
    for key in ("ADM0_A3", "ISO_A3", "SOV_A3"):
        value = props.get(key)
        if isinstance(value, str) and len(value) == 3:
            return value.upper()
    return ""


def main() -> int:
    raw = fetch_json(SOURCE_URL, "ne_110m_admin_0_countries")
    features_in = raw.get("features", [])
    features_out: list[dict] = []
    seen_iso: set[str] = set()
    for feature in features_in:
        iso = country_iso(feature.get("properties", {}))
        if iso not in NEIGHBOR_ISO_CODES or iso in seen_iso:
            continue
        seen_iso.add(iso)
        name_zh = NEIGHBOR_ISO_CODES[iso]
        props_in = feature.get("properties", {})
        features_out.append(
            {
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
        )
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
        f"Wrote {len(features_out)} vIndian neighbor admin-0 polygons "
        f"({OUT_PATH.stat().st_size/1024:.1f} KiB) to {OUT_PATH.relative_to(ROOT)}"
    )
    missing = sorted(set(NEIGHBOR_ISO_CODES) - seen_iso)
    if missing:
        print(f"  warn: missing ISO codes {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
