#!/usr/bin/env python3
"""Generate a v03-compatible yearly table for non-China world history datasets."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = ROOT / "input"

MASTER_FIELDS = [
    "polity_id",
    "macro_period",
    "dynasty_name",
    "polity_name",
    "polity_aliases",
    "polity_display_name",
    "polity_name_disambiguation",
    "polity_name_review_status",
    "polity_name_risk_flags",
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

RULER_FIELDS = [
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

YEARLY_MASTER_FIELDS = [
    "macro_period",
    "dynasty_name",
    "polity_name",
    "polity_aliases",
    "polity_display_name",
    "polity_name_disambiguation",
    "polity_name_review_status",
    "polity_name_risk_flags",
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
]

YEARLY_FIELDS = ["row_id", "polity_id", "ruler_id", "row_granularity", "year", "year_label"] + YEARLY_MASTER_FIELDS + RULER_FIELDS


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{(k or "").lstrip("\ufeff"): (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def write_rows(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fields} for row in rows])


def year_label(year: int) -> str:
    if year < 0:
        return f"公元前{abs(year)}年"
    return f"{year}年"


def parse_year(raw: str) -> int | None:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def iter_years(start: int, end: int) -> range:
    lo, hi = sorted((start, end))
    return range(lo, hi + 1)


def load_manifest(dataset_dir: Path) -> dict[str, str]:
    manifest_path = dataset_dir / "dataset_manifest_vIndian.json"
    generic_path = dataset_dir / "dataset_manifest.json"
    path = manifest_path if manifest_path.exists() else generic_path
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset manifest in {dataset_dir}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Dataset directory under input/, e.g. vIndian")
    args = parser.parse_args()

    dataset_dir = INPUT_ROOT / args.dataset
    manifest = load_manifest(dataset_dir)
    files = manifest["files"]

    master_path = dataset_dir / files["polities_master"]
    rulers_path = dataset_dir / files["rulers_master"]
    yearly_path = dataset_dir / files["polities_yearly"]

    master_rows = read_rows(master_path)
    ruler_rows = read_rows(rulers_path)

    rulers_by_polity: dict[str, list[dict[str, str]]] = {}
    for ruler in ruler_rows:
        rulers_by_polity.setdefault(ruler["polity_id"], []).append(ruler)

    yearly_rows: list[dict[str, str]] = []
    for polity in sorted(master_rows, key=lambda row: (parse_year(row.get("polity_start_year")) or 999999, row["polity_id"])):
        start = parse_year(polity.get("polity_start_year", ""))
        end = parse_year(polity.get("polity_end_year", ""))
        if start is None or end is None:
            continue

        for year in iter_years(start, end):
            if year == 0:
                continue
            matched = []
            for ruler in rulers_by_polity.get(polity["polity_id"], []):
                r_start = parse_year(ruler.get("ruler_reign_start_year", ""))
                r_end = parse_year(ruler.get("ruler_reign_end_year", ""))
                if r_start is None or r_end is None:
                    continue
                lo, hi = sorted((r_start, r_end))
                if lo <= year <= hi:
                    matched.append(ruler)

            if not matched:
                base = {
                    "row_id": f"year_ind_{year}_{polity['polity_id']}_none",
                    "polity_id": polity["polity_id"],
                    "ruler_id": "",
                    "row_granularity": "year_polity_unmatched_ruler",
                    "year": str(year),
                    "year_label": year_label(year),
                }
                for field in YEARLY_MASTER_FIELDS:
                    base[field] = polity.get(field, "")
                yearly_rows.append(base)
                continue

            for ruler in sorted(matched, key=lambda row: row["ruler_id"]):
                base = {
                    "row_id": f"year_ind_{year}_{polity['polity_id']}_{ruler['ruler_id']}",
                    "polity_id": polity["polity_id"],
                    "ruler_id": ruler["ruler_id"],
                    "row_granularity": "year_polity_ruler",
                    "year": str(year),
                    "year_label": year_label(year),
                }
                for field in YEARLY_MASTER_FIELDS:
                    base[field] = polity.get(field, "")
                for field in RULER_FIELDS:
                    base[field] = ruler.get(field, "")
                yearly_rows.append(base)

    yearly_rows.sort(key=lambda row: (int(row["year"]), row["polity_id"], row.get("ruler_id", "")))
    write_rows(yearly_path, YEARLY_FIELDS, yearly_rows)
    print(f"Wrote {len(yearly_rows)} yearly rows to {yearly_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
