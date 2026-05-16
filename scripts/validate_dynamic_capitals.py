#!/usr/bin/env python3
"""Validate generated dynamic-capital assets."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data" / "v03"
INPUT_DIR = ROOT / "input" / "v03"


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def coordinate_count(geometry) -> int:
    count = 0

    def walk(value) -> None:
        nonlocal count
        if isinstance(value, list) and value and isinstance(value[0], (int, float)):
            count += 1
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(geometry.get("coordinates", []))
    return count


def main() -> None:
    metadata = load_json(DATA_DIR / "metadata.json")
    capitals = load_json(DATA_DIR / "capitals.json")
    territories = load_json(DATA_DIR / "territories" / "approx_polities.geojson")
    modern_admin_units = load_json(DATA_DIR / "territories" / "modern_admin_units.geojson")
    boundary_manifest = load_json(INPUT_DIR / "admin_boundaries" / "admin_boundary_source_manifest.json")
    assert_true(metadata["has_year_zero"] is False, "metadata must report no year zero")
    assert_true(metadata["capital_event_count"] == len(capitals["capital_events"]), "capital event count mismatch")
    assert_true(metadata["capital_migration_count"] == len(capitals["capital_migrations"]), "migration count mismatch")
    assert_true(metadata["territory_polity_count"] == len(territories["features"]), "territory feature count mismatch")
    assert_true(metadata["admin_boundary_feature_count"] == len(modern_admin_units["features"]), "admin boundary feature count mismatch")
    assert_true(metadata["admin_boundary_source"] == boundary_manifest["source"], "admin boundary source mismatch")
    assert_true(metadata["territory_geometry_quality"]["formal_rect_fixture"] is False, "formal boundary fixture must not be rectangular")
    assert_true((DATA_DIR / "territories" / "territory_match_report.csv").exists(), "territory report missing")
    assert_true((DATA_DIR / "territories" / "admin_units_by_polity.geojson").exists(), "admin-unit debug layer missing")

    for feature in territories["features"]:
        assert_true(coordinate_count(feature["geometry"]) > 20, f"{feature['properties']['polity_name']} still looks like a rectangle fixture")
        assert_true(
            feature["properties"].get("geometry_source", "").endswith("china_adm1_normalized.geojson"),
            f"{feature['properties']['polity_name']} must use normalized ADM1 geometry",
        )

    event_ids = {event["capital_event_id"] for event in capitals["capital_events"]}
    assert_true(len(event_ids) == len(capitals["capital_events"]), "capital event ids must be unique")

    for event in capitals["capital_events"]:
        assert_true(event["valid_from_year"] != 0 and event["valid_to_year"] != 0, f"{event['capital_event_id']} includes year 0")
        assert_true(event["valid_from_year"] <= event["valid_to_year"], f"{event['capital_event_id']} has inverted range")
        assert_true(event["source_titles"], f"{event['capital_event_id']} missing source_titles")
        assert_true(event["source_raw"], f"{event['capital_event_id']} missing source_raw")
        assert_true(isinstance(event["longitude"], (int, float)), f"{event['capital_event_id']} longitude invalid")
        assert_true(isinstance(event["latitude"], (int, float)), f"{event['capital_event_id']} latitude invalid")

    required_migration_years = {-899, -514, 196, 313, 398, 494, 1153, 1214, 1421, 1644}
    assert_true(required_migration_years.issubset(set(metadata["capital_migration_years"])), "missing required migration years")

    checks = [
        (-514, "吴国", "吴", True),
        (1421, "明朝", "北京", True),
        (1644, "清朝", "北京", True),
        (-688, "楚国", None, False),
    ]
    for year, polity_name, capital_name, expects_capital in checks:
        year_data = load_json(DATA_DIR / "years" / f"{year}.json")
        polity = next((item for item in year_data["polities"] if item["polity_name"] == polity_name), None)
        assert_true(polity is not None, f"{polity_name} missing in {year}")
        if expects_capital:
            assert_true(polity["capitals"], f"{polity_name} should have active capital in {year}")
            assert_true(
                any(capital["capital_name_historical"] == capital_name for capital in polity["capitals"]),
                f"{polity_name} should have active capital {capital_name} in {year}",
            )
            assert_true(polity["capital_quality"]["status"] in {"present", "disputed"}, "capital status should be present/disputed")
        else:
            assert_true(not polity["capitals"], f"{polity_name} should not have pseudo capital in {year}")
            assert_true(polity["capital_quality"]["status"] == "missing", "missing capital must be explicit")

    territory_checks = [
        (-688, "楚国", True),
        (-688, "东周", True),
        (-221, "秦朝", True),
        (1421, "明朝", True),
        (1644, "清朝", True),
    ]
    for year, polity_name, expects_territory in territory_checks:
        year_data = load_json(DATA_DIR / "years" / f"{year}.json")
        polity = next((item for item in year_data["polities"] if item["polity_name"] == polity_name), None)
        assert_true(polity is not None, f"{polity_name} missing in {year}")
        territory = polity["territory"]
        assert_true("territory_status" in territory, f"{polity_name} missing territory_status")
        if expects_territory:
            assert_true(territory["territory_status"] != "missing", f"{polity_name} should have approximate territory")
            assert_true(territory["approx_area_km2"] is not None, f"{polity_name} missing approximate area")
            assert_true(territory["geometry_ref"], f"{polity_name} missing geometry_ref")
        else:
            assert_true(territory["territory_status"] == "missing", f"{polity_name} should explicitly lack territory")

    print("Dynamic capital and territory validation passed")


if __name__ == "__main__":
    main()
