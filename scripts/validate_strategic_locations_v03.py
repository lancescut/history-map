#!/usr/bin/env python3
"""Validate the v03 strategic locations input table.

The strategic-location layer is intentionally CSV-first: adding a new pass,
battlefield, river crossing, corridor, port, or allusion site should only
require editing input/v03/strategic_locations_v03.csv and regenerating data.
This validator keeps that table compatible with the public JSON/GeoJSON
generation path.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "input" / "v03"
STRATEGIC_PATH = INPUT_DIR / "strategic_locations_v03.csv"
EVENTS_PATH = INPUT_DIR / "historical_events_v03.csv"
ANECDOTES_PATH = INPUT_DIR / "historical_anecdotes_v03.csv"
POLITIES_PATH = INPUT_DIR / "chinese_history_polities_master_v03.csv"

REQUIRED_FIELDS = [
    "location_id",
    "name",
    "aliases",
    "category",
    "icon_key",
    "importance_level",
    "display_priority",
    "start_year",
    "end_year",
    "active_years_raw",
    "related_event_ids",
    "related_anecdote_ids",
    "related_polity_ids",
    "related_people",
    "historical_name",
    "modern_name",
    "modern_admin_units_raw",
    "longitude",
    "latitude",
    "location_precision",
    "location_confidence_score",
    "strategic_summary",
    "historical_significance",
    "source_titles",
    "source_urls",
    "source_type",
    "confidence_note",
    "review_status",
    "review_note",
]

CATEGORIES = {
    "pass",
    "battlefield",
    "river_crossing",
    "mountain_corridor",
    "fortress_city",
    "transport_hub",
    "frontier_gate",
    "maritime_port",
    "cultural_allusion",
}
PRECISIONS = {"exact", "city", "region", "approximate"}
REVIEW_STATUSES = {"verified", "needs_review", "candidate", "rejected"}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def split_list(value: str) -> list[str]:
    return [piece.strip() for piece in re.split(r"[|；;、,，]", value or "") if piece.strip()]


def int_value(value: str, field: str, row_no: int, errors: list[str], *, allow_blank: bool = True) -> int | None:
    value = (value or "").strip()
    if not value:
        if not allow_blank:
            errors.append(f"row {row_no}: {field} is required")
        return None
    try:
        parsed = int(value)
    except ValueError:
        errors.append(f"row {row_no}: {field} must be an integer, got {value!r}")
        return None
    if parsed == 0 and field in {"start_year", "end_year"}:
        errors.append(f"row {row_no}: {field} must not use year 0")
    return parsed


def validate_active_years(raw: str, row_no: int, errors: list[str]) -> None:
    for token in split_list(raw):
        if ":" in token:
            start_raw, end_raw = token.split(":", 1)
            try:
                start = int(start_raw)
                end = int(end_raw)
            except ValueError:
                errors.append(f"row {row_no}: active_years_raw range {token!r} must be start:end integers")
                continue
            if start == 0 or end == 0:
                errors.append(f"row {row_no}: active_years_raw must not use year 0")
            if start > end:
                errors.append(f"row {row_no}: active_years_raw range {token!r} has start > end")
            continue
        try:
            year = int(token)
        except ValueError:
            errors.append(f"row {row_no}: active_years_raw token {token!r} must be an integer or start:end range")
            continue
        if year == 0:
            errors.append(f"row {row_no}: active_years_raw must not use year 0")


def load_id_set(path: Path, field: str) -> set[str]:
    return {row.get(field, "").strip() for row in read_csv(path) if row.get(field, "").strip()}


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    if not STRATEGIC_PATH.exists():
        errors.append(f"missing required file: {STRATEGIC_PATH.relative_to(ROOT)}")
        print("\n".join(errors))
        return 1

    with STRATEGIC_PATH.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = [dict(row) for row in reader]

    missing_fields = [field for field in REQUIRED_FIELDS if field not in fields]
    extra_fields = [field for field in fields if field not in REQUIRED_FIELDS]
    if missing_fields:
        errors.append(f"missing fields: {', '.join(missing_fields)}")
    if extra_fields:
        errors.append(f"unexpected fields: {', '.join(extra_fields)}")

    event_ids = load_id_set(EVENTS_PATH, "event_id")
    anecdote_ids = load_id_set(ANECDOTES_PATH, "anecdote_id")
    polity_ids = load_id_set(POLITIES_PATH, "polity_id")

    seen_ids: set[str] = set()
    verified_count = 0
    for row_index, row in enumerate(rows, start=2):
        location_id = (row.get("location_id") or "").strip()
        if not location_id:
            errors.append(f"row {row_index}: location_id is required")
        elif location_id in seen_ids:
            errors.append(f"row {row_index}: duplicate location_id {location_id}")
        else:
            seen_ids.add(location_id)
        if location_id and not re.fullmatch(r"strategic_\d{4}", location_id):
            warnings.append(f"row {row_index}: location_id {location_id} does not match strategic_0000 style")

        name = (row.get("name") or "").strip()
        if not name:
            errors.append(f"row {row_index}: name is required")

        category = (row.get("category") or "").strip()
        if category not in CATEGORIES:
            errors.append(f"row {row_index}: invalid category {category!r}")

        if not (row.get("icon_key") or "").strip():
            errors.append(f"row {row_index}: icon_key is required")

        importance = int_value(row.get("importance_level", ""), "importance_level", row_index, errors, allow_blank=False)
        display_priority = int_value(row.get("display_priority", ""), "display_priority", row_index, errors, allow_blank=False)
        if importance is not None and not (1 <= importance <= 5):
            errors.append(f"row {row_index}: importance_level must be 1..5")
        if display_priority is not None and not (1 <= display_priority <= 6):
            errors.append(f"row {row_index}: display_priority must be 1..6")

        start = int_value(row.get("start_year", ""), "start_year", row_index, errors)
        end = int_value(row.get("end_year", ""), "end_year", row_index, errors)
        if start is not None and end is not None and start > end:
            errors.append(f"row {row_index}: start_year must be <= end_year")
        validate_active_years(row.get("active_years_raw", ""), row_index, errors)

        try:
            longitude = float((row.get("longitude") or "").strip())
            latitude = float((row.get("latitude") or "").strip())
        except ValueError:
            errors.append(f"row {row_index}: longitude and latitude must be numbers")
        else:
            if not (-180 <= longitude <= 180):
                errors.append(f"row {row_index}: longitude out of range")
            if not (-90 <= latitude <= 90):
                errors.append(f"row {row_index}: latitude out of range")

        precision = (row.get("location_precision") or "").strip()
        if precision not in PRECISIONS:
            errors.append(f"row {row_index}: invalid location_precision {precision!r}")

        confidence = int_value(
            row.get("location_confidence_score", ""),
            "location_confidence_score",
            row_index,
            errors,
            allow_blank=False,
        )
        if confidence is not None and not (0 <= confidence <= 100):
            errors.append(f"row {row_index}: location_confidence_score must be 0..100")

        if not (row.get("strategic_summary") or "").strip():
            errors.append(f"row {row_index}: strategic_summary is required")
        has_link_or_significance = any(
            (row.get(field) or "").strip()
            for field in ["related_event_ids", "related_anecdote_ids", "historical_significance"]
        )
        if not has_link_or_significance:
            errors.append(
                f"row {row_index}: must include related_event_ids, related_anecdote_ids, or historical_significance"
            )

        review_status = (row.get("review_status") or "").strip()
        if review_status not in REVIEW_STATUSES:
            errors.append(f"row {row_index}: invalid review_status {review_status!r}")
        if review_status == "verified":
            verified_count += 1
            if not (row.get("source_titles") or "").strip():
                errors.append(f"row {row_index}: verified row requires source_titles")
            if not (row.get("source_urls") or "").strip():
                errors.append(f"row {row_index}: verified row requires source_urls")
            if confidence is not None and confidence < 60:
                warnings.append(f"row {row_index}: verified row has confidence below default display threshold")

        for event_id in split_list(row.get("related_event_ids", "")):
            if event_id not in event_ids:
                errors.append(f"row {row_index}: related_event_id {event_id!r} not found")
        for anecdote_id in split_list(row.get("related_anecdote_ids", "")):
            if anecdote_id not in anecdote_ids:
                errors.append(f"row {row_index}: related_anecdote_id {anecdote_id!r} not found")
        for polity_id in split_list(row.get("related_polity_ids", "")):
            if polity_id not in polity_ids:
                errors.append(f"row {row_index}: related_polity_id {polity_id!r} not found")

    if errors:
        print("Strategic location validation FAILED")
        for error in errors:
            print(f"FAIL: {error}")
        for warning in warnings:
            print(f"WARN: {warning}")
        return 1

    print(
        "Strategic location validation PASS:",
        f"{len(rows)} rows,",
        f"{verified_count} verified,",
        f"{len(warnings)} warnings",
    )
    for warning in warnings:
        print(f"WARN: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
