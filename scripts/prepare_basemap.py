#!/usr/bin/env python3
"""Download Natural Earth 110m physical vectors and write to public/data/basemap/.

These layers serve as a physical-geography backdrop for the dynasty map (海岸线、
陆地、湖泊、河流、地理参考线、冰盖)。Natural Earth 数据为公共领域（CC0），
可以直接打包到产品中。

Run: python3 scripts/prepare_basemap.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "public" / "data" / "basemap"

# Natural Earth 110m physical vectors mirror (Nathan Kelso, public domain)
# https://github.com/nvkelso/natural-earth-vector
BASE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson"

LAYERS = [
    "ne_110m_land",
    "ne_110m_ocean",
    "ne_110m_coastline",
    "ne_110m_lakes",
    "ne_110m_rivers_lake_centerlines",
    "ne_110m_geographic_lines",
    "ne_110m_glaciated_areas",
    "ne_110m_admin_0_boundary_lines_land",
]


def download(name: str, max_retries: int = 4) -> dict:
    url = f"{BASE_URL}/{name}.geojson"
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"  fetching {name} (attempt {attempt})...", flush=True)
            request = urllib.request.Request(url, headers={"User-Agent": "history-map-basemap-prepare/1"})
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = response.read().decode("utf-8")
            return json.loads(payload)
        except Exception as error:  # noqa: BLE001 — surface any transient network error
            last_error = error
            print(f"    warn: {error}", file=sys.stderr, flush=True)
    raise RuntimeError(f"download failed for {name}: {last_error}")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "source": "Natural Earth (public domain) via nvkelso/natural-earth-vector",
        "source_url": BASE_URL,
        "license": "Public domain (CC0)",
        "attribution": "Made with Natural Earth",
        "layers": [],
    }
    for name in LAYERS:
        try:
            data = download(name)
        except Exception as error:  # noqa: BLE001
            print(f"  ! failed: {name}: {error}", file=sys.stderr)
            continue
        out_path = OUT_DIR / f"{name}.geojson"
        with out_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False)
        manifest["layers"].append({
            "name": name,
            "path": f"data/basemap/{name}.geojson",
            "feature_count": len(data.get("features", [])),
            "bytes": out_path.stat().st_size,
        })
    manifest_path = OUT_DIR / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    total_features = sum(layer["feature_count"] for layer in manifest["layers"])
    total_bytes = sum(layer["bytes"] for layer in manifest["layers"])
    print(
        f"Wrote {len(manifest['layers'])} layers · {total_features} features · "
        f"{total_bytes/1024:.1f} KiB to {OUT_DIR.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
