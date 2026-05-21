#!/usr/bin/env python3
"""Validate v03-compatible world history datasets under input/."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = ROOT / "input"
TEMPLATE_DIR = INPUT_ROOT / "templates"

POLITY_TYPES_ALLOW_EMPTY = True
LOCATION_PRECISIONS = {"exact", "city", "region", "approximate", "unknown", ""}
REVIEW_STATUSES = {"verified", "candidate", "needs_review", "rejected", ""}
MYTH_TRADITION_TYPES = {
    "epic",
    "puranic_genealogy",
    "dynastic_origin_legend",
    "regional_royal_chronicle",
    "ritual_text_context",
    "literary_cultural_cycle",
    "",
}
MYTH_HISTORICITY_STATUSES = {
    "mythic_tradition",
    "epic_tradition",
    "legendary_dynastic_origin",
    "puranic_chronology",
    "textual_cultural_horizon",
    "mixed_history_memory",
    "rejected_as_history",
    "",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{(k or "").lstrip("\ufeff"): (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def read_header(path: Path) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [(field or "").lstrip("\ufeff") for field in next(csv.reader(f))]


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["check_name", "status", "checked_count", "issue_count", "details"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_int(raw: str) -> int | None:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def parse_float(raw: str) -> float | None:
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return None


def split_ids(raw: str) -> list[str]:
    return [part.strip() for part in (raw or "").split("|") if part.strip()]


def load_manifest(dataset_dir: Path) -> dict:
    for name in ("dataset_manifest_vIndian.json", "dataset_manifest.json"):
        path = dataset_dir / name
        if path.exists():
            with path.open(encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError(f"Missing dataset manifest in {dataset_dir}")


def add(checks: list[dict[str, str]], name: str, checked: int, issues: list[str], warn: bool = False) -> None:
    checks.append(
        {
            "check_name": name,
            "status": "PASS" if not issues else ("WARN" if warn else "FAIL"),
            "checked_count": str(checked),
            "issue_count": str(len(issues)),
            "details": "; ".join(issues[:12]),
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Dataset directory under input/, e.g. vIndian")
    args = parser.parse_args()

    dataset_dir = INPUT_ROOT / args.dataset
    manifest = load_manifest(dataset_dir)
    files = manifest["files"]

    paths = {key: dataset_dir / value for key, value in files.items()}
    polities = read_rows(paths["polities_master"])
    rulers = read_rows(paths["rulers_master"])
    yearly = read_rows(paths["polities_yearly"])
    events = read_rows(paths["historical_events"])
    anecdotes = read_rows(paths["historical_anecdotes"])
    myths = read_rows(paths["mythological_timeline"]) if "mythological_timeline" in paths else []
    strategic = read_rows(paths["strategic_locations"])
    capitals = read_rows(paths["capital_events"])
    issues = read_rows(paths["issues"])
    sources = read_rows(paths["sources"])

    polity_ids = {row["polity_id"] for row in polities}
    ruler_ids = {row["ruler_id"] for row in rulers}
    event_ids = {row["event_id"] for row in events}
    anecdote_ids = {row["anecdote_id"] for row in anecdotes}
    source_ids = {row["source_id"] for row in sources}

    checks: list[dict[str, str]] = []

    # Template headers.
    template_map = manifest.get("template_files", {})
    header_issues = []
    for key, template_name in template_map.items():
        dataset_path = paths.get(key)
        template_path = TEMPLATE_DIR / template_name
        if not dataset_path or not dataset_path.exists() or not template_path.exists():
            header_issues.append(f"{key}:missing")
            continue
        if read_header(dataset_path) != read_header(template_path):
            header_issues.append(f"{key}:header_mismatch")
    add(checks, "template_header_compatibility", len(template_map), header_issues)

    # Unique ids.
    for key, rows, field in [
        ("polity_id_unique", polities, "polity_id"),
        ("ruler_id_unique", rulers, "ruler_id"),
        ("event_id_unique", events, "event_id"),
        ("anecdote_id_unique", anecdotes, "anecdote_id"),
        ("myth_id_unique", myths, "myth_id"),
        ("strategic_location_id_unique", strategic, "location_id"),
        ("source_id_unique", sources, "source_id"),
    ]:
        counter = Counter(row.get(field, "") for row in rows)
        bad = [value for value, count in counter.items() if not value or count > 1]
        add(checks, key, len(rows), bad)

    # Year ranges and no year zero.
    polity_year_issues = []
    for row in polities:
        start = parse_int(row.get("polity_start_year", ""))
        end = parse_int(row.get("polity_end_year", ""))
        if start is None or end is None:
            polity_year_issues.append(f"{row.get('polity_id')}:missing_year")
        elif start == 0 or end == 0:
            polity_year_issues.append(f"{row.get('polity_id')}:year_zero")
        elif start > end:
            polity_year_issues.append(f"{row.get('polity_id')}:start_after_end")
    add(checks, "polity_year_ranges", len(polities), polity_year_issues)

    yearly_range_issues = []
    yearly_index: dict[str, set[int]] = {}
    master_by_id = {row["polity_id"]: row for row in polities}
    for row in yearly:
        year = parse_int(row.get("year", ""))
        if year is None:
            yearly_range_issues.append(f"{row.get('row_id')}:bad_year")
            continue
        if year == 0:
            yearly_range_issues.append(f"{row.get('row_id')}:year_zero")
        yearly_index.setdefault(row.get("polity_id", ""), set()).add(year)
        master = master_by_id.get(row.get("polity_id", ""))
        if not master:
            continue
        start = parse_int(master.get("polity_start_year", ""))
        end = parse_int(master.get("polity_end_year", ""))
        if start is not None and end is not None and not (start <= year <= end):
            yearly_range_issues.append(f"{row.get('row_id')}:outside_polity")
    add(checks, "year_within_polity_range", len(yearly), yearly_range_issues)

    completeness_issues = []
    for row in polities:
        start = parse_int(row.get("polity_start_year", ""))
        end = parse_int(row.get("polity_end_year", ""))
        if start is None or end is None:
            continue
        expected = {year for year in range(start, end + 1) if year != 0}
        missing = expected - yearly_index.get(row["polity_id"], set())
        if missing:
            completeness_issues.append(f"{row['polity_id']}:missing {len(missing)}")
    add(checks, "polity_year_completeness", len(polities), completeness_issues)

    join_issues = [row.get("row_id", "") for row in yearly if row.get("polity_id", "") not in polity_ids]
    add(checks, "yearly_polity_id_join", len(yearly), join_issues)
    ruler_join_issues = [row.get("row_id", "") for row in yearly if row.get("ruler_id") and row.get("ruler_id") not in ruler_ids]
    add(checks, "yearly_ruler_id_join", len(yearly), ruler_join_issues)
    ruler_polity_issues = [row.get("ruler_id", "") for row in rulers if row.get("polity_id", "") not in polity_ids]
    add(checks, "ruler_polity_id_join", len(rulers), ruler_polity_issues)

    # Source presence and confidence scores.
    missing_source_issues = [row["polity_id"] for row in polities if not row.get("polity_source_titles") or not row.get("polity_source_urls")]
    add(checks, "polity_sources_present", len(polities), missing_source_issues)
    score_issues = []
    for collection, rows, field in [
        ("polity", polities, "confidence_score"),
        ("ruler", rulers, "ruler_confidence_score"),
        ("event", events, "confidence_score"),
        ("myth", myths, "confidence_score"),
        ("strategic", strategic, "location_confidence_score"),
    ]:
        for row in rows:
            score = parse_float(row.get(field, ""))
            if score is None or score < 0 or score > 100:
                score_issues.append(f"{collection}:{row.get('polity_id') or row.get('ruler_id') or row.get('event_id') or row.get('location_id')}")
    add(checks, "confidence_scores_0_100", len(polities) + len(rulers) + len(events) + len(myths) + len(strategic), score_issues)

    # Events and anecdotes.
    event_issues = []
    for row in events:
        year = parse_int(row.get("year", ""))
        if year is None or year == 0:
            event_issues.append(f"{row.get('event_id')}:bad_year")
        for pid in split_ids(row.get("related_polity_ids", "")):
            if pid not in polity_ids:
                event_issues.append(f"{row.get('event_id')}:bad_polity:{pid}")
        if not row.get("source_titles") or not row.get("source_urls"):
            event_issues.append(f"{row.get('event_id')}:missing_source")
    add(checks, "historical_events_valid", len(events), event_issues)

    anecdote_issues = []
    for row in anecdotes:
        year = parse_int(row.get("year", ""))
        if row.get("year") and (year is None or year == 0):
            anecdote_issues.append(f"{row.get('anecdote_id')}:bad_year")
        for pid in split_ids(row.get("related_polity_ids", "")):
            if pid not in polity_ids:
                anecdote_issues.append(f"{row.get('anecdote_id')}:bad_polity:{pid}")
        if row.get("review_status", "") not in REVIEW_STATUSES:
            anecdote_issues.append(f"{row.get('anecdote_id')}:bad_review_status")
    add(checks, "historical_anecdotes_valid", len(anecdotes), anecdote_issues)

    myth_issues = []
    for row in myths:
        year = parse_int(row.get("year", ""))
        coverage_start = parse_int(row.get("coverage_start_year", ""))
        coverage_end = parse_int(row.get("coverage_end_year", ""))
        if year is None or year == 0:
            myth_issues.append(f"{row.get('myth_id')}:bad_year")
        if coverage_start is None or coverage_end is None:
            myth_issues.append(f"{row.get('myth_id')}:bad_coverage")
        elif coverage_start == 0 or coverage_end == 0 or coverage_start > coverage_end:
            myth_issues.append(f"{row.get('myth_id')}:bad_coverage")
        if row.get("tradition_type", "") not in MYTH_TRADITION_TYPES:
            myth_issues.append(f"{row.get('myth_id')}:bad_tradition_type")
        if row.get("historicity_status", "") not in MYTH_HISTORICITY_STATUSES:
            myth_issues.append(f"{row.get('myth_id')}:bad_historicity_status")
        if row.get("review_status", "") not in REVIEW_STATUSES:
            myth_issues.append(f"{row.get('myth_id')}:bad_review_status")
        for pid in split_ids(row.get("related_historical_polity_ids", "")):
            if pid not in polity_ids:
                myth_issues.append(f"{row.get('myth_id')}:bad_polity:{pid}")
        if not row.get("summary") or not row.get("historical_boundary_note"):
            myth_issues.append(f"{row.get('myth_id')}:missing_boundary_note")
        if not row.get("source_titles") or not row.get("source_urls"):
            myth_issues.append(f"{row.get('myth_id')}:missing_source")
    add(checks, "mythological_timeline_valid", len(myths), myth_issues)

    # Coordinates.
    coord_issues = []
    for collection, rows, lon_field, lat_field, id_field in [
        ("event", events, "longitude", "latitude", "event_id"),
        ("myth", myths, "longitude", "latitude", "myth_id"),
        ("strategic", strategic, "longitude", "latitude", "location_id"),
        ("capital", capitals, "longitude", "latitude", "capital_event_id"),
    ]:
        for row in rows:
            lon_raw = row.get(lon_field, "")
            lat_raw = row.get(lat_field, "")
            if not lon_raw and not lat_raw:
                continue
            lon = parse_float(lon_raw)
            lat = parse_float(lat_raw)
            if lon is None or lat is None or not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
                coord_issues.append(f"{collection}:{row.get(id_field)}")
    add(checks, "coordinate_ranges", len(events) + len(strategic) + len(capitals), coord_issues)

    strategic_issues = []
    for row in strategic:
        if row.get("review_status", "") not in REVIEW_STATUSES:
            strategic_issues.append(f"{row.get('location_id')}:bad_review_status")
        if row.get("location_precision", "") not in LOCATION_PRECISIONS:
            strategic_issues.append(f"{row.get('location_id')}:bad_precision")
        for eid in split_ids(row.get("related_event_ids", "")):
            if eid not in event_ids:
                strategic_issues.append(f"{row.get('location_id')}:bad_event:{eid}")
        for aid in split_ids(row.get("related_anecdote_ids", "")):
            if aid not in anecdote_ids:
                strategic_issues.append(f"{row.get('location_id')}:bad_anecdote:{aid}")
        for pid in split_ids(row.get("related_polity_ids", "")):
            if pid not in polity_ids:
                strategic_issues.append(f"{row.get('location_id')}:bad_polity:{pid}")
    add(checks, "strategic_locations_valid", len(strategic), strategic_issues)

    source_ref_issues = []
    for row in issues:
        if row.get("polity_id") and row["polity_id"] not in polity_ids:
            source_ref_issues.append(f"{row.get('issue_id')}:bad_polity")
    for row in sources:
        if not row.get("source_title") or not row.get("source_url") or not row.get("credibility_tier"):
            source_ref_issues.append(f"{row.get('source_id')}:missing_fields")
    add(checks, "sources_and_issues_valid", len(sources) + len(issues), source_ref_issues)

    report_path = paths["validation_report"]
    write_rows(report_path, checks)

    failed = [row for row in checks if row["status"] == "FAIL"]
    for row in checks:
        print(f"{row['status']:4} {row['check_name']}: {row['issue_count']}")
    if failed:
        print(f"Validation failed; report written to {report_path}")
        return 1
    print(f"Validation passed; report written to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
