#!/usr/bin/env python3
"""Bootstrap the vEuropean dataset (Bronze Age → 1945).

Mirror of scripts/bootstrap_vindian_dataset.py, with European polities, rulers,
events, capitals, and strategic locations. Produces the full set of
input/vEuropean/*.csv files plus dataset_manifest_vEuropean.json.

This is a seed dataset, not a complete catalog. Confidence scores reflect
source authority:
  - 90+ : charter/inscription-attested, primary-source-aligned
  - 75-85: scholarly consensus, encyclopedia-verified
  - 55-70: regional/contested, multiple secondary sources but disputed details
  - ≤50  : legendary or partial, confidence_note required

Run:
    python3 scripts/bootstrap_european_dataset.py
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from generate_world_history_yearly import MASTER_FIELDS, YEARLY_FIELDS


ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = ROOT / "input"
DATASET_DIR = INPUT_ROOT / "vEuropean"

# Field lists — identical to bootstrap_vindian (templates dictate column order).
RULERS_MASTER_FIELDS = [
    "ruler_id", "polity_id", "polity_name", "ruler_name", "ruler_title",
    "ruler_temple_name", "ruler_posthumous_name", "ruler_personal_name",
    "ruler_reign_start_year", "ruler_reign_start_label", "ruler_reign_end_year",
    "ruler_reign_end_label", "ruler_reign_raw", "ruler_reign_precision",
    "era_names", "ruler_source_title", "ruler_source_url", "ruler_source_section",
    "ruler_confidence_score", "ruler_confidence_note", "merged_from_v02_rows",
]
CAPITAL_FIELDS = [
    "capital_event_id", "polity_id", "capital_name_historical", "capital_name_modern",
    "valid_from_year", "valid_to_year", "longitude", "latitude", "is_primary",
    "event_type", "location_precision", "source_titles", "source_urls", "source_raw",
    "confidence_score", "confidence_note",
]
EVENT_FIELDS = [
    "event_id", "year", "sort_order", "date_label", "date_precision", "coverage_role",
    "coverage_start_year", "coverage_end_year", "coverage_group_id", "item_kind",
    "event_type", "title", "description", "significance", "primary_education_stage",
    "education_stage_tags", "curriculum_basis", "importance_level", "display_priority",
    "related_polity_ids", "related_people", "location_name", "longitude", "latitude",
    "location_historical_name", "location_modern_name", "location_modern_admin_id",
    "location_precision", "location_confidence_score", "location_source_titles",
    "location_source_urls", "location_note", "source_titles", "source_urls",
    "source_type", "confidence_score", "confidence_note", "fact_review_status",
    "review_note",
]
ANECDOTE_FIELDS = [
    "anecdote_id", "dynasty_name", "macro_period", "year", "sort_order", "date_label",
    "date_precision", "coverage_start_year", "coverage_end_year", "anecdote_type",
    "title", "phrase", "short_description", "story_text", "source_title",
    "source_section", "source_url", "source_type", "source_note", "related_polity_ids",
    "related_people", "location_historical_name", "location_modern_name", "longitude",
    "latitude", "location_precision", "primary_education_stage", "education_stage_tags",
    "display_priority", "review_status", "review_note",
]
CONTEXT_FIELDS = [
    "context_id", "start_year", "end_year", "start_label", "end_label", "title",
    "description", "sort_order", "display_priority", "longitude", "latitude",
    "location_name", "source_titles", "source_urls", "source_type", "confidence_score",
    "confidence_note",
]
STRATEGIC_FIELDS = [
    "location_id", "name", "aliases", "category", "icon_key", "importance_level",
    "display_priority", "start_year", "end_year", "active_years_raw",
    "related_event_ids", "related_anecdote_ids", "related_polity_ids", "related_people",
    "historical_name", "modern_name", "modern_admin_units_raw", "longitude", "latitude",
    "location_precision", "location_confidence_score", "strategic_summary",
    "historical_significance", "source_titles", "source_urls", "source_type",
    "confidence_note", "review_status", "review_note",
]
TERRITORY_FIELDS = [
    "polity_id", "polity_name", "admin_ids", "valid_from_year", "valid_to_year",
    "match_source", "confidence_score", "note", "source_titles", "source_raw",
]
ISSUE_FIELDS = [
    "issue_id", "issue_type", "entity_type", "polity_id", "polity_name", "field_name",
    "selected_value", "alternative_values", "source_titles", "source_urls", "note",
    "action_in_v03",
]
SOURCE_FIELDS = [
    "source_id", "topic", "source_title", "source_url", "source_type",
    "credibility_tier", "covers_fields", "notes",
]
VALIDATION_FIELDS = ["check_name", "status", "checked_count", "issue_count", "details"]

DATASET_FILES = {
    "polities_master": "european_history_polities_master_vEuropean.csv",
    "rulers_master": "european_history_rulers_master_vEuropean.csv",
    "polities_yearly": "european_history_polities_yearly_vEuropean.csv",
    "capital_events": "capital_events_vEuropean.csv",
    "historical_events": "historical_events_vEuropean.csv",
    "historical_anecdotes": "historical_anecdotes_vEuropean.csv",
    "historical_contexts": "historical_contexts_vEuropean.csv",
    "strategic_locations": "strategic_locations_vEuropean.csv",
    "territory_overrides": "territory_overrides_vEuropean.csv",
    "issues": "european_history_unresolved_or_disputed_vEuropean.csv",
    "sources": "european_history_sources_vEuropean.csv",
    "validation_report": "european_history_validation_report_vEuropean.csv",
}
TEMPLATE_FILES = {
    "polities_master": "world_history_polities_master_template.csv",
    "rulers_master": "world_history_rulers_master_template.csv",
    "polities_yearly": "world_history_polities_yearly_template.csv",
    "capital_events": "capital_events_template.csv",
    "historical_events": "historical_events_template.csv",
    "historical_anecdotes": "historical_anecdotes_template.csv",
    "strategic_locations": "strategic_locations_template.csv",
    "territory_overrides": "territory_overrides_template.csv",
    "issues": "unresolved_or_disputed_template.csv",
    "sources": "sources_template.csv",
    "validation_report": "validation_report_template.csv",
}
HEADER_BY_KEY = {
    "polities_master": MASTER_FIELDS,
    "rulers_master": RULERS_MASTER_FIELDS,
    "polities_yearly": YEARLY_FIELDS,
    "capital_events": CAPITAL_FIELDS,
    "historical_events": EVENT_FIELDS,
    "historical_anecdotes": ANECDOTE_FIELDS,
    "historical_contexts": CONTEXT_FIELDS,
    "strategic_locations": STRATEGIC_FIELDS,
    "territory_overrides": TERRITORY_FIELDS,
    "issues": ISSUE_FIELDS,
    "sources": SOURCE_FIELDS,
    "validation_report": VALIDATION_FIELDS,
}


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fields} for row in rows])


def year_label(year: int) -> str:
    return f"公元前{abs(year)}年" if year < 0 else f"{year}年"


@dataclass
class SourceRef:
    source_id: str
    topic: str
    title: str
    url: str
    source_type: str
    tier: str
    fields: str
    notes: str


SOURCE_REFS = [
    SourceRef("source_eur_0001", "encyclopedia", "Encyclopaedia Britannica: History of Europe", "https://www.britannica.com/topic/history-of-Europe", "encyclopedia", "B", "overview|periodization", "High-level cross-period overview of European history."),
    SourceRef("source_eur_0002", "encyclopedia", "Encyclopaedia Britannica: Ancient Rome", "https://www.britannica.com/place/ancient-Rome", "encyclopedia", "B", "rome|republic|empire|rulers", "Reference for Republican and Imperial Rome."),
    SourceRef("source_eur_0003", "encyclopedia", "Encyclopaedia Britannica: Byzantine Empire", "https://www.britannica.com/place/Byzantine-Empire", "encyclopedia", "B", "byzantium|eastern_roman|rulers", "Reference for Eastern Roman / Byzantine history."),
    SourceRef("source_eur_0004", "encyclopedia", "Encyclopaedia Britannica: Holy Roman Empire", "https://www.britannica.com/place/Holy-Roman-Empire", "encyclopedia", "B", "hre|emperors|periodization", "Reference for HRE chronology and structure."),
    SourceRef("source_eur_0005", "encyclopedia", "Encyclopaedia Britannica: France — History", "https://www.britannica.com/place/France/History", "encyclopedia", "B", "france|capetian|valois|bourbon", "Reference for French dynastic history."),
    SourceRef("source_eur_0006", "encyclopedia", "Encyclopaedia Britannica: United Kingdom — History", "https://www.britannica.com/place/United-Kingdom/History", "encyclopedia", "B", "britain|england|monarchs", "Reference for British dynastic history."),
    SourceRef("source_eur_0007", "encyclopedia", "Encyclopaedia Britannica: Spain — History", "https://www.britannica.com/place/Spain/History", "encyclopedia", "B", "spain|iberia|reconquista|habsburg", "Reference for Spanish history."),
    SourceRef("source_eur_0008", "encyclopedia", "Encyclopaedia Britannica: Germany — History", "https://www.britannica.com/place/Germany/History", "encyclopedia", "B", "germany|prussia|empire", "Reference for German history."),
    SourceRef("source_eur_0009", "encyclopedia", "Encyclopaedia Britannica: Italy — History", "https://www.britannica.com/place/Italy/History", "encyclopedia", "B", "italy|city_states|unification", "Reference for Italian history."),
    SourceRef("source_eur_0010", "encyclopedia", "Encyclopaedia Britannica: Russia — History", "https://www.britannica.com/place/Russia/History", "encyclopedia", "B", "russia|muscovy|tsardom|romanov", "Reference for Russian dynastic history."),
    SourceRef("source_eur_0011", "encyclopedia", "Encyclopaedia Britannica: Greek civilization", "https://www.britannica.com/topic/ancient-Greek-civilization", "encyclopedia", "B", "greece|hellenistic|city_states", "Reference for ancient Greece."),
    SourceRef("source_eur_0012", "encyclopedia", "Encyclopaedia Britannica: Ottoman Empire", "https://www.britannica.com/place/Ottoman-Empire", "encyclopedia", "B", "ottoman|sultans|balkans", "Reference for Ottoman history."),
    SourceRef("source_eur_0013", "encyclopedia", "Encyclopaedia Britannica: Poland — History", "https://www.britannica.com/place/Poland/History", "encyclopedia", "B", "poland|piast|jagiellon|commonwealth", "Reference for Polish history."),
    SourceRef("source_eur_0014", "encyclopedia", "Encyclopaedia Britannica: Hungary — History", "https://www.britannica.com/place/Hungary/History", "encyclopedia", "B", "hungary|arpad|magyars", "Reference for Hungarian history."),
    SourceRef("source_eur_0015", "encyclopedia", "Encyclopaedia Britannica: Frankish kingdom", "https://www.britannica.com/place/Frankish-kingdom", "encyclopedia", "B", "franks|merovingian|carolingian", "Reference for Frankish dynasties."),
    SourceRef("source_eur_0016", "encyclopedia", "Encyclopaedia Britannica: Vikings", "https://www.britannica.com/topic/Viking-people", "encyclopedia", "B", "vikings|norse|scandinavia", "Reference for Viking polities."),
    SourceRef("source_eur_0017", "heritage", "UNESCO World Heritage Centre", "https://whc.unesco.org/en/list/", "heritage_record", "A", "strategic_locations|capitals", "UNESCO records used for capital and strategic-site coordinates."),
    SourceRef("source_eur_0018", "encyclopedia", "Encyclopaedia Britannica: Napoleonic Wars", "https://www.britannica.com/event/Napoleonic-Wars", "encyclopedia", "B", "napoleon|france|coalitions", "Reference for Napoleonic period."),
    SourceRef("source_eur_0019", "encyclopedia", "Encyclopaedia Britannica: World War I", "https://www.britannica.com/event/World-War-I", "encyclopedia", "A", "wwi|treaty_of_versailles", "Reference for WWI and Versailles aftermath."),
    SourceRef("source_eur_0020", "encyclopedia", "Encyclopaedia Britannica: World War II", "https://www.britannica.com/event/World-War-II", "encyclopedia", "A", "wwii|axis|allies", "Reference for WWII."),
    SourceRef("source_eur_0021", "archaeology", "Encyclopaedia Britannica: Minoan civilization", "https://www.britannica.com/topic/Minoan-civilization", "encyclopedia", "B", "minoan|bronze_age|crete", "Reference for Minoan Bronze Age."),
    SourceRef("source_eur_0022", "archaeology", "Encyclopaedia Britannica: Mycenaean civilization", "https://www.britannica.com/topic/Mycenaean-civilization", "encyclopedia", "B", "mycenaean|bronze_age|greece", "Reference for Mycenaean Bronze Age."),
    SourceRef("source_eur_0023", "encyclopedia", "Encyclopaedia Britannica: Carolingian dynasty", "https://www.britannica.com/topic/Carolingian-dynasty", "encyclopedia", "B", "carolingian|charlemagne", "Reference for Carolingian dynasty."),
    SourceRef("source_eur_0024", "encyclopedia", "Encyclopaedia Britannica: Carthage", "https://www.britannica.com/place/Carthage-ancient-city-Tunisia", "encyclopedia", "B", "carthage|phoenician|punic_wars", "Reference for Carthage."),
    SourceRef("source_eur_0025", "encyclopedia", "Encyclopaedia Britannica: Russian Empire", "https://www.britannica.com/place/Russian-Empire", "encyclopedia", "B", "russian_empire|romanov", "Reference for Russian Empire."),
    SourceRef("source_eur_0026", "encyclopedia", "Encyclopaedia Britannica: Crusades", "https://www.britannica.com/event/Crusades", "encyclopedia", "B", "crusades|holy_land", "Reference for Crusades."),
    SourceRef("source_eur_0027", "encyclopedia", "Encyclopaedia Britannica: Reformation", "https://www.britannica.com/event/Reformation", "encyclopedia", "B", "reformation|luther|wars_of_religion", "Reference for Protestant Reformation."),
    SourceRef("source_eur_0028", "encyclopedia", "Encyclopaedia Britannica: Thirty Years' War", "https://www.britannica.com/event/Thirty-Years-War", "encyclopedia", "B", "thirty_years_war|westphalia", "Reference for Thirty Years' War."),
    SourceRef("source_eur_0029", "encyclopedia", "Encyclopaedia Britannica: French Revolution", "https://www.britannica.com/event/French-Revolution", "encyclopedia", "B", "french_revolution|consulate", "Reference for French Revolution."),
    SourceRef("source_eur_0030", "encyclopedia", "Encyclopaedia Britannica: Italian unification", "https://www.britannica.com/event/Italian-unification", "encyclopedia", "B", "risorgimento|piedmont|cavour", "Reference for Italian unification."),
    SourceRef("source_eur_0031", "encyclopedia", "Encyclopaedia Britannica: Plantagenet", "https://www.britannica.com/topic/Plantagenet-dynasty", "encyclopedia", "B", "england|plantagenet", "Reference for Plantagenet dynasty."),
    SourceRef("source_eur_0032", "encyclopedia", "Encyclopaedia Britannica: Capetian dynasty", "https://www.britannica.com/topic/Capetian-dynasty", "encyclopedia", "B", "france|capet", "Reference for Capetian dynasty."),
    SourceRef("source_eur_0033", "encyclopedia", "Encyclopaedia Britannica: Habsburg", "https://www.britannica.com/topic/House-of-Habsburg", "encyclopedia", "B", "habsburg|austria|spain", "Reference for Habsburg dynasty."),
    SourceRef("source_eur_0034", "encyclopedia", "Encyclopaedia Britannica: Roman Empire", "https://www.britannica.com/place/Roman-Empire", "encyclopedia", "A", "roman_empire|julio_claudian|severan|tetrarchy", "Reference for Roman Empire periodization."),
    SourceRef("source_eur_0035", "encyclopedia", "Encyclopaedia Britannica: Achaemenian dynasty", "https://www.britannica.com/topic/Achaemenian-dynasty", "encyclopedia", "B", "persia|persian_wars", "Persian context for Greek wars."),
]

SOURCE_BY_ID = {source.source_id: source for source in SOURCE_REFS}


def source_titles(ids: list[str]) -> str:
    return "|".join(SOURCE_BY_ID[s].title for s in ids if s in SOURCE_BY_ID)


def source_urls(ids: list[str]) -> str:
    return "|".join(SOURCE_BY_ID[s].url for s in ids if s in SOURCE_BY_ID)


# Capital / strategic-location coordinates (lon, lat). City-level accuracy.
COORDS: dict[str, tuple[float, float]] = {
    "Knossos": (25.1631, 35.2980),
    "Mycenae": (22.7568, 37.7300),
    "Troy": (26.2389, 39.9575),
    "Tiryns": (22.7997, 37.5994),
    "Pylos": (21.6953, 36.9166),
    "Hattusa": (34.6155, 40.0186),
    "Athens": (23.7275, 37.9838),
    "Sparta": (22.4317, 37.0750),
    "Corinth": (22.9357, 37.9381),
    "Thebes": (23.3158, 38.3217),
    "Argos": (22.7331, 37.6309),
    "Miletus": (27.2778, 37.5306),
    "Delphi": (22.5009, 38.4824),
    "Olympia": (21.6300, 37.6383),
    "Syracuse": (15.2866, 37.0755),
    "Carthage": (10.3232, 36.8531),
    "Gadir": (-6.2924, 36.5298),
    "Utica": (10.0617, 37.0567),
    "Rome": (12.4964, 41.9028),
    "Veii": (12.4133, 42.0238),
    "Tarquinia": (11.7569, 42.2536),
    "Capua": (14.2125, 41.0833),
    "Massalia": (5.3698, 43.2965),
    "Pella": (22.5266, 40.7572),
    "Alexandria": (29.9187, 31.2001),
    "Pergamon": (27.1846, 39.1322),
    "Antioch": (36.1500, 36.2025),
    "Seleucia": (44.5197, 33.0863),
    "Byzantium": (28.9784, 41.0082),
    "Constantinople": (28.9784, 41.0082),
    "Ravenna": (12.2035, 44.4173),
    "Milan": (9.1900, 45.4642),
    "Trier": (6.6431, 49.7596),
    "Lugdunum": (4.8357, 45.7640),
    "Londinium": (-0.1276, 51.5074),
    "Tournai": (3.3886, 50.6053),
    "Aachen": (6.0839, 50.7753),
    "Paris": (2.3522, 48.8566),
    "Reims": (4.0317, 49.2583),
    "Vienna": (16.3738, 48.2082),
    "Toledo": (-4.0273, 39.8628),
    "Cordoba": (-4.7794, 37.8882),
    "Granada": (-3.5986, 37.1773),
    "León": (-5.5707, 42.5987),
    "Burgos": (-3.7037, 42.3439),
    "Lisbon": (-9.1393, 38.7223),
    "Madrid": (-3.7038, 40.4168),
    "Barcelona": (2.1734, 41.3851),
    "Saragossa": (-0.8773, 41.6488),
    "Naples": (14.2681, 40.8518),
    "Florence": (11.2558, 43.7696),
    "Venice": (12.3155, 45.4408),
    "Genoa": (8.9463, 44.4056),
    "Pisa": (10.4017, 43.7228),
    "Palermo": (13.3614, 38.1157),
    "Salerno": (14.7681, 40.6824),
    "Pavia": (9.1559, 45.1847),
    "Cologne": (6.9603, 50.9375),
    "Mainz": (8.2473, 49.9929),
    "Frankfurt": (8.6821, 50.1109),
    "Munich": (11.5820, 48.1351),
    "Nuremberg": (11.0767, 49.4521),
    "Berlin": (13.4050, 52.5200),
    "Potsdam": (13.0645, 52.3906),
    "Königsberg": (20.5128, 54.7104),
    "Dresden": (13.7373, 51.0504),
    "Prague": (14.4378, 50.0755),
    "Krakow": (19.9450, 50.0647),
    "Warsaw": (21.0122, 52.2297),
    "Vilnius": (25.2797, 54.6872),
    "Budapest": (19.0402, 47.4979),
    "Esztergom": (18.7406, 47.7872),
    "Belgrade": (20.4612, 44.7866),
    "Sofia": (23.3219, 42.6977),
    "Bucharest": (26.1025, 44.4268),
    "Kiev": (30.5234, 50.4501),
    "Moscow": (37.6173, 55.7558),
    "Novgorod": (31.2742, 58.5215),
    "Saint Petersburg": (30.3351, 59.9343),
    "Kazan": (49.1064, 55.7963),
    "Sarai": (47.0667, 47.7833),
    "Stockholm": (18.0686, 59.3293),
    "Uppsala": (17.6389, 59.8586),
    "Copenhagen": (12.5683, 55.6761),
    "Roskilde": (12.0833, 55.6422),
    "Oslo": (10.7522, 59.9139),
    "Trondheim": (10.3951, 63.4305),
    "Bergen": (5.3221, 60.3913),
    "Reykjavik": (-21.8278, 64.1466),
    "Dublin": (-6.2603, 53.3498),
    "Edinburgh": (-3.1883, 55.9533),
    "York": (-1.0815, 53.9590),
    "London": (-0.1276, 51.5074),
    "Winchester": (-1.3081, 51.0632),
    "Avignon": (4.8059, 43.9493),
    "Brussels": (4.3517, 50.8503),
    "Amsterdam": (4.9041, 52.3676),
    "The Hague": (4.3007, 52.0705),
    "Antwerp": (4.4025, 51.2194),
    "Tournai-Frankish": (3.3886, 50.6053),
    "Ankara": (32.8541, 39.9334),
    "Edirne": (26.5557, 41.6771),
    "Bursa": (29.0610, 40.1828),
    "Hastings": (0.5727, 50.8543),
    "Bouvines": (3.1900, 50.5817),
    "Crécy": (1.8909, 50.2528),
    "Agincourt": (2.1430, 50.4636),
    "Tours": (0.6890, 47.3941),
    "Lepanto": (21.3329, 38.4012),
    "Vienna-1683": (16.3738, 48.2082),
    "Waterloo": (4.4119, 50.6800),
    "Sevastopol": (33.5253, 44.6166),
    "Verdun": (5.3823, 49.1602),
    "Somme": (2.7000, 50.0000),
    "Stalingrad": (44.5018, 48.7080),
    "Normandy": (-0.9472, 49.3000),
    "Dunkirk": (2.3772, 51.0353),
    "Sarajevo": (18.4131, 43.8563),
    "Riga": (24.1052, 56.9496),
    "Tallinn": (24.7536, 59.4370),
    "Helsinki": (24.9384, 60.1699),
    "Bratislava": (17.1077, 48.1486),
    "Zagreb": (15.9819, 45.8150),
    "Ljubljana": (14.5058, 46.0569),
    "Skopje": (21.4254, 41.9981),
    "Tirana": (19.8189, 41.3275),
    "Pristina": (21.1655, 42.6629),
    "Podgorica": (19.2594, 42.4304),
    "Athens-modern": (23.7275, 37.9838),
    "Pforzheim": (8.6973, 48.8920),
    "Aquileia": (13.3722, 45.7704),
    "Ostia": (12.2877, 41.7558),
    "Heuneburg": (9.4042, 48.0883),
    "Bibracte": (4.0414, 46.9219),
    "Alesia": (4.5000, 47.5364),
    "Numantia": (-2.4500, 41.8044),
}


def make_manifest() -> dict:
    return {
        "dataset_id": "vEuropean",
        "dataset_name": "欧洲史 vEuropean",
        "schema_family": "v03-compatible-world-history",
        "created_by": "scripts/bootstrap_european_dataset.py",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "year_min": -3000,
        "year_max": 1945,
        "year_zero_policy": "no_year_zero",
        "space_scope": "Europe from Bronze Age (-3000) through the end of WWII (1945). Mediterranean / Levant / North-African neighbors referenced where they intersect European history (Carthage, Byzantine East, Crusader states, Ottoman expansion).",
        "files": DATASET_FILES,
        "template_files": TEMPLATE_FILES,
        "field_notes": {
            "macro_period": "Large chronological period (Bronze Age, Iron Age, Classical, Migration Period, Early Medieval, High Medieval, Late Medieval, Early Modern, Long 19th, World Wars).",
            "dynasty_name": "Dynasty, ruling house, civilization phase, or republic/constitutional regime label.",
            "modern_admin_units_raw": "Pipe-separated ISO3 country codes (FRA|DEU|ITA) + optional ADM1 codes for federations (DE-BY|IT-25|ES-CT).",
            "ruler_temple_name": "East Asian style field; leave empty for European rulers.",
            "v02_*": "Retained only for v03 compatibility; empty for non-v02 datasets.",
            "ruler_continuity": "European succession rules vary (primogeniture, elective monarchy, papal election, republican magistracy). Use documented system per polity.",
        },
    }


class Builder:
    def __init__(self) -> None:
        self.polities: list[dict[str, str]] = []
        self.rulers: list[dict[str, str]] = []
        self.capitals: list[dict[str, str]] = []
        self.events: list[dict[str, str]] = []
        self.anecdotes: list[dict[str, str]] = []
        self.contexts: list[dict[str, str]] = []
        self.strategic: list[dict[str, str]] = []
        self.territories: list[dict[str, str]] = []
        self.issues: list[dict[str, str]] = []
        self.polity_key_to_id: dict[str, str] = {}
        self.polity_names: set[str] = set()
        self._polity_seq = 1
        self._ruler_seq = 1
        self._capital_seq = 1
        self._event_seq = 1
        self._anecdote_seq = 1
        self._context_seq = 1
        self._strategic_seq = 1
        self._issue_seq = 1

    def add_polity(
        self, key: str, name: str, macro: str, dynasty: str, ptype: str,
        start: int, end: int, *,
        aliases: str = "", display: str = "", disambiguation: str = "",
        date_precision: str = "year", geography: str = "", modern_admin: str = "",
        capital: str = "", family: str = "", group: str = "", founder: str = "",
        last_ruler: str = "", successor: str = "", source_ids: list[str] | None = None,
        source_raw: str = "", confidence: int = 75, note: str = "",
        review_status: str = "verified", risk_flags: str = "",
    ) -> str:
        source_ids = source_ids or ["source_eur_0001"]
        pid = f"polity_eur_{self._polity_seq:04d}"
        self._polity_seq += 1
        row = {
            "polity_id": pid, "macro_period": macro, "dynasty_name": dynasty,
            "polity_name": name, "polity_aliases": aliases,
            "polity_display_name": display or name,
            "polity_name_disambiguation": disambiguation,
            "polity_name_review_status": review_status, "polity_name_risk_flags": risk_flags,
            "polity_type": ptype, "polity_start_year": str(start),
            "polity_start_label": year_label(start), "polity_end_year": str(end),
            "polity_end_label": year_label(end),
            "polity_date_raw": f"{year_label(start)}-{year_label(end)}",
            "polity_date_precision": date_precision, "historical_geography_raw": geography,
            "modern_admin_units_raw": modern_admin,
            "capital_historical": capital, "capital_modern": capital,
            "ruling_family_or_clan": family, "ethnicity_or_group": group,
            "founder": founder, "last_ruler": last_ruler, "destroyed_by_or_successor": successor,
            "polity_source_titles": source_titles(source_ids),
            "polity_source_urls": source_urls(source_ids),
            "polity_source_raw": source_raw, "confidence_score": str(confidence),
            "confidence_note": note,
            "calendar_system_note": "BCE years are negative; no year 0. Pre-Christian-era dates often approximate.",
            "v02_row_count": "", "v02_actual_min_year": "", "v02_actual_max_year": "",
            "v02_actual_years": "", "merged_from_v02_contexts": "",
        }
        self.polities.append(row)
        self.polity_key_to_id[key] = pid
        self.polity_names.add(name.lower())
        return pid

    def add_ruler(
        self, polity_key: str, name: str, title: str, start: int, end: int, *,
        personal: str = "", source_ids: list[str] | None = None,
        section: str = "", confidence: int = 75, note: str = "",
    ) -> str:
        pid = self.polity_key_to_id[polity_key]
        polity_name = next(row["polity_name"] for row in self.polities if row["polity_id"] == pid)
        rid = f"ruler_eur_{self._ruler_seq:05d}"
        self._ruler_seq += 1
        source_ids = source_ids or ["source_eur_0001"]
        self.rulers.append({
            "ruler_id": rid, "polity_id": pid, "polity_name": polity_name,
            "ruler_name": name, "ruler_title": title,
            "ruler_temple_name": "", "ruler_posthumous_name": "",
            "ruler_personal_name": personal,
            "ruler_reign_start_year": str(start), "ruler_reign_start_label": year_label(start),
            "ruler_reign_end_year": str(end), "ruler_reign_end_label": year_label(end),
            "ruler_reign_raw": f"{year_label(start)}-{year_label(end)}",
            "ruler_reign_precision": "year", "era_names": "",
            "ruler_source_title": source_titles(source_ids),
            "ruler_source_url": source_urls(source_ids),
            "ruler_source_section": section,
            "ruler_confidence_score": str(confidence), "ruler_confidence_note": note,
            "merged_from_v02_rows": "",
        })
        return rid

    def add_capital(
        self, polity_key: str, capital: str, start: int, end: int,
        source_ids: list[str] | None = None, confidence: int = 80, note: str = "",
    ) -> None:
        if capital not in COORDS or polity_key not in self.polity_key_to_id:
            return
        lon, lat = COORDS[capital]
        pid = self.polity_key_to_id[polity_key]
        source_ids = source_ids or ["source_eur_0017"]
        self.capitals.append({
            "capital_event_id": f"capital_eur_{self._capital_seq:04d}",
            "polity_id": pid, "capital_name_historical": capital,
            "capital_name_modern": capital,
            "valid_from_year": str(start), "valid_to_year": str(end),
            "longitude": str(lon), "latitude": str(lat),
            "is_primary": "true", "event_type": "initial_capital",
            "location_precision": "city",
            "source_titles": source_titles(source_ids),
            "source_urls": source_urls(source_ids),
            "source_raw": "Capital coordinates from city-level geocoding.",
            "confidence_score": str(confidence),
            "confidence_note": note or "City-level approximation for historical capital marker.",
        })
        self._capital_seq += 1

    def add_event(
        self, year: int, title: str, description: str, significance: str, *,
        event_type: str, polity_keys: list[str] | None = None, people: str = "",
        location: str = "", source_ids: list[str] | None = None,
        date_precision: str = "year", item_kind: str = "core_event",
        coverage_role: str = "exact_year_event", importance: int = 2,
        priority: int = 100, confidence: int = 80, note: str = "",
    ) -> str:
        eid = f"event_eur_{self._event_seq:04d}"
        self._event_seq += 1
        source_ids = source_ids or ["source_eur_0001"]
        pids = "|".join(self.polity_key_to_id[k] for k in polity_keys or [] if k in self.polity_key_to_id)
        lon, lat = COORDS.get(location, ("", ""))
        self.events.append({
            "event_id": eid, "year": str(year), "sort_order": str(self._event_seq),
            "date_label": year_label(year), "date_precision": date_precision,
            "coverage_role": coverage_role,
            "coverage_start_year": str(year), "coverage_end_year": str(year),
            "coverage_group_id": "", "item_kind": item_kind, "event_type": event_type,
            "title": title, "description": description, "significance": significance,
            "primary_education_stage": "高中",
            "education_stage_tags": "世界史|欧洲史",
            "curriculum_basis": "world_history_dataset_vEuropean",
            "importance_level": str(importance), "display_priority": str(priority),
            "related_polity_ids": pids, "related_people": people,
            "location_name": location, "longitude": str(lon), "latitude": str(lat),
            "location_historical_name": location, "location_modern_name": location,
            "location_modern_admin_id": "",
            "location_precision": "city" if location and lon != "" else "",
            "location_confidence_score": "80" if location and lon != "" else "",
            "location_source_titles": source_titles(["source_eur_0017"]) if location and lon != "" else "",
            "location_source_urls": source_urls(["source_eur_0017"]) if location and lon != "" else "",
            "location_note": "Coordinates are city/site approximations for map placement." if location and lon != "" else "",
            "source_titles": source_titles(source_ids),
            "source_urls": source_urls(source_ids),
            "source_type": "synthesized_secondary", "confidence_score": str(confidence),
            "confidence_note": note,
            "fact_review_status": "verified" if confidence >= 75 else "candidate",
            "review_note": "",
        })
        return eid

    def add_strategic(
        self, name: str, category: str, *, importance: int = 2, priority: int = 100,
        start: int | str = "", end: int | str = "", historical: str = "",
        modern: str = "", admin: str = "", summary: str = "", significance: str = "",
        source_ids: list[str] | None = None, location: str | None = None,
        location_precision: str = "city", confidence: int = 75, note: str = "",
        related_polity_keys: list[str] | None = None,
    ) -> str:
        loc_key = location or name
        lon, lat = COORDS.get(loc_key, ("", ""))
        sid = f"location_eur_{self._strategic_seq:04d}"
        self._strategic_seq += 1
        source_ids = source_ids or ["source_eur_0017"]
        related = "|".join(
            self.polity_key_to_id[k] for k in related_polity_keys or [] if k in self.polity_key_to_id
        )
        self.strategic.append({
            "location_id": sid, "name": name, "aliases": "", "category": category,
            "icon_key": category, "importance_level": str(importance),
            "display_priority": str(priority),
            "start_year": str(start), "end_year": str(end),
            "active_years_raw": f"{start}-{end}" if start and end else "",
            "related_event_ids": "", "related_anecdote_ids": "",
            "related_polity_ids": related, "related_people": "",
            "historical_name": historical or name, "modern_name": modern or name,
            "modern_admin_units_raw": admin,
            "longitude": str(lon), "latitude": str(lat),
            "location_precision": location_precision if lon != "" else "",
            "location_confidence_score": str(confidence) if lon != "" else "",
            "strategic_summary": summary, "historical_significance": significance,
            "source_titles": source_titles(source_ids),
            "source_urls": source_urls(source_ids),
            "source_type": "synthesized_secondary",
            "confidence_note": note, "review_status": "verified",
            "review_note": "",
        })
        return sid

    def add_anecdote(
        self, year: int, dynasty: str, macro: str, title: str, *,
        anecdote_type: str = "legend",
        phrase: str = "",
        short_description: str = "",
        story_text: str = "",
        source_id: str = "source_eur_0001",
        source_section: str = "",
        polity_keys: list[str] | None = None,
        people: str = "",
        location: str = "",
        coverage_start: int | None = None,
        coverage_end: int | None = None,
        date_precision: str = "approx",
        priority: int = 200,
        review_status: str = "candidate",
        review_note: str = "",
    ) -> str:
        aid = f"anecdote_eur_{self._anecdote_seq:04d}"
        self._anecdote_seq += 1
        source = SOURCE_BY_ID.get(source_id)
        title_str = source.title if source else ""
        url_str = source.url if source else ""
        type_str = source.source_type if source else "synthesized_secondary"
        related = "|".join(
            self.polity_key_to_id[k] for k in polity_keys or [] if k in self.polity_key_to_id
        )
        lon, lat = COORDS.get(location, ("", ""))
        self.anecdotes.append({
            "anecdote_id": aid, "dynasty_name": dynasty, "macro_period": macro,
            "year": str(year), "sort_order": str(self._anecdote_seq),
            "date_label": year_label(year), "date_precision": date_precision,
            "coverage_start_year": str(coverage_start if coverage_start is not None else year),
            "coverage_end_year": str(coverage_end if coverage_end is not None else year),
            "anecdote_type": anecdote_type,
            "title": title, "phrase": phrase,
            "short_description": short_description, "story_text": story_text or short_description,
            "source_title": title_str, "source_section": source_section,
            "source_url": url_str, "source_type": type_str,
            "source_note": "Anecdote/context row; not used as sole chronology source.",
            "related_polity_ids": related, "related_people": people,
            "location_historical_name": location, "location_modern_name": location,
            "longitude": str(lon), "latitude": str(lat),
            "location_precision": "city" if location and lon != "" else "",
            "primary_education_stage": "高中",
            "education_stage_tags": "世界史|欧洲史",
            "display_priority": str(priority),
            "review_status": review_status, "review_note": review_note,
        })
        return aid

    def add_context(
        self, start: int, end: int, title: str, description: str, *,
        location_name: str = "", confidence: int = 80, note: str = "",
        priority: int = 100, source_ids: list[str] | None = None,
    ) -> str:
        cid = f"context_eur_{self._context_seq:04d}"
        self._context_seq += 1
        source_ids = source_ids or ["source_eur_0001"]
        lon, lat = COORDS.get(location_name, ("", ""))
        self.contexts.append({
            "context_id": cid, "start_year": str(start), "end_year": str(end),
            "start_label": year_label(start), "end_label": year_label(end),
            "title": title, "description": description,
            "sort_order": str(self._context_seq), "display_priority": str(priority),
            "longitude": str(lon), "latitude": str(lat),
            "location_name": location_name,
            "source_titles": source_titles(source_ids),
            "source_urls": source_urls(source_ids),
            "source_type": "synthesized_secondary",
            "confidence_score": str(confidence), "confidence_note": note,
        })
        return cid

    def add_territory_override(
        self, polity_key: str, admin_ids: str, *, valid_from: int = 0, valid_to: int = 0,
        match_source: str = "manual_override", confidence: int = 75, note: str = "",
        source_ids: list[str] | None = None, source_raw: str = "",
    ) -> None:
        if polity_key not in self.polity_key_to_id:
            return
        pid = self.polity_key_to_id[polity_key]
        polity_name = next(row["polity_name"] for row in self.polities if row["polity_id"] == pid)
        source_ids = source_ids or ["source_eur_0001"]
        self.territories.append({
            "polity_id": pid, "polity_name": polity_name, "admin_ids": admin_ids,
            "valid_from_year": str(valid_from), "valid_to_year": str(valid_to),
            "match_source": match_source,
            "confidence_score": str(confidence), "note": note,
            "source_titles": source_titles(source_ids), "source_raw": source_raw,
        })

    def add_issue(
        self, issue_type: str, polity_key: str, field_name: str,
        selected: str, alternatives: str, note: str, *,
        source_ids: list[str] | None = None, action: str = "documented_in_release_notes",
    ) -> None:
        pid = self.polity_key_to_id.get(polity_key, "")
        polity_name = ""
        if pid:
            polity_name = next(row["polity_name"] for row in self.polities if row["polity_id"] == pid)
        source_ids = source_ids or ["source_eur_0001"]
        iid = f"issue_eur_{self._issue_seq:04d}"
        self._issue_seq += 1
        self.issues.append({
            "issue_id": iid, "issue_type": issue_type, "entity_type": "polity",
            "polity_id": pid, "polity_name": polity_name, "field_name": field_name,
            "selected_value": selected, "alternative_values": alternatives,
            "source_titles": source_titles(source_ids),
            "source_urls": source_urls(source_ids),
            "note": note, "action_in_v03": action,
        })


def _register_bronze_age(b: Builder) -> None:
    """Bronze Age polities (-3000 to -1200). Minoan, Mycenaean, Cycladic,
    early continental cultures. Most dates are archaeological approximations
    with confidence ≤ 65."""
    src_min = ["source_eur_0021"]
    src_myc = ["source_eur_0022"]

    b.add_polity(
        "minoan_palatial", "Minoan Civilization (Palatial Period)",
        "青铜时代", "Minoan", "civilization", -1900, -1450,
        aliases="Minoans|Cretans", display="米诺斯文明（宫殿期）",
        geography="克里特岛与爱琴海岛屿，以克诺索斯、斐斯托斯、马利亚为宫殿中心。",
        modern_admin="GRC", capital="Knossos",
        family="Minoan elites (no recorded dynastic names)", group="Aegean Bronze Age",
        founder="(legendary Minos)", successor="Mycenaean Greeks",
        source_ids=src_min, confidence=60,
        note="Minoan palatial period dates from Aegean archaeology; specific rulers not historically attested.",
    )
    b.add_capital("minoan_palatial", "Knossos", -1900, -1450, src_min, 70)

    b.add_polity(
        "minoan_neopalatial", "Minoan Neopalatial Period",
        "青铜时代", "Minoan", "civilization", -1700, -1450,
        aliases="Neopalatial Crete", display="米诺斯新宫殿期",
        geography="克里特岛重建的克诺索斯宫殿建筑群盛期。",
        modern_admin="GRC", capital="Knossos",
        group="Aegean Bronze Age",
        successor="Mycenaean Crete",
        source_ids=src_min, confidence=58,
        note="Subperiod within Minoan palatial era; overlaps with main Minoan polity.",
    )

    b.add_polity(
        "mycenaean", "Mycenaean Greece",
        "青铜时代", "Mycenaean", "civilization", -1600, -1100,
        aliases="Achaeans|Mycenaeans", display="迈锡尼文明",
        geography="希腊大陆与爱琴海，以迈锡尼、皮洛斯、底比斯、提林斯等堡垒为中心。",
        modern_admin="GRC", capital="Mycenae",
        group="Aegean Bronze Age",
        founder="(legendary Perseus)", successor="Dark Age Greek tribes",
        source_ids=src_myc, confidence=65,
        note="Mycenaean civilization periodized from Linear B tablets and archaeological strata.",
    )
    b.add_capital("mycenaean", "Mycenae", -1600, -1100, src_myc, 72)

    b.add_polity(
        "trojan_kingdom", "Kingdom of Troy",
        "青铜时代", "Trojan", "kingdom", -1300, -1180,
        aliases="Ilios|Wilusa", display="特洛伊王国",
        geography="安纳托利亚西北角希萨利克丘的城邦，控制达达尼尔海峡贸易。",
        modern_admin="TUR", capital="Troy",
        group="Anatolian Bronze Age",
        last_ruler="Priam (legendary)", successor="Destroyed in Trojan War (legendary)",
        source_ids=["source_eur_0011"], confidence=55,
        note="Troy VIIa destruction layer often equated with Trojan War; Homeric account is legendary.",
    )
    b.add_capital("trojan_kingdom", "Troy", -1300, -1180, ["source_eur_0011"], 65)

    b.add_polity(
        "hittite_anatolian", "Hittite Kingdom (Anatolian context)",
        "青铜时代", "Hittite", "kingdom", -1650, -1180,
        aliases="Hatti|Hittites", display="赫梯王国（安纳托利亚联络体）",
        geography="安纳托利亚高原；与迈锡尼希腊、特洛伊有外交与冲突。",
        modern_admin="TUR|SYR", capital="Hattusa",
        family="Hittite royal house", group="Anatolian Indo-European",
        successor="Sea Peoples / Phrygians",
        source_ids=["source_eur_0011"], confidence=70,
        note="Listed in vEuropean as Anatolian neighbor; primary coverage belongs to a future vNearEast dataset.",
    )
    b.add_capital("hittite_anatolian", "Hattusa", -1650, -1180, ["source_eur_0011"], 72)

    b.add_polity(
        "cycladic", "Cycladic Civilization",
        "青铜时代", "Cycladic", "civilization", -3000, -1100,
        aliases="Cyclades culture", display="基克拉迪文明",
        geography="爱琴海中部基克拉迪群岛；以大理石雕像与海上贸易闻名。",
        modern_admin="GRC", group="Aegean Bronze Age",
        source_ids=src_min, confidence=55,
        note="Pre-Minoan and contemporaneous Aegean island culture; no centralized polity, dates archaeological.",
    )

    b.add_polity(
        "etruscan_proto", "Proto-Etruscan / Villanovan",
        "青铜时代", "Villanovan", "culture", -1100, -700,
        aliases="Villanovan culture", display="前埃特鲁里亚 / 维兰诺瓦文化",
        geography="意大利中部托斯卡纳与拉齐奥北部；埃特鲁里亚文明先驱。",
        modern_admin="ITA", group="Italic Iron Age proto-culture",
        successor="Etruscan League",
        source_ids=["source_eur_0009"], confidence=55,
        note="Iron Age culture transitioning into historical Etruscan polities.",
    )

    b.add_polity(
        "bronze_iberia", "Bronze Age Iberia (El Argar)",
        "青铜时代", "Argaric", "culture", -2200, -1550,
        aliases="El Argar culture", display="伊比利亚青铜时代（阿尔加文化）",
        geography="伊比利亚半岛东南部，以山顶聚落与冶金著称。",
        modern_admin="ESP", group="Iberian Bronze Age",
        source_ids=["source_eur_0007"], confidence=55,
        note="Archaeological culture; no named rulers or capitals.",
    )

    b.add_polity(
        "nordic_bronze", "Nordic Bronze Age",
        "青铜时代", "Nordic Bronze", "culture", -1750, -500,
        aliases="Nordic Bronze Age culture", display="北欧青铜时代",
        geography="斯堪的纳维亚南部与日德兰半岛；岩画与青铜器证据。",
        modern_admin="DNK|NOR|SWE", group="Nordic Bronze Age",
        source_ids=src_min, confidence=50,
        note="Cultural horizon, not a political entity; included to mark Northern European Bronze Age era.",
    )

    b.add_polity(
        "urnfield", "Urnfield Culture",
        "青铜时代", "Urnfield", "culture", -1300, -750,
        aliases="Hallstatt-precursor|Urnfield", display="骨灰瓮文化",
        geography="中欧多瑙河流域；以骨灰瓮葬俗为标志，前凯尔特先驱。",
        modern_admin="DEU|AUT|CZE|HUN|POL", group="Central European Bronze Age",
        successor="Hallstatt (Iron Age Celts)",
        source_ids=["source_eur_0001"], confidence=55,
        note="Late Bronze Age cultural horizon transitioning into Iron Age Hallstatt/Celtic cultures.",
    )

    b.add_event(
        year=-1450, title="Destruction of Minoan palaces",
        description="米诺斯文明各宫殿在 -1450 前后陆续被毁，迈锡尼希腊接管克里特岛主要据点。",
        significance="爱琴海主导权由米诺斯文明转向迈锡尼文明。",
        event_type="political_transition",
        polity_keys=["minoan_palatial", "mycenaean"], people="Mycenaean rulers",
        location="Knossos", source_ids=src_min,
        date_precision="approx", confidence=55, importance=2,
    )
    b.add_event(
        year=-1180, title="Sea Peoples upheavals (approx)",
        description="海上民族大规模迁徙冲击东地中海，赫梯帝国崩溃，特洛伊 VIIa 烧毁，迈锡尼宫殿陆续放弃。",
        significance="青铜时代晚期崩溃，开启希腊黑暗时代。",
        event_type="systemic_collapse",
        polity_keys=["trojan_kingdom", "mycenaean", "hittite_anatolian"],
        location="Troy",
        source_ids=["source_eur_0011", "source_eur_0022"],
        date_precision="approx", confidence=60, importance=3,
    )

    b.add_context(
        start=-3000, end=-1100, title="爱琴海青铜时代",
        description="米诺斯-迈锡尼为主导的爱琴海青铜时代；与近东、安纳托利亚、埃及形成密集贸易网。",
        source_ids=src_min, confidence=70,
    )

    b.add_strategic(
        "Knossos", "capital", start=-1900, end=-1450,
        modern="Knossos archaeological site",
        admin="GRC", summary="米诺斯文明最大宫殿建筑群，行政与宗教中心。",
        significance="米诺斯王宫与线性 A 文字主要发现地。",
        source_ids=src_min, related_polity_keys=["minoan_palatial", "minoan_neopalatial"],
        confidence=80,
    )
    b.add_strategic(
        "Mycenae", "capital", start=-1600, end=-1100,
        modern="Mycenae archaeological site",
        admin="GRC", summary="迈锡尼文明最重要的城堡型宫殿，狮门遗址。",
        significance="迈锡尼希腊政治军事中心；线性 B 文字主要发现地。",
        source_ids=src_myc, related_polity_keys=["mycenaean"],
        confidence=82,
    )
    b.add_strategic(
        "Troy", "strategic_city", start=-1700, end=-1180,
        modern="Hisarlık archaeological site",
        admin="TUR", summary="达达尼尔海峡战略城邦，控制博斯普鲁斯通道。",
        significance="《伊利亚特》主角；考古发现至少九层叠加聚落。",
        source_ids=["source_eur_0011"], related_polity_keys=["trojan_kingdom"],
        confidence=72,
    )


def _register_iron_archaic(b: Builder) -> None:
    """Iron Age & Archaic (-1200 to -500). Greek city-states, Etruscans,
    Phoenician colonies (Carthage), Roman Kingdom, early Celts."""
    src_grc = ["source_eur_0011"]
    src_car = ["source_eur_0024"]
    src_rom = ["source_eur_0002"]

    b.add_polity(
        "dark_age_greece", "Greek Dark Age",
        "铁器时代", "Geometric Greece", "tribal_confederations", -1100, -800,
        aliases="Geometric period", display="希腊黑暗时代",
        geography="希腊大陆与爱琴海岛屿；文字消失、人口下降。",
        modern_admin="GRC", group="Greek",
        successor="Greek archaic city-states",
        source_ids=src_grc, confidence=60,
        note="Post-Mycenaean collapse, before alphabet adoption; not a centralized polity.",
    )

    b.add_polity(
        "phoenician_homeland", "Phoenician City-States (homeland)",
        "铁器时代", "Phoenician", "city_state_federation", -1200, -332,
        aliases="Tyre|Sidon|Byblos", display="腓尼基城邦（黎凡特本土）",
        geography="黎凡特沿海（推罗、西顿、比布鲁斯、贝鲁特）；海上贸易帝国母邦。",
        modern_admin="LBN|SYR|ISR", capital="",
        group="Semitic Canaanite", successor="Persian, then Hellenistic",
        source_ids=src_car, confidence=72,
        note="Listed for completeness; Phoenician homeland in Levant, contemporaneous with Greek archaic.",
    )

    b.add_polity(
        "carthage_punic", "Carthage (Phoenician Colony to Punic Republic)",
        "铁器时代", "Magonid / Barcid", "republic", -814, -146,
        aliases="Qart-ḥadašt|Carthago", display="迦太基（腓尼基殖民地到布匿共和国）",
        geography="北非现突尼斯；最大殖民帝国控制西地中海。",
        modern_admin="TUN|DZA|ESP|ITA", capital="Carthage",
        family="Magonid family, Barcid family", group="Phoenician",
        founder="(legendary) Dido / Elissa",
        last_ruler="Hasdrubal (last Punic War general)",
        successor="Roman Republic (Third Punic War, 146 BCE)",
        source_ids=src_car, confidence=85,
        note="Founded c. 814 BCE per Phoenician tradition; destroyed 146 BCE by Rome.",
    )
    b.add_capital("carthage_punic", "Carthage", -814, -146, src_car, 85)
    b.add_ruler("carthage_punic", "Hamilcar Barca", "general", -247, -228, personal="Hamilcar", source_ids=src_car, confidence=80)
    b.add_ruler("carthage_punic", "Hannibal Barca", "general", -218, -201, personal="Hannibal", source_ids=src_car, confidence=85)
    b.add_ruler("carthage_punic", "Hasdrubal the Boetharch", "general", -149, -146, personal="Hasdrubal", source_ids=src_car, confidence=78)

    b.add_polity(
        "athens_archaic", "Athens (Archaic Period)",
        "古风时代", "Athenian", "city_state", -753, -508,
        aliases="Athenai", display="雅典（古风时代）",
        geography="阿提卡半岛；以雅典卫城为政治宗教中心。",
        modern_admin="GRC", capital="Athens",
        group="Greek", founder="(legendary) Theseus",
        successor="Classical Athens (Cleisthenes reforms, 508 BCE)",
        source_ids=src_grc, confidence=72,
        note="Pre-democratic Athens; archon system, Solon and Peisistratus reforms.",
    )
    b.add_capital("athens_archaic", "Athens", -753, -508, src_grc, 78)
    b.add_ruler("athens_archaic", "Solon", "archon (lawgiver)", -594, -593, personal="Solon", source_ids=src_grc, confidence=75)
    b.add_ruler("athens_archaic", "Peisistratus", "tyrant", -546, -528, personal="Peisistratus", source_ids=src_grc, confidence=75)

    b.add_polity(
        "sparta_archaic", "Sparta (Archaic-Classical)",
        "古风时代", "Spartan", "dual_monarchy", -700, -371,
        aliases="Lacedaemon", display="斯巴达",
        geography="拉科尼亚平原；以严格军事社会与双王制著称。",
        modern_admin="GRC", capital="Sparta",
        family="Agiad and Eurypontid royal houses", group="Doric Greek",
        successor="Decline after Battle of Leuctra (371 BCE)",
        source_ids=src_grc, confidence=78,
        note="Dual kingship; rule by gerousia and apella; dominant land power until 371 BCE.",
    )
    b.add_capital("sparta_archaic", "Sparta", -700, -371, src_grc, 78)
    b.add_ruler("sparta_archaic", "Leonidas I", "king", -489, -480, personal="Leonidas", source_ids=src_grc, confidence=85, note="Famed at Thermopylae 480 BCE.")

    b.add_polity(
        "corinth_archaic", "Corinth (Archaic)",
        "古风时代", "Bacchiadae / Cypselid", "city_state", -750, -146,
        aliases="Korinthos", display="科林斯",
        geography="伊斯特摩斯地峡；连接伯罗奔尼撒与希腊大陆，重要海上贸易枢纽。",
        modern_admin="GRC", capital="Corinth",
        group="Doric Greek",
        successor="Roman destruction 146 BCE",
        source_ids=src_grc, confidence=72,
    )
    b.add_capital("corinth_archaic", "Corinth", -750, -146, src_grc, 72)

    b.add_polity(
        "thebes_boeotia", "Thebes (Boeotia)",
        "古风时代", "Theban", "city_state", -1100, -335,
        aliases="Thebai", display="底比斯（维奥蒂亚）",
        geography="希腊中部维奥蒂亚平原；维奥蒂亚同盟领袖。",
        modern_admin="GRC", capital="Thebes",
        group="Aeolic Greek",
        successor="Destroyed by Alexander 335 BCE",
        source_ids=src_grc, confidence=70,
    )
    b.add_capital("thebes_boeotia", "Thebes", -1100, -335, src_grc, 70)

    b.add_polity(
        "miletus", "Miletus",
        "古风时代", "Milesian", "city_state", -1000, -494,
        aliases="Miletos", display="米利都",
        geography="安纳托利亚西海岸，爱奥尼亚同盟核心，前苏格拉底哲学发源。",
        modern_admin="TUR", capital="Miletus",
        group="Ionian Greek",
        successor="Sacked by Persians 494 BCE during Ionian Revolt",
        source_ids=src_grc, confidence=68,
    )

    b.add_polity(
        "roman_kingdom", "Roman Kingdom",
        "古风时代", "Roman Kings", "kingdom", -753, -509,
        aliases="Regnum Romanum", display="罗马王政时期",
        geography="拉丁姆罗马城；据传由七王统治。",
        modern_admin="ITA", capital="Rome",
        family="Seven Kings of Rome (legendary)", group="Latin",
        founder="Romulus (legendary, 753 BCE)",
        last_ruler="Tarquinius Superbus (expelled 509 BCE)",
        successor="Roman Republic",
        source_ids=src_rom, confidence=55,
        note="Founding date 753 BCE per Varronian chronology; first four kings considered legendary.",
    )
    b.add_capital("roman_kingdom", "Rome", -753, -509, src_rom, 60)
    b.add_ruler("roman_kingdom", "Romulus", "rex", -753, -715, personal="Romulus", source_ids=src_rom, confidence=40, note="Legendary founder.")
    b.add_ruler("roman_kingdom", "Tarquinius Superbus", "rex", -534, -509, personal="Lucius Tarquinius Superbus", source_ids=src_rom, confidence=60)

    b.add_polity(
        "etruscan_league", "Etruscan League (Dodecapolis)",
        "古风时代", "Etruscan", "city_state_federation", -800, -264,
        aliases="Etrusci|Tusci", display="埃特鲁里亚十二城联盟",
        geography="意大利中部托斯卡纳/拉齐奥北部；十二座城邦松散联盟。",
        modern_admin="ITA", capital="",
        group="Etruscan (pre-Indo-European)", successor="Roman conquest",
        source_ids=["source_eur_0009"], confidence=68,
        note="Loose religious-political federation; cities include Veii, Tarquinia, Volsinii, Caere.",
    )

    b.add_polity(
        "hallstatt_celts", "Hallstatt Celts",
        "古风时代", "Hallstatt", "tribal_culture", -800, -450,
        aliases="Early Celtic culture", display="哈尔施塔特凯尔特文化",
        geography="中欧多瑙河上游、东法兰西；以盐矿与铁器工艺著称。",
        modern_admin="AUT|DEU|CHE|FRA|CZE", group="Celtic",
        successor="La Tène culture",
        source_ids=["source_eur_0001"], confidence=58,
        note="Iron Age culture; transitions to La Tène c. 450 BCE.",
    )

    b.add_polity(
        "scythian_kingdom", "Scythian Kingdom (Pontic Steppe)",
        "古风时代", "Scythian", "nomadic_kingdom", -700, -200,
        aliases="Scythians|Sakas", display="斯基泰王国（黑海草原）",
        geography="黑海北岸草原；游牧民族强权，与希腊殖民地交界。",
        modern_admin="UKR|RUS|MDA|ROU", group="Indo-Iranian",
        successor="Sarmatian displacement",
        source_ids=["source_eur_0001"], confidence=62,
        note="Pontic Scythian polity; included for vEuropean coverage as Black Sea frontier neighbor.",
    )

    b.add_polity(
        "thracian_odrysian", "Odrysian Kingdom (Thracians)",
        "古风时代", "Odrysian", "kingdom", -480, -46,
        aliases="Thracians", display="奥德里西亚（色雷斯）王国",
        geography="色雷斯（保加利亚现境内）；与马其顿、雅典周旋。",
        modern_admin="BGR|GRC|TUR", group="Thracian",
        successor="Roman Thracia province (46 CE)",
        source_ids=["source_eur_0001"], confidence=65,
    )

    b.add_polity(
        "illyrian_kingdoms", "Illyrian Kingdoms",
        "古风时代", "Illyrian dynasts", "tribal_kingdoms", -400, -168,
        aliases="Illyrians", display="伊利里亚诸王国",
        geography="亚得里亚海东岸（现阿尔巴尼亚、克罗地亚南、黑山）。",
        modern_admin="ALB|HRV|MNE|BIH", group="Illyrian",
        successor="Roman conquest 168 BCE",
        source_ids=["source_eur_0001"], confidence=62,
    )

    b.add_polity(
        "iberian_celts", "Celtiberian Confederations",
        "古风时代", "Celtiberian tribes", "tribal_confederations", -500, -19,
        aliases="Celtiberi", display="塞尔特伊比利亚部落联盟",
        geography="伊比利亚半岛中北部；凯尔特人与本地伊比利亚人融合。",
        modern_admin="ESP", group="Celtiberian",
        successor="Roman conquest under Augustus",
        source_ids=["source_eur_0007"], confidence=60,
    )

    b.add_event(
        year=-776, title="First recorded Olympic Games",
        description="第一届有文献记载的奥林匹亚祭祀竞技在伯罗奔尼撒奥林匹亚举行。",
        significance="希腊编年史与文学传统的标志性起点。",
        event_type="cultural", polity_keys=["athens_archaic", "sparta_archaic"],
        location="Olympia", source_ids=src_grc,
        confidence=75, importance=2,
    )
    b.add_event(
        year=-753, title="Legendary founding of Rome",
        description="瓦罗编年法定罗慕路斯于公元前 753 年建立罗马城。",
        significance="罗马城建国传说，后续罗马年代记的起点。",
        event_type="political_origin",
        polity_keys=["roman_kingdom"], people="Romulus",
        location="Rome", source_ids=src_rom,
        date_precision="approx", confidence=45, importance=3,
        note="Legendary chronology; archaeology of early Rome is older but no central polity attested.",
    )
    b.add_event(
        year=-509, title="Founding of the Roman Republic",
        description="塔克文王朝末王 Tarquinius Superbus 被驱逐，罗马进入共和制。",
        significance="罗马共和的开端。",
        event_type="constitutional_transition",
        polity_keys=["roman_kingdom"], people="Lucius Junius Brutus",
        location="Rome", source_ids=src_rom,
        date_precision="approx", confidence=65, importance=3,
    )

    b.add_context(
        start=-1100, end=-500, title="希腊与意大利铁器时代",
        description="迈锡尼崩溃后希腊进入黑暗时代，约前 800 年起复兴；拉丁姆出现罗马城邦；中欧凯尔特文化扩张。",
        source_ids=src_grc, confidence=72,
    )

    b.add_strategic("Carthage", "capital", start=-814, end=-146, modern="Carthage",
                    admin="TUN", summary="布匿帝国首都，西地中海最大贸易城市。",
                    significance="迦太基-罗马百余年争霸的政治军事中心。",
                    source_ids=src_car, related_polity_keys=["carthage_punic"], confidence=82)
    b.add_strategic("Olympia", "religious_site", start=-1000, end=393, modern="Olympia",
                    admin="GRC", summary="奥林匹亚祭祀竞技中心。",
                    significance="泛希腊宗教纽带与编年标志。",
                    source_ids=src_grc, confidence=80)
    b.add_strategic("Delphi", "religious_site", start=-800, end=393, modern="Delphi",
                    admin="GRC", summary="阿波罗神谕中心，希腊世界宗教与外交枢纽。",
                    significance="希腊各邦决策前必访神谕地。",
                    source_ids=src_grc, confidence=82)


def _register_classical(b: Builder) -> None:
    """Classical era (-500 to 500). Greek classical → Hellenistic → Roman
    Republic → Roman Empire → Migration period barbarian kingdoms."""
    src_grc = ["source_eur_0011"]
    src_rom = ["source_eur_0002"]
    src_emp = ["source_eur_0034"]
    src_byz = ["source_eur_0003"]
    src_per = ["source_eur_0035"]
    src_car = ["source_eur_0024"]

    b.add_polity(
        "athens_classical", "Classical Athens",
        "古典时代", "Athenian democracy", "democratic_city_state", -508, -322,
        aliases="Athenai|Demos Athēnaion", display="古典雅典",
        geography="阿提卡；希波战争后建立提洛同盟海上帝国。",
        modern_admin="GRC", capital="Athens",
        family="Cleisthenic democracy (no dynasty)", group="Ionian Greek",
        founder="Cleisthenes (508 BCE reforms)",
        successor="Macedonian hegemony after Chaeronea",
        source_ids=src_grc, confidence=88,
        note="Democratic period from Cleisthenes reforms to Lamian War end.",
    )
    b.add_capital("athens_classical", "Athens", -508, -322, src_grc, 86)
    b.add_ruler("athens_classical", "Pericles", "strategos", -461, -429, personal="Pericles", source_ids=src_grc, confidence=88)
    b.add_ruler("athens_classical", "Alcibiades", "strategos", -420, -407, personal="Alcibiades", source_ids=src_grc, confidence=78)

    b.add_polity(
        "macedonia_argead", "Kingdom of Macedonia (Argead)",
        "古典时代", "Argead", "kingdom", -700, -310,
        aliases="Makedonia", display="马其顿王国（阿基德王朝）",
        geography="希腊北部马其顿地区；菲利普二世与亚历山大大帝建立希腊化帝国。",
        modern_admin="GRC|MKD|BGR", capital="Pella",
        family="Argead dynasty", group="Macedonian Greek",
        founder="Caranus (legendary)",
        last_ruler="Alexander IV (assassinated 310 BCE)",
        successor="Antigonid Macedonia",
        source_ids=src_grc, confidence=82,
    )
    b.add_capital("macedonia_argead", "Pella", -400, -310, src_grc, 82)
    b.add_ruler("macedonia_argead", "Philip II", "basileus", -359, -336, personal="Philip", source_ids=src_grc, confidence=88)
    b.add_ruler("macedonia_argead", "Alexander III the Great", "basileus", -336, -323, personal="Alexandros", source_ids=src_grc, confidence=92)

    b.add_polity(
        "macedonia_antigonid", "Antigonid Macedonia",
        "希腊化时代", "Antigonid", "kingdom", -276, -168,
        aliases="Antigonids", display="安提柯王朝马其顿",
        geography="马其顿核心；与罗马多次马其顿战争。",
        modern_admin="GRC|MKD", capital="Pella",
        family="Antigonid dynasty", group="Macedonian Greek",
        founder="Antigonus II Gonatas",
        last_ruler="Perseus (captured at Pydna 168 BCE)",
        successor="Roman province of Macedonia",
        source_ids=src_grc, confidence=82,
    )
    b.add_capital("macedonia_antigonid", "Pella", -276, -168, src_grc, 82)

    b.add_polity(
        "seleucid_empire", "Seleucid Empire",
        "希腊化时代", "Seleucid", "empire", -312, -63,
        aliases="Basileia tōn Seleukidōn", display="塞琉古帝国",
        geography="西到小亚细亚，东达印度边境；亚历山大帝国东半部主要继业者。",
        modern_admin="TUR|SYR|IRQ|IRN", capital="Antioch",
        family="Seleucid dynasty", group="Macedonian Greek elite",
        founder="Seleucus I Nicator",
        last_ruler="Philip II Philoromaeus",
        successor="Roman Syria 63 BCE",
        source_ids=src_grc, confidence=82,
    )
    b.add_capital("seleucid_empire", "Seleucia", -305, -240, src_grc, 78)
    b.add_capital("seleucid_empire", "Antioch", -240, -63, src_grc, 82)
    b.add_ruler("seleucid_empire", "Seleucus I Nicator", "basileus", -305, -281, source_ids=src_grc, confidence=85)
    b.add_ruler("seleucid_empire", "Antiochus III the Great", "basileus", -222, -187, source_ids=src_grc, confidence=82)

    b.add_polity(
        "ptolemaic_egypt", "Ptolemaic Egypt",
        "希腊化时代", "Ptolemaic", "kingdom", -305, -30,
        aliases="Lagid dynasty", display="托勒密埃及",
        geography="埃及尼罗河谷；亚历山大里亚为希腊化世界最大文化中心。",
        modern_admin="EGY|LBY|CYP", capital="Alexandria",
        family="Ptolemaic dynasty", group="Macedonian Greek elite",
        founder="Ptolemy I Soter",
        last_ruler="Cleopatra VII",
        successor="Roman Egypt 30 BCE",
        source_ids=src_grc, confidence=86,
    )
    b.add_capital("ptolemaic_egypt", "Alexandria", -331, -30, src_grc, 88)
    b.add_ruler("ptolemaic_egypt", "Ptolemy I Soter", "basileus", -305, -283, source_ids=src_grc, confidence=85)
    b.add_ruler("ptolemaic_egypt", "Cleopatra VII", "basilissa", -51, -30, personal="Cleopatra", source_ids=src_grc, confidence=92)

    b.add_polity(
        "pergamon_attalid", "Kingdom of Pergamon (Attalid)",
        "希腊化时代", "Attalid", "kingdom", -281, -133,
        aliases="Pergamene", display="帕加马（阿塔利德王朝）",
        geography="安纳托利亚西部；以图书馆与雕塑闻名。",
        modern_admin="TUR", capital="Pergamon",
        family="Attalid dynasty", group="Macedonian Greek elite",
        founder="Philetaerus",
        last_ruler="Attalus III (bequeathed kingdom to Rome 133 BCE)",
        successor="Roman province of Asia",
        source_ids=src_grc, confidence=80,
    )
    b.add_capital("pergamon_attalid", "Pergamon", -281, -133, src_grc, 82)

    b.add_polity(
        "roman_republic", "Roman Republic",
        "古典时代", "Senatus Populusque Romanus", "republic", -509, -27,
        aliases="Res Publica Romana|SPQR", display="罗马共和国",
        geography="从拉丁姆扩张至整个地中海；最终演变为罗马帝国。",
        modern_admin="ITA|FRA|ESP|PRT|GRC|TUR|EGY|TUN|LBY|DZA|MAR|GBR|HRV|SVN|MKD|ALB|BGR|ROU",
        capital="Rome",
        family="Senatorial oligarchy / consular rotation", group="Latin / Italic",
        founder="Lucius Junius Brutus (509 BCE expulsion of kings)",
        last_ruler="Octavian (Augustus, ended Republic 27 BCE)",
        successor="Roman Empire",
        source_ids=src_rom, confidence=92,
    )
    b.add_capital("roman_republic", "Rome", -509, -27, src_rom, 92)
    b.add_ruler("roman_republic", "Gaius Julius Caesar", "dictator perpetuo", -49, -44, personal="Gaius Julius Caesar", source_ids=src_rom, confidence=95)
    b.add_ruler("roman_republic", "Pompey the Great", "consul", -70, -48, personal="Gnaeus Pompeius Magnus", source_ids=src_rom, confidence=88)
    b.add_ruler("roman_republic", "Sulla", "dictator", -82, -79, personal="Lucius Cornelius Sulla", source_ids=src_rom, confidence=85)
    b.add_ruler("roman_republic", "Cicero", "consul", -63, -63, personal="Marcus Tullius Cicero", source_ids=src_rom, confidence=85)
    b.add_ruler("roman_republic", "Marcus Antonius", "triumvir", -43, -30, personal="Marcus Antonius", source_ids=src_rom, confidence=85)

    b.add_polity(
        "roman_principate", "Roman Empire (Principate)",
        "古典时代", "Julio-Claudian, Flavian, Antonine, Severan",
        "empire", -27, 284,
        aliases="Imperium Romanum", display="罗马帝国（元首制）",
        geography="地中海全境、不列颠、莱茵-多瑙边境、近东。",
        modern_admin="ITA|FRA|ESP|PRT|GRC|TUR|EGY|TUN|LBY|DZA|MAR|GBR|HRV|SVN|MKD|ALB|BGR|ROU|SRB|BIH|CHE|AUT|HUN|DEU|BEL|NLD|LUX|SYR|LBN|ISR|JOR|IRQ|MDA",
        capital="Rome",
        family="Julio-Claudian → Flavian → Nerva-Antonine → Severan", group="Roman",
        founder="Augustus (Octavian)",
        last_ruler="Carinus (assassinated 285 CE before Diocletian's reforms)",
        successor="Roman Dominate (Diocletian, 284 CE)",
        source_ids=src_emp, confidence=92,
    )
    b.add_capital("roman_principate", "Rome", -27, 284, src_emp, 92)
    b.add_ruler("roman_principate", "Augustus", "princeps / imperator", -27, 14, personal="Gaius Octavius / Imperator Caesar Augustus", source_ids=src_emp, confidence=95)
    b.add_ruler("roman_principate", "Tiberius", "princeps", 14, 37, personal="Tiberius Claudius Nero", source_ids=src_emp, confidence=92)
    b.add_ruler("roman_principate", "Nero", "princeps", 54, 68, personal="Nero Claudius Caesar", source_ids=src_emp, confidence=90)
    b.add_ruler("roman_principate", "Vespasian", "princeps", 69, 79, personal="Titus Flavius Vespasianus", source_ids=src_emp, confidence=90)
    b.add_ruler("roman_principate", "Trajan", "princeps", 98, 117, personal="Marcus Ulpius Traianus", source_ids=src_emp, confidence=92)
    b.add_ruler("roman_principate", "Hadrian", "princeps", 117, 138, personal="Publius Aelius Hadrianus", source_ids=src_emp, confidence=92)
    b.add_ruler("roman_principate", "Marcus Aurelius", "princeps", 161, 180, personal="Marcus Aurelius Antoninus", source_ids=src_emp, confidence=92)
    b.add_ruler("roman_principate", "Septimius Severus", "augustus", 193, 211, personal="Lucius Septimius Severus", source_ids=src_emp, confidence=88)

    b.add_polity(
        "roman_dominate", "Roman Empire (Dominate)",
        "古典时代", "Diocletianic / Constantinian", "empire", 284, 395,
        aliases="Late Roman Empire", display="罗马帝国（君主制）",
        geography="戴克里先四帝共治改革后的晚期罗马帝国，最终东西分治。",
        modern_admin="ITA|FRA|ESP|PRT|GRC|TUR|EGY|TUN|LBY|DZA|MAR|GBR|HRV|SVN|MKD|ALB|BGR|ROU|SRB|BIH|CHE|AUT|HUN|DEU|BEL|NLD|LUX|SYR|LBN|ISR|JOR",
        capital="Rome",
        family="Tetrarchy → Constantinian → Valentinian → Theodosian", group="Roman",
        founder="Diocletian",
        last_ruler="Theodosius I (last to rule both halves)",
        successor="Western Roman Empire / Eastern Roman (Byzantine)",
        source_ids=src_emp, confidence=88,
    )
    b.add_capital("roman_dominate", "Constantinople", 330, 395, src_emp, 88)
    b.add_ruler("roman_dominate", "Diocletian", "augustus", 284, 305, source_ids=src_emp, confidence=90)
    b.add_ruler("roman_dominate", "Constantine I the Great", "augustus", 306, 337, personal="Flavius Valerius Constantinus", source_ids=src_emp, confidence=92)
    b.add_ruler("roman_dominate", "Theodosius I", "augustus", 379, 395, personal="Flavius Theodosius", source_ids=src_emp, confidence=88)

    b.add_polity(
        "western_roman", "Western Roman Empire",
        "古典时代", "Theodosian / Valentinian III", "empire", 395, 476,
        aliases="Imperium Romanum Occidentale", display="西罗马帝国",
        geography="西部行省：意大利、高卢、不列颠、伊比利亚、北非西半。",
        modern_admin="ITA|FRA|ESP|PRT|GBR|TUN|DZA|MAR|CHE|AUT|DEU|BEL|NLD|LUX",
        capital="Ravenna",
        family="Theodosian dynasty, later puppet emperors", group="Roman",
        founder="Honorius (first separate Western emperor)",
        last_ruler="Romulus Augustulus (deposed by Odoacer 476)",
        successor="Odoacer's kingdom / Ostrogothic Italy",
        source_ids=src_emp, confidence=90,
    )
    b.add_capital("western_roman", "Milan", 395, 402, src_emp, 88)
    b.add_capital("western_roman", "Ravenna", 402, 476, src_emp, 90)
    b.add_ruler("western_roman", "Honorius", "augustus", 395, 423, source_ids=src_emp, confidence=85)
    b.add_ruler("western_roman", "Valentinian III", "augustus", 425, 455, source_ids=src_emp, confidence=82)
    b.add_ruler("western_roman", "Romulus Augustulus", "augustus", 475, 476, source_ids=src_emp, confidence=80)

    b.add_polity(
        "eastern_roman", "Eastern Roman Empire (early Byzantine)",
        "古典时代", "Theodosian / Justinian / Heraclian", "empire", 395, 717,
        aliases="Basileia Rhōmaiōn", display="东罗马帝国（早期拜占庭）",
        geography="希腊、巴尔干、安纳托利亚、黎凡特、埃及，后失东方诸省。",
        modern_admin="GRC|TUR|BGR|MKD|ALB|SRB|MNE|HRV|EGY|SYR|LBN|ISR|JOR|LBY|TUN|ITA",
        capital="Constantinople",
        family="Theodosian → Leonid → Justinian → Heraclian", group="Greco-Roman",
        founder="Arcadius",
        successor="Middle Byzantine (Iconoclast era from 717)",
        source_ids=src_byz, confidence=88,
    )
    b.add_capital("eastern_roman", "Constantinople", 395, 717, src_byz, 90)
    b.add_ruler("eastern_roman", "Justinian I", "augustus", 527, 565, personal="Petrus Sabbatius", source_ids=src_byz, confidence=92)
    b.add_ruler("eastern_roman", "Heraclius", "augustus", 610, 641, source_ids=src_byz, confidence=88)

    b.add_polity(
        "ostrogothic_italy", "Ostrogothic Kingdom of Italy",
        "古典时代", "Amal dynasty", "kingdom", 493, 553,
        aliases="Regnum Italiae", display="东哥特意大利王国",
        geography="意大利全境；西罗马继承者，由查士丁尼东哥特战争消灭。",
        modern_admin="ITA|SVN|HRV", capital="Ravenna",
        family="Amal dynasty", group="Ostrogoth",
        founder="Theodoric the Great",
        last_ruler="Teia (killed at Mons Lactarius 553)",
        successor="Byzantine reconquest / Lombard invasion",
        source_ids=src_rom, confidence=82,
    )
    b.add_capital("ostrogothic_italy", "Ravenna", 493, 553, src_rom, 82)
    b.add_ruler("ostrogothic_italy", "Theodoric the Great", "rex", 493, 526, source_ids=src_rom, confidence=88)

    b.add_polity(
        "visigothic_kingdom", "Visigothic Kingdom",
        "古典时代", "Visigothic", "kingdom", 418, 711,
        aliases="Regnum Gothorum", display="西哥特王国",
        geography="阿基坦与伊比利亚；最终为伊比利亚穆斯林征服。",
        modern_admin="ESP|PRT|FRA", capital="Toledo",
        family="Visigothic elective monarchy", group="Visigoth",
        founder="Theodoric I",
        last_ruler="Roderic (killed at Guadalete 711)",
        successor="Al-Andalus (Umayyad Iberia)",
        source_ids=["source_eur_0007"], confidence=80,
    )
    b.add_capital("visigothic_kingdom", "Toledo", 507, 711, ["source_eur_0007"], 82)

    b.add_polity(
        "vandal_kingdom", "Vandal Kingdom",
        "古典时代", "Hasdingi", "kingdom", 435, 534,
        aliases="Regnum Vandalorum", display="汪达尔王国",
        geography="北非（迦太基为都）；曾洗劫罗马 455 年。",
        modern_admin="TUN|DZA|LBY", capital="Carthage",
        family="Hasdingi dynasty", group="Vandal",
        founder="Genseric",
        last_ruler="Gelimer (defeated by Belisarius 534)",
        successor="Byzantine reconquest",
        source_ids=src_rom, confidence=80,
    )
    b.add_capital("vandal_kingdom", "Carthage", 439, 534, src_rom, 78)

    b.add_polity(
        "frankish_merovingian", "Merovingian Frankish Kingdom",
        "古典时代", "Merovingian", "kingdom", 481, 751,
        aliases="Francia|Frankish Realm", display="墨洛温法兰克王国",
        geography="高卢全境，从图尔奈扩展到整个莱茵-比利时-法国-德意志西部。",
        modern_admin="FRA|BEL|NLD|LUX|DEU|CHE", capital="Tournai",
        family="Merovingian dynasty", group="Frankish (Salian)",
        founder="Clovis I",
        last_ruler="Childeric III (deposed 751)",
        successor="Carolingian dynasty",
        source_ids=["source_eur_0015"], confidence=85,
    )
    b.add_capital("frankish_merovingian", "Paris", 511, 561, ["source_eur_0015"], 82)
    b.add_capital("frankish_merovingian", "Tournai", 481, 511, ["source_eur_0015"], 80)
    b.add_ruler("frankish_merovingian", "Clovis I", "rex", 481, 511, source_ids=["source_eur_0015"], confidence=88)
    b.add_ruler("frankish_merovingian", "Charles Martel", "mayor of the palace", 718, 741, source_ids=["source_eur_0015"], confidence=88, note="De facto Frankish ruler under puppet Merovingian kings.")

    b.add_polity(
        "anglo_saxon_kingdoms", "Anglo-Saxon Heptarchy",
        "古典时代", "Anglo-Saxon", "kingdoms_confederation", 410, 927,
        aliases="Seven Kingdoms", display="盎格鲁-撒克逊七国时代",
        geography="不列颠岛南半部；七大主要王国（肯特、苏塞克斯、韦塞克斯、埃塞克斯、东盎格利亚、麦西亚、诺森布里亚）。",
        modern_admin="GBR|GB-ENG", capital="Winchester",
        family="Multiple Anglo-Saxon dynasties", group="Anglo-Saxon",
        founder="Hengist & Horsa (legendary, 449)",
        successor="Kingdom of England (Æthelstan, 927)",
        source_ids=src_grc, confidence=72,
    )
    b.add_capital("anglo_saxon_kingdoms", "Winchester", 519, 927, ["source_eur_0006"], 75)

    b.add_polity(
        "achaemenid_neighbor", "Achaemenid Persian Empire (European context)",
        "古典时代", "Achaemenid", "empire", -550, -330,
        aliases="First Persian Empire", display="阿契美尼德波斯帝国（欧洲语境）",
        geography="波斯本土加全部近东，西延至安纳托利亚色雷斯。",
        modern_admin="IRN|IRQ|SYR|TUR|EGY", capital="",
        family="Achaemenid", group="Persian",
        founder="Cyrus the Great",
        last_ruler="Darius III (killed 330 BCE)",
        successor="Alexander's empire",
        source_ids=src_per, confidence=85,
        note="Listed for vEuropean coverage as Persian Wars antagonist; primary coverage in vNearEast (future).",
    )

    b.add_event(year=-490, title="Battle of Marathon",
                description="雅典与普拉提亚联军在马拉松击败波斯入侵军。",
                significance="希波战争第一次重大胜利。",
                event_type="battle", polity_keys=["athens_classical", "achaemenid_neighbor"],
                people="Miltiades", location="Athens",
                source_ids=src_grc, confidence=90, importance=3)
    b.add_event(year=-480, title="Battle of Thermopylae",
                description="斯巴达国王列奥尼达率三百精锐与希腊联军在温泉关阻击波斯王薛西斯。",
                significance="希波战争经典战役，希腊联军象征性抵抗。",
                event_type="battle", polity_keys=["sparta_archaic", "achaemenid_neighbor"],
                people="Leonidas I; Xerxes I", location="Athens",
                source_ids=src_grc, confidence=92, importance=3)
    b.add_event(year=-480, title="Battle of Salamis",
                description="希腊联合舰队在萨拉米斯海峡击败波斯舰队。",
                significance="扭转希波战争局势。",
                event_type="naval_battle", polity_keys=["athens_classical", "achaemenid_neighbor"],
                people="Themistocles", location="Athens",
                source_ids=src_grc, confidence=92, importance=3)
    b.add_event(year=-431, title="Outbreak of Peloponnesian War",
                description="雅典提洛同盟与斯巴达伯罗奔尼撒同盟开战。",
                significance="希腊城邦体系内战。",
                event_type="war_outbreak",
                polity_keys=["athens_classical", "sparta_archaic"], location="Athens",
                source_ids=src_grc, confidence=90, importance=3)
    b.add_event(year=-336, title="Alexander the Great accedes",
                description="腓力二世遇刺，亚历山大继位马其顿王。",
                significance="希腊化时代序幕。",
                event_type="succession", polity_keys=["macedonia_argead"],
                people="Alexander III the Great", location="Pella",
                source_ids=src_grc, confidence=92, importance=3)
    b.add_event(year=-323, title="Death of Alexander, division of empire",
                description="亚历山大在巴比伦去世，将领瓜分帝国引发继业者战争。",
                significance="希腊化王国体系形成（塞琉古、托勒密、安提柯）。",
                event_type="political_collapse",
                polity_keys=["macedonia_argead", "seleucid_empire", "ptolemaic_egypt"],
                people="Alexander III the Great",
                source_ids=src_grc, confidence=92, importance=3)
    b.add_event(year=-218, title="Hannibal crosses the Alps",
                description="迦太基将军汉尼拔率军跨越阿尔卑斯山攻入意大利，第二次布匿战争开战。",
                significance="迦太基-罗马最严酷战争开始。",
                event_type="military_campaign",
                polity_keys=["carthage_punic", "roman_republic"],
                people="Hannibal Barca",
                source_ids=src_car, confidence=90, importance=3)
    b.add_event(year=-146, title="Destruction of Carthage",
                description="罗马在第三次布匿战争中彻底摧毁迦太基。",
                significance="罗马成为西地中海唯一强权。",
                event_type="city_destruction",
                polity_keys=["carthage_punic", "roman_republic"],
                people="Scipio Aemilianus", location="Carthage",
                source_ids=src_rom, confidence=92, importance=3)
    b.add_event(year=-44, title="Assassination of Julius Caesar",
                description="凯撒在元老院遇刺，引发后三头同盟内战。",
                significance="罗马共和向帝制转型关键事件。",
                event_type="assassination",
                polity_keys=["roman_republic"],
                people="Gaius Julius Caesar; Brutus; Cassius", location="Rome",
                source_ids=src_rom, confidence=95, importance=3)
    b.add_event(year=-31, title="Battle of Actium",
                description="屋大维舰队在阿克提乌姆击败安东尼与克利奥帕特拉。",
                significance="罗马内战终结，元首制即将建立。",
                event_type="naval_battle",
                polity_keys=["roman_republic", "ptolemaic_egypt"],
                people="Octavian; Marcus Antonius; Cleopatra VII",
                source_ids=src_rom, confidence=92, importance=3)
    b.add_event(year=-27, title="Octavian becomes Augustus, founding of Principate",
                description="元老院授予屋大维 Augustus 称号，罗马帝国元首制成立。",
                significance="罗马帝国正式起点。",
                event_type="constitutional_transition",
                polity_keys=["roman_republic", "roman_principate"],
                people="Augustus", location="Rome",
                source_ids=src_emp, confidence=95, importance=3)
    b.add_event(year=313, title="Edict of Milan",
                description="君士坦丁与李锡尼颁布米兰敕令，承认基督教合法。",
                significance="基督教从被迫害宗教转为帝国合法信仰。",
                event_type="religious_edict",
                polity_keys=["roman_dominate"],
                people="Constantine I; Licinius", location="Milan",
                source_ids=src_emp, confidence=90, importance=3)
    b.add_event(year=330, title="Foundation of Constantinople",
                description="君士坦丁将首都迁至拜占庭并改名君士坦丁堡。",
                significance="东罗马 / 拜占庭首都奠基。",
                event_type="capital_founding",
                polity_keys=["roman_dominate", "eastern_roman"],
                people="Constantine I", location="Constantinople",
                source_ids=src_byz, confidence=92, importance=3)
    b.add_event(year=395, title="Final division of the Roman Empire",
                description="狄奥多西去世，帝国永久分为东西两部，分别交由阿卡迪乌斯和霍诺里乌斯统治。",
                significance="罗马帝国正式分裂。",
                event_type="political_division",
                polity_keys=["roman_dominate", "western_roman", "eastern_roman"],
                people="Theodosius I", location="Rome",
                source_ids=src_emp, confidence=92, importance=3)
    b.add_event(year=410, title="Sack of Rome by Alaric",
                description="西哥特国王阿拉里克率军攻陷并劫掠罗马城。",
                significance="罗马城八百年来首次陷落，西罗马衰亡加速。",
                event_type="city_sack",
                polity_keys=["western_roman", "visigothic_kingdom"],
                people="Alaric I", location="Rome",
                source_ids=src_emp, confidence=92, importance=3)
    b.add_event(year=476, title="Deposition of Romulus Augustulus",
                description="奥多亚塞废黜西罗马末帝罗慕路斯·奥古斯都，传统视为西罗马帝国终结。",
                significance="西罗马帝国名义灭亡。",
                event_type="political_collapse",
                polity_keys=["western_roman", "ostrogothic_italy"],
                people="Odoacer; Romulus Augustulus", location="Ravenna",
                source_ids=src_emp, confidence=92, importance=3)
    b.add_event(year=496, title="Conversion of Clovis I",
                description="法兰克国王克洛维一世皈依天主教。",
                significance="高卢蛮族王国与罗马教会结盟雏形。",
                event_type="religious_conversion",
                polity_keys=["frankish_merovingian"],
                people="Clovis I", location="Reims",
                source_ids=["source_eur_0015"], confidence=82, importance=2)

    b.add_context(start=-500, end=500, title="希腊-罗马古典时代",
                  description="希波战争 → 伯罗奔尼撒战争 → 亚历山大帝国 → 罗马共和扩张 → 罗马帝国 → 西罗马灭亡。",
                  source_ids=src_rom, confidence=85)

    b.add_strategic("Rome", "capital", start=-753, end=476, modern="Rome",
                    admin="ITA", summary="罗马王政、共和、帝国都城。",
                    significance="地中海世界政治中心。",
                    source_ids=src_rom, related_polity_keys=["roman_kingdom", "roman_republic", "roman_principate"], confidence=92)
    b.add_strategic("Alexandria", "capital", start=-331, end=641, modern="Alexandria",
                    admin="EGY", summary="希腊化最大文化、学术中心。",
                    significance="亚历山大图书馆与法罗斯灯塔所在地。",
                    source_ids=src_grc, related_polity_keys=["ptolemaic_egypt"], confidence=88)
    b.add_strategic("Constantinople", "capital", start=330, end=1453, modern="Istanbul",
                    admin="TUR", summary="新罗马，东罗马 / 拜占庭千年都城。",
                    significance="基督教东方教会中心。",
                    source_ids=src_byz, related_polity_keys=["roman_dominate", "eastern_roman"], confidence=92)
    b.add_strategic("Pella", "capital", start=-400, end=-148, modern="Pella",
                    admin="GRC", summary="马其顿王国首都，亚历山大大帝出生地。",
                    significance="希腊化时代起源地。",
                    source_ids=src_grc, related_polity_keys=["macedonia_argead", "macedonia_antigonid"], confidence=82)


def _register_early_medieval(b: Builder) -> None:
    """Early Medieval (500-1000). Byzantine, Carolingian, al-Andalus,
    Anglo-Saxon, Viking, Kievan Rus', early Slavic states."""
    src_byz = ["source_eur_0003"]
    src_car = ["source_eur_0023"]
    src_frk = ["source_eur_0015"]
    src_uk = ["source_eur_0006"]
    src_vik = ["source_eur_0016"]
    src_rus = ["source_eur_0010"]
    src_isl = ["source_eur_0012"]

    b.add_polity(
        "byzantine_middle", "Middle Byzantine Empire",
        "中古时代", "Isaurian / Macedonian / Komnenian", "empire", 717, 1204,
        aliases="Basileia Rhōmaiōn", display="中期拜占庭帝国",
        geography="希腊与安纳托利亚核心；马其顿王朝时期一度恢复至意大利南部与黎凡特。",
        modern_admin="GRC|TUR|BGR|MKD|ALB|SRB|MNE|HRV|CYP|ITA|SYR|LBN|ISR|JOR",
        capital="Constantinople",
        family="Isaurian → Amorian → Macedonian → Doukas → Komnenos → Angelos", group="Greco-Roman",
        founder="Leo III the Isaurian",
        last_ruler="Alexios V Doukas (Constantinople sacked 1204)",
        successor="Nicaean Empire / Latin Empire",
        source_ids=src_byz, confidence=88,
    )
    b.add_capital("byzantine_middle", "Constantinople", 717, 1204, src_byz, 90)
    b.add_ruler("byzantine_middle", "Leo III the Isaurian", "basileus", 717, 741, source_ids=src_byz, confidence=88)
    b.add_ruler("byzantine_middle", "Basil II Bulgar-Slayer", "basileus", 976, 1025, personal="Basileios Boulgaroktonos", source_ids=src_byz, confidence=92)
    b.add_ruler("byzantine_middle", "Alexios I Komnenos", "basileus", 1081, 1118, source_ids=src_byz, confidence=88)

    b.add_polity(
        "carolingian_empire", "Carolingian Empire",
        "中古时代", "Carolingian", "empire", 751, 887,
        aliases="Imperium Francorum", display="加洛林帝国",
        geography="法兰西、低地、德意志西部、意大利北部、加泰罗尼亚边境。",
        modern_admin="FRA|DEU|BEL|NLD|LUX|CHE|AUT|ITA|ESP", capital="Aachen",
        family="Carolingian dynasty", group="Frankish",
        founder="Pepin the Short (751)",
        last_ruler="Charles the Fat (deposed 887)",
        successor="West Francia / East Francia / Lotharingia",
        source_ids=src_car, confidence=90,
    )
    b.add_capital("carolingian_empire", "Aachen", 794, 814, src_car, 90)
    b.add_capital("carolingian_empire", "Paris", 814, 887, src_car, 80)
    b.add_ruler("carolingian_empire", "Pepin the Short", "rex Francorum", 751, 768, source_ids=src_car, confidence=88)
    b.add_ruler("carolingian_empire", "Charlemagne", "imperator Romanorum", 768, 814, personal="Carolus Magnus", source_ids=src_car, confidence=95)
    b.add_ruler("carolingian_empire", "Louis the Pious", "imperator", 814, 840, source_ids=src_car, confidence=88)

    b.add_polity(
        "west_francia", "West Francia",
        "中古时代", "Carolingian / Capetian", "kingdom", 843, 987,
        aliases="Francia Occidentalis", display="西法兰克王国",
        geography="法兰西大致疆域（Verdun 条约划定）。",
        modern_admin="FRA|BEL", capital="Paris",
        family="Carolingian → Robertian → Capetian", group="Frankish",
        founder="Charles the Bald (Treaty of Verdun)",
        last_ruler="Louis V (last Carolingian)",
        successor="Kingdom of France (Hugh Capet, 987)",
        source_ids=src_car, confidence=85,
    )

    b.add_polity(
        "east_francia", "East Francia",
        "中古时代", "Carolingian / Ottonian", "kingdom", 843, 962,
        aliases="Francia Orientalis", display="东法兰克王国",
        geography="德意志诸公国（萨克森、巴伐利亚、士瓦本、法兰克尼亚等）。",
        modern_admin="DEU|AUT|CHE|NLD", capital="Frankfurt",
        family="Carolingian → Ottonian", group="Frankish / Saxon",
        founder="Louis the German",
        last_ruler="Otto I (crowned emperor 962, marks HRE founding)",
        successor="Holy Roman Empire",
        source_ids=src_car, confidence=85,
    )

    b.add_polity(
        "lotharingia", "Middle Francia / Lotharingia",
        "中古时代", "Carolingian", "kingdom", 843, 870,
        aliases="Lotharingia", display="中法兰克 / 洛塔尔林吉亚",
        geography="低地国、洛林、勃艮第、意大利北部、普罗旺斯。",
        modern_admin="NLD|BEL|LUX|FRA|CHE|DEU|ITA", capital="Pavia",
        family="Carolingian (Lothair line)", group="Frankish",
        founder="Lothair I (Treaty of Verdun)",
        last_ruler="Lothair II",
        successor="Divided by Treaty of Meersen 870",
        source_ids=src_car, confidence=78,
    )

    b.add_polity(
        "umayyad_iberia", "Umayyad al-Andalus (Caliphate of Córdoba)",
        "中古时代", "Umayyad", "emirate_caliphate", 711, 1031,
        aliases="Al-Andalus|Caliphate of Córdoba", display="后倭马亚安达卢斯（科尔多瓦哈里发国）",
        geography="伊比利亚半岛大部；穆斯林西班牙的鼎盛期。",
        modern_admin="ESP|PRT", capital="Cordoba",
        family="Umayyad dynasty (Andalusian branch)", group="Arab-Berber Muslim",
        founder="Abd al-Rahman I (756 Emirate); Abd al-Rahman III (929 Caliphate)",
        last_ruler="Hisham III (deposed 1031)",
        successor="Taifa kingdoms",
        source_ids=["source_eur_0007"], confidence=88,
    )
    b.add_capital("umayyad_iberia", "Cordoba", 756, 1031, ["source_eur_0007"], 88)
    b.add_ruler("umayyad_iberia", "Abd al-Rahman I", "emir", 756, 788, source_ids=["source_eur_0007"], confidence=88)
    b.add_ruler("umayyad_iberia", "Abd al-Rahman III", "caliph", 929, 961, source_ids=["source_eur_0007"], confidence=88)

    b.add_polity(
        "asturias_leon", "Kingdom of Asturias / León",
        "中古时代", "Asturian / Leonese", "kingdom", 718, 1230,
        aliases="Regnum Asturorum", display="阿斯图里亚斯-莱昂王国",
        geography="伊比利亚北部基督教抵抗中心；阿斯图里亚斯→莱昂。",
        modern_admin="ESP", capital="León",
        family="Asturian-Leonese", group="Iberian Christian",
        founder="Pelagius of Asturias",
        successor="Castile-Leon union 1230",
        source_ids=["source_eur_0007"], confidence=78,
    )
    b.add_capital("asturias_leon", "León", 910, 1230, ["source_eur_0007"], 80)

    b.add_polity(
        "navarre_kingdom", "Kingdom of Navarre",
        "中古时代", "Navarrese", "kingdom", 824, 1620,
        aliases="Regnum Navarrae", display="纳瓦拉王国",
        geography="比利牛斯山西部，巴斯克地区核心。",
        modern_admin="ESP|FRA|ES-NC", capital="",
        family="Navarrese (Íñiguez → Jiménez → others)", group="Basque / Iberian Christian",
        founder="Iñigo Arista",
        successor="Castilian annexation south 1512, French Bourbon north until 1620",
        source_ids=["source_eur_0007"], confidence=78,
    )

    b.add_polity(
        "anglo_saxon_wessex", "Kingdom of Wessex",
        "中古时代", "House of Wessex / Cerdicings", "kingdom", 519, 927,
        aliases="West Saxons", display="韦塞克斯王国",
        geography="英格兰西南部；阿尔弗雷德大王抵御维京后扩张为英格兰。",
        modern_admin="GBR|GB-ENG", capital="Winchester",
        family="House of Wessex", group="Anglo-Saxon",
        founder="Cerdic (legendary, 519)",
        last_ruler="Æthelstan (first king of all England, 927)",
        successor="Kingdom of England",
        source_ids=src_uk, confidence=80,
    )
    b.add_capital("anglo_saxon_wessex", "Winchester", 519, 927, src_uk, 80)
    b.add_ruler("anglo_saxon_wessex", "Alfred the Great", "rex", 871, 899, source_ids=src_uk, confidence=92)
    b.add_ruler("anglo_saxon_wessex", "Æthelstan", "rex Anglorum", 924, 939, source_ids=src_uk, confidence=88)

    b.add_polity(
        "viking_norway", "Kingdom of Norway (Viking Age)",
        "中古时代", "Fairhair dynasty", "kingdom", 872, 1397,
        aliases="Norwegian Vikings", display="挪威王国（维京时代起）",
        geography="挪威本土加冰岛、法罗群岛、奥克尼、设得兰、北部不列颠殖民点。",
        modern_admin="NOR|ISL", capital="Trondheim",
        family="Fairhair → Hardrada → various", group="Norse",
        founder="Harald Fairhair",
        successor="Kalmar Union (1397)",
        source_ids=src_vik, confidence=82,
    )
    b.add_capital("viking_norway", "Trondheim", 1030, 1300, src_vik, 78)
    b.add_capital("viking_norway", "Oslo", 1300, 1397, src_vik, 80)
    b.add_ruler("viking_norway", "Harald Fairhair", "rex", 872, 932, source_ids=src_vik, confidence=72)
    b.add_ruler("viking_norway", "Harald Hardrada", "rex", 1046, 1066, source_ids=src_vik, confidence=85)

    b.add_polity(
        "viking_denmark", "Kingdom of Denmark (Viking Age)",
        "中古时代", "Jelling dynasty", "kingdom", 936, 1397,
        aliases="Danish Vikings", display="丹麦王国（维京时代起）",
        geography="日德兰半岛、岛屿；北海帝国时期含英格兰部分。",
        modern_admin="DNK|GB-ENG", capital="Roskilde",
        family="Jelling → Estridsen", group="Danish Norse",
        founder="Gorm the Old",
        successor="Kalmar Union (1397)",
        source_ids=src_vik, confidence=82,
    )
    b.add_capital("viking_denmark", "Roskilde", 980, 1416, src_vik, 80)
    b.add_ruler("viking_denmark", "Harald Bluetooth", "rex", 958, 986, source_ids=src_vik, confidence=85)
    b.add_ruler("viking_denmark", "Cnut the Great", "rex", 1016, 1035, source_ids=src_vik, confidence=88, note="King of England, Denmark, Norway (North Sea Empire).")

    b.add_polity(
        "viking_sweden", "Kingdom of Sweden (Viking Age)",
        "中古时代", "House of Munsö", "kingdom", 970, 1397,
        aliases="Swedish Vikings", display="瑞典王国（维京时代起）",
        geography="斯堪的纳维亚东部；瓦良格人扩张到东欧水道。",
        modern_admin="SWE", capital="Uppsala",
        family="House of Munsö → Sverker → Eric", group="Swedish Norse",
        founder="Eric the Victorious",
        successor="Kalmar Union (1397)",
        source_ids=src_vik, confidence=78,
    )
    b.add_capital("viking_sweden", "Uppsala", 1100, 1397, src_vik, 75)

    b.add_polity(
        "kievan_rus", "Kievan Rus'",
        "中古时代", "Rurikid", "principality_federation", 882, 1240,
        aliases="Rus'|Kyivan Rus'", display="基辅罗斯",
        geography="东欧河流网络；从基辅向北诺夫哥罗德至北冰洋。",
        modern_admin="UKR|RUS|BLR", capital="Kiev",
        family="Rurikid dynasty", group="East Slavic + Norse Varangians",
        founder="Oleg of Novgorod",
        last_ruler="Mikhail I of Kiev",
        successor="Mongol invasion / Galicia-Volhynia / various principalities",
        source_ids=src_rus, confidence=82,
    )
    b.add_capital("kievan_rus", "Kiev", 882, 1240, src_rus, 85)
    b.add_ruler("kievan_rus", "Vladimir the Great", "knyaz", 980, 1015, source_ids=src_rus, confidence=88, note="Christianized Kievan Rus' 988.")
    b.add_ruler("kievan_rus", "Yaroslav the Wise", "knyaz", 1019, 1054, source_ids=src_rus, confidence=88)

    b.add_polity(
        "great_moravia", "Great Moravia",
        "中古时代", "Mojmír dynasty", "principality", 833, 907,
        aliases="Moravian Empire", display="大摩拉维亚",
        geography="今捷克东部、斯洛伐克、匈牙利北部；早期斯拉夫国家。",
        modern_admin="CZE|SVK|HUN|POL", capital="",
        family="Mojmír dynasty", group="West Slavic",
        founder="Mojmír I",
        last_ruler="Mojmír II",
        successor="Conquered by Magyars 907",
        source_ids=["source_eur_0001"], confidence=72,
    )

    b.add_polity(
        "first_bulgarian", "First Bulgarian Empire",
        "中古时代", "Krum / Krumid dynasty", "empire", 681, 1018,
        aliases="Bulgarian Empire", display="第一保加利亚帝国",
        geography="巴尔干东部；与拜占庭长期对抗。",
        modern_admin="BGR|MKD|SRB|ROU", capital="",
        family="Krum and successors", group="Bulgar + Slav",
        founder="Asparuh",
        last_ruler="Ivan Vladislav (1018 fall to Basil II)",
        successor="Byzantine reconquest",
        source_ids=src_byz, confidence=82,
    )
    b.add_ruler("first_bulgarian", "Simeon I the Great", "tsar", 893, 927, source_ids=src_byz, confidence=85)

    b.add_polity(
        "magyars_principality", "Principality of Hungary (Magyar)",
        "中古时代", "Árpád dynasty", "principality", 895, 1000,
        aliases="Magyars", display="马扎尔（匈牙利公国）",
        geography="喀尔巴阡盆地；匈牙利定居后。",
        modern_admin="HUN|SVK|ROU|HRV|SRB|SVN", capital="",
        family="Árpád dynasty", group="Magyar (Finno-Ugric)",
        founder="Árpád",
        successor="Kingdom of Hungary (Stephen I, 1000)",
        source_ids=["source_eur_0014"], confidence=78,
    )

    b.add_polity(
        "papal_states_early", "Papal States (early temporal rule)",
        "中古时代", "Papacy", "theocracy", 754, 1095,
        aliases="Patrimonium Petri", display="教皇国（早期世俗统治）",
        geography="意大利中部拉齐奥与翁布里亚；丕平献土起源。",
        modern_admin="ITA|VAT", capital="Rome",
        family="Roman papacy", group="Italian / Latin Church",
        founder="Stephen II (Donation of Pepin, 756)",
        successor="High medieval papal monarchy",
        source_ids=["source_eur_0009"], confidence=82,
    )
    b.add_capital("papal_states_early", "Rome", 754, 1095, ["source_eur_0009"], 85)

    b.add_polity(
        "abbasid_iberia_neighbor", "Abbasid Caliphate (European frontier)",
        "中古时代", "Abbasid", "empire", 750, 1258,
        aliases="Abbasids", display="阿拔斯王朝（欧洲边界视角）",
        geography="近东与北非；通过西班牙穆斯林与黎凡特与欧洲交错。",
        modern_admin="IRQ|SYR|IRN|EGY|TUR", capital="",
        family="Abbasid dynasty", group="Arab Muslim",
        founder="Abu al-Abbas al-Saffah",
        last_ruler="Al-Musta'sim",
        successor="Mongol sack of Baghdad 1258",
        source_ids=["source_eur_0026"], confidence=80,
        note="Listed for vEuropean coverage as crusade adversary; primary coverage in future Near East dataset.",
    )

    b.add_event(year=732, title="Battle of Tours (Poitiers)",
                description="查理·马特尔率法兰克军在图尔击败倭马亚军北上扩张。",
                significance="阻止穆斯林军向北深入西欧。",
                event_type="battle", polity_keys=["frankish_merovingian", "umayyad_iberia"],
                people="Charles Martel", location="Tours",
                source_ids=src_frk, confidence=88, importance=3)
    b.add_event(year=751, title="Pepin the Short crowned king of the Franks",
                description="加洛林家族正式取代墨洛温王朝。",
                significance="加洛林王朝建立。",
                event_type="dynastic_change",
                polity_keys=["frankish_merovingian", "carolingian_empire"],
                people="Pepin the Short", location="Paris",
                source_ids=src_car, confidence=85, importance=2)
    b.add_event(year=800, title="Coronation of Charlemagne as Roman Emperor",
                description="教皇利奥三世在罗马圣彼得大教堂为查理曼加冕罗马人皇帝。",
                significance="西方罗马帝国称号复活。",
                event_type="coronation",
                polity_keys=["carolingian_empire"], people="Charlemagne; Pope Leo III",
                location="Rome", source_ids=src_car, confidence=95, importance=3)
    b.add_event(year=843, title="Treaty of Verdun",
                description="加洛林帝国按 Verdun 条约划分为西、中、东三部分。",
                significance="法兰西与德意志雏形。",
                event_type="treaty",
                polity_keys=["carolingian_empire", "west_francia", "east_francia", "lotharingia"],
                location="Verdun", source_ids=src_car, confidence=92, importance=3)
    b.add_event(year=987, title="Hugh Capet elected king of West Francia",
                description="休·卡佩成为西法兰克国王，开启卡佩王朝。",
                significance="法兰西卡佩王朝起点，加洛林直系结束。",
                event_type="dynastic_change",
                polity_keys=["west_francia"],
                people="Hugh Capet", location="Reims",
                source_ids=["source_eur_0032"], confidence=88, importance=3)
    b.add_event(year=962, title="Otto I crowned Holy Roman Emperor",
                description="奥托一世由教皇约翰十二世加冕，神圣罗马帝国成立。",
                significance="HRE 名义起点。",
                event_type="coronation",
                polity_keys=["east_francia"], people="Otto I; Pope John XII",
                location="Rome", source_ids=["source_eur_0004"], confidence=92, importance=3)
    b.add_event(year=988, title="Christianization of Kievan Rus'",
                description="弗拉基米尔大公皈依希腊正教，定基辅罗斯国教。",
                significance="俄罗斯-乌克兰-白俄罗斯东正教传统起点。",
                event_type="religious_conversion",
                polity_keys=["kievan_rus"], people="Vladimir the Great",
                location="Kiev", source_ids=src_rus, confidence=92, importance=3)

    b.add_context(start=500, end=1000, title="早期中世纪",
                  description="罗马废墟上的蛮族王国 → 加洛林复兴 → 维京 / 阿拉伯 / 马扎尔三面扰动 → 西欧基本骨架成形。",
                  source_ids=src_car, confidence=82)

    b.add_strategic("Aachen", "capital", start=794, end=843, modern="Aachen",
                    admin="DEU|DE-NW", summary="加洛林帝国首都，查理曼宫廷与教堂所在地。",
                    significance="加洛林文艺复兴中心。",
                    source_ids=src_car, related_polity_keys=["carolingian_empire"], confidence=88)
    b.add_strategic("Cordoba", "capital", start=756, end=1031, modern="Córdoba",
                    admin="ESP|ES-AN", summary="后倭马亚安达卢斯首都。",
                    significance="十世纪欧洲最大、最繁荣的城市之一。",
                    source_ids=["source_eur_0007"], related_polity_keys=["umayyad_iberia"], confidence=88)
    b.add_strategic("Kiev", "capital", start=882, end=1240, modern="Kyiv",
                    admin="UKR", summary="基辅罗斯首都，东欧斯拉夫文明中心。",
                    significance="东斯拉夫文明与东正教传播枢纽。",
                    source_ids=src_rus, related_polity_keys=["kievan_rus"], confidence=88)
    b.add_strategic("Winchester", "capital", start=519, end=1066, modern="Winchester",
                    admin="GBR|GB-ENG", summary="韦塞克斯王国首都，盎格鲁-撒克逊英格兰行政中心。",
                    significance="阿尔弗雷德大王所在。",
                    source_ids=src_uk, related_polity_keys=["anglo_saxon_wessex"], confidence=82)


def _register_high_late_medieval(b: Builder) -> None:
    """High & Late Medieval (1000-1453). HRE constituents, Italian city-states,
    France, England, Scotland, Iberian Reconquista, Scandinavian, Polish,
    Byzantine decline, Crusader states, Ottoman expansion to 1453."""
    src_hre = ["source_eur_0004"]
    src_fra = ["source_eur_0005"]
    src_uk = ["source_eur_0006"]
    src_esp = ["source_eur_0007"]
    src_ita = ["source_eur_0009"]
    src_pol = ["source_eur_0013"]
    src_hun = ["source_eur_0014"]
    src_rus = ["source_eur_0010"]
    src_byz = ["source_eur_0003"]
    src_ott = ["source_eur_0012"]
    src_cru = ["source_eur_0026"]
    src_vik = ["source_eur_0016"]

    b.add_polity(
        "hre_early", "Holy Roman Empire (Salian / Hohenstaufen)",
        "中世纪盛期", "Salian → Hohenstaufen", "empire", 962, 1254,
        aliases="Sacrum Imperium Romanum",
        display="神圣罗马帝国（萨利-霍亨斯陶芬时期）",
        geography="德意志诸公国、勃艮第、意大利北部与中部。",
        modern_admin="DEU|AUT|CHE|ITA|CZE|BEL|NLD|LUX|FRA",
        capital="",
        family="Ottonian → Salian → Hohenstaufen", group="German / Frankish",
        founder="Otto I",
        last_ruler="Conrad IV (Hohenstaufen end approaching)",
        successor="Great Interregnum",
        source_ids=src_hre, confidence=88,
    )
    b.add_ruler("hre_early", "Otto I the Great", "imperator", 962, 973, source_ids=src_hre, confidence=92)
    b.add_ruler("hre_early", "Henry IV", "imperator", 1084, 1105, source_ids=src_hre, confidence=88, note="Investiture Controversy with Pope Gregory VII.")
    b.add_ruler("hre_early", "Frederick I Barbarossa", "imperator", 1155, 1190, personal="Friedrich von Hohenstaufen", source_ids=src_hre, confidence=92)
    b.add_ruler("hre_early", "Frederick II", "imperator", 1220, 1250, source_ids=src_hre, confidence=92, note="Stupor mundi, ruled Sicily + Germany.")

    b.add_polity(
        "hre_late", "Holy Roman Empire (Luxembourg / Habsburg era)",
        "中世纪晚期", "Luxembourg → Habsburg", "empire", 1273, 1806,
        aliases="HRE late medieval / early modern",
        display="神圣罗马帝国（卢森堡-哈布斯堡时期）",
        geography="德意志、波西米亚、奥地利、低地（直到 1581）、北意大利残余。",
        modern_admin="DEU|AUT|CHE|CZE|BEL|NLD|LUX|ITA|FRA|SVN|HRV",
        capital="Vienna",
        family="Luxembourg → Habsburg → Habsburg-Lorraine", group="German",
        founder="Rudolf I of Habsburg",
        last_ruler="Francis II (abdicated 1806)",
        successor="Confederation of the Rhine / Austrian Empire",
        source_ids=src_hre, confidence=90,
    )
    b.add_capital("hre_late", "Vienna", 1438, 1806, src_hre, 88)
    b.add_capital("hre_late", "Prague", 1346, 1437, src_hre, 82, note="Under Luxembourg Emperor Charles IV.")
    b.add_ruler("hre_late", "Charles IV", "imperator", 1355, 1378, source_ids=src_hre, confidence=92, note="Promulgated Golden Bull 1356.")
    b.add_ruler("hre_late", "Frederick III", "imperator", 1452, 1493, source_ids=src_hre, confidence=88)

    b.add_polity(
        "kingdom_france", "Kingdom of France",
        "中世纪盛期", "Capetian / Valois / Bourbon", "kingdom", 987, 1792,
        aliases="Royaume de France", display="法兰西王国",
        geography="法兰西本土；中世纪封建王国 → 集权绝对君主国。",
        modern_admin="FRA|BEL|LUX",
        capital="Paris",
        family="Capetian → Valois → Bourbon", group="French",
        founder="Hugh Capet (987)",
        last_ruler="Louis XVI (executed 1793)",
        successor="French Republic",
        source_ids=src_fra, confidence=92,
    )
    b.add_capital("kingdom_france", "Paris", 987, 1792, src_fra, 90)
    b.add_ruler("kingdom_france", "Philip II Augustus", "rex Francorum", 1180, 1223, source_ids=src_fra, confidence=92)
    b.add_ruler("kingdom_france", "Louis IX (Saint Louis)", "rex", 1226, 1270, source_ids=src_fra, confidence=92)
    b.add_ruler("kingdom_france", "Philip IV the Fair", "rex", 1285, 1314, source_ids=src_fra, confidence=92)
    b.add_ruler("kingdom_france", "Charles V", "rex", 1364, 1380, source_ids=src_fra, confidence=88)
    b.add_ruler("kingdom_france", "Louis XI", "rex", 1461, 1483, source_ids=src_fra, confidence=88)
    b.add_ruler("kingdom_france", "Francis I", "rex", 1515, 1547, source_ids=src_fra, confidence=92)
    b.add_ruler("kingdom_france", "Henry IV", "rex", 1589, 1610, source_ids=src_fra, confidence=92, note="First Bourbon king, Edict of Nantes 1598.")
    b.add_ruler("kingdom_france", "Louis XIV the Sun King", "rex", 1643, 1715, source_ids=src_fra, confidence=95)
    b.add_ruler("kingdom_france", "Louis XV", "rex", 1715, 1774, source_ids=src_fra, confidence=92)
    b.add_ruler("kingdom_france", "Louis XVI", "rex", 1774, 1792, source_ids=src_fra, confidence=92)

    b.add_polity(
        "kingdom_england", "Kingdom of England",
        "中世纪盛期", "Norman / Plantagenet / Lancaster / York / Tudor / Stuart",
        "kingdom", 927, 1707,
        aliases="Regnum Angliae", display="英格兰王国",
        geography="英格兰本土；1284 后含威尔士，1541 起合并爱尔兰。",
        modern_admin="GBR|GB-ENG|GB-WLS",
        capital="London",
        family="Wessex → Norman → Plantagenet → Lancaster → York → Tudor → Stuart",
        group="English",
        founder="Æthelstan (927) / William I (Norman conquest 1066)",
        last_ruler="Anne (Acts of Union 1707)",
        successor="Kingdom of Great Britain",
        source_ids=src_uk, confidence=92,
    )
    b.add_capital("kingdom_england", "London", 1066, 1707, src_uk, 90)
    b.add_ruler("kingdom_england", "William I the Conqueror", "rex Anglorum", 1066, 1087, source_ids=["source_eur_0031"], confidence=95)
    b.add_ruler("kingdom_england", "Henry II", "rex", 1154, 1189, source_ids=["source_eur_0031"], confidence=92)
    b.add_ruler("kingdom_england", "Richard I the Lionheart", "rex", 1189, 1199, source_ids=src_uk, confidence=92)
    b.add_ruler("kingdom_england", "John", "rex", 1199, 1216, source_ids=src_uk, confidence=92, note="Magna Carta 1215.")
    b.add_ruler("kingdom_england", "Edward I", "rex", 1272, 1307, source_ids=src_uk, confidence=92)
    b.add_ruler("kingdom_england", "Edward III", "rex", 1327, 1377, source_ids=src_uk, confidence=92)
    b.add_ruler("kingdom_england", "Henry V", "rex", 1413, 1422, source_ids=src_uk, confidence=92)
    b.add_ruler("kingdom_england", "Henry VII", "rex", 1485, 1509, source_ids=src_uk, confidence=92, note="First Tudor king.")
    b.add_ruler("kingdom_england", "Henry VIII", "rex", 1509, 1547, source_ids=src_uk, confidence=95)
    b.add_ruler("kingdom_england", "Elizabeth I", "regina", 1558, 1603, source_ids=src_uk, confidence=95)

    b.add_polity(
        "kingdom_scotland", "Kingdom of Scotland",
        "中世纪盛期", "Alpinid / Canmore / Bruce / Stewart", "kingdom", 843, 1707,
        aliases="Regnum Scotorum", display="苏格兰王国",
        geography="苏格兰本土；与英格兰长期对抗，1707 合并。",
        modern_admin="GBR|GB-SCT", capital="Edinburgh",
        family="House of Alpin → Canmore → Bruce → Stewart", group="Scottish",
        founder="Kenneth MacAlpin (843)",
        last_ruler="Anne (Acts of Union 1707)",
        successor="Kingdom of Great Britain",
        source_ids=src_uk, confidence=85,
    )
    b.add_capital("kingdom_scotland", "Edinburgh", 1437, 1707, src_uk, 85)
    b.add_ruler("kingdom_scotland", "Robert I the Bruce", "rex Scottorum", 1306, 1329, source_ids=src_uk, confidence=92)

    b.add_polity(
        "venetian_republic", "Republic of Venice",
        "中世纪盛期", "Venetian doges", "merchant_republic", 697, 1797,
        aliases="Serenissima|Repubblica di Venezia", display="威尼斯共和国",
        geography="威尼斯潟湖、亚得里亚海港口、克里特、塞浦路斯（一度）。",
        modern_admin="ITA|HRV|GRC|CYP|MNE|ALB",
        capital="Venice",
        family="Elective dogeship (multiple families)", group="Venetian Italian",
        founder="(traditional) Paolo Lucio Anafesto 697",
        last_ruler="Ludovico Manin (abdicated to Napoleon 1797)",
        successor="French / Austrian rule",
        source_ids=src_ita, confidence=90,
    )
    b.add_capital("venetian_republic", "Venice", 810, 1797, src_ita, 90)

    b.add_polity(
        "florence_republic", "Republic of Florence",
        "中世纪盛期", "Medici-influenced republican", "republic", 1115, 1532,
        aliases="Repubblica Fiorentina", display="佛罗伦萨共和国",
        geography="托斯卡纳；文艺复兴中心。",
        modern_admin="ITA|IT-NORDOVES",
        capital="Florence",
        family="Albizzi → Medici (de facto)", group="Florentine",
        founder="Communal government (1115)",
        last_ruler="Alessandro de' Medici (became Duke 1532)",
        successor="Duchy of Florence → Grand Duchy of Tuscany",
        source_ids=src_ita, confidence=88,
    )
    b.add_capital("florence_republic", "Florence", 1115, 1532, src_ita, 90)
    b.add_ruler("florence_republic", "Cosimo de' Medici (the Elder)", "Pater Patriae", 1434, 1464, source_ids=src_ita, confidence=88)
    b.add_ruler("florence_republic", "Lorenzo de' Medici (the Magnificent)", "informal head", 1469, 1492, source_ids=src_ita, confidence=92)

    b.add_polity(
        "genoa_republic", "Republic of Genoa",
        "中世纪盛期", "Genoese doges", "merchant_republic", 1099, 1797,
        aliases="Repubblica di Genova", display="热那亚共和国",
        geography="利古里亚沿海、科西嘉、地中海贸易点。",
        modern_admin="ITA|FRA", capital="Genoa",
        group="Genoese Italian", successor="French annexation 1797",
        source_ids=src_ita, confidence=85,
    )
    b.add_capital("genoa_republic", "Genoa", 1099, 1797, src_ita, 88)

    b.add_polity(
        "milan_duchy", "Duchy of Milan",
        "中世纪盛期", "Visconti → Sforza", "duchy", 1395, 1796,
        aliases="Ducato di Milano", display="米兰公国",
        geography="伦巴第；连接意大利与阿尔卑斯。",
        modern_admin="ITA",
        capital="Milan",
        family="Visconti → Sforza → Spanish Habsburg → Austrian Habsburg",
        group="Lombard Italian",
        founder="Gian Galeazzo Visconti",
        successor="Cisalpine Republic (Napoleonic)",
        source_ids=src_ita, confidence=85,
    )
    b.add_capital("milan_duchy", "Milan", 1395, 1796, src_ita, 88)

    b.add_polity(
        "kingdom_naples", "Kingdom of Naples / Sicily",
        "中世纪盛期", "Hauteville → Hohenstaufen → Anjou → Aragon → Bourbon",
        "kingdom", 1130, 1816,
        aliases="Regnum Siciliae|Regno di Napoli", display="那不勒斯-西西里王国",
        geography="意大利南部加西西里岛；多次易主。",
        modern_admin="ITA|IT-SUD|IT-ISOLE",
        capital="Naples",
        family="Multiple dynasties", group="Southern Italian",
        founder="Roger II",
        successor="Kingdom of the Two Sicilies",
        source_ids=src_ita, confidence=85,
    )
    b.add_capital("kingdom_naples", "Naples", 1282, 1816, src_ita, 88)
    b.add_capital("kingdom_naples", "Palermo", 1130, 1282, src_ita, 85)

    b.add_polity(
        "papal_states_high", "Papal States (high medieval to 1870)",
        "中世纪盛期", "Papacy", "theocracy", 1095, 1870,
        aliases="Stato Pontificio", display="教皇国（中世纪盛期至 1870）",
        geography="意大利中部教皇直接统治区。",
        modern_admin="ITA|VAT",
        capital="Rome",
        family="Roman papacy", group="Italian Latin Church",
        successor="Italian unification 1870",
        source_ids=src_ita, confidence=90,
    )
    b.add_capital("papal_states_high", "Rome", 1095, 1870, src_ita, 90)
    b.add_capital("papal_states_high", "Avignon", 1309, 1377, ["source_eur_0026"], 88, note="Avignon papacy.")

    b.add_polity(
        "kingdom_castile", "Kingdom of Castile",
        "中世纪盛期", "Castilian", "kingdom", 1035, 1715,
        aliases="Regnum Castellae", display="卡斯蒂利亚王国",
        geography="伊比利亚中部；与莱昂、阿拉贡、葡萄牙并立到联合。",
        modern_admin="ESP|ES-CL|ES-MD",
        capital="Burgos",
        family="Jiménez → Burgundy → Trastámara → Habsburg → Bourbon", group="Castilian",
        founder="Ferdinand I",
        successor="Crown of Castile within united Spain",
        source_ids=src_esp, confidence=85,
    )
    b.add_capital("kingdom_castile", "Burgos", 1035, 1480, src_esp, 82)
    b.add_capital("kingdom_castile", "Toledo", 1085, 1561, src_esp, 82)
    b.add_capital("kingdom_castile", "Madrid", 1561, 1715, src_esp, 90)
    b.add_ruler("kingdom_castile", "Alfonso X the Wise", "rex", 1252, 1284, source_ids=src_esp, confidence=88)
    b.add_ruler("kingdom_castile", "Isabella I of Castile", "regina", 1474, 1504, source_ids=src_esp, confidence=92)

    b.add_polity(
        "kingdom_aragon", "Kingdom (Crown) of Aragon",
        "中世纪盛期", "Aragonese / Trastámara", "kingdom_federation", 1035, 1715,
        aliases="Corona de Aragón", display="阿拉贡王冠",
        geography="阿拉贡、加泰罗尼亚、巴伦西亚、马略卡、那不勒斯、西西里。",
        modern_admin="ESP|ES-AR|ES-CT|ES-VC|IT-ISOLE",
        capital="Saragossa",
        family="House of Aragon → Trastámara", group="Aragonese / Catalan",
        founder="Ramiro I",
        successor="Bourbon centralization after Nueva Planta 1707-1715",
        source_ids=src_esp, confidence=85,
    )
    b.add_capital("kingdom_aragon", "Saragossa", 1118, 1715, src_esp, 82)
    b.add_capital("kingdom_aragon", "Barcelona", 1137, 1410, src_esp, 80, note="Catalan secondary capital.")
    b.add_ruler("kingdom_aragon", "James I the Conqueror", "rex", 1213, 1276, source_ids=src_esp, confidence=88)
    b.add_ruler("kingdom_aragon", "Ferdinand II of Aragon", "rex", 1479, 1516, source_ids=src_esp, confidence=92)

    b.add_polity(
        "kingdom_portugal", "Kingdom of Portugal",
        "中世纪盛期", "Burgundian → Aviz → Braganza", "kingdom", 1139, 1910,
        aliases="Reino de Portugal", display="葡萄牙王国",
        geography="伊比利亚西部；加上海外殖民帝国（巴西、非洲、亚洲据点）。",
        modern_admin="PRT",
        capital="Lisbon",
        family="Burgundian → Aviz → Habsburg (1580-1640) → Braganza", group="Portuguese",
        founder="Afonso I (1139)",
        last_ruler="Manuel II (republic 1910)",
        successor="Portuguese First Republic",
        source_ids=src_esp, confidence=88,
    )
    b.add_capital("kingdom_portugal", "Lisbon", 1255, 1910, src_esp, 90)

    b.add_polity(
        "kingdom_poland", "Kingdom of Poland (Piast & Jagiellonian)",
        "中世纪盛期", "Piast → Jagiellonian", "kingdom", 1025, 1569,
        aliases="Regnum Poloniae", display="波兰王国（皮亚斯特-雅盖隆王朝）",
        geography="波兰核心，13-14 世纪扩张到立陶宛与乌克兰。",
        modern_admin="POL|UKR|BLR|LTU",
        capital="Krakow",
        family="Piast → Jagiellonian", group="Polish",
        founder="Bolesław I the Brave",
        last_ruler="Sigismund II Augustus",
        successor="Polish-Lithuanian Commonwealth (1569)",
        source_ids=src_pol, confidence=88,
    )
    b.add_capital("kingdom_poland", "Krakow", 1038, 1596, src_pol, 88)
    b.add_ruler("kingdom_poland", "Casimir III the Great", "rex", 1333, 1370, source_ids=src_pol, confidence=88)
    b.add_ruler("kingdom_poland", "Władysław II Jagiełło", "rex", 1386, 1434, source_ids=src_pol, confidence=88)

    b.add_polity(
        "lithuania_duchy", "Grand Duchy of Lithuania",
        "中世纪盛期", "Gediminids / Jagiellonian", "grand_duchy", 1236, 1569,
        aliases="Lietuvos Didžioji Kunigaikštystė", display="立陶宛大公国",
        geography="波罗的海到黑海；中世纪欧洲面积最大国家之一。",
        modern_admin="LTU|BLR|UKR|POL|RUS",
        capital="Vilnius",
        family="Gediminids → Jagiellonian", group="Lithuanian",
        founder="Mindaugas",
        successor="Polish-Lithuanian Commonwealth (1569)",
        source_ids=src_pol, confidence=82,
    )
    b.add_capital("lithuania_duchy", "Vilnius", 1323, 1569, src_pol, 85)

    b.add_polity(
        "kingdom_hungary", "Kingdom of Hungary",
        "中世纪盛期", "Árpád → Angevin → Jagiellonian → Habsburg", "kingdom", 1000, 1918,
        aliases="Regnum Hungariae", display="匈牙利王国",
        geography="喀尔巴阡盆地与跨喀尔巴阡 trans-Tisza、克罗地亚、特兰西瓦尼亚。",
        modern_admin="HUN|SVK|ROU|HRV|SRB|UKR|SVN",
        capital="Esztergom",
        family="Árpád → Angevin → multiple → Habsburg", group="Hungarian / Magyar",
        founder="Stephen I (Saint Stephen, 1000)",
        last_ruler="Charles IV / Karl I (1918)",
        successor="Hungarian Republic (1918)",
        source_ids=src_hun, confidence=88,
    )
    b.add_capital("kingdom_hungary", "Esztergom", 1000, 1242, src_hun, 78)
    b.add_capital("kingdom_hungary", "Budapest", 1361, 1918, src_hun, 85, note="Buda before 1873; Budapest formed by union of Buda+Pest+Óbuda.")
    b.add_ruler("kingdom_hungary", "Stephen I (Saint Stephen)", "rex", 1000, 1038, source_ids=src_hun, confidence=88)
    b.add_ruler("kingdom_hungary", "Matthias Corvinus", "rex", 1458, 1490, source_ids=src_hun, confidence=92)

    b.add_polity(
        "bohemia_kingdom", "Kingdom of Bohemia",
        "中世纪盛期", "Přemyslid → Luxembourg → Jagiellonian → Habsburg",
        "kingdom", 1198, 1918,
        aliases="Regnum Bohemiae", display="波西米亚王国",
        geography="今捷克核心；HRE 重要选侯国之一。",
        modern_admin="CZE|SVK|POL|DEU",
        capital="Prague",
        family="Přemyslid → Luxembourg → Jagiellonian → Habsburg", group="Czech",
        founder="Ottokar I",
        successor="Czechoslovakia 1918",
        source_ids=src_hre, confidence=88,
    )
    b.add_capital("bohemia_kingdom", "Prague", 1198, 1918, src_hre, 90)

    b.add_polity(
        "second_bulgarian", "Second Bulgarian Empire",
        "中世纪盛期", "Asen / Shishman", "empire", 1185, 1396,
        aliases="Tsardom of Bulgaria", display="第二保加利亚帝国",
        geography="保加利亚核心，复独立反抗拜占庭；1396 为奥斯曼所灭。",
        modern_admin="BGR|MKD|ROU|SRB",
        capital="",
        group="Bulgarian", successor="Ottoman conquest",
        source_ids=src_byz, confidence=82,
    )

    b.add_polity(
        "serbian_empire", "Serbian Empire (Nemanjić)",
        "中世纪盛期", "Nemanjić", "empire", 1346, 1371,
        aliases="Carstvo Srbsko", display="塞尔维亚帝国（涅马尼奇王朝）",
        geography="巴尔干西部；史蒂芬·杜尚短暂建立大帝国。",
        modern_admin="SRB|MNE|MKD|ALB|BIH|GRC",
        capital="Skopje",
        family="Nemanjić", group="Serbian",
        founder="Stefan Dušan",
        last_ruler="Stefan Uroš V",
        successor="Serbian despotates / Ottoman vassalage",
        source_ids=src_byz, confidence=82,
    )
    b.add_ruler("serbian_empire", "Stefan Dušan", "tsar", 1346, 1355, source_ids=src_byz, confidence=88)

    b.add_polity(
        "kalmar_union", "Kalmar Union",
        "中世纪晚期", "Pomeranian / Bavarian / Oldenburg",
        "personal_union", 1397, 1523,
        aliases="Unionen", display="卡尔马联盟",
        geography="丹麦、挪威、瑞典三国共主联盟。",
        modern_admin="DNK|NOR|SWE|ISL",
        capital="Copenhagen",
        family="House of Pomerania → Bavaria → Oldenburg", group="Scandinavian",
        founder="Margaret I (founder)",
        last_ruler="Christian II",
        successor="Dissolution 1523 (Sweden secedes)",
        source_ids=src_vik, confidence=85,
    )
    b.add_capital("kalmar_union", "Copenhagen", 1397, 1523, src_vik, 85)
    b.add_ruler("kalmar_union", "Margaret I of Denmark", "regina", 1387, 1412, source_ids=src_vik, confidence=92)

    b.add_polity(
        "kingdom_ireland_gaelic", "Gaelic Ireland",
        "中世纪盛期", "Various Gaelic kingdoms", "kingdoms_confederation", 800, 1542,
        aliases="Ireland (Gaelic)", display="盖尔爱尔兰",
        geography="爱尔兰岛；多王国（莱因斯特、芒斯特、康诺特、阿尔斯特、米斯）。",
        modern_admin="IRL|GB-NIR",
        group="Gaelic Irish", successor="Tudor conquest, Kingdom of Ireland 1542",
        source_ids=src_uk, confidence=75,
    )

    b.add_polity(
        "crusader_jerusalem", "Kingdom of Jerusalem",
        "中世纪盛期", "Crusader / Lusignan", "kingdom", 1099, 1291,
        aliases="Regnum Hierosolymitanum", display="耶路撒冷王国",
        geography="圣地（巴勒斯坦、黎巴嫩、约旦西部）。",
        modern_admin="ISR|JOR|LBN|SYR",
        capital="",
        family="House of Boulogne → Lusignan etc.", group="Frankish Crusader",
        founder="Godfrey of Bouillon (Defender) / Baldwin I (king)",
        last_ruler="Henry II of Cyprus (Acre fall 1291)",
        successor="Mamluk conquest",
        source_ids=src_cru, confidence=85,
    )
    b.add_ruler("crusader_jerusalem", "Baldwin I", "rex", 1100, 1118, source_ids=src_cru, confidence=85)
    b.add_ruler("crusader_jerusalem", "Saladin (Ayyubid opponent)", "sultan (opponent)", 1187, 1187, source_ids=src_cru, confidence=80, note="Captured Jerusalem 1187; listed for cross-reference, not as king of Jerusalem.")

    b.add_polity(
        "byzantine_late", "Late Byzantine Empire (Nicaea & restored)",
        "中世纪晚期", "Palaiologos", "empire", 1261, 1453,
        aliases="Palaeologan Byzantium", display="晚期拜占庭帝国（巴列奥略王朝）",
        geography="逐渐萎缩为君士坦丁堡及周边；最终仅剩首都。",
        modern_admin="TUR|GRC", capital="Constantinople",
        family="Palaiologos", group="Greek",
        founder="Michael VIII Palaiologos",
        last_ruler="Constantine XI (killed 1453)",
        successor="Ottoman conquest",
        source_ids=src_byz, confidence=92,
    )
    b.add_capital("byzantine_late", "Constantinople", 1261, 1453, src_byz, 92)
    b.add_ruler("byzantine_late", "Constantine XI Palaiologos", "basileus", 1449, 1453, source_ids=src_byz, confidence=92)

    b.add_polity(
        "early_ottoman", "Early Ottoman Beylik / Sultanate",
        "中世纪晚期", "Osman dynasty", "sultanate", 1299, 1453,
        aliases="Osmanlı Beyliği", display="早期奥斯曼贝伊国 / 苏丹国",
        geography="安纳托利亚西北部 → 巴尔干扩张 → 1453 攻占君士坦丁堡。",
        modern_admin="TUR|BGR|GRC|MKD|ALB|SRB|BIH|HRV|ROU|MNE",
        capital="Bursa",
        family="Osman dynasty", group="Turkish Muslim",
        founder="Osman I",
        successor="Ottoman Empire (post-1453)",
        source_ids=src_ott, confidence=88,
    )
    b.add_capital("early_ottoman", "Bursa", 1326, 1365, src_ott, 88)
    b.add_capital("early_ottoman", "Edirne", 1365, 1453, src_ott, 88)
    b.add_ruler("early_ottoman", "Osman I", "bey", 1299, 1326, source_ids=src_ott, confidence=78)
    b.add_ruler("early_ottoman", "Mehmed II the Conqueror", "sultan", 1444, 1481, source_ids=src_ott, confidence=92, note="Captured Constantinople 1453.")

    b.add_polity(
        "muscovy_grand", "Grand Duchy of Moscow",
        "中世纪晚期", "Daniilovichi Rurikid", "grand_duchy", 1283, 1547,
        aliases="Velikoye Knyazhestvo Moskovskoye", display="莫斯科大公国",
        geography="俄罗斯东北部；从蒙古汗国附庸成长为独立大国。",
        modern_admin="RUS|RU-MOW", capital="Moscow",
        family="Daniilovichi (Rurikid branch)", group="Russian East Slavic",
        founder="Daniel of Moscow",
        last_ruler="Ivan IV (crowned Tsar 1547)",
        successor="Tsardom of Russia",
        source_ids=src_rus, confidence=88,
    )
    b.add_capital("muscovy_grand", "Moscow", 1283, 1547, src_rus, 90)
    b.add_ruler("muscovy_grand", "Ivan III the Great", "grand prince", 1462, 1505, source_ids=src_rus, confidence=92, note="End of Mongol yoke 1480.")

    b.add_polity(
        "golden_horde", "Golden Horde (European context)",
        "中世纪晚期", "Jochid Mongol", "khanate", 1240, 1502,
        aliases="Ulus of Jochi", display="金帐汗国（欧洲视角）",
        geography="伏尔加流域到第聂伯河；统治俄罗斯诸公国约 240 年。",
        modern_admin="RUS|UKR|KAZ|MDA",
        capital="Sarai",
        family="Jochid Mongol dynasty", group="Mongol / Turkic",
        founder="Batu Khan",
        successor="Crimean / Kazan / Astrakhan / Sibir khanates",
        source_ids=src_rus, confidence=82,
    )
    b.add_capital("golden_horde", "Sarai", 1240, 1502, src_rus, 78)

    b.add_event(year=1054, title="East-West Schism",
                description="罗马教皇与君士坦丁堡牧首互相绝罚，基督教正式分裂。",
                significance="天主教-东正教千年分裂。",
                event_type="religious_schism",
                polity_keys=["hre_early", "byzantine_middle"],
                location="Rome",
                source_ids=["source_eur_0001"], confidence=92, importance=3)
    b.add_event(year=1066, title="Battle of Hastings",
                description="诺曼底公爵威廉击败哈罗德二世，征服英格兰。",
                significance="诺曼征服改变英格兰政治语言文化。",
                event_type="battle",
                polity_keys=["kingdom_england", "anglo_saxon_wessex"],
                people="William the Conqueror; Harold II", location="Hastings",
                source_ids=src_uk, confidence=95, importance=3)
    b.add_event(year=1095, title="Pope Urban II calls First Crusade",
                description="教皇乌尔班二世在克莱蒙公会议号召收复圣地。",
                significance="十字军运动起点。",
                event_type="religious_event",
                polity_keys=["papal_states_high"], people="Pope Urban II",
                source_ids=src_cru, confidence=92, importance=3)
    b.add_event(year=1099, title="Crusaders capture Jerusalem",
                description="第一次十字军攻陷耶路撒冷，建立耶路撒冷王国。",
                significance="拉丁王国在圣地建立。",
                event_type="city_capture",
                polity_keys=["crusader_jerusalem"], people="Godfrey of Bouillon",
                source_ids=src_cru, confidence=92, importance=3)
    b.add_event(year=1187, title="Battle of Hattin / Fall of Jerusalem",
                description="萨拉丁在哈丁角击溃十字军军，10 月攻陷耶路撒冷。",
                significance="第二次/第三次十字军起因。",
                event_type="battle",
                polity_keys=["crusader_jerusalem"], people="Saladin",
                source_ids=src_cru, confidence=90, importance=3)
    b.add_event(year=1204, title="Sack of Constantinople (Fourth Crusade)",
                description="第四次十字军被威尼斯说服攻陷君士坦丁堡，建立拉丁帝国。",
                significance="拜占庭遭受致命打击；东西方教会更难调和。",
                event_type="city_sack",
                polity_keys=["byzantine_middle", "venetian_republic"],
                people="Enrico Dandolo", location="Constantinople",
                source_ids=src_byz, confidence=92, importance=3)
    b.add_event(year=1215, title="Magna Carta signed",
                description="英格兰国王约翰被迫签署《大宪章》。",
                significance="英国宪政与权利保障早期文本。",
                event_type="treaty_constitutional",
                polity_keys=["kingdom_england"], people="John of England",
                location="London", source_ids=src_uk, confidence=95, importance=3)
    b.add_event(year=1241, title="Mongol invasion of Europe",
                description="拔都西征蒙古军大破匈牙利、波兰联军，进入中欧。",
                significance="蒙古震慑欧洲并奠基金帐汗国。",
                event_type="invasion",
                polity_keys=["kingdom_hungary", "kingdom_poland", "golden_horde"],
                people="Batu Khan; Subutai",
                source_ids=src_rus, confidence=88, importance=3)
    b.add_event(year=1291, title="Fall of Acre",
                description="马穆鲁克攻陷阿卡，十字军在圣地最后据点。",
                significance="拉丁基督教在圣地统治终结。",
                event_type="city_capture",
                polity_keys=["crusader_jerusalem"],
                source_ids=src_cru, confidence=92, importance=3)
    b.add_event(year=1337, title="Hundred Years' War begins",
                description="英王爱德华三世主张法兰西王位，英法长期战争开始。",
                significance="英法民族国家形成的关键战争。",
                event_type="war_outbreak",
                polity_keys=["kingdom_england", "kingdom_france"],
                people="Edward III; Philip VI",
                source_ids=src_fra, confidence=92, importance=3)
    b.add_event(year=1347, title="Black Death reaches Europe",
                description="鼠疫沿黑海贸易路线进入西西里、热那亚等港口。",
                significance="14 世纪欧洲人口锐减 1/3 至 1/2。",
                event_type="pandemic",
                polity_keys=["venetian_republic", "genoa_republic"],
                location="Genoa",
                source_ids=["source_eur_0001"], confidence=92, importance=3)
    b.add_event(year=1378, title="Western Schism begins",
                description="罗马与阿维尼翁同时选出教皇，天主教大分裂。",
                significance="天主教内部权威危机。",
                event_type="religious_schism",
                polity_keys=["papal_states_high"], location="Avignon",
                source_ids=src_ita, confidence=90, importance=2)
    b.add_event(year=1415, title="Battle of Agincourt",
                description="亨利五世以少胜多击败法军。",
                significance="百年战争英方代表性胜利。",
                event_type="battle",
                polity_keys=["kingdom_england", "kingdom_france"],
                people="Henry V", location="Agincourt",
                source_ids=src_uk, confidence=92, importance=3)
    b.add_event(year=1453, title="Fall of Constantinople",
                description="奥斯曼苏丹穆罕默德二世攻陷君士坦丁堡，拜占庭灭亡。",
                significance="中世纪终结的标志性事件。",
                event_type="city_capture",
                polity_keys=["byzantine_late", "early_ottoman"],
                people="Mehmed II; Constantine XI",
                location="Constantinople",
                source_ids=src_byz, confidence=95, importance=3)

    b.add_context(start=1000, end=1453, title="中世纪盛期与晚期",
                  description="封建欧洲、十字军运动、商业革命、瘟疫、英法百年战争，至君士坦丁堡陷落收束。",
                  source_ids=src_hre, confidence=85)

    b.add_strategic("Avignon", "religious_seat", start=1309, end=1377,
                    modern="Avignon", admin="FRA|FR-PAC",
                    summary="阿维尼翁教廷期间教皇驻地。",
                    significance="罗马天主教权威外移的标志地。",
                    source_ids=src_ita, related_polity_keys=["papal_states_high"], confidence=88)
    b.add_strategic("Krakow", "capital", start=1038, end=1596,
                    modern="Kraków", admin="POL|PL-MA",
                    summary="波兰皮亚斯特与雅盖隆王朝首都。",
                    significance="瓦维尔城堡所在。",
                    source_ids=src_pol, related_polity_keys=["kingdom_poland"], confidence=88)
    b.add_strategic("Prague", "capital", start=1198, end=1918,
                    modern="Prague", admin="CZE",
                    summary="波西米亚王国首都，HRE 重要选侯国都。",
                    significance="查理四世建为帝国第二都。",
                    source_ids=src_hre, related_polity_keys=["bohemia_kingdom", "hre_late"], confidence=88)


def _register_early_modern(b: Builder) -> None:
    """Early Modern (1453-1789). Habsburg Spain & Austria, Ottoman in Balkans,
    HRE Reformation states, England → Britain, Polish-Lithuanian Commonwealth,
    Tsardom of Russia / Romanov, Dutch Republic, Swedish empire phase."""
    src_esp = ["source_eur_0007"]
    src_hre = ["source_eur_0004"]
    src_hbg = ["source_eur_0033"]
    src_ott = ["source_eur_0012"]
    src_pol = ["source_eur_0013"]
    src_rus = ["source_eur_0010"]
    src_uk = ["source_eur_0006"]
    src_fra = ["source_eur_0005"]
    src_swe = ["source_eur_0016"]
    src_ref = ["source_eur_0027"]
    src_30w = ["source_eur_0028"]

    b.add_polity(
        "spanish_habsburg", "Spanish Habsburg Monarchy",
        "近代早期", "Habsburg", "composite_monarchy", 1516, 1700,
        aliases="Monarquía Hispánica", display="西班牙哈布斯堡王朝",
        geography="伊比利亚、那不勒斯-西西里-米兰-荷兰、美洲与亚洲殖民地。",
        modern_admin="ESP|PRT|ITA|BEL|NLD|LUX",
        capital="Madrid",
        family="Habsburg (Spanish branch)", group="Castilian-Aragonese",
        founder="Charles I (Holy Roman Emperor Charles V)",
        last_ruler="Charles II (childless death 1700)",
        successor="Spanish Bourbon dynasty",
        source_ids=src_hbg, confidence=92,
    )
    b.add_capital("spanish_habsburg", "Madrid", 1561, 1700, src_hbg, 92)
    b.add_ruler("spanish_habsburg", "Charles I (Emperor Charles V)", "rey", 1516, 1556, source_ids=src_hbg, confidence=95)
    b.add_ruler("spanish_habsburg", "Philip II", "rey", 1556, 1598, source_ids=src_hbg, confidence=95)
    b.add_ruler("spanish_habsburg", "Philip IV", "rey", 1621, 1665, source_ids=src_hbg, confidence=92)
    b.add_ruler("spanish_habsburg", "Charles II", "rey", 1665, 1700, source_ids=src_hbg, confidence=90)

    b.add_polity(
        "spanish_bourbon", "Spanish Bourbon Monarchy (early)",
        "近代早期", "Bourbon", "monarchy", 1700, 1808,
        aliases="Borbones", display="西班牙波旁王朝（早期）",
        geography="西班牙本土与拉美殖民地；意大利诸领最终独立。",
        modern_admin="ESP|PRT",
        capital="Madrid",
        family="House of Bourbon", group="Castilian",
        founder="Philip V (grandson of Louis XIV)",
        successor="Napoleonic occupation",
        source_ids=src_esp, confidence=90,
    )
    b.add_capital("spanish_bourbon", "Madrid", 1700, 1808, src_esp, 92)
    b.add_ruler("spanish_bourbon", "Philip V", "rey", 1700, 1746, source_ids=src_esp, confidence=92)
    b.add_ruler("spanish_bourbon", "Charles III", "rey", 1759, 1788, source_ids=src_esp, confidence=92)

    b.add_polity(
        "austrian_habsburg", "Austrian Habsburg Monarchy",
        "近代早期", "Habsburg / Habsburg-Lorraine", "composite_monarchy",
        1526, 1804,
        aliases="Habsburg Hereditary Lands", display="奥地利哈布斯堡君主国",
        geography="奥地利、波西米亚、匈牙利、克罗地亚、低地南部（部分）、意大利北部（部分）。",
        modern_admin="AUT|CZE|HUN|SVK|SVN|HRV|BEL|NLD|ITA|ROU|UKR|POL",
        capital="Vienna",
        family="Habsburg → Habsburg-Lorraine", group="Austrian / German",
        founder="Ferdinand I",
        last_ruler="Francis II (became Emperor of Austria 1804)",
        successor="Austrian Empire",
        source_ids=src_hbg, confidence=92,
    )
    b.add_capital("austrian_habsburg", "Vienna", 1526, 1804, src_hbg, 92)
    b.add_ruler("austrian_habsburg", "Maria Theresa", "regina apostolica", 1740, 1780, source_ids=src_hbg, confidence=95)
    b.add_ruler("austrian_habsburg", "Joseph II", "imperator", 1765, 1790, source_ids=src_hbg, confidence=92)

    b.add_polity(
        "ottoman_empire", "Ottoman Empire (Classical/Imperial)",
        "近代早期", "Osman dynasty", "empire", 1453, 1922,
        aliases="Osmanlı Devleti", display="奥斯曼帝国（古典-帝国期）",
        geography="安纳托利亚 + 巴尔干 + 黎凡特 + 北非 + 美索不达米亚。",
        modern_admin="TUR|GRC|BGR|MKD|ALB|SRB|MNE|BIH|HRV|HUN|ROU|MDA|UKR|CYP|SYR|LBN|ISR|JOR|EGY|LBY|TUN|DZA|IRQ",
        capital="Constantinople",
        family="Osman dynasty", group="Turkish Muslim",
        founder="Mehmed II (post-1453 imperial transformation)",
        last_ruler="Mehmed VI (deposed 1922)",
        successor="Republic of Turkey",
        source_ids=src_ott, confidence=92,
    )
    b.add_capital("ottoman_empire", "Constantinople", 1453, 1922, src_ott, 92)
    b.add_ruler("ottoman_empire", "Selim I the Grim", "sultan", 1512, 1520, source_ids=src_ott, confidence=92)
    b.add_ruler("ottoman_empire", "Suleiman the Magnificent", "sultan", 1520, 1566, source_ids=src_ott, confidence=95)
    b.add_ruler("ottoman_empire", "Mehmed IV", "sultan", 1648, 1687, source_ids=src_ott, confidence=88)

    b.add_polity(
        "england_tudor", "Kingdom of England (Tudor / early Stuart)",
        "近代早期", "Tudor → Stuart", "kingdom", 1485, 1649,
        aliases="Regnum Angliae (Tudor era)", display="英格兰都铎-早期斯图亚特王朝",
        geography="英格兰、威尔士（1543 起入英格兰行政体系）、爱尔兰（名义）。",
        modern_admin="GBR|GB-ENG|GB-WLS|IRL",
        capital="London",
        family="Tudor → Stuart", group="English",
        founder="Henry VII",
        last_ruler="Charles I (executed 1649)",
        successor="Commonwealth of England",
        source_ids=src_uk, confidence=92,
    )
    b.add_capital("england_tudor", "London", 1485, 1649, src_uk, 92)
    b.add_ruler("england_tudor", "Edward VI", "rex", 1547, 1553, source_ids=src_uk, confidence=88)
    b.add_ruler("england_tudor", "Mary I", "regina", 1553, 1558, source_ids=src_uk, confidence=88)
    b.add_ruler("england_tudor", "James I (VI of Scotland)", "rex", 1603, 1625, source_ids=src_uk, confidence=92)
    b.add_ruler("england_tudor", "Charles I", "rex", 1625, 1649, source_ids=src_uk, confidence=92)

    b.add_polity(
        "england_commonwealth", "Commonwealth of England / Protectorate",
        "近代早期", "Cromwellian", "republic", 1649, 1660,
        aliases="Interregnum|Protectorate", display="英格兰联邦与护国公",
        geography="英格兰 + 爱尔兰 + 苏格兰 + 殖民地。",
        modern_admin="GBR|GB-ENG|GB-SCT|GB-WLS|IRL",
        capital="London",
        family="Cromwell family", group="English Puritan",
        founder="Long Parliament / Oliver Cromwell",
        last_ruler="Richard Cromwell",
        successor="Restoration of Charles II",
        source_ids=src_uk, confidence=92,
    )
    b.add_capital("england_commonwealth", "London", 1649, 1660, src_uk, 92)
    b.add_ruler("england_commonwealth", "Oliver Cromwell", "Lord Protector", 1653, 1658, source_ids=src_uk, confidence=92)

    b.add_polity(
        "england_restoration", "Kingdom of England (Restoration & Glorious Revolution)",
        "近代早期", "Stuart → House of Orange", "kingdom", 1660, 1707,
        aliases="Restoration England", display="英格兰王朝复辟与光荣革命",
        geography="英格兰、苏格兰（共主）、爱尔兰、殖民地。",
        modern_admin="GBR|GB-ENG|GB-SCT|GB-WLS|IRL",
        capital="London",
        family="Stuart → Orange-Nassau", group="English",
        founder="Charles II (Restoration 1660)",
        last_ruler="Anne (Acts of Union 1707)",
        successor="Kingdom of Great Britain",
        source_ids=src_uk, confidence=92,
    )
    b.add_ruler("england_restoration", "Charles II", "rex", 1660, 1685, source_ids=src_uk, confidence=92)
    b.add_ruler("england_restoration", "James II", "rex", 1685, 1688, source_ids=src_uk, confidence=92)
    b.add_ruler("england_restoration", "William III & Mary II", "rex et regina", 1689, 1694, source_ids=src_uk, confidence=92)
    b.add_ruler("england_restoration", "Anne", "regina", 1702, 1707, source_ids=src_uk, confidence=92)

    b.add_polity(
        "great_britain", "Kingdom of Great Britain",
        "近代早期", "Stuart → Hanover", "kingdom", 1707, 1801,
        aliases="GB", display="大不列颠王国",
        geography="英格兰 + 苏格兰 + 威尔士；殖民帝国扩张至北美、印度、加勒比。",
        modern_admin="GBR|GB-ENG|GB-SCT|GB-WLS|IRL",
        capital="London",
        family="Stuart → Hanover", group="British",
        founder="Anne (Acts of Union 1707)",
        last_ruler="George III (Acts of Union 1801)",
        successor="United Kingdom of Great Britain and Ireland",
        source_ids=src_uk, confidence=92,
    )
    b.add_capital("great_britain", "London", 1707, 1801, src_uk, 92)
    b.add_ruler("great_britain", "George I", "rex", 1714, 1727, source_ids=src_uk, confidence=92)
    b.add_ruler("great_britain", "George II", "rex", 1727, 1760, source_ids=src_uk, confidence=92)
    b.add_ruler("great_britain", "George III", "rex", 1760, 1801, source_ids=src_uk, confidence=92, note="Continues into United Kingdom.")

    b.add_polity(
        "dutch_republic", "Dutch Republic (United Provinces)",
        "近代早期", "Stadtholder / Republic", "republic", 1581, 1795,
        aliases="Republiek der Zeven Verenigde Nederlanden",
        display="荷兰共和国（联省共和国）",
        geography="低地北部七省；海上贸易、殖民帝国（VOC, WIC）。",
        modern_admin="NLD",
        capital="The Hague",
        family="House of Orange-Nassau (stadtholders)", group="Dutch",
        founder="William the Silent",
        last_ruler="William V (Stadtholder, deposed 1795)",
        successor="Batavian Republic (French satellite)",
        source_ids=["source_eur_0001"], confidence=90,
    )
    b.add_capital("dutch_republic", "The Hague", 1588, 1795, ["source_eur_0001"], 90)
    b.add_ruler("dutch_republic", "William the Silent (Stadtholder)", "stadhouder", 1581, 1584, source_ids=["source_eur_0001"], confidence=92)
    b.add_ruler("dutch_republic", "William III (Stadtholder, then King of England)", "stadhouder", 1672, 1702, source_ids=["source_eur_0001"], confidence=92)

    b.add_polity(
        "polish_lithuanian", "Polish-Lithuanian Commonwealth",
        "近代早期", "Vasa / Wettin / Poniatowski (elective)",
        "composite_republic", 1569, 1795,
        aliases="Rzeczpospolita Obojga Narodów", display="波兰-立陶宛联邦",
        geography="波兰、立陶宛、白俄罗斯、乌克兰大部；选王制贵族共和。",
        modern_admin="POL|LTU|BLR|UKR|LVA",
        capital="Warsaw",
        family="Multiple elected dynasties", group="Polish-Lithuanian",
        founder="Sigismund II Augustus (Union of Lublin)",
        last_ruler="Stanisław August Poniatowski (final partition 1795)",
        successor="Three Partitions → Prussia, Austria, Russia",
        source_ids=src_pol, confidence=92,
    )
    b.add_capital("polish_lithuanian", "Krakow", 1569, 1596, src_pol, 85)
    b.add_capital("polish_lithuanian", "Warsaw", 1596, 1795, src_pol, 90)
    b.add_ruler("polish_lithuanian", "Stephen Báthory", "rex", 1576, 1586, source_ids=src_pol, confidence=88)
    b.add_ruler("polish_lithuanian", "Jan III Sobieski", "rex", 1674, 1696, source_ids=src_pol, confidence=92, note="Lifted Ottoman siege of Vienna 1683.")
    b.add_ruler("polish_lithuanian", "Stanisław August Poniatowski", "rex", 1764, 1795, source_ids=src_pol, confidence=90)

    b.add_polity(
        "russia_tsardom", "Tsardom of Russia",
        "近代早期", "Rurikid → Romanov", "tsardom", 1547, 1721,
        aliases="Russkoye Tsarstvo", display="俄罗斯沙皇国",
        geography="莫斯科基础上向东、东北、南扩张（吞并喀山、阿斯特拉罕、西伯利亚开始）。",
        modern_admin="RUS|UKR|BLR",
        capital="Moscow",
        family="Rurikid → Romanov", group="Russian",
        founder="Ivan IV (the Terrible, crowned Tsar 1547)",
        last_ruler="Peter I (transformed into Empire 1721)",
        successor="Russian Empire",
        source_ids=src_rus, confidence=92,
    )
    b.add_capital("russia_tsardom", "Moscow", 1547, 1712, src_rus, 92)
    b.add_capital("russia_tsardom", "Saint Petersburg", 1712, 1721, src_rus, 92, note="Founded 1703, capital from 1712.")
    b.add_ruler("russia_tsardom", "Ivan IV the Terrible", "tsar", 1547, 1584, source_ids=src_rus, confidence=92)
    b.add_ruler("russia_tsardom", "Michael Romanov", "tsar", 1613, 1645, source_ids=src_rus, confidence=92)
    b.add_ruler("russia_tsardom", "Peter I the Great", "tsar", 1682, 1721, source_ids=src_rus, confidence=95)

    b.add_polity(
        "russian_empire_early", "Russian Empire (Petrine-Catherinian)",
        "近代早期", "Romanov", "empire", 1721, 1801,
        aliases="Rossiyskaya Imperiya (early)", display="俄罗斯帝国（彼得-叶卡捷琳娜时代）",
        geography="俄罗斯扩张到波罗的海、黑海；卷入波兰瓜分。",
        modern_admin="RUS|UKR|BLR|FIN|EST|LVA|LTU|POL|MDA|GEO",
        capital="Saint Petersburg",
        family="Romanov → Holstein-Gottorp-Romanov", group="Russian",
        founder="Peter I (became Emperor 1721)",
        last_ruler="Paul I (assassinated 1801)",
        successor="Russian Empire (continued under Alexander I)",
        source_ids=src_rus, confidence=92,
    )
    b.add_capital("russian_empire_early", "Saint Petersburg", 1721, 1801, src_rus, 92)
    b.add_ruler("russian_empire_early", "Peter I (as Emperor)", "imperator", 1721, 1725, source_ids=src_rus, confidence=95)
    b.add_ruler("russian_empire_early", "Elizabeth", "imperatritsa", 1741, 1762, source_ids=src_rus, confidence=92)
    b.add_ruler("russian_empire_early", "Catherine II the Great", "imperatritsa", 1762, 1796, source_ids=src_rus, confidence=95)

    b.add_polity(
        "sweden_empire", "Swedish Empire (Stormaktstiden)",
        "近代早期", "Vasa / Palatinate-Zweibrücken / Holstein-Gottorp",
        "kingdom", 1611, 1721,
        aliases="Svenska stormaktstiden", display="瑞典帝国（强权时代）",
        geography="瑞典 + 芬兰 + 波罗的海诸省 + 波美拉尼亚部分。",
        modern_admin="SWE|FIN|EST|LVA|RUS|DEU|POL",
        capital="Stockholm",
        family="Vasa → Palatinate-Zweibrücken → Holstein-Gottorp", group="Swedish",
        founder="Gustavus Adolphus",
        last_ruler="Charles XII (killed 1718, Great Northern War end 1721)",
        successor="Age of Liberty Sweden",
        source_ids=src_swe, confidence=88,
    )
    b.add_capital("sweden_empire", "Stockholm", 1611, 1721, src_swe, 90)
    b.add_ruler("sweden_empire", "Gustavus Adolphus", "rex", 1611, 1632, source_ids=src_swe, confidence=92)
    b.add_ruler("sweden_empire", "Charles XII", "rex", 1697, 1718, source_ids=src_swe, confidence=92)

    b.add_polity(
        "denmark_norway", "Denmark-Norway",
        "近代早期", "Oldenburg", "personal_union_kingdom", 1523, 1814,
        aliases="Dannmark og Norge", display="丹麦-挪威",
        geography="丹麦本土、挪威、冰岛、法罗、北大西洋；曾控制石勒苏益格-荷尔斯泰因。",
        modern_admin="DNK|NOR|ISL|DEU",
        capital="Copenhagen",
        family="House of Oldenburg", group="Danish-Norwegian",
        founder="Frederick I",
        last_ruler="Frederick VI (Treaty of Kiel 1814 cedes Norway to Sweden)",
        successor="Denmark | Sweden-Norway",
        source_ids=src_swe, confidence=88,
    )
    b.add_capital("denmark_norway", "Copenhagen", 1523, 1814, src_swe, 90)

    b.add_polity(
        "swiss_confederation", "Old Swiss Confederacy",
        "近代早期", "Cantonal federation", "confederation", 1291, 1798,
        aliases="Eidgenossenschaft", display="老瑞士同盟",
        geography="阿尔卑斯地区多个州；HRE 内自治到 1648 正式独立。",
        modern_admin="CHE|FRA|ITA|LIE",
        capital="",
        group="Swiss", successor="Helvetic Republic (French satellite)",
        source_ids=["source_eur_0001"], confidence=85,
    )

    b.add_polity(
        "prussia_brandenburg", "Brandenburg-Prussia",
        "近代早期", "Hohenzollern", "duchy_kingdom", 1525, 1701,
        aliases="Mark Brandenburg + Herzogtum Preußen", display="勃兰登堡-普鲁士",
        geography="勃兰登堡（HRE 边境侯国）+ 普鲁士公国（波兰附庸→主权）。",
        modern_admin="DEU|POL|LTU|RUS",
        capital="Berlin",
        family="Hohenzollern", group="German",
        founder="Albert (Duke of Prussia)",
        last_ruler="Frederick III/I (declared King 1701)",
        successor="Kingdom of Prussia",
        source_ids=src_hre, confidence=85,
    )
    b.add_capital("prussia_brandenburg", "Berlin", 1525, 1701, src_hre, 88)

    b.add_polity(
        "kingdom_prussia", "Kingdom of Prussia",
        "近代早期", "Hohenzollern", "kingdom", 1701, 1918,
        aliases="Königreich Preußen", display="普鲁士王国",
        geography="勃兰登堡 + 普鲁士 + 西里西亚 + 莱茵兰 + 萨克森部分。",
        modern_admin="DEU|POL|LTU|RUS|BEL|FRA|CZE",
        capital="Berlin",
        family="Hohenzollern", group="German",
        founder="Frederick I (1701)",
        last_ruler="Wilhelm II (abdicated 1918)",
        successor="Free State of Prussia (Weimar)",
        source_ids=src_hre, confidence=92,
    )
    b.add_capital("kingdom_prussia", "Berlin", 1701, 1918, src_hre, 92)
    b.add_ruler("kingdom_prussia", "Frederick II the Great", "rex", 1740, 1786, source_ids=src_hre, confidence=95)
    b.add_ruler("kingdom_prussia", "Frederick William III", "rex", 1797, 1840, source_ids=src_hre, confidence=88)
    b.add_ruler("kingdom_prussia", "Wilhelm I", "rex", 1861, 1888, source_ids=src_hre, confidence=92, note="Became German Emperor 1871.")
    b.add_ruler("kingdom_prussia", "Wilhelm II", "rex", 1888, 1918, source_ids=src_hre, confidence=92)

    b.add_polity(
        "tuscany_grand_duchy", "Grand Duchy of Tuscany",
        "近代早期", "Medici → Habsburg-Lorraine", "grand_duchy", 1569, 1860,
        aliases="Granducato di Toscana", display="托斯卡纳大公国",
        geography="托斯卡纳；以佛罗伦萨为中心。",
        modern_admin="ITA|IT-CENTRO",
        capital="Florence",
        family="Medici → Habsburg-Lorraine", group="Tuscan Italian",
        founder="Cosimo I de' Medici",
        successor="Kingdom of Italy",
        source_ids=["source_eur_0009"], confidence=88,
    )
    b.add_capital("tuscany_grand_duchy", "Florence", 1569, 1860, ["source_eur_0009"], 88)

    b.add_polity(
        "two_sicilies", "Kingdom of the Two Sicilies",
        "近代早期", "Bourbon-Naples", "kingdom", 1816, 1861,
        aliases="Regno delle Due Sicilie", display="两西西里王国",
        geography="意大利南部 + 西西里；维也纳会议后由那不勒斯王国+西西里王国合并而来。",
        modern_admin="ITA|IT-SUD|IT-ISOLE",
        capital="Naples",
        family="Bourbon (Naples branch)", group="Southern Italian",
        founder="Ferdinand I",
        last_ruler="Francis II (deposed 1861)",
        successor="Kingdom of Italy",
        source_ids=["source_eur_0009"], confidence=88,
    )
    b.add_capital("two_sicilies", "Naples", 1816, 1861, ["source_eur_0009"], 88)

    b.add_polity(
        "savoy_kingdom", "Duchy / Kingdom of Sardinia-Piedmont (Savoy)",
        "近代早期", "House of Savoy", "kingdom", 1416, 1861,
        aliases="Regno di Sardegna|Savoia", display="萨伏依-皮埃蒙特-撒丁王国",
        geography="皮埃蒙特、萨伏依、萨丁岛；意大利统一核心。",
        modern_admin="ITA|FRA|CHE",
        capital="Turin",
        family="House of Savoy", group="Piedmontese Italian",
        founder="Amadeus VIII (Duke)",
        last_ruler="Victor Emmanuel II (became King of Italy 1861)",
        successor="Kingdom of Italy",
        source_ids=["source_eur_0030"], confidence=88,
    )

    b.add_event(year=1492, title="Fall of Granada & Columbus's voyage",
                description="阿拉贡-卡斯蒂利亚联军攻克格拉纳达，结束伊比利亚 reconquista；同年哥伦布抵达美洲。",
                significance="基督教伊比利亚统一与大航海时代开端。",
                event_type="reconquest_and_voyage",
                polity_keys=["kingdom_castile", "kingdom_aragon"],
                people="Ferdinand II; Isabella I; Christopher Columbus",
                location="Granada",
                source_ids=src_esp, confidence=92, importance=3)
    b.add_event(year=1517, title="Luther's 95 Theses",
                description="马丁·路德在维滕贝格发表《九十五条论纲》，引发宗教改革。",
                significance="宗教改革开始。",
                event_type="religious_event",
                polity_keys=["hre_early"], people="Martin Luther",
                source_ids=src_ref, confidence=92, importance=3)
    b.add_event(year=1529, title="Siege of Vienna by Ottoman forces",
                description="奥斯曼苏丹苏莱曼一世围攻维也纳未果。",
                significance="奥斯曼扩张达到中欧地理极限。",
                event_type="siege",
                polity_keys=["ottoman_empire", "austrian_habsburg"],
                people="Suleiman the Magnificent", location="Vienna",
                source_ids=src_ott, confidence=92, importance=3)
    b.add_event(year=1571, title="Battle of Lepanto",
                description="神圣同盟舰队在希腊勒班陀击败奥斯曼舰队。",
                significance="结束奥斯曼地中海海上不可挑战的迷思。",
                event_type="naval_battle",
                polity_keys=["spanish_habsburg", "venetian_republic", "papal_states_high", "ottoman_empire"],
                location="Lepanto",
                source_ids=["source_eur_0009"], confidence=92, importance=3)
    b.add_event(year=1588, title="Spanish Armada defeated",
                description="伊丽莎白一世英军舰队击败西班牙无敌舰队入侵英格兰图谋。",
                significance="海上霸权天平向英格兰倾斜。",
                event_type="naval_battle",
                polity_keys=["england_tudor", "spanish_habsburg"],
                people="Philip II; Elizabeth I",
                source_ids=src_uk, confidence=92, importance=3)
    b.add_event(year=1618, title="Defenestration of Prague — Thirty Years' War begins",
                description="布拉格抛窗事件引爆三十年战争。",
                significance="近代早期欧洲最具毁灭性战争之一。",
                event_type="war_outbreak",
                polity_keys=["bohemia_kingdom", "austrian_habsburg"],
                location="Prague",
                source_ids=src_30w, confidence=92, importance=3)
    b.add_event(year=1648, title="Peace of Westphalia",
                description="威斯特伐利亚和约结束三十年战争，确立主权国家体系。",
                significance="近代国际体系基石。",
                event_type="treaty",
                polity_keys=["austrian_habsburg", "kingdom_france", "sweden_empire", "spanish_habsburg", "dutch_republic"],
                source_ids=src_30w, confidence=95, importance=3)
    b.add_event(year=1683, title="Second Siege of Vienna",
                description="约翰三世·索别斯基率波兰-奥地利联军击退奥斯曼围攻。",
                significance="奥斯曼帝国扩张极限的转折点。",
                event_type="siege",
                polity_keys=["ottoman_empire", "polish_lithuanian", "austrian_habsburg"],
                people="Jan III Sobieski; Kara Mustafa Pasha",
                location="Vienna-1683",
                source_ids=src_ott, confidence=92, importance=3)
    b.add_event(year=1707, title="Acts of Union — Kingdom of Great Britain",
                description="英格兰王国与苏格兰王国合并为大不列颠王国。",
                significance="不列颠民族国家成形。",
                event_type="political_union",
                polity_keys=["england_restoration", "kingdom_scotland", "great_britain"],
                people="Anne",
                source_ids=src_uk, confidence=95, importance=3)
    b.add_event(year=1721, title="Peter the Great becomes Emperor of All Russia",
                description="北方大战结束，俄罗斯沙皇国正式升格为帝国。",
                significance="俄罗斯进入大国行列。",
                event_type="constitutional_transition",
                polity_keys=["russia_tsardom", "russian_empire_early"],
                people="Peter I the Great", location="Saint Petersburg",
                source_ids=src_rus, confidence=92, importance=3)
    b.add_event(year=1763, title="Treaty of Paris — end of Seven Years' War",
                description="七年战争结束，英国获得加拿大、印度大部，法国损失殖民地。",
                significance="英国成为全球最大殖民帝国。",
                event_type="treaty",
                polity_keys=["great_britain", "kingdom_france", "kingdom_prussia"],
                source_ids=src_uk, confidence=92, importance=3)
    b.add_event(year=1772, title="First Partition of Poland",
                description="俄罗斯、普鲁士、奥地利第一次瓜分波兰。",
                significance="波兰-立陶宛联邦衰亡过程的第一阶段。",
                event_type="territorial_partition",
                polity_keys=["polish_lithuanian", "russian_empire_early", "austrian_habsburg", "kingdom_prussia"],
                source_ids=src_pol, confidence=92, importance=3)

    b.add_context(start=1453, end=1789, title="近代早期",
                  description="宗教改革、大航海、专制主义国家形成、奥斯曼-哈布斯堡对抗、英国 / 法国 / 普鲁士 / 俄罗斯崛起。",
                  source_ids=src_hbg, confidence=88)

    b.add_strategic("Madrid", "capital", start=1561, end=2026,
                    modern="Madrid", admin="ESP|ES-MD",
                    summary="西班牙首都。",
                    significance="哈布斯堡-波旁西班牙政治中心。",
                    source_ids=src_esp, related_polity_keys=["spanish_habsburg", "spanish_bourbon"], confidence=92)
    b.add_strategic("Vienna", "capital", start=1438, end=2026,
                    modern="Vienna", admin="AUT|AT-9",
                    summary="哈布斯堡君主国与神圣罗马帝国晚期首都。",
                    significance="中欧政治中心，多瑙河沿岸枢纽。",
                    source_ids=src_hbg, related_polity_keys=["austrian_habsburg", "hre_late"], confidence=92)
    b.add_strategic("Berlin", "capital", start=1701, end=2026,
                    modern="Berlin", admin="DEU|DE-BE",
                    summary="普鲁士与德意志统一帝国首都。",
                    significance="德意志近现代政治中心。",
                    source_ids=src_hre, related_polity_keys=["prussia_brandenburg", "kingdom_prussia"], confidence=92)
    b.add_strategic("Saint Petersburg", "capital", start=1712, end=1918,
                    modern="Saint Petersburg", admin="RUS|RU-SPE",
                    summary="彼得大帝建立的俄罗斯帝国首都。",
                    significance="俄罗斯朝西转向的标志。",
                    source_ids=src_rus, related_polity_keys=["russian_empire_early"], confidence=92)
    b.add_strategic("Warsaw", "capital", start=1596, end=2026,
                    modern="Warsaw", admin="POL|PL-MZ",
                    summary="波兰-立陶宛联邦首都。",
                    significance="近代波兰政治中心。",
                    source_ids=src_pol, related_polity_keys=["polish_lithuanian"], confidence=88)


def _register_long_19th(b: Builder) -> None:
    """Long 19th century (1789-1914). French Revolution, Napoleon, Italian /
    German unifications, Austro-Hungarian Ausgleich, late Ottoman, declining
    empires, new Balkan states."""
    src_fra = ["source_eur_0005"]
    src_uk = ["source_eur_0006"]
    src_hre = ["source_eur_0004"]
    src_hbg = ["source_eur_0033"]
    src_rus = ["source_eur_0010"]
    src_pol = ["source_eur_0013"]
    src_ott = ["source_eur_0012"]
    src_ita = ["source_eur_0030"]
    src_nap = ["source_eur_0018"]
    src_rev = ["source_eur_0029"]

    b.add_polity(
        "french_revolution", "French First Republic",
        "长十九世纪", "Revolutionary government", "republic", 1792, 1804,
        aliases="République française", display="法兰西第一共和国",
        geography="法兰西本土 + 革命扩张到低地、莱茵、北意大利。",
        modern_admin="FRA|BEL|NLD|LUX|DEU|CHE|ITA",
        capital="Paris",
        family="National Convention → Directory → Consulate", group="French",
        founder="National Convention (1792)",
        last_ruler="Napoleon Bonaparte (became Emperor 1804)",
        successor="First French Empire",
        source_ids=src_rev, confidence=92,
    )
    b.add_capital("french_revolution", "Paris", 1792, 1804, src_rev, 92)
    b.add_ruler("french_revolution", "Maximilien Robespierre", "leader (Committee of Public Safety)", 1793, 1794, source_ids=src_rev, confidence=92)
    b.add_ruler("french_revolution", "Napoleon Bonaparte (First Consul)", "premier consul", 1799, 1804, source_ids=src_nap, confidence=95)

    b.add_polity(
        "first_french_empire", "First French Empire",
        "长十九世纪", "Bonaparte", "empire", 1804, 1814,
        aliases="Premier Empire français", display="法兰西第一帝国",
        geography="法兰西核心 + 莱茵联邦 + 意大利 + 伊比利亚部分 + 1812 入侵俄罗斯。",
        modern_admin="FRA|BEL|NLD|LUX|DEU|CHE|ITA|ESP|HRV|SVN",
        capital="Paris",
        family="Bonaparte", group="French",
        founder="Napoleon I",
        last_ruler="Napoleon II (briefly, 1815)",
        successor="Bourbon Restoration",
        source_ids=src_nap, confidence=92,
    )
    b.add_capital("first_french_empire", "Paris", 1804, 1814, src_nap, 92)
    b.add_ruler("first_french_empire", "Napoleon I", "empereur", 1804, 1814, source_ids=src_nap, confidence=95)

    b.add_polity(
        "bourbon_restoration", "Bourbon Restoration",
        "长十九世纪", "Bourbon", "constitutional_monarchy", 1814, 1830,
        aliases="Restauration", display="波旁复辟",
        geography="法兰西本土；维也纳会议恢复疆界。",
        modern_admin="FRA",
        capital="Paris",
        family="Bourbon", group="French",
        founder="Louis XVIII",
        last_ruler="Charles X (deposed 1830)",
        successor="July Monarchy",
        source_ids=src_fra, confidence=92,
    )
    b.add_ruler("bourbon_restoration", "Louis XVIII", "roi", 1814, 1824, source_ids=src_fra, confidence=92)
    b.add_ruler("bourbon_restoration", "Charles X", "roi", 1824, 1830, source_ids=src_fra, confidence=88)

    b.add_polity(
        "july_monarchy", "July Monarchy",
        "长十九世纪", "Orléans", "constitutional_monarchy", 1830, 1848,
        aliases="Monarchie de Juillet", display="七月王朝",
        geography="法兰西本土；阿尔及利亚殖民开始。",
        modern_admin="FRA|DZA",
        capital="Paris",
        family="Orléans", group="French",
        founder="Louis Philippe I",
        last_ruler="Louis Philippe I (abdicated 1848)",
        successor="Second French Republic",
        source_ids=src_fra, confidence=92,
    )
    b.add_ruler("july_monarchy", "Louis Philippe I", "roi des Français", 1830, 1848, source_ids=src_fra, confidence=92)

    b.add_polity(
        "second_french_republic", "Second French Republic",
        "长十九世纪", "Republican", "republic", 1848, 1852,
        aliases="Deuxième République", display="法兰西第二共和国",
        geography="法兰西本土。",
        modern_admin="FRA",
        capital="Paris",
        family="Republican", group="French",
        founder="Provisional Government 1848",
        last_ruler="Louis-Napoléon Bonaparte (became Emperor 1852)",
        successor="Second French Empire",
        source_ids=src_fra, confidence=92,
    )

    b.add_polity(
        "second_french_empire", "Second French Empire",
        "长十九世纪", "Bonaparte", "empire", 1852, 1870,
        aliases="Second Empire", display="法兰西第二帝国",
        geography="法兰西本土；克里米亚战争、墨西哥远征、普法战争。",
        modern_admin="FRA",
        capital="Paris",
        family="Bonaparte", group="French",
        founder="Napoleon III",
        last_ruler="Napoleon III (deposed 1870)",
        successor="Third French Republic",
        source_ids=src_fra, confidence=92,
    )
    b.add_ruler("second_french_empire", "Napoleon III", "empereur", 1852, 1870, source_ids=src_fra, confidence=92)

    b.add_polity(
        "third_french_republic", "Third French Republic",
        "长十九世纪", "Republican", "republic", 1870, 1940,
        aliases="Troisième République", display="法兰西第三共和国",
        geography="法兰西本土 + 殖民帝国（北非、印支、西非等）。",
        modern_admin="FRA|DZA|MAR|TUN|LBN|SYR",
        capital="Paris",
        family="Parliamentary", group="French",
        founder="National Government (1870)",
        last_ruler="Albert Lebrun (resigned 1940)",
        successor="Vichy France / Free France",
        source_ids=src_fra, confidence=92,
    )
    b.add_capital("third_french_republic", "Paris", 1870, 1940, src_fra, 92)

    b.add_polity(
        "uk_19th", "United Kingdom of Great Britain and Ireland",
        "长十九世纪", "Hanover → Saxe-Coburg → Windsor", "kingdom", 1801, 1922,
        aliases="UK (1801-1922)", display="大不列颠及爱尔兰联合王国",
        geography="不列颠岛 + 爱尔兰 + 全球殖民帝国（印度、加拿大、澳洲、非洲等）。",
        modern_admin="GBR|GB-ENG|GB-SCT|GB-WLS|GB-NIR|IRL",
        capital="London",
        family="Hanover → Saxe-Coburg-Gotha → Windsor", group="British",
        founder="George III (1801)",
        last_ruler="George V (Irish Free State 1922)",
        successor="United Kingdom of Great Britain and Northern Ireland",
        source_ids=src_uk, confidence=95,
    )
    b.add_capital("uk_19th", "London", 1801, 1922, src_uk, 95)
    b.add_ruler("uk_19th", "Victoria", "regina", 1837, 1901, source_ids=src_uk, confidence=95)
    b.add_ruler("uk_19th", "Edward VII", "rex", 1901, 1910, source_ids=src_uk, confidence=92)
    b.add_ruler("uk_19th", "George V", "rex", 1910, 1922, source_ids=src_uk, confidence=92)

    b.add_polity(
        "austrian_empire", "Austrian Empire",
        "长十九世纪", "Habsburg-Lorraine", "empire", 1804, 1867,
        aliases="Kaisertum Österreich", display="奥地利帝国",
        geography="奥地利、波西米亚、匈牙利、加利西亚、伦巴第-威尼西亚、达尔马提亚等。",
        modern_admin="AUT|CZE|HUN|SVK|SVN|HRV|ITA|POL|UKR|ROU|BIH|SRB",
        capital="Vienna",
        family="Habsburg-Lorraine", group="Austrian / German",
        founder="Francis I",
        last_ruler="Franz Joseph I (Ausgleich 1867)",
        successor="Austria-Hungary",
        source_ids=src_hbg, confidence=92,
    )
    b.add_capital("austrian_empire", "Vienna", 1804, 1867, src_hbg, 92)
    b.add_ruler("austrian_empire", "Francis I", "Kaiser", 1804, 1835, source_ids=src_hbg, confidence=92)
    b.add_ruler("austrian_empire", "Franz Joseph I", "Kaiser", 1848, 1867, source_ids=src_hbg, confidence=92)

    b.add_polity(
        "austria_hungary", "Austria-Hungary",
        "长十九世纪", "Habsburg-Lorraine (dual)", "dual_monarchy", 1867, 1918,
        aliases="K.u.k. Monarchie", display="奥匈帝国",
        geography="奥地利 + 匈牙利 + 波西米亚 + 加利西亚 + 克罗地亚 + 波斯尼亚（1908 起）+ 伦巴第外的部分意大利领。",
        modern_admin="AUT|HUN|CZE|SVK|SVN|HRV|ROU|UKR|POL|BIH|SRB|MNE|ITA",
        capital="Vienna",
        family="Habsburg-Lorraine", group="Austrian / Hungarian",
        founder="Franz Joseph I (Ausgleich)",
        last_ruler="Karl I (abdicated 1918)",
        successor="Austria | Hungary | Czechoslovakia | Yugoslavia | Poland (Galicia)",
        source_ids=src_hbg, confidence=92,
    )
    b.add_capital("austria_hungary", "Vienna", 1867, 1918, src_hbg, 92)
    b.add_capital("austria_hungary", "Budapest", 1867, 1918, ["source_eur_0014"], 92, note="Hungarian co-capital under Ausgleich.")
    b.add_ruler("austria_hungary", "Franz Joseph I", "Kaiser und König", 1867, 1916, source_ids=src_hbg, confidence=95)
    b.add_ruler("austria_hungary", "Karl I", "Kaiser und König", 1916, 1918, source_ids=src_hbg, confidence=88)

    b.add_polity(
        "german_confederation", "German Confederation",
        "长十九世纪", "Inter-state confederation", "confederation", 1815, 1866,
        aliases="Deutscher Bund", display="德意志邦联",
        geography="维也纳会议后德意志诸邦松散联合。",
        modern_admin="DEU|AUT|CHE|LIE|LUX|CZE|POL",
        capital="Frankfurt",
        group="German", successor="North German Confederation / German Empire",
        source_ids=src_hre, confidence=85,
    )
    b.add_capital("german_confederation", "Frankfurt", 1815, 1866, src_hre, 85)

    b.add_polity(
        "north_german_confederation", "North German Confederation",
        "长十九世纪", "Hohenzollern-led", "confederation", 1867, 1871,
        aliases="Norddeutscher Bund", display="北德意志邦联",
        geography="德意志北部诸邦在普鲁士主导下结盟。",
        modern_admin="DEU|POL", capital="Berlin",
        group="German", successor="German Empire",
        source_ids=src_hre, confidence=85,
    )

    b.add_polity(
        "german_empire", "German Empire",
        "长十九世纪", "Hohenzollern", "empire", 1871, 1918,
        aliases="Deutsches Kaiserreich", display="德意志帝国",
        geography="德意志统一民族国家：北德 + 巴伐利亚 + 巴登 + 符腾堡 + 黑森 + 阿尔萨斯-洛林。",
        modern_admin="DEU|POL|FRA|LTU|RUS|DNK|BEL|LUX",
        capital="Berlin",
        family="Hohenzollern", group="German",
        founder="Wilhelm I",
        last_ruler="Wilhelm II (abdicated 1918)",
        successor="Weimar Republic",
        source_ids=src_hre, confidence=95,
    )
    b.add_capital("german_empire", "Berlin", 1871, 1918, src_hre, 95)
    b.add_ruler("german_empire", "Wilhelm I", "Kaiser", 1871, 1888, source_ids=src_hre, confidence=95)
    b.add_ruler("german_empire", "Wilhelm II", "Kaiser", 1888, 1918, source_ids=src_hre, confidence=95)

    b.add_polity(
        "kingdom_italy", "Kingdom of Italy",
        "长十九世纪", "Savoy", "kingdom", 1861, 1946,
        aliases="Regno d'Italia", display="意大利王国",
        geography="意大利统一民族国家；1870 加罗马；1919 加南蒂罗尔/特里雅斯特。",
        modern_admin="ITA|HRV|SVN",
        capital="Rome",
        family="Savoy", group="Italian",
        founder="Victor Emmanuel II",
        last_ruler="Umberto II (referendum 1946)",
        successor="Italian Republic",
        source_ids=src_ita, confidence=92,
    )
    b.add_capital("kingdom_italy", "Turin", 1861, 1865, src_ita, 88)
    b.add_capital("kingdom_italy", "Florence", 1865, 1871, src_ita, 88)
    b.add_capital("kingdom_italy", "Rome", 1871, 1946, src_ita, 92)
    b.add_ruler("kingdom_italy", "Victor Emmanuel II", "rex", 1861, 1878, source_ids=src_ita, confidence=92)
    b.add_ruler("kingdom_italy", "Umberto I", "rex", 1878, 1900, source_ids=src_ita, confidence=88)
    b.add_ruler("kingdom_italy", "Victor Emmanuel III", "rex", 1900, 1946, source_ids=src_ita, confidence=92)

    b.add_polity(
        "russian_empire_late", "Russian Empire (Alexandrine to Nicholas II)",
        "长十九世纪", "Romanov-Holstein-Gottorp", "empire", 1801, 1917,
        aliases="Rossiyskaya Imperiya (late)", display="俄罗斯帝国（晚期）",
        geography="俄罗斯本土 + 波兰立陶宛 + 芬兰 + 高加索 + 中亚 + 西伯利亚 + 远东。",
        modern_admin="RUS|UKR|BLR|FIN|EST|LVA|LTU|POL|MDA|GEO|AZE|ARM|KAZ|KGZ|TJK|TKM|UZB",
        capital="Saint Petersburg",
        family="Romanov-Holstein-Gottorp", group="Russian",
        founder="Alexander I",
        last_ruler="Nicholas II (abdicated 1917)",
        successor="Russian Provisional Government / RSFSR",
        source_ids=src_rus, confidence=95,
    )
    b.add_capital("russian_empire_late", "Saint Petersburg", 1801, 1917, src_rus, 95)
    b.add_ruler("russian_empire_late", "Alexander I", "imperator", 1801, 1825, source_ids=src_rus, confidence=92)
    b.add_ruler("russian_empire_late", "Nicholas I", "imperator", 1825, 1855, source_ids=src_rus, confidence=92)
    b.add_ruler("russian_empire_late", "Alexander II", "imperator", 1855, 1881, source_ids=src_rus, confidence=92, note="Emancipated serfs 1861.")
    b.add_ruler("russian_empire_late", "Alexander III", "imperator", 1881, 1894, source_ids=src_rus, confidence=92)
    b.add_ruler("russian_empire_late", "Nicholas II", "imperator", 1894, 1917, source_ids=src_rus, confidence=95)

    b.add_polity(
        "ottoman_tanzimat", "Ottoman Empire (Tanzimat to late period)",
        "长十九世纪", "Osman (reformist)", "empire", 1789, 1908,
        aliases="Ottoman late empire", display="奥斯曼帝国（坦齐马特至晚期）",
        geography="奥斯曼疆域逐步收缩：希腊、塞尔维亚、罗马尼亚、保加利亚、波黑相继脱离。",
        modern_admin="TUR|GRC|BGR|MKD|ALB|SRB|MNE|BIH|HRV|ROU|MDA|UKR|CYP|SYR|LBN|ISR|JOR|EGY|LBY|TUN|DZA|IRQ",
        capital="Constantinople",
        family="Osman dynasty", group="Ottoman Turkish",
        founder="Selim III (Nizam-ı Cedid reforms 1789)",
        last_ruler="Abdul Hamid II (deposed 1909)",
        successor="Constitutional Ottoman period (1908+)",
        source_ids=src_ott, confidence=88,
    )
    b.add_ruler("ottoman_tanzimat", "Mahmud II", "sultan", 1808, 1839, source_ids=src_ott, confidence=92)
    b.add_ruler("ottoman_tanzimat", "Abdulmejid I", "sultan", 1839, 1861, source_ids=src_ott, confidence=88)
    b.add_ruler("ottoman_tanzimat", "Abdul Hamid II", "sultan", 1876, 1909, source_ids=src_ott, confidence=92)

    b.add_polity(
        "ottoman_young_turk", "Ottoman Empire (Young Turk to end)",
        "长十九世纪", "Constitutional Ottoman / CUP", "empire", 1908, 1922,
        aliases="Second Constitutional Era", display="奥斯曼帝国（青年土耳其党时期）",
        geography="奥斯曼晚期：失去利比亚（意大利）、巴尔干战争疆域、阿拉伯领土（一战后）。",
        modern_admin="TUR|SYR|LBN|ISR|JOR|IRQ", capital="Constantinople",
        family="Osman dynasty (constitutional)", group="Ottoman Turkish",
        founder="Mehmed V (acceded under Young Turk regime)",
        last_ruler="Mehmed VI (deposed 1922)",
        successor="Republic of Turkey",
        source_ids=src_ott, confidence=90,
    )
    b.add_capital("ottoman_young_turk", "Constantinople", 1908, 1922, src_ott, 90)

    b.add_polity(
        "kingdom_greece", "Kingdom of Greece",
        "长十九世纪", "Wittelsbach → Glücksburg", "kingdom", 1832, 1924,
        aliases="Basileio tēs Hellados", display="希腊王国",
        geography="希腊独立后疆域逐步扩张（色萨利 1881、克里特 1908、马其顿 1912-13）。",
        modern_admin="GRC", capital="Athens",
        family="Wittelsbach → Glücksburg", group="Greek",
        founder="Otto of Greece",
        successor="First Hellenic Republic (1924)",
        source_ids=["source_eur_0011"], confidence=88,
    )
    b.add_capital("kingdom_greece", "Athens", 1834, 1924, ["source_eur_0011"], 88)

    b.add_polity(
        "principality_serbia", "Principality / Kingdom of Serbia",
        "长十九世纪", "Obrenović / Karađorđević", "principality_kingdom",
        1815, 1918,
        aliases="Knjaževina/Kraljevina Srbija", display="塞尔维亚公国 / 王国",
        geography="塞尔维亚本土；1882 升格为王国。",
        modern_admin="SRB|MKD|BIH", capital="Belgrade",
        family="Obrenović → Karađorđević", group="Serbian",
        founder="Miloš Obrenović",
        last_ruler="Peter I (until Yugoslav unification 1918)",
        successor="Kingdom of Serbs, Croats and Slovenes",
        source_ids=["source_eur_0001"], confidence=85,
    )
    b.add_capital("principality_serbia", "Belgrade", 1815, 1918, ["source_eur_0001"], 88)

    b.add_polity(
        "principality_romania", "United Principalities / Kingdom of Romania",
        "长十九世纪", "Hohenzollern-Sigmaringen", "principality_kingdom",
        1859, 1947,
        aliases="Principatele Unite / Regatul României", display="罗马尼亚公国 / 王国",
        geography="罗马尼亚本土；瓦拉几亚与摩尔达维亚合并 1859 → 1881 升格为王国。",
        modern_admin="ROU|MDA", capital="Bucharest",
        family="Hohenzollern-Sigmaringen", group="Romanian",
        founder="Alexandru Ioan Cuza → Carol I",
        successor="People's Republic of Romania (1947)",
        source_ids=["source_eur_0001"], confidence=85,
    )
    b.add_capital("principality_romania", "Bucharest", 1862, 1947, ["source_eur_0001"], 88)

    b.add_polity(
        "principality_bulgaria", "Principality / Kingdom of Bulgaria",
        "长十九世纪", "Battenberg / Saxe-Coburg-Gotha", "principality_kingdom",
        1878, 1946,
        aliases="Knyazhestvo/Tsarstvo Balgariya", display="保加利亚公国 / 王国",
        geography="保加利亚独立后疆域逐步扩张到东鲁米利亚（1885）等。",
        modern_admin="BGR", capital="Sofia",
        family="Battenberg → Saxe-Coburg-Gotha", group="Bulgarian",
        founder="Alexander of Battenberg",
        successor="People's Republic of Bulgaria",
        source_ids=["source_eur_0001"], confidence=85,
    )
    b.add_capital("principality_bulgaria", "Sofia", 1879, 1946, ["source_eur_0001"], 88)

    b.add_polity(
        "kingdom_belgium", "Kingdom of Belgium",
        "长十九世纪", "Saxe-Coburg-Gotha", "kingdom", 1830, 2026,
        aliases="Royaume de Belgique", display="比利时王国",
        geography="比利时本土；1908 加刚果自由邦改为殖民地。",
        modern_admin="BEL", capital="Brussels",
        family="Saxe-Coburg-Gotha (Belgian branch)", group="Belgian",
        founder="Leopold I",
        source_ids=["source_eur_0001"], confidence=92,
    )
    b.add_capital("kingdom_belgium", "Brussels", 1830, 2026, ["source_eur_0001"], 92)
    b.add_ruler("kingdom_belgium", "Leopold I", "roi des Belges", 1831, 1865, source_ids=["source_eur_0001"], confidence=92)
    b.add_ruler("kingdom_belgium", "Leopold II", "roi des Belges", 1865, 1909, source_ids=["source_eur_0001"], confidence=92, note="Personal rule of Congo Free State.")

    b.add_polity(
        "kingdom_netherlands", "Kingdom of the Netherlands",
        "长十九世纪", "Orange-Nassau", "kingdom", 1815, 2026,
        aliases="Koninkrijk der Nederlanden", display="荷兰王国",
        geography="荷兰本土；1815-1830 含比利时；殖民地（东印度、苏里南、加勒比）。",
        modern_admin="NLD", capital="Amsterdam",
        family="Orange-Nassau", group="Dutch",
        founder="William I",
        source_ids=["source_eur_0001"], confidence=92,
    )
    b.add_capital("kingdom_netherlands", "Amsterdam", 1815, 2026, ["source_eur_0001"], 90)

    b.add_polity(
        "swiss_confederation_modern", "Swiss Confederation (modern federal state)",
        "长十九世纪", "Federal democratic", "federation", 1848, 2026,
        aliases="Schweizerische Eidgenossenschaft (1848+)", display="瑞士联邦（1848 联邦宪法）",
        geography="瑞士联邦各州；中立国地位逐步固化。",
        modern_admin="CHE", capital="",
        group="Swiss", source_ids=["source_eur_0001"], confidence=88,
    )

    b.add_polity(
        "kingdom_norway_modern", "Kingdom of Norway (modern)",
        "长十九世纪", "Bernadotte (in union) → Glücksburg", "kingdom",
        1814, 2026,
        aliases="Kongeriket Norge", display="挪威王国（1814 起）",
        geography="挪威本土；1814-1905 与瑞典共主联盟；1905 完全独立。",
        modern_admin="NOR", capital="Oslo",
        family="Bernadotte (in union) → Glücksburg", group="Norwegian",
        founder="Christian Frederick (briefly 1814) / Karl Johan",
        source_ids=["source_eur_0001"], confidence=85,
    )

    b.add_polity(
        "kingdom_sweden_modern", "Kingdom of Sweden (Bernadotte)",
        "长十九世纪", "Bernadotte", "kingdom", 1814, 2026,
        aliases="Konungariket Sverige", display="瑞典王国（贝尔纳多特王朝）",
        geography="瑞典本土；1814-1905 与挪威共主联盟。",
        modern_admin="SWE", capital="Stockholm",
        family="Bernadotte", group="Swedish",
        founder="Karl XIII / Karl XIV Johan",
        source_ids=["source_eur_0001"], confidence=88,
    )

    b.add_polity(
        "kingdom_denmark_modern", "Kingdom of Denmark (modern)",
        "长十九世纪", "Glücksburg", "kingdom", 1814, 2026,
        aliases="Kongeriget Danmark", display="丹麦王国（1814 起）",
        geography="丹麦本土；冰岛 1918 起共主；殖民地（格陵兰、法罗）。",
        modern_admin="DNK", capital="Copenhagen",
        family="Glücksburg", group="Danish",
        founder="Frederick VI",
        source_ids=["source_eur_0001"], confidence=85,
    )

    b.add_polity(
        "russia_polish_kingdom", "Kingdom of Poland (Congress Poland)",
        "长十九世纪", "Romanov (as Russian client)", "personal_union_kingdom",
        1815, 1867,
        aliases="Królestwo Polskie / Congress Poland",
        display="波兰王国（俄属，1815-1867）",
        geography="维也纳会议设立的俄属波兰王国；1867 起被完全俄罗斯化。",
        modern_admin="POL|LTU|UKR|BLR", capital="Warsaw",
        family="Romanov", group="Polish (under Russian rule)",
        founder="Alexander I",
        successor="Vistula Land (Russian province)",
        source_ids=src_pol, confidence=82,
    )

    b.add_event(year=1789, title="Storming of the Bastille",
                description="巴黎人民攻陷巴士底狱，法国大革命爆发。",
                significance="法国大革命象征性开端。",
                event_type="revolution_outbreak",
                polity_keys=["kingdom_france", "french_revolution"],
                people="Sans-culottes; Marquis de Lafayette",
                location="Paris",
                source_ids=src_rev, confidence=95, importance=3)
    b.add_event(year=1804, title="Napoleon crowned Emperor",
                description="拿破仑·波拿巴在巴黎圣母院加冕为法兰西人皇帝。",
                significance="法兰西第一帝国成立。",
                event_type="coronation",
                polity_keys=["first_french_empire"],
                people="Napoleon I", location="Paris",
                source_ids=src_nap, confidence=95, importance=3)
    b.add_event(year=1812, title="Napoleon's Russian campaign",
                description="拿破仑率大军远征俄罗斯，最终撤退中损失惨重。",
                significance="拿破仑第一帝国由盛转衰。",
                event_type="military_campaign",
                polity_keys=["first_french_empire", "russian_empire_late"],
                people="Napoleon I; Kutuzov; Alexander I",
                location="Moscow",
                source_ids=src_nap, confidence=92, importance=3)
    b.add_event(year=1815, title="Battle of Waterloo & Congress of Vienna",
                description="拿破仑在滑铁卢战败；维也纳会议重画欧洲版图。",
                significance="拿破仑战争结束，欧洲均势体系建立。",
                event_type="battle_and_treaty",
                polity_keys=["first_french_empire", "uk_19th", "kingdom_prussia", "austrian_empire", "russian_empire_late"],
                people="Napoleon I; Wellington; Blücher; Metternich",
                location="Waterloo",
                source_ids=src_nap, confidence=95, importance=3)
    b.add_event(year=1830, title="July Revolution in France",
                description="七月革命推翻波旁复辟，七月王朝（路易·菲利普）建立。",
                significance="自由派民族革命浪潮第一波。",
                event_type="revolution",
                polity_keys=["bourbon_restoration", "july_monarchy"],
                location="Paris",
                source_ids=src_fra, confidence=92, importance=3)
    b.add_event(year=1848, title="Springtime of Nations",
                description="欧洲多国爆发自由主义与民族主义革命。",
                significance="19 世纪欧洲政治格局重大转折。",
                event_type="revolution_wave",
                polity_keys=["july_monarchy", "austrian_empire", "german_confederation", "kingdom_italy"],
                source_ids=src_fra, confidence=92, importance=3)
    b.add_event(year=1853, title="Crimean War begins",
                description="俄罗斯与奥斯曼-英法奥联合开战。",
                significance="欧洲协调机制首次重大破裂。",
                event_type="war_outbreak",
                polity_keys=["russian_empire_late", "ottoman_tanzimat", "uk_19th", "second_french_empire"],
                location="Sevastopol",
                source_ids=src_rus, confidence=92, importance=3)
    b.add_event(year=1861, title="Proclamation of the Kingdom of Italy",
                description="意大利复兴运动统一各邦，宣布意大利王国成立。",
                significance="意大利统一民族国家成形。",
                event_type="political_unification",
                polity_keys=["kingdom_italy", "savoy_kingdom"],
                people="Victor Emmanuel II; Cavour; Garibaldi",
                location="Turin",
                source_ids=src_ita, confidence=95, importance=3)
    b.add_event(year=1867, title="Austro-Hungarian Ausgleich",
                description="奥地利帝国改组为奥地利-匈牙利双元帝国。",
                significance="哈布斯堡君主国应对民族主义压力的政治妥协。",
                event_type="constitutional_compromise",
                polity_keys=["austrian_empire", "austria_hungary"],
                people="Franz Joseph I; Andrássy",
                source_ids=src_hbg, confidence=92, importance=3)
    b.add_event(year=1870, title="Franco-Prussian War & end of Second French Empire",
                description="普鲁士击败法国，色当之役后拿破仑三世被俘，第二帝国垮台。",
                significance="德意志统一最后阶段。",
                event_type="battle_and_collapse",
                polity_keys=["second_french_empire", "kingdom_prussia"],
                people="Napoleon III; Bismarck; Moltke",
                source_ids=src_hre, confidence=95, importance=3)
    b.add_event(year=1871, title="Proclamation of the German Empire",
                description="威廉一世在凡尔赛镜厅加冕德意志皇帝。",
                significance="德意志统一民族国家成形。",
                event_type="political_unification",
                polity_keys=["german_empire", "kingdom_prussia"],
                people="Wilhelm I; Bismarck",
                source_ids=src_hre, confidence=95, importance=3)
    b.add_event(year=1878, title="Congress of Berlin",
                description="俾斯麦主持柏林会议，重新划定巴尔干疆界；塞、罗、门独立，保加利亚自治。",
                significance="俄土战争后欧洲列强干涉东南欧。",
                event_type="treaty",
                polity_keys=["german_empire", "russian_empire_late", "ottoman_tanzimat", "principality_serbia", "principality_romania", "principality_bulgaria"],
                location="Berlin",
                source_ids=src_hre, confidence=92, importance=2)
    b.add_event(year=1905, title="Russian Revolution of 1905",
                description="日俄战败、血腥星期日触发首次大规模革命；尼古拉二世颁《十月宣言》，建立国家杜马。",
                significance="俄罗斯立宪改革雏形与社会动荡先兆。",
                event_type="revolution",
                polity_keys=["russian_empire_late"],
                people="Nicholas II", location="Saint Petersburg",
                source_ids=src_rus, confidence=92, importance=2)
    b.add_event(year=1908, title="Young Turk Revolution",
                description="青年土耳其党人迫使阿卜杜勒-哈米德二世恢复 1876 年宪法。",
                significance="奥斯曼帝国宪政改革重启。",
                event_type="revolution",
                polity_keys=["ottoman_tanzimat", "ottoman_young_turk"],
                location="Constantinople",
                source_ids=src_ott, confidence=92, importance=2)
    b.add_event(year=1912, title="First Balkan War",
                description="塞尔维亚、保加利亚、希腊、黑山联军击败奥斯曼帝国，瓜分巴尔干欧洲领土。",
                significance="奥斯曼帝国基本退出欧洲。",
                event_type="war",
                polity_keys=["ottoman_young_turk", "principality_serbia", "principality_bulgaria", "kingdom_greece"],
                source_ids=src_ott, confidence=92, importance=2)

    b.add_context(start=1789, end=1914, title="长十九世纪",
                  description="法国大革命与拿破仑战争 → 维也纳体系 → 民族主义革命 → 意德统一 → 列强协调 → 巴尔干危机。",
                  source_ids=src_fra, confidence=92)


def _register_world_wars(b: Builder) -> None:
    """WWI / Interwar / WWII (1914-1945). Versailles successor states,
    interwar dictatorships, WWII occupations, end-state 1945."""
    src_wwi = ["source_eur_0019"]
    src_wwii = ["source_eur_0020"]
    src_rus = ["source_eur_0010"]
    src_pol = ["source_eur_0013"]
    src_hun = ["source_eur_0014"]
    src_uk = ["source_eur_0006"]
    src_fra = ["source_eur_0005"]
    src_ita = ["source_eur_0030"]
    src_esp = ["source_eur_0007"]
    src_hre = ["source_eur_0004"]
    src_hbg = ["source_eur_0033"]

    b.add_polity(
        "uk_interwar", "United Kingdom of Great Britain and Northern Ireland",
        "两次世界大战", "Windsor", "kingdom", 1922, 2026,
        aliases="UK (1922+)", display="大不列颠及北爱尔兰联合王国（1922 起）",
        geography="不列颠 + 北爱尔兰 + 殖民帝国。",
        modern_admin="GBR|GB-ENG|GB-SCT|GB-WLS|GB-NIR",
        capital="London",
        family="Windsor", group="British",
        founder="George V",
        source_ids=src_uk, confidence=95,
    )
    b.add_capital("uk_interwar", "London", 1922, 2026, src_uk, 95)
    b.add_ruler("uk_interwar", "George V", "rex", 1922, 1936, source_ids=src_uk, confidence=92)
    b.add_ruler("uk_interwar", "George VI", "rex", 1936, 1945, source_ids=src_uk, confidence=92)

    b.add_polity(
        "weimar_republic", "Weimar Republic",
        "两次世界大战", "Parliamentary republic", "republic", 1919, 1933,
        aliases="Deutsches Reich (Weimar)", display="魏玛共和国",
        geography="一战后德国本土；失阿尔萨斯-洛林、波兰走廊、北石勒苏益格、欧本-马尔默迪等。",
        modern_admin="DEU|POL", capital="Berlin",
        family="Parliamentary", group="German",
        founder="Friedrich Ebert",
        last_ruler="Paul von Hindenburg (appointed Hitler chancellor 1933)",
        successor="Nazi Germany",
        source_ids=src_hre, confidence=92,
    )
    b.add_capital("weimar_republic", "Berlin", 1919, 1933, src_hre, 92)
    b.add_ruler("weimar_republic", "Friedrich Ebert", "Reichspräsident", 1919, 1925, source_ids=src_hre, confidence=92)
    b.add_ruler("weimar_republic", "Paul von Hindenburg", "Reichspräsident", 1925, 1934, source_ids=src_hre, confidence=92)

    b.add_polity(
        "nazi_germany", "Nazi Germany (Third Reich)",
        "两次世界大战", "NSDAP single-party", "dictatorship", 1933, 1945,
        aliases="Drittes Reich", display="纳粹德国（第三帝国）",
        geography="德国本土 + 奥地利合并 + 苏台德 + 占领波兰、低地、法国、巴尔干等。",
        modern_admin="DEU|AUT|POL|CZE|FRA|BEL|NLD|LUX|DNK|NOR|YUG|GRC|HUN|UKR|BLR|RUS",
        capital="Berlin",
        family="NSDAP single-party", group="German",
        founder="Adolf Hitler",
        last_ruler="Karl Dönitz (briefly, 1945)",
        successor="Allied occupation zones",
        source_ids=src_wwii, confidence=95,
    )
    b.add_capital("nazi_germany", "Berlin", 1933, 1945, src_wwii, 95)
    b.add_ruler("nazi_germany", "Adolf Hitler", "Führer und Reichskanzler", 1933, 1945, source_ids=src_wwii, confidence=95)
    b.add_ruler("nazi_germany", "Karl Dönitz", "Reichspräsident", 1945, 1945, source_ids=src_wwii, confidence=85)

    b.add_polity(
        "austria_first_republic", "First Austrian Republic",
        "两次世界大战", "Parliamentary republic", "republic", 1919, 1938,
        aliases="Republik Österreich (Erste)", display="奥地利第一共和国",
        geography="一战后奥地利疆域。",
        modern_admin="AUT", capital="Vienna",
        family="Parliamentary → Federal State (Austrofascism)", group="Austrian",
        founder="Karl Renner",
        last_ruler="Kurt Schuschnigg",
        successor="Anschluss with Nazi Germany",
        source_ids=src_hbg, confidence=90,
    )
    b.add_capital("austria_first_republic", "Vienna", 1919, 1938, src_hbg, 92)

    b.add_polity(
        "kingdom_hungary_interwar", "Kingdom of Hungary (interwar regency)",
        "两次世界大战", "Horthy regency", "kingdom_without_king", 1920, 1946,
        aliases="Magyar Királyság (1920-1946)", display="匈牙利王国（霍尔蒂摄政时期）",
        geography="一战后特里亚农条约后疆域；二战时与轴心国结盟。",
        modern_admin="HUN", capital="Budapest",
        family="Habsburg-Lorraine (vacant throne)", group="Hungarian",
        founder="Miklós Horthy (regent)",
        last_ruler="Ferenc Szálasi (Arrow Cross, 1944-1945)",
        successor="Hungarian Republic",
        source_ids=src_hun, confidence=88,
    )
    b.add_capital("kingdom_hungary_interwar", "Budapest", 1920, 1946, src_hun, 92)

    b.add_polity(
        "czechoslovakia_first", "Czechoslovakia (First Republic & WWII)",
        "两次世界大战", "Masaryk / Beneš republic", "republic", 1918, 1948,
        aliases="Československo", display="捷克斯洛伐克（第一共和国与二战期间）",
        geography="捷克 + 斯洛伐克 + 喀尔巴阡乌克兰；1938 慕尼黑后丢失苏台德。",
        modern_admin="CZE|SVK|UKR", capital="Prague",
        family="Parliamentary", group="Czech / Slovak",
        founder="Tomáš Garrigue Masaryk",
        last_ruler="Klement Gottwald (Communist coup 1948)",
        successor="Czechoslovak Socialist Republic",
        source_ids=src_hre, confidence=92,
    )
    b.add_capital("czechoslovakia_first", "Prague", 1918, 1948, src_hre, 92)
    b.add_ruler("czechoslovakia_first", "Tomáš Masaryk", "president", 1918, 1935, source_ids=src_hre, confidence=92)
    b.add_ruler("czechoslovakia_first", "Edvard Beneš", "president", 1935, 1948, source_ids=src_hre, confidence=92)

    b.add_polity(
        "poland_second_republic", "Second Polish Republic",
        "两次世界大战", "Piłsudski / sanation regime", "republic", 1918, 1939,
        aliases="II Rzeczpospolita Polska", display="波兰第二共和国",
        geography="波兰本土 + 前俄占波兰东部 + 加利西亚 + 部分白俄、乌克兰、立陶宛地区。",
        modern_admin="POL|UKR|BLR|LTU", capital="Warsaw",
        family="Parliamentary → semi-authoritarian", group="Polish",
        founder="Józef Piłsudski",
        last_ruler="Ignacy Mościcki (resigned in exile 1939)",
        successor="Government-in-exile / General Government",
        source_ids=src_pol, confidence=92,
    )
    b.add_capital("poland_second_republic", "Warsaw", 1918, 1939, src_pol, 92)
    b.add_ruler("poland_second_republic", "Józef Piłsudski", "Marshal of Poland", 1926, 1935, source_ids=src_pol, confidence=92)

    b.add_polity(
        "yugoslavia_kingdom", "Kingdom of Yugoslavia",
        "两次世界大战", "Karađorđević", "kingdom", 1918, 1945,
        aliases="Kraljevina Srba, Hrvata i Slovenaca → Kraljevina Jugoslavija",
        display="南斯拉夫王国",
        geography="塞尔维亚 + 克罗地亚 + 斯洛文尼亚 + 波斯尼亚 + 黑山 + 马其顿。",
        modern_admin="SRB|HRV|SVN|BIH|MNE|MKD|XKX",
        capital="Belgrade",
        family="Karađorđević", group="South Slavic (Serbian-led)",
        founder="Peter I (Karađorđević)",
        last_ruler="Peter II (deposed by communists 1945)",
        successor="SFR Yugoslavia (Tito)",
        source_ids=["source_eur_0001"], confidence=88,
    )
    b.add_capital("yugoslavia_kingdom", "Belgrade", 1918, 1945, ["source_eur_0001"], 90)

    b.add_polity(
        "romania_interwar", "Kingdom of Romania (Greater Romania)",
        "两次世界大战", "Hohenzollern-Sigmaringen", "kingdom", 1918, 1947,
        aliases="România Mare", display="大罗马尼亚王国",
        geography="一战胜利扩张至特兰西瓦尼亚、布科维纳、贝萨拉比亚。",
        modern_admin="ROU|MDA|UKR", capital="Bucharest",
        family="Hohenzollern-Sigmaringen", group="Romanian",
        founder="Ferdinand I",
        last_ruler="Michael I (forced abdication 1947)",
        successor="People's Republic of Romania",
        source_ids=["source_eur_0001"], confidence=92,
    )
    b.add_capital("romania_interwar", "Bucharest", 1918, 1947, ["source_eur_0001"], 92)

    b.add_polity(
        "bulgaria_interwar", "Kingdom of Bulgaria (interwar & WWII)",
        "两次世界大战", "Saxe-Coburg-Gotha (Bulgarian branch)", "kingdom",
        1914, 1946,
        aliases="Tsarstvo Balgariya (interwar)",
        display="保加利亚王国（两次大战间与二战）",
        geography="保加利亚本土；二战时短暂占据马其顿与色雷斯。",
        modern_admin="BGR|MKD|GRC|SRB", capital="Sofia",
        family="Saxe-Coburg-Gotha", group="Bulgarian",
        founder="Ferdinand I (then Boris III)",
        last_ruler="Simeon II (referendum 1946)",
        successor="People's Republic of Bulgaria",
        source_ids=["source_eur_0001"], confidence=88,
    )

    b.add_polity(
        "estonia_first", "Republic of Estonia (first independence)",
        "两次世界大战", "Parliamentary republic", "republic", 1918, 1940,
        aliases="Eesti Vabariik (1918-1940)", display="爱沙尼亚共和国（首次独立）",
        geography="爱沙尼亚本土。",
        modern_admin="EST", capital="Tallinn",
        family="Parliamentary → authoritarian (1934)", group="Estonian",
        founder="Konstantin Päts",
        last_ruler="Konstantin Päts (annexed by USSR 1940)",
        successor="Soviet annexation",
        source_ids=["source_eur_0001"], confidence=90,
    )
    b.add_capital("estonia_first", "Tallinn", 1918, 1940, ["source_eur_0001"], 92)

    b.add_polity(
        "latvia_first", "Republic of Latvia (first independence)",
        "两次世界大战", "Parliamentary republic", "republic", 1918, 1940,
        aliases="Latvijas Republika (1918-1940)", display="拉脱维亚共和国（首次独立）",
        geography="拉脱维亚本土。",
        modern_admin="LVA", capital="Riga",
        family="Parliamentary → Ulmanis authoritarian", group="Latvian",
        founder="Kārlis Ulmanis",
        last_ruler="Kārlis Ulmanis (annexed by USSR 1940)",
        successor="Soviet annexation",
        source_ids=["source_eur_0001"], confidence=90,
    )
    b.add_capital("latvia_first", "Riga", 1918, 1940, ["source_eur_0001"], 92)

    b.add_polity(
        "lithuania_first", "Republic of Lithuania (first independence)",
        "两次世界大战", "Smetona authoritarian republic", "republic", 1918, 1940,
        aliases="Lietuvos Respublika (1918-1940)",
        display="立陶宛共和国（首次独立）",
        geography="立陶宛本土；维尔纽斯 1920-1939 被波兰占。",
        modern_admin="LTU|POL", capital="",
        family="Parliamentary → Smetona authoritarian", group="Lithuanian",
        founder="Antanas Smetona",
        last_ruler="Antanas Smetona (annexed by USSR 1940)",
        successor="Soviet annexation",
        source_ids=["source_eur_0001"], confidence=88,
    )

    b.add_polity(
        "finland_independence", "Republic of Finland",
        "两次世界大战", "Parliamentary republic", "republic", 1917, 2026,
        aliases="Suomen tasavalta", display="芬兰共和国",
        geography="芬兰本土；冬战、继续战争中与苏联交战。",
        modern_admin="FIN", capital="Helsinki",
        family="Parliamentary", group="Finnish",
        founder="Pehr Evind Svinhufvud",
        source_ids=["source_eur_0001"], confidence=92,
    )
    b.add_capital("finland_independence", "Helsinki", 1917, 2026, ["source_eur_0001"], 92)

    b.add_polity(
        "irish_free_state", "Irish Free State / Republic of Ireland",
        "两次世界大战", "Cosgrave / de Valera", "republic", 1922, 2026,
        aliases="Saorstát Éireann → Éire / Ireland",
        display="爱尔兰自由邦 / 共和国",
        geography="爱尔兰岛除北爱尔兰之外的 26 郡。",
        modern_admin="IRL", capital="Dublin",
        family="Parliamentary", group="Irish",
        founder="W.T. Cosgrave",
        source_ids=src_uk, confidence=92,
    )
    b.add_capital("irish_free_state", "Dublin", 1922, 2026, src_uk, 92)

    b.add_polity(
        "iceland_independence", "Kingdom / Republic of Iceland",
        "两次世界大战", "Personal union with Denmark → republic",
        "kingdom_to_republic", 1918, 2026,
        aliases="Ísland", display="冰岛王国 / 共和国",
        geography="冰岛全岛；1918 与丹麦共主 → 1944 共和。",
        modern_admin="ISL", capital="Reykjavik",
        family="Glücksburg (until 1944)", group="Icelandic",
        founder="Frederik VIII (then republic 1944)",
        source_ids=["source_eur_0001"], confidence=88,
    )
    b.add_capital("iceland_independence", "Reykjavik", 1918, 2026, ["source_eur_0001"], 88)

    b.add_polity(
        "soviet_russia", "Russian SFSR / USSR (early)",
        "两次世界大战", "Bolshevik / CPSU", "soviet_state", 1917, 1945,
        aliases="RSFSR → USSR", display="苏俄 / 苏联（早期）",
        geography="俄罗斯本土 + 乌克兰、白俄罗斯、外高加索（联盟成员）；二战扩展至波罗的海、东欧。",
        modern_admin="RUS|UKR|BLR|EST|LVA|LTU|POL|MDA|GEO|ARM|AZE|KAZ|KGZ|TJK|TKM|UZB|FIN|ROU",
        capital="Moscow",
        family="Bolshevik party / CPSU", group="Russian / Soviet",
        founder="Vladimir Lenin",
        last_ruler="Joseph Stalin (1945, WWII victor)",
        successor="USSR Cold War period (post-1945)",
        source_ids=src_rus, confidence=95,
    )
    b.add_capital("soviet_russia", "Moscow", 1918, 1945, src_rus, 95, note="Capital moved from Petrograd to Moscow March 1918.")
    b.add_ruler("soviet_russia", "Vladimir Lenin", "Chairman of the Sovnarkom", 1917, 1924, source_ids=src_rus, confidence=95)
    b.add_ruler("soviet_russia", "Joseph Stalin", "General Secretary CPSU", 1922, 1945, source_ids=src_rus, confidence=95)

    b.add_polity(
        "fascist_italy", "Kingdom of Italy under Fascism",
        "两次世界大战", "Mussolini / National Fascist Party",
        "fascist_dictatorship", 1922, 1943,
        aliases="Regno d'Italia (Fascist era)", display="法西斯意大利",
        geography="意大利本土 + 利比亚、埃塞俄比亚、阿尔巴尼亚（1939 起）+ 多德卡尼斯。",
        modern_admin="ITA|LBY|ALB|GRC|HRV|SVN", capital="Rome",
        family="Mussolini cabinet (under King Victor Emmanuel III)", group="Italian",
        founder="Benito Mussolini",
        last_ruler="Benito Mussolini (dismissed July 1943)",
        successor="Italian Social Republic | Allied-occupied Italy",
        source_ids=src_ita, confidence=92,
    )
    b.add_capital("fascist_italy", "Rome", 1922, 1943, src_ita, 92)
    b.add_ruler("fascist_italy", "Benito Mussolini", "Duce / Prime Minister", 1922, 1943, source_ids=src_ita, confidence=95)

    b.add_polity(
        "italian_social_republic", "Italian Social Republic (Salò)",
        "两次世界大战", "Mussolini puppet government",
        "puppet_state", 1943, 1945,
        aliases="Repubblica Sociale Italiana", display="意大利社会共和国（萨罗共和国）",
        geography="德占北意大利。",
        modern_admin="ITA|IT-NORDOVES|IT-NORDEST", capital="",
        family="Fascist (German puppet)", group="Italian",
        founder="Benito Mussolini",
        last_ruler="Benito Mussolini (executed April 1945)",
        successor="Republic of Italy",
        source_ids=src_ita, confidence=92,
    )

    b.add_polity(
        "vichy_france", "French State (Vichy)",
        "两次世界大战", "Pétain regime", "puppet_state", 1940, 1944,
        aliases="État français", display="法兰西国（维希）",
        geography="法国南部未占领区，1942 后全境德占。",
        modern_admin="FRA|DZA|MAR|TUN|SYR|LBN", capital="",
        family="Vichy regime", group="French (collaborationist)",
        founder="Philippe Pétain",
        last_ruler="Philippe Pétain",
        successor="Provisional Government of the French Republic",
        source_ids=src_fra, confidence=92,
    )

    b.add_polity(
        "free_france", "Free France / Provisional Government",
        "两次世界大战", "de Gaulle", "government_in_exile", 1940, 1946,
        aliases="France Libre → GPRF", display="自由法国 / 法兰西共和国临时政府",
        geography="伦敦总部 → 阿尔及尔 → 1944 后巴黎；解放的法国与殖民地。",
        modern_admin="FRA|DZA", capital="Paris",
        family="Gaullist", group="French",
        founder="Charles de Gaulle",
        last_ruler="Charles de Gaulle (resigned Jan 1946)",
        successor="Fourth French Republic",
        source_ids=src_fra, confidence=92,
    )

    b.add_polity(
        "franco_spain", "Spanish State (Franco regime)",
        "两次世界大战", "Franco dictatorship", "fascist_dictatorship",
        1939, 1975,
        aliases="Estado Español (Franquista)", display="弗朗哥独裁西班牙",
        geography="西班牙全境 + 摩洛哥殖民地、西撒、赤道几内亚。",
        modern_admin="ESP|MAR", capital="Madrid",
        family="Franco (single party Falange)", group="Spanish",
        founder="Francisco Franco",
        successor="Bourbon restoration (Juan Carlos I)",
        source_ids=src_esp, confidence=92,
    )
    b.add_capital("franco_spain", "Madrid", 1939, 1975, src_esp, 92)
    b.add_ruler("franco_spain", "Francisco Franco", "Caudillo", 1939, 1945, source_ids=src_esp, confidence=95, note="Continued in power until death 1975; vEuropean coverage stops at WWII end.")

    b.add_polity(
        "salazar_portugal", "Portuguese Second Republic (Estado Novo)",
        "两次世界大战", "Salazar dictatorship", "authoritarian_republic",
        1933, 1974,
        aliases="Estado Novo", display="葡萄牙第二共和国（新国家）",
        geography="葡萄牙本土 + 殖民帝国（安哥拉、莫桑比克、果阿、澳门、东帝汶等）。",
        modern_admin="PRT", capital="Lisbon",
        family="Salazar regime", group="Portuguese",
        founder="António de Oliveira Salazar",
        successor="Third Republic (Carnation Revolution 1974)",
        source_ids=["source_eur_0001"], confidence=92,
    )

    b.add_polity(
        "neutral_sweden", "Kingdom of Sweden (WWII neutral)",
        "两次世界大战", "Bernadotte", "kingdom", 1914, 2026,
        aliases="Konungariket Sverige (WWII)", display="瑞典王国（两次大战中立）",
        geography="瑞典本土；两次大战均保持中立。",
        modern_admin="SWE", capital="Stockholm",
        family="Bernadotte", group="Swedish",
        founder="Gustaf V (already king)",
        source_ids=["source_eur_0001"], confidence=88,
    )

    b.add_polity(
        "neutral_switzerland", "Swiss Confederation (WWII neutral)",
        "两次世界大战", "Federal democratic", "federation", 1914, 2026,
        aliases="Schweizerische Eidgenossenschaft (WWII)",
        display="瑞士联邦（两次大战中立）",
        geography="瑞士联邦核心；二战期间被轴心国包围但保持武装中立。",
        modern_admin="CHE", capital="",
        group="Swiss", source_ids=["source_eur_0001"], confidence=85,
    )

    b.add_polity(
        "independent_croatia_ndh", "Independent State of Croatia (Ustaše)",
        "两次世界大战", "Ustaše regime", "puppet_state", 1941, 1945,
        aliases="Nezavisna Država Hrvatska", display="克罗地亚独立国",
        geography="克罗地亚 + 波斯尼亚-黑塞哥维那（轴心国扶植傀儡政权）。",
        modern_admin="HRV|BIH", capital="Zagreb",
        family="Ustaše regime", group="Croatian (fascist)",
        founder="Ante Pavelić",
        last_ruler="Ante Pavelić",
        successor="SFR Yugoslavia",
        source_ids=src_wwii, confidence=88,
    )
    b.add_capital("independent_croatia_ndh", "Zagreb", 1941, 1945, src_wwii, 88)

    b.add_polity(
        "slovak_state", "First Slovak Republic (Slovak State)",
        "两次世界大战", "Tiso regime", "puppet_state", 1939, 1945,
        aliases="Slovenská republika", display="斯洛伐克国",
        geography="斯洛伐克本土（德国扶植）。",
        modern_admin="SVK", capital="Bratislava",
        family="Slovak People's Party (clerico-fascist)", group="Slovak",
        founder="Jozef Tiso",
        last_ruler="Jozef Tiso (executed 1947)",
        successor="Restored Czechoslovakia",
        source_ids=src_wwii, confidence=88,
    )
    b.add_capital("slovak_state", "Bratislava", 1939, 1945, src_wwii, 88)

    b.add_event(year=1914, title="Assassination of Archduke Franz Ferdinand",
                description="塞尔维亚学生加夫里洛·普林齐普在萨拉热窝刺杀奥地利大公弗朗茨·斐迪南。",
                significance="一战导火索。",
                event_type="assassination",
                polity_keys=["austria_hungary", "principality_serbia"],
                people="Gavrilo Princip; Franz Ferdinand",
                location="Sarajevo",
                source_ids=src_wwi, confidence=95, importance=3)
    b.add_event(year=1914, title="Outbreak of World War I",
                description="奥匈帝国对塞尔维亚宣战，列强先后卷入。",
                significance="第一次世界大战爆发。",
                event_type="war_outbreak",
                polity_keys=["austria_hungary", "german_empire", "russian_empire_late", "kingdom_france", "uk_19th", "ottoman_young_turk"],
                source_ids=src_wwi, confidence=95, importance=3)
    b.add_event(year=1917, title="Russian Revolutions of 1917",
                description="二月革命推翻沙皇尼古拉二世；十月革命推翻临时政府，布尔什维克掌权。",
                significance="苏俄诞生，欧洲政治格局重塑。",
                event_type="revolution",
                polity_keys=["russian_empire_late", "soviet_russia"],
                people="Lenin; Trotsky; Kerensky",
                location="Saint Petersburg",
                source_ids=src_rus, confidence=95, importance=3)
    b.add_event(year=1918, title="Armistice of 11 November & end of WWI",
                description="11 月 11 日协约国与德国签订康边停战协定，一战结束。",
                significance="一战停战。",
                event_type="treaty",
                polity_keys=["german_empire", "uk_19th", "third_french_republic"],
                source_ids=src_wwi, confidence=95, importance=3)
    b.add_event(year=1919, title="Treaty of Versailles",
                description="一战战胜国与德国签订《凡尔赛条约》。",
                significance="战后欧洲秩序重建；为二战埋下种子。",
                event_type="treaty",
                polity_keys=["weimar_republic", "uk_19th", "third_french_republic", "kingdom_italy"],
                location="Paris",
                source_ids=src_wwi, confidence=95, importance=3)
    b.add_event(year=1922, title="March on Rome — Mussolini takes power",
                description="法西斯党向罗马进军，国王任命墨索里尼为首相。",
                significance="法西斯独裁在意大利建立。",
                event_type="coup",
                polity_keys=["kingdom_italy", "fascist_italy"],
                people="Benito Mussolini; Victor Emmanuel III",
                location="Rome",
                source_ids=src_ita, confidence=92, importance=3)
    b.add_event(year=1933, title="Hitler appointed Chancellor",
                description="兴登堡任命希特勒为德国总理，纳粹党迅速集中权力。",
                significance="纳粹党在德国掌权。",
                event_type="political_appointment",
                polity_keys=["weimar_republic", "nazi_germany"],
                people="Adolf Hitler; Paul von Hindenburg",
                location="Berlin",
                source_ids=src_wwii, confidence=95, importance=3)
    b.add_event(year=1936, title="Spanish Civil War begins",
                description="弗朗哥发动政变引发西班牙内战。",
                significance="意德法西斯阵营试金石。",
                event_type="war_outbreak",
                polity_keys=["franco_spain", "fascist_italy", "nazi_germany"],
                people="Francisco Franco",
                source_ids=src_esp, confidence=92, importance=3)
    b.add_event(year=1938, title="Munich Agreement & Anschluss",
                description="慕尼黑协定割让苏台德给德国；同年德国吞并奥地利。",
                significance="英法对纳粹绥靖政策顶点。",
                event_type="treaty_and_annexation",
                polity_keys=["nazi_germany", "czechoslovakia_first", "austria_first_republic"],
                people="Hitler; Chamberlain; Daladier",
                source_ids=src_wwii, confidence=95, importance=3)
    b.add_event(year=1939, title="Molotov-Ribbentrop Pact & invasion of Poland",
                description="苏德互不侵犯条约附密件瓜分东欧；9 月 1 日德入侵波兰，二战爆发。",
                significance="第二次世界大战在欧洲爆发。",
                event_type="war_outbreak",
                polity_keys=["nazi_germany", "soviet_russia", "poland_second_republic"],
                people="Hitler; Stalin; Molotov; Ribbentrop",
                location="Warsaw",
                source_ids=src_wwii, confidence=95, importance=3)
    b.add_event(year=1940, title="Fall of France",
                description="6 月 22 日法国签订康边停战协定，维希政权成立。",
                significance="纳粹德国占领西欧大部。",
                event_type="capitulation",
                polity_keys=["third_french_republic", "vichy_france", "nazi_germany"],
                people="Pétain; de Gaulle",
                source_ids=src_wwii, confidence=95, importance=3)
    b.add_event(year=1941, title="Operation Barbarossa",
                description="6 月 22 日纳粹德国及其盟友入侵苏联。",
                significance="东线战争开启，最终决定二战胜负。",
                event_type="invasion",
                polity_keys=["nazi_germany", "soviet_russia"],
                people="Hitler; Stalin",
                source_ids=src_wwii, confidence=95, importance=3)
    b.add_event(year=1943, title="Battle of Stalingrad ends",
                description="2 月 2 日德第六集团军在斯大林格勒投降。",
                significance="东线战争转折点。",
                event_type="battle",
                polity_keys=["nazi_germany", "soviet_russia"],
                people="Friedrich Paulus; Vasily Chuikov; Zhukov",
                location="Stalingrad",
                source_ids=src_wwii, confidence=95, importance=3)
    b.add_event(year=1944, title="D-Day landings in Normandy",
                description="6 月 6 日盟军在诺曼底登陆开辟西线第二战场。",
                significance="西欧解放开始。",
                event_type="invasion",
                polity_keys=["nazi_germany", "uk_interwar", "free_france"],
                people="Eisenhower; Montgomery",
                location="Normandy",
                source_ids=src_wwii, confidence=95, importance=3)
    b.add_event(year=1945, title="V-E Day — Germany surrenders",
                description="5 月 8 日纳粹德国无条件投降，欧洲二战结束。",
                significance="二战欧洲战场结束。",
                event_type="surrender",
                polity_keys=["nazi_germany", "uk_interwar", "soviet_russia", "free_france"],
                people="Karl Dönitz; Wilhelm Keitel",
                location="Berlin",
                source_ids=src_wwii, confidence=98, importance=3)

    b.add_context(start=1914, end=1945, title="两次世界大战与战间期",
                  description="一战 → 凡尔赛体系 → 经济危机 → 法西斯崛起 → 二战 → 1945 雅尔塔会议奠基冷战。",
                  source_ids=src_wwii, confidence=95)


def _register_anecdotes(b: Builder) -> None:
    """30 European legends / myths / folk tales spanning cultural cycles.
    All entered with anecdote_type=legend and review_status=candidate to
    flag them as cultural-memory rows, not historical chronology evidence."""
    # ---------- Greek myth (7) ----------
    b.add_anecdote(year=-1200, dynasty="希腊神话", macro="古风时代",
                   title="特洛伊木马（Trojan Horse）",
                   phrase="木马屠城",
                   short_description="希腊联军用巨大木马伪装作贡品送入特洛伊，夜间藏于其中的希腊战士打开城门，特洛伊陷落。",
                   source_id="source_eur_0011", people="Odysseus; Priam; Helen",
                   location="Troy", polity_keys=["trojan_kingdom", "mycenaean"])
    b.add_anecdote(year=-1300, dynasty="希腊神话", macro="青铜时代",
                   title="忒修斯与米诺陶（Theseus and the Minotaur）",
                   phrase="阿里阿德涅之线",
                   short_description="雅典王子忒修斯进入克里特迷宫斩杀牛头怪米诺陶，靠米诺斯公主阿里阿德涅赠予的线团走出迷宫。",
                   source_id="source_eur_0021", people="Theseus; Minos; Ariadne; Minotaur",
                   location="Knossos", polity_keys=["minoan_palatial", "athens_archaic"])
    b.add_anecdote(year=-1200, dynasty="希腊神话", macro="青铜时代",
                   title="赫拉克勒斯十二试炼（The Twelve Labors of Heracles）",
                   phrase="大力神十二试炼",
                   short_description="赫拉克勒斯为赎杀子之罪，受迈锡尼王欧律斯透斯命令完成十二项不可能的任务，包括尼米亚狮、勒拿水蛇、革律翁牛群等。",
                   source_id="source_eur_0011", people="Heracles; Eurystheus",
                   location="Mycenae", polity_keys=["mycenaean"])
    b.add_anecdote(year=-1300, dynasty="希腊神话", macro="青铜时代",
                   title="伊阿宋与金羊毛（Jason and the Argonauts）",
                   phrase="阿尔戈号远征",
                   short_description="伊阿宋率阿尔戈英雄团乘阿尔戈号远征科尔基斯（黑海东岸）夺取金羊毛，获美狄亚相助。",
                   source_id="source_eur_0011", people="Jason; Medea; Argonauts",
                   location="Pella", polity_keys=["mycenaean"])
    b.add_anecdote(year=-700, dynasty="希腊神话", macro="古风时代",
                   title="俄狄浦斯王（Oedipus Rex）",
                   phrase="弑父娶母",
                   short_description="底比斯王子俄狄浦斯不知情下杀父娶母，应验德尔斐神谕，揭示后自残双目流亡。索福克勒斯悲剧母题。",
                   source_id="source_eur_0011", people="Oedipus; Laius; Jocasta",
                   location="Thebes", polity_keys=["thebes_boeotia"])
    b.add_anecdote(year=-1200, dynasty="希腊神话", macro="青铜时代",
                   title="珀尔修斯与美杜莎（Perseus and Medusa）",
                   phrase="斩蛇发美杜莎",
                   short_description="阿耳戈斯王子珀尔修斯借雅典娜之盾与赫尔墨斯之剑斩下美杜莎之头，救埃塞俄比亚公主安德罗墨达。",
                   source_id="source_eur_0011", people="Perseus; Medusa; Andromeda",
                   location="Argos", polity_keys=["mycenaean"])
    b.add_anecdote(year=-431, dynasty="希腊神话/历史交汇", macro="古典时代",
                   title="伯里克利的悼词（Funeral Oration of Pericles）",
                   phrase="雅典是希腊的学校",
                   short_description="伯罗奔尼撒战争首年雅典阵亡将士葬礼上，伯里克利发表演说赞颂雅典民主与公民精神。修昔底德记录。",
                   source_id="source_eur_0011", people="Pericles",
                   location="Athens", polity_keys=["athens_classical"],
                   anecdote_type="historical_memory")

    # ---------- Roman legend (5) ----------
    b.add_anecdote(year=-753, dynasty="罗马神话", macro="古风时代",
                   title="罗慕路斯与雷穆斯（Romulus and Remus）",
                   phrase="双子建罗马",
                   short_description="战神玛尔斯与维斯塔贞女之子双胞胎被遗弃台伯河，由母狼哺育，长大后建罗马城；罗慕路斯杀雷穆斯成为首王。",
                   source_id="source_eur_0002", people="Romulus; Remus",
                   location="Rome", polity_keys=["roman_kingdom"])
    b.add_anecdote(year=-509, dynasty="罗马传说", macro="古风时代",
                   title="卢克丽霞之死（Lucretia）",
                   phrase="贞女之耻",
                   short_description="贵族卢克丽霞遭末王塔克文之子凌辱后自尽，引发布鲁图斯领导贵族驱逐塔克文王朝，建立共和。",
                   source_id="source_eur_0002", people="Lucretia; Sextus Tarquinius; Lucius Junius Brutus",
                   location="Rome", polity_keys=["roman_kingdom", "roman_republic"])
    b.add_anecdote(year=-507, dynasty="罗马传说", macro="古风时代",
                   title="贺拉提乌斯守桥（Horatius Cocles）",
                   phrase="独守苏布利契亚桥",
                   short_description="罗马英雄贺拉提乌斯·科克勒斯独立守桥抵御伊特鲁里亚军，给身后罗马人毁桥时间，自己跳河逃生。",
                   source_id="source_eur_0002", people="Horatius Cocles; Lars Porsena",
                   location="Rome", polity_keys=["roman_republic"])
    b.add_anecdote(year=-458, dynasty="罗马传说", macro="古典时代",
                   title="辛辛纳图斯归田（Cincinnatus）",
                   phrase="十六天的独裁",
                   short_description="独裁官辛辛纳图斯击败埃魁人后十六日卸任，回到自家小农场。共和制公民德行的典范。",
                   source_id="source_eur_0002", people="Lucius Quinctius Cincinnatus",
                   location="Rome", polity_keys=["roman_republic"])
    b.add_anecdote(year=-390, dynasty="罗马传说", macro="古典时代",
                   title="高卢人入侵罗马 — 卡庇托利的鹅（Brennus & the Geese）",
                   phrase="高卢人来了！",
                   short_description="布伦努斯率高卢人攻陷罗马，唯卡庇托山堡守住——夜袭被神庙群鹅鸣叫警觉。布伦努斯索贡时把剑掷上天平喊 'Vae victis'（败者无理）。",
                   source_id="source_eur_0002", people="Brennus; Marcus Manlius",
                   location="Rome", polity_keys=["roman_republic"])

    # ---------- Norse myth (4) ----------
    b.add_anecdote(year=-100, dynasty="北欧神话", macro="铁器时代",
                   title="奥丁与世界树（Odin and Yggdrasil）",
                   phrase="一只眼换智慧",
                   short_description="主神奥丁挂在世界树 Yggdrasil 上九天九夜，自挽枪刃以换取卢恩字符的智慧；又在密米尔之泉献出一只眼以饮泉获洞见。",
                   source_id="source_eur_0016", people="Odin; Mimir",
                   location="Uppsala", polity_keys=["nordic_bronze"])
    b.add_anecdote(year=900, dynasty="北欧神话", macro="中古时代",
                   title="雷神之锤（Thor's Hammer Mjölnir）",
                   phrase="姆约尼尔",
                   short_description="雷神托尔的战锤姆约尼尔由侏儒锻造，能掷出击碎山岳又自动回到手中。维京船首与坠饰常见雷锤造型。",
                   source_id="source_eur_0016", people="Thor; Loki; Sif",
                   location="Uppsala", polity_keys=["viking_norway", "viking_sweden"])
    b.add_anecdote(year=1000, dynasty="北欧神话", macro="中古时代",
                   title="诸神黄昏（Ragnarök）",
                   phrase="诸神之末日",
                   short_description="末日预言：芬利尔狼吞噬奥丁、托尔与世界蛇耶梦加得同归于尽、世界树燃烧、九界沉海，而后新世界重生。",
                   source_id="source_eur_0016", people="Odin; Thor; Loki; Fenrir; Jörmungandr",
                   location="Uppsala", polity_keys=["viking_norway", "viking_denmark"])
    b.add_anecdote(year=750, dynasty="盎格鲁-撒克逊/北欧叙事", macro="古典时代",
                   title="贝奥武夫（Beowulf）",
                   phrase="斩格伦德尔",
                   short_description="高特族英雄贝奥武夫赴丹麦助赫罗斯加王斩怪物格伦德尔母子，晚年化龙之战中同归于尽。盎格鲁-撒克逊最古老英语史诗。",
                   source_id="source_eur_0016", people="Beowulf; Grendel; Hrothgar",
                   location="Roskilde", polity_keys=["anglo_saxon_wessex", "viking_denmark"])

    # ---------- Arthurian (4) ----------
    b.add_anecdote(year=500, dynasty="不列颠传说", macro="古典时代",
                   title="石中剑与亚瑟王（Arthur Pulls the Sword from the Stone）",
                   phrase="拔出石中剑者方为不列颠之王",
                   short_description="少年亚瑟从教堂前石砧中拔出剑（不是 Excalibur），证明自己是合法的不列颠王。后获 Lady of the Lake 赠湖中剑 Excalibur。",
                   source_id="source_eur_0006", people="Arthur; Merlin",
                   location="Winchester", polity_keys=["anglo_saxon_wessex"])
    b.add_anecdote(year=520, dynasty="不列颠传说", macro="古典时代",
                   title="圆桌骑士（Knights of the Round Table）",
                   phrase="圆桌无上下",
                   short_description="亚瑟王在卡梅洛特设圆桌，使所有骑士席位平等。骑士团包括 Lancelot、Gawain、Galahad、Percival 等。",
                   source_id="source_eur_0006", people="Arthur; Lancelot; Galahad; Gawain",
                   location="Winchester")
    b.add_anecdote(year=540, dynasty="不就传说", macro="古典时代",
                   title="圣杯探求（The Quest for the Holy Grail）",
                   phrase="圣杯",
                   short_description="圆桌骑士寻求基督最后晚餐的圣杯，只有 Galahad、Percival、Bors 三纯洁骑士见到圣杯并升天。",
                   source_id="source_eur_0006", people="Galahad; Percival; Bors",
                   location="Winchester")
    b.add_anecdote(year=550, dynasty="不列颠传说", macro="古典时代",
                   title="特里斯坦与伊瑟（Tristan and Iseult）",
                   phrase="爱情灵药",
                   short_description="康沃尔骑士特里斯坦被派去爱尔兰为叔父马克王迎娶伊瑟公主，两人误饮爱情灵药生死相恋，悲剧收场。中世纪 courtly love 母题。",
                   source_id="source_eur_0006", people="Tristan; Iseult; Mark of Cornwall",
                   location="London")

    # ---------- Carolingian cycle (3) ----------
    b.add_anecdote(year=778, dynasty="加洛林叙事诗", macro="中古时代",
                   title="罗兰之歌（La Chanson de Roland）",
                   phrase="罗兰吹响奥利凡特号角",
                   short_description="查理曼东征西班牙归途中，后卫罗兰在比利牛斯山隆塞斯瓦列斯关被巴斯克伏击；罗兰拒吹号求援直至临终时方吹奥利凡特，号声裂喉而亡。",
                   source_id="source_eur_0023", people="Roland; Oliver; Charlemagne; Ganelon",
                   location="Saragossa", polity_keys=["carolingian_empire", "umayyad_iberia"])
    b.add_anecdote(year=800, dynasty="加洛林叙事诗", macro="中古时代",
                   title="十二骑士（The Twelve Paladins of Charlemagne）",
                   phrase="十二圣骑士",
                   short_description="查理曼宫廷传说中的十二位主要骑士，包括 Roland、Oliver、Ogier the Dane、Renaud de Montauban 等。中世纪 chansons de geste 主角群。",
                   source_id="source_eur_0023", people="Roland; Oliver; Ogier; Renaud",
                   location="Aachen", polity_keys=["carolingian_empire"])
    b.add_anecdote(year=850, dynasty="加洛林叙事诗", macro="中古时代",
                   title="奥吉尔之歌（Ogier the Dane）",
                   phrase="丹麦的奥吉尔",
                   short_description="加洛林叙事诗中的丹麦骑士奥吉尔，先与查理曼对抗，后归顺成为加洛林十二骑士之一。法国与丹麦民间英雄。",
                   source_id="source_eur_0023", people="Ogier the Dane; Charlemagne",
                   location="Roskilde", polity_keys=["carolingian_empire", "viking_denmark"])

    # ---------- Folk legends (5) ----------
    b.add_anecdote(year=1190, dynasty="英格兰民间传说", macro="中世纪盛期",
                   title="罗宾汉（Robin Hood）",
                   phrase="劫富济贫",
                   short_description="舍伍德森林绿衣神射手罗宾汉率快乐兄弟会反抗诺丁汉郡长的暴政，劫富济贫，等待狮心王理查回归。",
                   source_id="source_eur_0006", people="Robin Hood; Little John; Maid Marian; Sheriff of Nottingham",
                   location="York", polity_keys=["kingdom_england"])
    b.add_anecdote(year=1307, dynasty="瑞士民间传说", macro="中世纪晚期",
                   title="威廉·退尔（William Tell）",
                   phrase="射苹果",
                   short_description="瑞士神射手威廉·退尔拒向哈布斯堡奥地利总督 Gessler 之帽行礼，被罚射儿子头顶苹果；射中后刺杀 Gessler，引发瑞士独立。",
                   source_id="source_eur_0001", people="William Tell; Gessler",
                   location="Bern" if False else "",  # no coord
                   polity_keys=["swiss_confederation"])
    b.add_anecdote(year=1300, dynasty="德意志民间传说", macro="中世纪晚期",
                   title="哈梅尔的吹笛人（The Pied Piper of Hamelin）",
                   phrase="吹笛人带走 130 孩童",
                   short_description="花衣吹笛人受雇于哈梅尔镇驱赶老鼠，事后不获报酬，吹笛诱走全镇 130 名孩童，消失于山中。可能反映 1284 年儿童东进运动的历史阴影。",
                   source_id="source_eur_0001", people="Pied Piper",
                   location="Hamelin" if False else "",
                   polity_keys=["hre_early", "hre_late"])
    b.add_anecdote(year=1480, dynasty="德意志民间传说", macro="中世纪晚期",
                   title="浮士德博士（Doctor Faust）",
                   phrase="灵魂交易",
                   short_description="德意志学者浮士德博士与魔鬼梅菲斯特费勒斯签约，以灵魂换 24 年知识与享乐。歌德戏剧化为德意志最重要文学母题之一。",
                   source_id="source_eur_0001", people="Doctor Faust; Mephistopheles",
                   location="" if True else "Wittenberg",
                   polity_keys=["hre_late"])
    b.add_anecdote(year=1390, dynasty="瑞士民间传说", macro="中世纪晚期",
                   title="阿诺德·冯·温克尔里德（Arnold von Winkelried）",
                   phrase="给同志开路",
                   short_description="森帕赫战役（1386）瑞士联军对阵奥地利重骑士，温克尔里德怀抱一束敌方长矛刺入自身胸膛为联军开路，使联军突破奥军方阵。",
                   source_id="source_eur_0001", people="Arnold von Winkelried",
                   location="", polity_keys=["swiss_confederation", "hre_late"])

    # ---------- Other / additional (2) ----------
    b.add_anecdote(year=1099, dynasty="十字军记忆", macro="中世纪盛期",
                   title="十字军攻陷耶路撒冷的血雨（Sack of Jerusalem）",
                   phrase="血流至马膝",
                   short_description="第一次十字军攻陷耶路撒冷后大规模屠杀穆斯林与犹太居民。同时代编年史夸张写「血流至马膝」。中世纪基督教 / 伊斯兰记忆中长期回响。",
                   source_id="source_eur_0026", people="Godfrey of Bouillon; Raymond of Toulouse",
                   location="", polity_keys=["crusader_jerusalem"],
                   anecdote_type="historical_memory")
    b.add_anecdote(year=1453, dynasty="拜占庭遗民记忆", macro="中世纪晚期",
                   title="末代皇帝消失于战场（Constantine XI's Last Stand）",
                   phrase="紫衣帝最后一战",
                   short_description="奥斯曼破城之日，末代皇帝君士坦丁十一世弃帝服披普通士兵盔甲冲入城门战死；尸首未被认出。拜占庭遗民传说他将在希腊复国之日复活。",
                   source_id="source_eur_0003", people="Constantine XI Palaiologos; Mehmed II",
                   location="Constantinople", polity_keys=["byzantine_late", "early_ottoman"],
                   anecdote_type="historical_memory")


def write_dataset(b: Builder) -> None:
    """Materialize Builder state to input/vEuropean/*.csv + manifest."""
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    write_csv(DATASET_DIR / DATASET_FILES["polities_master"], MASTER_FIELDS, b.polities)
    write_csv(DATASET_DIR / DATASET_FILES["rulers_master"], RULERS_MASTER_FIELDS, b.rulers)
    write_csv(DATASET_DIR / DATASET_FILES["capital_events"], CAPITAL_FIELDS, b.capitals)
    write_csv(DATASET_DIR / DATASET_FILES["historical_events"], EVENT_FIELDS, b.events)
    write_csv(DATASET_DIR / DATASET_FILES["historical_anecdotes"], ANECDOTE_FIELDS, b.anecdotes)
    write_csv(DATASET_DIR / DATASET_FILES["historical_contexts"], CONTEXT_FIELDS, b.contexts)
    write_csv(DATASET_DIR / DATASET_FILES["strategic_locations"], STRATEGIC_FIELDS, b.strategic)
    # territory_overrides_vEuropean.csv is hand-curated (peak-extent admin_ids
    # for empire-class polities). Bootstrap should never overwrite it unless
    # builder explicitly populated it (b.territories non-empty).
    if b.territories:
        write_csv(DATASET_DIR / DATASET_FILES["territory_overrides"], TERRITORY_FIELDS, b.territories)
    write_csv(DATASET_DIR / DATASET_FILES["issues"], ISSUE_FIELDS, b.issues)
    write_csv(
        DATASET_DIR / DATASET_FILES["sources"],
        SOURCE_FIELDS,
        [
            {
                "source_id": s.source_id, "topic": s.topic, "source_title": s.title,
                "source_url": s.url, "source_type": s.source_type,
                "credibility_tier": s.tier, "covers_fields": s.fields, "notes": s.notes,
            }
            for s in SOURCE_REFS
        ],
    )
    # validation_report 由 validate_world_history_dataset.py 在管线中生成；这里写空表头。
    write_csv(DATASET_DIR / DATASET_FILES["validation_report"], VALIDATION_FIELDS, [])
    # polities_yearly 由 generate_world_history_yearly.py 生成，这里只写表头。
    write_csv(DATASET_DIR / DATASET_FILES["polities_yearly"], YEARLY_FIELDS, [])

    manifest_path = DATASET_DIR / f"dataset_manifest_{'vEuropean'}.json"
    manifest_path.write_text(
        json.dumps(make_manifest(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    b = Builder()
    _register_bronze_age(b)
    _register_iron_archaic(b)
    _register_classical(b)
    _register_early_medieval(b)
    _register_high_late_medieval(b)
    _register_early_modern(b)
    _register_long_19th(b)
    _register_world_wars(b)
    _register_anecdotes(b)
    write_dataset(b)
    print(
        f"[bootstrap_european_dataset] {len(b.polities)} polities, "
        f"{len(b.rulers)} rulers, {len(b.capitals)} capital events, "
        f"{len(b.events)} events, {len(b.anecdotes)} anecdotes, "
        f"{len(b.contexts)} contexts, "
        f"{len(b.strategic)} strategic locations, "
        f"{len(b.territories)} territory overrides (skipped write if 0), "
        f"{len(b.issues)} issues → input/vEuropean/"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
