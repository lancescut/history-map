#!/usr/bin/env python3
"""Download Natural Earth 110m admin-0 country polygons for vEuropean neighbors.

Mirror of scripts/prepare_indian_neighbor_boundaries.py for Europe. Output is
used to draw modern neighbor outlines on the map when vEuropean dataset is
active, so historical polities that intersected with non-European powers
(Byzantine/Roman south & east frontiers, Crusader states, Ottoman expansion,
Phoenician/Carthaginian Mediterranean network) have a visible canvas.

Europe itself is rendered from `eu_adm0_normalized.geojson` (aggregated from
per-country geoBoundaries pulls in prepare_european_admin_boundaries.py).
This script handles only the non-European neighbors that European polities
historically crossed into or contested.

Output: input/vEuropean/admin_boundaries/neighbor_adm0.geojson
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "input" / "vEuropean" / "admin_boundaries" / "neighbor_adm0.geojson"
MANIFEST_PATH = ROOT / "input" / "vEuropean" / "admin_boundaries" / "neighbor_adm0_manifest.json"

SOURCE_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
    "ne_110m_admin_0_countries.geojson"
)

# 欧洲史外部相关近邻 ISO-A3 列表。覆盖地中海东岸（拜占庭、十字军、奥斯曼）、
# 北非（迦太基、罗马、汪达尔、阿拉伯哈里发、奥斯曼）、波斯/美索不达米亚
# （帕提亚-萨珊与罗马-拜占庭东境对抗）。
# 不含欧洲国家本身——欧洲 ADM0 由 prepare_european_admin_boundaries.py 单独聚合。
NEIGHBOR_ISO_CODES = {
    "TUR": "土耳其",   # 安纳托利亚：拜占庭、奥斯曼核心
    "SYR": "叙利亚",   # 罗马叙利亚行省、十字军、奥斯曼
    "LBN": "黎巴嫩",   # 腓尼基（推罗、西顿）、十字军
    "ISR": "以色列",   # 圣地、十字军、罗马犹太行省（NE 110m 不含独立巴勒斯坦 feature，ISR 几何覆盖该区域）
    "JOR": "约旦",     # 十字军、纳巴泰、奥斯曼
    "EGY": "埃及",     # 托勒密、罗马、拜占庭、法蒂玛、马穆鲁克、奥斯曼
    "LBY": "利比亚",   # 罗马阿非利加行省、汪达尔、阿拉伯、奥斯曼
    "TUN": "突尼斯",   # 迦太基、罗马、汪达尔、阿拉伯、奥斯曼
    "DZA": "阿尔及利亚", # 努米底亚、罗马、汪达尔、阿拉伯、奥斯曼
    "MAR": "摩洛哥",   # 毛里塔尼亚、罗马、阿拉伯、马里尼德
    "IRN": "伊朗",     # 帕提亚、萨珊、阿巴斯（与拜占庭/罗马东境长期对抗）
    "IRQ": "伊拉克",   # 萨珊、阿拉伯哈里发、奥斯曼（十字军与拜占庭交错）
}


def fetch_json(url: str, label: str, max_retries: int = 4) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"fetching {label} (attempt {attempt})...", flush=True)
            request = urllib.request.Request(
                url, headers={"User-Agent": "history-map-veuropean-neighbor-prepare/1"}
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
        f"Wrote {len(features_out)} vEuropean neighbor admin-0 polygons "
        f"({OUT_PATH.stat().st_size/1024:.1f} KiB) to {OUT_PATH.relative_to(ROOT)}"
    )
    missing = sorted(set(NEIGHBOR_ISO_CODES) - seen_iso)
    if missing:
        print(f"  warn: missing ISO codes {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
