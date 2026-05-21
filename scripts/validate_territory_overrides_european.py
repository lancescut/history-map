#!/usr/bin/env python3
"""Validate input/vEuropean/territory_overrides_vEuropean.csv.

Checks:
- polity_id exists in input/vEuropean/european_history_polities_master_vEuropean.csv.
- Each token in admin_ids resolves to one of:
  * ISO3 string (e.g. FRA, DEU, ITA): matches admin_id in eu_adm0_normalized.geojson
    (which is the aggregated European ADM0 collection).
  * `{ISO2}-{region}` (e.g. DE-BY, IT-25, GB-SCT): matches admin_id in any of the
    per-federation ADM1 normalized geojsons (deu_adm1_normalized.geojson,
    ita_adm1_normalized.geojson, etc.).
  * Neighbor ISO3 (e.g. TUR, EGY, MAR): matches iso_a3 in neighbor_adm0.geojson.
- valid_from_year ≤ valid_to_year; confidence_score ∈ [0, 100].

Unlike vIndian's `IND` all-country shorthand, vEuropean has no single
"all-Europe" token — pan-European overrides must enumerate ISOs explicitly.
Free-text tokens (uncoded) are warnings, not errors (transitional state).

Exit code 0 = pass; 1 = at least one error.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "input" / "vEuropean"
BOUNDARY_DIR = INPUT_DIR / "admin_boundaries"
OVERRIDES_PATH = INPUT_DIR / "territory_overrides_vEuropean.csv"
MASTER_PATH = INPUT_DIR / "european_history_polities_master_vEuropean.csv"
ADM0_PATH = BOUNDARY_DIR / "eu_adm0_normalized.geojson"
NEIGHBOR_PATH = BOUNDARY_DIR / "neighbor_adm0.geojson"

# ADM1 normalized files glob — pick up every {iso3}_adm1_normalized.geojson present.
ADM1_PATTERN = "*_adm1_normalized.geojson"

# {ISO2}-{1..4 chars alphanumeric} — ISO 3166-2 form used as ADM1 admin_id.
ADM1_TOKEN_RE = re.compile(r"^[A-Z]{2}-[A-Z0-9]{1,12}(-[0-9]+)?$")
ISO3_TOKEN_RE = re.compile(r"^[A-Z]{3}$")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def pipe_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in str(value).split("|") if v.strip()]


def load_adm1_ids() -> set[str]:
    """Union of admin_id values across all per-federation ADM1 normalized files."""
    ids: set[str] = set()
    for path in sorted(BOUNDARY_DIR.glob(ADM1_PATTERN)):
        data = read_json(path) or {"features": []}
        for feat in data.get("features", []):
            admin_id = (feat.get("properties", {}).get("admin_id") or "").strip()
            if admin_id:
                ids.add(admin_id)
    return ids


def main() -> int:
    if not OVERRIDES_PATH.exists():
        print(f"ERROR: {OVERRIDES_PATH} not found", file=sys.stderr)
        return 1

    polities = read_csv(MASTER_PATH)
    valid_polity_ids = {(p.get("polity_id") or "").strip() for p in polities}

    adm0_data = read_json(ADM0_PATH) or {"features": []}
    valid_eu_iso = {(f["properties"].get("admin_id") or "").upper() for f in adm0_data["features"]}
    neighbor_data = read_json(NEIGHBOR_PATH) or {"features": []}
    valid_neighbor_iso = {(f["properties"].get("iso_a3") or "").upper() for f in neighbor_data["features"]}
    valid_adm1 = load_adm1_ids()

    overrides = read_csv(OVERRIDES_PATH)
    errors: list[str] = []
    warnings: list[str] = []
    stats = {
        "total_rows": len(overrides),
        "with_admin_ids": 0,
        "fully_resolved": 0,
        "free_text_only": 0,
        "unmapped_polities": 0,
    }

    for i, row in enumerate(overrides, start=2):  # +1 header, +1 1-based
        polity_id = (row.get("polity_id") or "").strip()
        if not polity_id:
            errors.append(f"row {i}: empty polity_id")
            continue
        if polity_id not in valid_polity_ids:
            errors.append(f"row {i}: polity_id {polity_id} not in master csv")

        admin_ids_raw = (row.get("admin_ids") or "").strip()
        tokens = pipe_list(admin_ids_raw)
        if not tokens:
            stats["unmapped_polities"] += 1
            continue
        stats["with_admin_ids"] += 1

        unknown_tokens: list[str] = []
        resolved_tokens: list[str] = []
        free_text_tokens: list[str] = []
        for token in tokens:
            token_u = token.upper()
            if ADM1_TOKEN_RE.match(token_u):
                if token_u in valid_adm1:
                    resolved_tokens.append(token_u)
                else:
                    unknown_tokens.append(token)
            elif ISO3_TOKEN_RE.match(token_u):
                if token_u in valid_eu_iso or token_u in valid_neighbor_iso:
                    resolved_tokens.append(token_u)
                else:
                    unknown_tokens.append(token)
            else:
                free_text_tokens.append(token)

        for u in unknown_tokens:
            errors.append(f"row {i} (polity_id={polity_id}): unknown admin_id token '{u}'")

        if resolved_tokens and not free_text_tokens and not unknown_tokens:
            stats["fully_resolved"] += 1
        if free_text_tokens and not resolved_tokens:
            stats["free_text_only"] += 1
            warnings.append(
                f"row {i} (polity_id={polity_id}): admin_ids contains only free text "
                f"({', '.join(free_text_tokens)}); territory will not render."
            )
        elif free_text_tokens:
            warnings.append(
                f"row {i} (polity_id={polity_id}): mixed coded + free text "
                f"({', '.join(free_text_tokens)} ignored); coded tokens still render."
            )

        # Year sanity
        try:
            from_year = int(row.get("valid_from_year") or 0)
        except ValueError:
            errors.append(f"row {i}: valid_from_year not integer ({row.get('valid_from_year')!r})")
            from_year = 0
        try:
            to_year = int(row.get("valid_to_year") or 0)
        except ValueError:
            errors.append(f"row {i}: valid_to_year not integer ({row.get('valid_to_year')!r})")
            to_year = 0
        if from_year and to_year and from_year > to_year:
            errors.append(f"row {i}: valid_from_year ({from_year}) > valid_to_year ({to_year})")

        # Confidence
        conf_raw = (row.get("confidence_score") or "").strip()
        if conf_raw:
            try:
                conf = float(conf_raw)
                if conf < 0 or conf > 100:
                    errors.append(f"row {i}: confidence_score out of range [0,100]: {conf}")
            except ValueError:
                errors.append(f"row {i}: confidence_score not numeric: {conf_raw!r}")

    print(f"[validate_territory_overrides_vEuropean]")
    print(f"  total rows                : {stats['total_rows']}")
    print(f"  rows with admin_ids       : {stats['with_admin_ids']}")
    print(f"  fully resolved (renderable): {stats['fully_resolved']}")
    print(f"  free text only            : {stats['free_text_only']}")
    print(f"  unmapped polities         : {stats['unmapped_polities']}")
    print(f"  unmapped/total ratio       : {stats['unmapped_polities']}/{stats['total_rows']}")
    print(f"  ADM0 admin_ids loaded     : {len(valid_eu_iso)}")
    print(f"  ADM1 admin_ids loaded     : {len(valid_adm1)}")
    print(f"  neighbor ISO3 loaded      : {len(valid_neighbor_iso)}")
    if warnings:
        print(f"\n  {len(warnings)} warnings:")
        for w in warnings[:20]:
            print(f"    - {w}")
        if len(warnings) > 20:
            print(f"    ... ({len(warnings) - 20} more)")
    if errors:
        print(f"\n  {len(errors)} ERRORS:")
        for e in errors[:30]:
            print(f"    - {e}")
        if len(errors) > 30:
            print(f"    ... ({len(errors) - 30} more)")
        return 1
    print("\n  OK (no errors)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
