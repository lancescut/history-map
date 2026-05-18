#!/usr/bin/env python3
"""Validate generated dynamic-capital assets."""

from __future__ import annotations

import json
import csv
import re
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
    polities = load_json(DATA_DIR / "polities.json")
    capitals = load_json(DATA_DIR / "capitals.json")
    historical_events = load_json(DATA_DIR / "events.json")
    historical_anecdotes = load_json(DATA_DIR / "anecdotes.json")
    historical_contexts = load_json(DATA_DIR / "contexts.json")
    territories = load_json(DATA_DIR / "territories" / "approx_polities.geojson")
    modern_admin_units = load_json(DATA_DIR / "territories" / "modern_admin_units.geojson")
    county_units = load_json(DATA_DIR / "territories" / "county_units.geojson")
    county_index = load_json(DATA_DIR / "territories" / "polity_county_index.json")
    boundary_manifest = load_json(INPUT_DIR / "admin_boundaries" / "admin_boundary_source_manifest.json")
    assert_true((INPUT_DIR / "polity_name_audit_v03.csv").exists(), "polity name audit report missing")
    assert_true(metadata["has_year_zero"] is False, "metadata must report no year zero")
    assert_true(metadata["capital_event_count"] == len(capitals["capital_events"]), "capital event count mismatch")
    assert_true(metadata["historical_event_count"] == historical_events["event_count"], "historical event count mismatch")
    assert_true(metadata["historical_event_marker_count"] == historical_events["marker_count"], "historical event marker count mismatch")
    assert_true(
        metadata.get("historical_anecdote_count") == historical_anecdotes["anecdote_count"],
        "historical anecdote count mismatch",
    )
    assert_true(
        metadata.get("historical_anecdote_marker_count") == historical_anecdotes["marker_count"],
        "historical anecdote marker count mismatch",
    )
    assert_true(
        metadata.get("historical_context_count") == historical_contexts["context_count"],
        "historical context count mismatch",
    )
    expected_years = [year for year in range(metadata["year_min"], metadata["year_max"] + 1) if year != 0]
    assert_true(
        metadata.get("historical_context_covered_year_count") == len(expected_years),
        "historical context covered year count mismatch",
    )
    assert_true(metadata.get("historical_context_full_year_coverage") is True, "historical contexts must cover every playable year")
    assert_true(historical_contexts.get("covered_year_count") == len(expected_years), "contexts.json covered year count mismatch")
    assert_true(historical_contexts.get("full_year_coverage") is True, "contexts.json must report full year coverage")
    assert_true(metadata["capital_migration_count"] == len(capitals["capital_migrations"]), "migration count mismatch")
    assert_true(metadata["territory_polity_count"] == len(territories["features"]), "territory feature count mismatch")
    assert_true(metadata["admin_boundary_feature_count"] == len(county_units["features"]), "county boundary feature count mismatch")
    assert_true(
        metadata["modern_admin_reference_feature_count"] == len(modern_admin_units["features"]),
        "modern admin reference feature count mismatch",
    )
    assert_true(metadata["admin_boundary_source"] == boundary_manifest["source"], "admin boundary source mismatch")
    assert_true(metadata["county_unit_count"] == len(county_units["features"]), "county unit count mismatch")
    assert_true(len(county_index["polities"]) == metadata["polity_count"], "county index polity count mismatch")
    assert_true(metadata["territory_geometry_quality"]["formal_rect_fixture"] is False, "formal boundary fixture must not be rectangular")
    assert_true((DATA_DIR / "territories" / "territory_match_report.csv").exists(), "territory report missing")
    assert_true((DATA_DIR / "territories" / "admin_units_by_polity.geojson").exists(), "admin-unit debug layer missing")
    assert_true((DATA_DIR / "territories" / "county_units.geojson").exists(), "county-unit layer missing")
    assert_true((DATA_DIR / "territories" / "polity_county_index.json").exists(), "polity county index missing")

    for feature in territories["features"]:
        props = feature["properties"]
        polity_name = props["polity_name"]
        assert_true(coordinate_count(feature["geometry"]) > 20, f"{polity_name} still looks like a rectangle fixture")
        geometry_source = props.get("geometry_source", "")
        county_source = props.get("county_geometry_source", "")
        matched_counties = int(props.get("matched_county_count") or 0)
        cross_border_ids = props.get("cross_border_iso_codes", []) or []
        cross_border_adm1_ids = props.get("cross_border_adm1_ids", []) or []
        matched_admin_ids = props.get("matched_admin_ids", []) or []
        if matched_counties > 0:
            assert_true(
                geometry_source.endswith("china_adm1_normalized.geojson")
                or geometry_source.endswith("china_adm3_normalized.geojson"),
                f"{polity_name} domestic aggregate must use normalized ADM1 or ADM3 geometry",
            )
            assert_true(
                county_source.endswith("china_adm3_normalized.geojson"),
                f"{polity_name} county index must reference normalized ADM3 geometry",
            )
            assert_true(props.get("county_index_ref"), f"{polity_name} missing county index ref")
        elif matched_admin_ids:
            assert_true(
                geometry_source.endswith("china_adm1_normalized.geojson"),
                f"{polity_name} domestic province-only aggregate must use normalized ADM1 geometry",
            )
        else:
            assert_true(
                bool(cross_border_ids or cross_border_adm1_ids),
                f"{polity_name} has geometry without domestic counties or cross-border references",
            )
            assert_true(
                geometry_source.endswith("neighbor_adm0.geojson") or geometry_source.endswith("neighbor_adm1.geojson"),
                f"{polity_name} cross-border geometry must use normalized neighbor geometry",
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

    polity_ids = {row["polity_id"] for row in polities["polities"]}
    modern_country_collisions = {"英国", "韩国"}
    bad_name_pattern = re.compile(r"[县市省]|一带|/|（|\(")
    for polity in polities["polities"]:
        polity_name = polity["polity_name"]
        display_name = polity.get("polity_display_name", "")
        disambiguation = polity.get("polity_name_disambiguation", "")
        assert_true(display_name, f"{polity_name} missing polity_display_name")
        assert_true(polity.get("polity_name_review_status") in {"verified", "needs_review"}, f"{polity_name} invalid name review status")
        if polity_name in modern_country_collisions:
            assert_true(
                display_name != polity_name and disambiguation,
                f"{polity_name} collides with modern country name without disambiguation",
            )
        if bad_name_pattern.search(polity_name):
            assert_true(
                polity.get("polity_name_review_status") == "verified" and disambiguation,
                f"{polity_name} contains location or note text without verified disambiguation",
            )

    year_m1034 = load_json(DATA_DIR / "years" / "-1034.json")
    english_polity = next((item for item in year_m1034["polities"] if item["polity_id"] == "polity_0119"), None)
    assert_true(english_polity is not None, "polity_0119 missing in -1034")
    assert_true(english_polity["polity_name"] == "英氏国", "polity_0119 must be renamed to 英氏国")
    assert_true(english_polity.get("polity_display_name") == "英氏国", "polity_0119 display name must be 英氏国")

    year_m230 = load_json(DATA_DIR / "years" / "-230.json")
    han_polity = next((item for item in year_m230["polities"] if item["polity_id"] == "polity_0161"), None)
    assert_true(han_polity is not None, "polity_0161 missing in -230")
    assert_true(han_polity.get("polity_display_name") == "韩国（战国）", "战国韩国 must use disambiguated display name")

    historical_event_ids = {event["event_id"] for event in historical_events["events"]}
    assert_true(len(historical_event_ids) == len(historical_events["events"]), "historical event ids must be unique")
    assert_true((INPUT_DIR / "historical_anecdotes_v03.csv").exists(), "historical anecdotes csv missing")
    assert_true((INPUT_DIR / "historical_activity_gaps_report_v03.csv").exists(), "historical activity gaps report missing")
    assert_true((INPUT_DIR / "historical_events_v03_review_report.csv").exists(), "historical event review report missing")
    assert_true((INPUT_DIR / "historical_event_coverage_report_v03.csv").exists(), "historical event coverage report missing")
    banned_fragments = ("持续存在", "年度政权格局", "当前有效主都城", "匹配到在位君主", "v03 记录")
    disallowed_event_types = {"polity_status", "period_context", "capital_status", "territory_context", "ruler_reign"}
    coverage_roles = {"exact_year_event", "annual_chronicle", "nearby_enrichment"}
    historical_events_by_year: dict[int, list[dict]] = {}
    for event in historical_events["events"]:
        event_id = event["event_id"]
        assert_true(event["year"] != 0, f"{event_id} includes year 0")
        historical_events_by_year.setdefault(event["year"], []).append(event)
        assert_true(event.get("fact_review_status") == "verified", f"{event_id} is not verified")
        assert_true(event.get("event_type") not in disallowed_event_types, f"{event_id} uses removed event type")
        coverage_role = event.get("coverage_role")
        assert_true(coverage_role in coverage_roles, f"{event_id} invalid coverage_role {coverage_role}")
        assert_true(bool(event.get("coverage_group_id")), f"{event_id} missing coverage_group_id")
        coverage_start = event.get("coverage_start_year")
        coverage_end = event.get("coverage_end_year")
        assert_true(isinstance(coverage_start, int) and coverage_start != 0, f"{event_id} invalid coverage_start_year")
        assert_true(isinstance(coverage_end, int) and coverage_end != 0, f"{event_id} invalid coverage_end_year")
        assert_true(coverage_start <= event["year"] <= coverage_end, f"{event_id} coverage range excludes year")
        assert_true(coverage_role != "range_anchor", f"{event_id} range_anchor must be exported as context, not event")
        assert_true(event.get("date_precision") != "range", f"{event_id} non-range entry cannot use date_precision=range")
        assert_true(isinstance(event.get("longitude"), (int, float)), f"{event_id} missing longitude")
        assert_true(isinstance(event.get("latitude"), (int, float)), f"{event_id} missing latitude")
        location = event.get("location") or {}
        assert_true(location.get("historical_name"), f"{event_id} missing historical location")
        assert_true(location.get("modern_name"), f"{event_id} missing modern location")
        assert_true(location.get("precision") in {"exact", "city", "region", "approximate"}, f"{event_id} invalid location precision")
        assert_true(isinstance(location.get("longitude"), (int, float)), f"{event_id} location missing longitude")
        assert_true(isinstance(location.get("latitude"), (int, float)), f"{event_id} location missing latitude")
        if coverage_role == "annual_chronicle":
            assert_true(len(event.get("source_urls") or []) >= 1, f"{event_id} needs one verified event source url")
        else:
            assert_true(len(event.get("source_urls") or []) >= 2, f"{event_id} needs two event source urls")
        assert_true(len(location.get("source_urls") or []) >= 2, f"{event_id} needs two location source urls")
        for polity_id in event.get("related_polity_ids") or []:
            assert_true(polity_id in polity_ids, f"{event_id} has orphan polity id {polity_id}")
        text = " ".join(str(event.get(field, "")) for field in ("title", "description", "significance", "confidence_note"))
        for fragment in banned_fragments:
            assert_true(fragment not in text, f"{event_id} still contains banned fragment {fragment}")

    context_ids = {context["context_id"] for context in historical_contexts["contexts"]}
    assert_true(len(context_ids) == len(historical_contexts["contexts"]), "historical context ids must be unique")
    assert_true(context_ids, "historical contexts must not be empty")
    for context in historical_contexts["contexts"]:
        context_id = context["context_id"]
        assert_true(context["start_year"] != 0 and context["end_year"] != 0, f"{context_id} includes year 0")
        assert_true(context["start_year"] <= context["end_year"], f"{context_id} has inverted range")
        assert_true(context.get("title"), f"{context_id} missing title")
        assert_true(context.get("description"), f"{context_id} missing description")
        assert_true(isinstance(context.get("longitude"), (int, float)), f"{context_id} missing longitude")
        assert_true(isinstance(context.get("latitude"), (int, float)), f"{context_id} missing latitude")
        location = context.get("location") or {}
        assert_true(location.get("historical_name"), f"{context_id} missing historical location")
        assert_true(location.get("modern_name"), f"{context_id} missing modern location")
        assert_true(location.get("precision") in {"exact", "city", "region", "approximate"}, f"{context_id} invalid location precision")
        assert_true(context.get("source_urls"), f"{context_id} missing source urls")
        text = " ".join(str(context.get(field, "")) for field in ("title", "description", "confidence_note"))
        for fragment in banned_fragments:
            assert_true(fragment not in text, f"{context_id} contains banned fragment {fragment}")

    yearly_context_years: set[int] = set()
    missing_activity_years: list[int] = []
    for year in expected_years:
        year_data = load_json(DATA_DIR / "years" / f"{year}.json")
        context_rows = year_data.get("historical_contexts") or []
        if context_rows:
            yearly_context_years.add(year)
        has_content = bool(year_data.get("historical_events") or year_data.get("historical_anecdotes") or context_rows)
        if not has_content:
            missing_activity_years.append(year)
        for context in context_rows:
            context_id = context.get("context_id")
            assert_true(context_id in context_ids, f"{context_id} missing from contexts.json")
            assert_true(context.get("current_year") == year, f"{context_id} current_year mismatch in {year}")
            assert_true(0 <= context.get("progress_ratio", -1) <= 1, f"{context_id} invalid progress_ratio")
    assert_true(not missing_activity_years, f"missing all historical content for years {missing_activity_years[:12]}")
    assert_true(len(yearly_context_years) == len(expected_years), "year files must include contexts for every playable year")

    anecdote_ids = {anecdote["anecdote_id"] for anecdote in historical_anecdotes["anecdotes"]}
    assert_true(len(anecdote_ids) == len(historical_anecdotes["anecdotes"]), "historical anecdote ids must be unique")
    assert_true(len(anecdote_ids) >= 80, "historical anecdotes must include at least 80 verified entries")
    anecdote_types = {"chengyu", "historical_story", "literary_allusion", "folk_tale"}
    anecdote_source_types = {
        "classic_text",
        "official_history",
        "literary_collection",
        "folk_tradition",
        "secondary_reference",
    }
    anecdote_banned_fragments = (
        "体现了",
        "说明了",
        "具有重要意义",
        "据资料显示",
        "本文讲述",
        "我们可以看到",
        "该典故",
    )
    for anecdote in historical_anecdotes["anecdotes"]:
        anecdote_id = anecdote["anecdote_id"]
        assert_true(anecdote["event_id"] == anecdote_id, f"{anecdote_id} event_id mismatch")
        assert_true(anecdote.get("item_kind") == "anecdote", f"{anecdote_id} invalid item_kind")
        assert_true(anecdote.get("event_type") == "allusion", f"{anecdote_id} invalid event_type")
        assert_true(anecdote.get("coverage_role") == "anecdote", f"{anecdote_id} invalid coverage_role")
        assert_true(anecdote.get("anecdote_type") in anecdote_types, f"{anecdote_id} invalid anecdote_type")
        assert_true(anecdote.get("source_type") in anecdote_source_types, f"{anecdote_id} invalid source_type")
        assert_true(anecdote.get("fact_review_status") == "verified", f"{anecdote_id} is not verified")
        assert_true(anecdote["year"] != 0, f"{anecdote_id} includes year 0")
        assert_true(anecdote.get("dynasty_name"), f"{anecdote_id} missing dynasty_name")
        assert_true(anecdote.get("source_title"), f"{anecdote_id} missing source_title")
        assert_true(anecdote.get("source_urls") or anecdote.get("source_type") == "folk_tradition", f"{anecdote_id} missing source_url")
        story_text = anecdote.get("story_text", "")
        assert_true(90 <= len(story_text) <= 240, f"{anecdote_id} story_text length out of range")
        assert_true(bool(anecdote.get("description")), f"{anecdote_id} missing short description")
        assert_true(isinstance(anecdote.get("longitude"), (int, float)), f"{anecdote_id} missing longitude")
        assert_true(isinstance(anecdote.get("latitude"), (int, float)), f"{anecdote_id} missing latitude")
        location = anecdote.get("location") or {}
        assert_true(location.get("historical_name"), f"{anecdote_id} missing historical location")
        assert_true(location.get("modern_name"), f"{anecdote_id} missing modern location")
        assert_true(location.get("precision") in {"exact", "city", "region", "approximate"}, f"{anecdote_id} invalid location precision")
        for polity_id in anecdote.get("related_polity_ids") or []:
            assert_true(polity_id in polity_ids, f"{anecdote_id} has orphan polity id {polity_id}")
        text = " ".join(str(anecdote.get(field, "")) for field in ("title", "description", "story_text", "review_note"))
        for fragment in anecdote_banned_fragments:
            assert_true(fragment not in text, f"{anecdote_id} contains banned fragment {fragment}")

    with (INPUT_DIR / "historical_events_v03_review_report.csv").open(encoding="utf-8", newline="") as handle:
        review_rows = list(csv.DictReader(handle))
    assert_true(all(row.get("reason") for row in review_rows), "review rows must include reason")
    with (INPUT_DIR / "historical_event_coverage_report_v03.csv").open(encoding="utf-8", newline="") as handle:
        coverage_rows = list(csv.DictReader(handle))
    assert_true(len(coverage_rows) == len(expected_years), "coverage report must include every playable year")
    assert_true(all(int(row["event_count"]) >= 1 for row in coverage_rows), "coverage report contains empty event year")
    with (INPUT_DIR / "historical_activity_gaps_report_v03.csv").open(encoding="utf-8", newline="") as handle:
        activity_rows = list(csv.DictReader(handle))
    assert_true(len(activity_rows) == len(expected_years), "activity gaps report must include every playable year")
    assert_true(
        all(int(row["historical_context_count"]) >= 1 for row in activity_rows),
        "activity gaps report contains year without context",
    )

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
        (420, "刘宋", True),
        (420, "北魏", True),
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
            assert_true(territory["boundary_level"] == "county", f"{polity_name} missing county boundary_level")
            assert_true(territory["matched_county_count"] > 0, f"{polity_name} missing matched counties")
            assert_true(territory["county_index_ref"], f"{polity_name} missing county index ref")
            indexed = county_index["polities"].get(polity["polity_id"])
            assert_true(indexed is not None, f"{polity_name} missing county index entry")
            assert_true(
                indexed["county_count"] == territory["matched_county_count"],
                f"{polity_name} county count mismatch",
            )
        else:
            assert_true(territory["territory_status"] == "missing", f"{polity_name} should explicitly lack territory")

    print("Dynamic capital and territory validation passed")


if __name__ == "__main__":
    main()
