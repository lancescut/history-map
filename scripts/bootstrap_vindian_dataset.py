#!/usr/bin/env python3
"""Create reusable v03-compatible templates and the initial vIndian dataset."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from generate_world_history_yearly import MASTER_FIELDS, YEARLY_FIELDS


ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = ROOT / "input"
TEMPLATE_DIR = INPUT_ROOT / "templates"
DATASET_DIR = INPUT_ROOT / "vIndian"

RULERS_MASTER_FIELDS = [
    "ruler_id",
    "polity_id",
    "polity_name",
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
    "merged_from_v02_rows",
]

CAPITAL_FIELDS = [
    "capital_event_id",
    "polity_id",
    "capital_name_historical",
    "capital_name_modern",
    "valid_from_year",
    "valid_to_year",
    "longitude",
    "latitude",
    "is_primary",
    "event_type",
    "location_precision",
    "source_titles",
    "source_urls",
    "source_raw",
    "confidence_score",
    "confidence_note",
]

EVENT_FIELDS = [
    "event_id",
    "year",
    "sort_order",
    "date_label",
    "date_precision",
    "coverage_role",
    "coverage_start_year",
    "coverage_end_year",
    "coverage_group_id",
    "item_kind",
    "event_type",
    "title",
    "description",
    "significance",
    "primary_education_stage",
    "education_stage_tags",
    "curriculum_basis",
    "importance_level",
    "display_priority",
    "related_polity_ids",
    "related_people",
    "location_name",
    "longitude",
    "latitude",
    "location_historical_name",
    "location_modern_name",
    "location_modern_admin_id",
    "location_precision",
    "location_confidence_score",
    "location_source_titles",
    "location_source_urls",
    "location_note",
    "source_titles",
    "source_urls",
    "source_type",
    "confidence_score",
    "confidence_note",
    "fact_review_status",
    "review_note",
]

ANECDOTE_FIELDS = [
    "anecdote_id",
    "dynasty_name",
    "macro_period",
    "year",
    "sort_order",
    "date_label",
    "date_precision",
    "coverage_start_year",
    "coverage_end_year",
    "anecdote_type",
    "title",
    "phrase",
    "short_description",
    "story_text",
    "source_title",
    "source_section",
    "source_url",
    "source_type",
    "source_note",
    "related_polity_ids",
    "related_people",
    "location_historical_name",
    "location_modern_name",
    "longitude",
    "latitude",
    "location_precision",
    "primary_education_stage",
    "education_stage_tags",
    "display_priority",
    "review_status",
    "review_note",
]

MYTH_FIELDS = [
    "myth_id",
    "tradition_name",
    "tradition_type",
    "mythic_cycle",
    "title",
    "variant_title",
    "relative_sequence",
    "traditional_year",
    "year",
    "year_label",
    "date_precision",
    "coverage_start_year",
    "coverage_end_year",
    "calendar_note",
    "geographic_scope",
    "location_name",
    "longitude",
    "latitude",
    "location_precision",
    "related_historical_polity_ids",
    "related_people_or_deities",
    "related_texts",
    "summary",
    "cultural_significance",
    "historicity_status",
    "historical_boundary_note",
    "source_titles",
    "source_urls",
    "source_type",
    "confidence_score",
    "confidence_note",
    "review_status",
    "review_note",
]

STRATEGIC_FIELDS = [
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

TERRITORY_FIELDS = [
    "polity_id",
    "polity_name",
    "admin_ids",
    "valid_from_year",
    "valid_to_year",
    "match_source",
    "confidence_score",
    "note",
    "source_titles",
    "source_raw",
]

ISSUE_FIELDS = [
    "issue_id",
    "issue_type",
    "entity_type",
    "polity_id",
    "polity_name",
    "field_name",
    "selected_value",
    "alternative_values",
    "source_titles",
    "source_urls",
    "note",
    "action_in_v03",
]

SOURCE_FIELDS = [
    "source_id",
    "topic",
    "source_title",
    "source_url",
    "source_type",
    "credibility_tier",
    "covers_fields",
    "notes",
]

VALIDATION_FIELDS = ["check_name", "status", "checked_count", "issue_count", "details"]

TEMPLATE_FILES = {
    "polities_master": "world_history_polities_master_template.csv",
    "rulers_master": "world_history_rulers_master_template.csv",
    "polities_yearly": "world_history_polities_yearly_template.csv",
    "capital_events": "capital_events_template.csv",
    "historical_events": "historical_events_template.csv",
    "historical_anecdotes": "historical_anecdotes_template.csv",
    "mythological_timeline": "mythological_timeline_template.csv",
    "strategic_locations": "strategic_locations_template.csv",
    "territory_overrides": "territory_overrides_template.csv",
    "issues": "unresolved_or_disputed_template.csv",
    "sources": "sources_template.csv",
    "validation_report": "validation_report_template.csv",
}

DATASET_FILES = {
    "polities_master": "indian_history_polities_master_vIndian.csv",
    "rulers_master": "indian_history_rulers_master_vIndian.csv",
    "polities_yearly": "indian_history_polities_yearly_vIndian.csv",
    "capital_events": "capital_events_vIndian.csv",
    "historical_events": "historical_events_vIndian.csv",
    "historical_anecdotes": "historical_anecdotes_vIndian.csv",
    "mythological_timeline": "mythological_timeline_vIndian.csv",
    "strategic_locations": "strategic_locations_vIndian.csv",
    "territory_overrides": "territory_overrides_vIndian.csv",
    "issues": "indian_history_unresolved_or_disputed_vIndian.csv",
    "sources": "indian_history_sources_vIndian.csv",
    "validation_report": "indian_history_validation_report_vIndian.csv",
}

HEADER_BY_KEY = {
    "polities_master": MASTER_FIELDS,
    "rulers_master": RULERS_MASTER_FIELDS,
    "polities_yearly": YEARLY_FIELDS,
    "capital_events": CAPITAL_FIELDS,
    "historical_events": EVENT_FIELDS,
    "historical_anecdotes": ANECDOTE_FIELDS,
    "mythological_timeline": MYTH_FIELDS,
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


def strip_tags(raw: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", raw)).replace("\xa0", " ")


def year_from_text(raw: str) -> int | None:
    text = strip_tags(raw).replace("*", "")
    match = re.search(r"(?<!\d)(\d{3,4})(?!\d)", text)
    if not match:
        return None
    return int(match.group(1))


def clean_name(raw: str) -> str:
    value = re.sub(r"\s*\(b\..*$", "", raw)
    value = re.sub(r"\s*\(s\.a\.\).*$", "", value)
    value = re.sub(r"\s*\(.*?regent.*?\).*$", "", value, flags=re.I)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" .;")


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
    SourceRef("source_ind_0001", "historical_atlas", "Digital South Asia Library: A Historical Atlas of South Asia", "https://dsal.uchicago.edu/reference/schwartzberg/bootstrap_index.html", "historical_atlas", "A", "periodization|geography|polity_context", "Schwartzberg atlas scans and map commentary for South Asian historical geography."),
    SourceRef("source_ind_0002", "gazetteer", "Imperial Gazetteer of India", "https://dsal.uchicago.edu/reference/gazetteer/index.html", "colonial_gazetteer", "B", "princely_states|geography|capital_context", "Colonial gazetteer; strong for administrative geography, read with colonial-source caveats."),
    SourceRef("source_ind_0003", "gazetteer_atlas", "Imperial Gazetteer Atlas of India, 1931", "https://dsal.uchicago.edu/reference/gaz_atlas_1931/", "historical_atlas", "B", "territory_context|colonial_geography", "Map reference for late-colonial administrative and princely-state geography."),
    SourceRef("source_ind_0004", "textbook", "NCERT Themes in Indian History, Part I", "https://ncert.nic.in/textbook/pdf/lehs101.pdf", "education_source", "A", "ancient_history|events|periodization", "Indian national educational history text for ancient and early historical periods."),
    SourceRef("source_ind_0005", "textbook", "NCERT Themes in Indian History, Part II", "https://ncert.nic.in/textbook/pdf/lehs201.pdf", "education_source", "A", "medieval_history|events|periodization", "Indian national educational history text for medieval periods."),
    SourceRef("source_ind_0006", "textbook", "NCERT Themes in Indian History, Part III", "https://ncert.nic.in/textbook/pdf/lehs301.pdf", "education_source", "A", "modern_history|events|periodization", "Indian national educational history text for modern periods."),
    SourceRef("source_ind_0007", "archaeology", "UNESCO World Heritage Centre: Dholavira, a Harappan City", "https://whc.unesco.org/en/list/1645", "heritage_record", "A", "harappan_sites|coordinates|chronology", "UNESCO record for one of the major Harappan urban sites."),
    SourceRef("source_ind_0008", "official_history", "Know India: Profile and History", "https://knowindia.india.gov.in/profile/", "official_overview", "A", "modern_india|political_context", "Government of India overview; use with more detailed sources for exact chronology."),
    SourceRef("source_ind_0009", "overview", "Encyclopaedia Britannica: India", "https://www.britannica.com/place/India", "encyclopedia", "B", "overview|periodization|events", "High-level cross-period overview."),
    SourceRef("source_ind_0010", "ancient_empire", "Encyclopaedia Britannica: Mauryan Empire", "https://www.britannica.com/place/Mauryan-Empire", "encyclopedia", "B", "polity_dates|rulers|events", "Secondary reference for Mauryan chronology."),
    SourceRef("source_ind_0011", "ancient_empire", "Encyclopaedia Britannica: Gupta dynasty", "https://www.britannica.com/topic/Gupta-dynasty", "encyclopedia", "B", "polity_dates|rulers|events", "Secondary reference for Gupta chronology."),
    SourceRef("source_ind_0012", "medieval_polity", "Encyclopaedia Britannica: Delhi Sultanate", "https://www.britannica.com/place/Delhi-sultanate", "encyclopedia", "B", "polity_dates|rulers|events", "Secondary reference for Delhi Sultanate chronology."),
    SourceRef("source_ind_0013", "early_modern_polity", "Encyclopaedia Britannica: Mughal dynasty", "https://www.britannica.com/topic/Mughal-dynasty", "encyclopedia", "B", "polity_dates|rulers|events", "Secondary reference for Mughal chronology."),
    SourceRef("source_ind_0014", "colonial_polity", "Encyclopaedia Britannica: British Raj", "https://www.britannica.com/event/British-raj", "encyclopedia", "B", "colonial_period|events", "Secondary reference for Crown rule in India."),
    SourceRef("source_ind_0015", "colonial_polity", "Encyclopaedia Britannica: Princely state", "https://www.britannica.com/topic/princely-state-colonial-India", "encyclopedia", "B", "princely_states|political_status", "Context for indirect rule and princely-state status."),
    SourceRef("source_ind_0016", "official_law", "India Code: States Reorganisation Act, 1956", "https://www.indiacode.nic.in/handle/123456789/1680?view_type=search", "official_law", "A", "post_1947_events|territorial_reorganization", "Official legal reference for linguistic state reorganization."),
    SourceRef("source_ind_0017", "diplomatic_history", "Office of the Historian: South Asia Crisis, 1971", "https://history.state.gov/historicaldocuments/frus1969-76v11/d1", "official_archive", "A", "1971_war|bangladesh|diplomacy", "US official diplomatic source for the 1971 crisis."),
    SourceRef("source_ind_0018", "primary_law", "The Indian Independence Act 1947", "https://www.legislation.gov.uk/ukpga/1947/30/pdfs/ukpga_19470030_en.pdf", "official_law", "A", "partition|dominion_status", "Primary statute for partition and the two dominions."),
    SourceRef("source_ind_0019", "primary_law", "Legislative Department of India: Constitution of India", "https://legislative.gov.in/constitution-of-india/", "official_law", "A", "republic|constitution|post_1947", "Official Constitution text portal."),
    SourceRef("source_ind_0020", "chronology", "Rulers.org: Indian states before 1947 A-J", "https://www.rulers.org/indstat1.html", "chronology_database", "C", "princely_states|ruler_dates", "Secondary chronology database; use as a structured index and corroborate important states."),
    SourceRef("source_ind_0021", "chronology", "Rulers.org: Indian states before 1947 K-W", "https://www.rulers.org/indstat2.html", "chronology_database", "C", "princely_states|ruler_dates", "Secondary chronology database; use as a structured index and corroborate important states."),
    SourceRef("source_ind_0022", "archaeology", "Archaeological Survey of India", "https://asi.nic.in/", "official_archaeology", "A", "archaeological_sites|heritage_context", "Official Indian archaeology body; used for site-level cross-checking."),
    SourceRef("source_ind_0023", "heritage", "UNESCO World Heritage Centre: Archaeological Site of Nalanda Mahavihara", "https://whc.unesco.org/en/list/1502", "heritage_record", "A", "strategic_locations|education_sites", "UNESCO record for Nalanda."),
    SourceRef("source_ind_0024", "heritage", "UNESCO World Heritage Centre: Qutb Minar and its Monuments, Delhi", "https://whc.unesco.org/en/list/233", "heritage_record", "A", "strategic_locations|delhi_sultanate", "UNESCO record for Delhi Sultanate monumental geography."),
    SourceRef("source_ind_0025", "heritage", "UNESCO World Heritage Centre: Group of Monuments at Hampi", "https://whc.unesco.org/en/list/241", "heritage_record", "A", "strategic_locations|vijayanagara", "UNESCO record for Vijayanagara/Hampi."),
    SourceRef("source_ind_0026", "heritage", "UNESCO World Heritage Centre: Fatehpur Sikri", "https://whc.unesco.org/en/list/255", "heritage_record", "A", "strategic_locations|mughal_capital", "UNESCO record for Akbar's capital."),
    SourceRef("source_ind_0027", "heritage", "UNESCO World Heritage Centre: Taj Mahal", "https://whc.unesco.org/en/list/252", "heritage_record", "A", "strategic_locations|mughal_context", "UNESCO record for Agra Mughal monumental geography."),
    SourceRef("source_ind_0028", "heritage", "UNESCO World Heritage Centre: Red Fort Complex", "https://whc.unesco.org/en/list/231", "heritage_record", "A", "strategic_locations|mughal_delhi|modern_india", "UNESCO record for Red Fort."),
    SourceRef("source_ind_0029", "heritage", "UNESCO World Heritage Centre: Mahabodhi Temple Complex at Bodh Gaya", "https://whc.unesco.org/en/list/1056", "heritage_record", "A", "strategic_locations|buddhist_history", "UNESCO record for Bodh Gaya."),
    SourceRef("source_ind_0030", "overview", "Encyclopaedia Britannica: Indus civilization", "https://www.britannica.com/topic/Indus-civilization", "encyclopedia", "B", "harappan_chronology|sites", "Secondary reference for Indus civilization."),
    SourceRef("source_ind_0031", "overview", "Encyclopaedia Britannica: Vedic religion", "https://www.britannica.com/topic/Vedic-religion", "encyclopedia", "B", "vedic_period|context", "Context for Vedic cultural chronology."),
    SourceRef("source_ind_0032", "overview", "Encyclopaedia Britannica: Magadha", "https://www.britannica.com/place/Magadha", "encyclopedia", "B", "mahajanapada|magadha", "Secondary reference for Magadha."),
    SourceRef("source_ind_0033", "overview", "Encyclopaedia Britannica: Ashoka", "https://www.britannica.com/biography/Ashoka", "encyclopedia", "B", "mauryan_rulers|events", "Secondary reference for Ashoka."),
    SourceRef("source_ind_0034", "overview", "Encyclopaedia Britannica: Kushan dynasty", "https://www.britannica.com/topic/Kushan-dynasty", "encyclopedia", "B", "kushan|rulers", "Secondary reference for Kushan chronology."),
    SourceRef("source_ind_0035", "overview", "Encyclopaedia Britannica: Chola dynasty", "https://www.britannica.com/topic/Chola-dynasty", "encyclopedia", "B", "south_india|chola", "Secondary reference for Chola chronology."),
    SourceRef("source_ind_0036", "overview", "Encyclopaedia Britannica: Vijayanagar", "https://www.britannica.com/place/Vijayanagar-empire", "encyclopedia", "B", "vijayanagara|events", "Secondary reference for Vijayanagara."),
    SourceRef("source_ind_0037", "overview", "Encyclopaedia Britannica: Maratha confederacy", "https://www.britannica.com/topic/Maratha-confederacy", "encyclopedia", "B", "maratha|events", "Secondary reference for Maratha history."),
    SourceRef("source_ind_0038", "overview", "Encyclopaedia Britannica: Sikh Wars", "https://www.britannica.com/event/Sikh-Wars", "encyclopedia", "B", "sikh_empire|colonial_wars", "Secondary reference for Sikh-British conflict."),
    SourceRef("source_ind_0039", "overview", "Encyclopaedia Britannica: Indian Mutiny", "https://www.britannica.com/event/Indian-Mutiny", "encyclopedia", "B", "1857|colonial_events", "Secondary reference for the 1857 uprising."),
    SourceRef("source_ind_0040", "overview", "Encyclopaedia Britannica: Indian National Congress", "https://www.britannica.com/topic/Indian-National-Congress", "encyclopedia", "B", "national_movement|events", "Secondary reference for the nationalist movement."),
    SourceRef("source_ind_0041", "overview", "Encyclopaedia Britannica: Partition of India", "https://www.britannica.com/event/Partition-of-India", "encyclopedia", "B", "partition|migration|violence", "Secondary reference for partition."),
    SourceRef("source_ind_0042", "overview", "Encyclopaedia Britannica: Bangladesh Liberation War", "https://www.britannica.com/event/Bangladesh-Liberation-War", "encyclopedia", "B", "1971_war|bangladesh", "Secondary reference for Bangladesh Liberation War."),
    SourceRef("source_ind_0043", "overview", "Encyclopaedia Britannica: Sikkim", "https://www.britannica.com/place/Sikkim", "encyclopedia", "B", "sikkim|post_1947_integration", "Secondary reference for Sikkim's incorporation."),
    SourceRef("source_ind_0044", "overview", "Encyclopaedia Britannica: Goa", "https://www.britannica.com/place/Goa-state-India", "encyclopedia", "B", "goa|portuguese_india", "Secondary reference for Goa."),
    SourceRef("source_ind_0045", "overview", "Encyclopaedia Britannica: Kashmir region", "https://www.britannica.com/place/Kashmir-region-Indian-subcontinent", "encyclopedia", "B", "kashmir|disputed_territory", "Secondary reference for Kashmir."),
    SourceRef("source_ind_0046", "overview", "Encyclopaedia Britannica: East India Company", "https://www.britannica.com/topic/East-India-Company", "encyclopedia", "B", "company_rule|colonial_events", "Secondary reference for Company rule."),
    SourceRef("source_ind_0047", "overview", "Encyclopaedia Britannica: Mysore Wars", "https://www.britannica.com/event/Mysore-Wars", "encyclopedia", "B", "mysore|colonial_wars", "Secondary reference for Mysore Wars."),
    SourceRef("source_ind_0048", "official_law", "Constitution (Thirty-sixth Amendment) Act, 1975", "https://www.indiacode.nic.in/handle/123456789/1537", "official_law", "A", "sikkim|post_1947_integration", "Official legal reference for Sikkim's statehood."),
    SourceRef("source_ind_0049", "official_law", "Goa, Daman and Diu Reorganisation Act, 1987", "https://www.indiacode.nic.in/handle/123456789/1904", "official_law", "A", "goa|statehood", "Official legal reference for Goa statehood."),
    SourceRef("source_ind_0050", "official_law", "Punjab Reorganisation Act, 1966", "https://www.indiacode.nic.in/handle/123456789/1533", "official_law", "A", "post_1947_state_reorganization", "Official legal reference for Punjab/Haryana reorganization."),
    SourceRef("source_ind_0051", "epic_text", "Encyclopaedia Britannica: Mahabharata", "https://www.britannica.com/topic/Mahabharata", "encyclopedia", "B", "mythological_timeline|epic_tradition", "Secondary reference for Mahabharata as epic tradition and debated historicity."),
    SourceRef("source_ind_0052", "epic_text", "Encyclopaedia Britannica: Ramayana", "https://www.britannica.com/topic/Ramayana-Indian-epic", "encyclopedia", "B", "mythological_timeline|epic_tradition", "Secondary reference for Ramayana composition and cultural influence."),
    SourceRef("source_ind_0053", "regional_chronicle", "Banglapedia: Rajmala", "https://en.banglapedia.org/index.php/Rajmala", "encyclopedia", "B", "mythological_timeline|tripura|royal_chronicle", "Reference for Rajmala compilation and lack of evidence for early Tripura king lists."),
    SourceRef("source_ind_0054", "regional_history", "Banglapedia: Tripura", "https://en.banglapedia.org/index.php/Tripura", "encyclopedia", "B", "tripura|manikya|political_context", "Reference for Tripura and Manikya princely-state context."),
    SourceRef("source_ind_0055", "ancient_dynasty", "Encyclopaedia Britannica: Satavahana dynasty", "https://www.britannica.com/topic/Satavahana-dynasty", "encyclopedia", "B", "satavahana|puranic_chronology", "Secondary reference distinguishing Puranic dating from late first century BCE ascendancy."),
    SourceRef("source_ind_0056", "regional_history", "District Chamba Government: History", "https://hpchamba.nic.in/history/", "official_history", "A", "chamba|dynastic_origin_legend", "Official district history noting Maru as legendary hero and Kalpagrama as mythical place."),
    SourceRef("source_ind_0057", "regional_history", "Encyclopaedia Britannica: Chamba", "https://www.britannica.com/place/Chamba", "encyclopedia", "B", "chamba|princely_state", "Secondary reference for Chamba state founded in the sixth century CE."),
    SourceRef("source_ind_0058", "regional_history", "Encyclopaedia Britannica: Rajasthan History", "https://www.britannica.com/place/Rajasthan/History", "encyclopedia", "B", "mewar|guhilla|rajput_context", "Secondary reference for Rajasthan history and Guhila control around Mewar."),
    SourceRef("source_ind_0059", "regional_history", "Treccani: Mewar", "https://www.treccani.it/enciclopedia/mewar_%28Dizionario-di-Storia%29/", "encyclopedia", "B", "mewar|bappa_rawal|chittor", "Secondary reference using 734 for Bappa Rawal founding Chitor-centered Mewar."),
    SourceRef("source_ind_0060", "regional_history", "Encyclopaedia Britannica: Guhilla", "https://www.britannica.com/topic/Guhilla", "encyclopedia", "B", "mewar|guhilla|rajput_context", "Secondary reference linking the Guhilla Rajput dynasty to Mewar and Chitor."),
]

SOURCE_BY_ID = {source.source_id: source for source in SOURCE_REFS}


def source_titles(ids: list[str]) -> str:
    return "|".join(SOURCE_BY_ID[source_id].title for source_id in ids if source_id in SOURCE_BY_ID)


def source_urls(ids: list[str]) -> str:
    return "|".join(SOURCE_BY_ID[source_id].url for source_id in ids if source_id in SOURCE_BY_ID)


COORDS = {
    "Mehrgarh": (67.6167, 29.3833),
    "Harappa": (72.8667, 30.6333),
    "Mohenjo-daro": (68.1389, 27.3294),
    "Dholavira": (70.2142, 23.8876),
    "Lothal": (72.2496, 22.5222),
    "Rakhigarhi": (76.1137, 29.2875),
    "Taxila": (72.8397, 33.7463),
    "Rajgir": (85.4210, 25.0277),
    "Pataliputra": (85.1376, 25.5941),
    "Vaishali": (85.1300, 25.9800),
    "Bodh Gaya": (84.9913, 24.6951),
    "Sarnath": (83.0220, 25.3811),
    "Ujjain": (75.7849, 23.1765),
    "Mathura": (77.6737, 27.4924),
    "Kannauj": (79.9180, 27.0514),
    "Nalanda": (85.4448, 25.1357),
    "Kanchipuram": (79.7036, 12.8342),
    "Badami": (75.6768, 15.9149),
    "Manyakheta": (77.1637, 17.1745),
    "Thanjavur": (79.1378, 10.7867),
    "Gangaikonda Cholapuram": (79.4462, 11.2060),
    "Delhi": (77.2090, 28.6139),
    "Hampi": (76.4600, 15.3350),
    "Gulbarga": (76.8333, 17.3333),
    "Bidar": (77.5300, 17.9104),
    "Bijapur": (75.7100, 16.8302),
    "Golconda": (78.4011, 17.3833),
    "Agra": (78.0081, 27.1767),
    "Fatehpur Sikri": (77.6679, 27.0945),
    "Pune": (73.8567, 18.5204),
    "Lahore": (74.3587, 31.5204),
    "Srirangapatna": (76.6930, 12.4226),
    "Mysore": (76.6394, 12.2958),
    "Kolkata": (88.3639, 22.5726),
    "New Delhi": (77.2090, 28.6139),
    "Hyderabad": (78.4867, 17.3850),
    "Junagadh": (70.4579, 21.5222),
    "Srinagar": (74.7973, 34.0837),
    "Gangtok": (88.6138, 27.3314),
    "Goa": (74.1240, 15.2993),
    "Puducherry": (79.8083, 11.9416),
    "Bhopal": (77.4126, 23.2599),
    "Jaipur": (75.7873, 26.9124),
    "Jodhpur": (73.0243, 26.2389),
    "Udaipur": (73.7125, 24.5854),
    "Gwalior": (78.1828, 26.2183),
    "Baroda": (73.1812, 22.3072),
    "Travancore": (76.9366, 8.5241),
    "Kochi": (76.2673, 9.9312),
    "Amritsar": (74.8723, 31.6340),
    "Panipat": (76.9635, 29.3909),
    "Tarain": (76.8170, 29.9695),
    "Kurukshetra": (76.8170, 29.9695),
    "Chittorgarh": (74.6269, 24.8887),
    "Ayodhya": (82.1998, 26.7922),
    "Agartala": (91.2868, 23.8315),
    "Bharmour": (76.5419, 32.4425),
    "Pratishthana": (75.3860, 19.4750),
    "Haldighati": (73.6952, 24.8871),
    "Plassey": (88.2510, 23.7810),
    "Buxar": (83.9808, 25.5647),
    "Lucknow": (80.9462, 26.8467),
    "Jhansi": (78.5676, 25.4484),
    "Meerut": (77.7064, 28.9845),
    "Dandi": (72.8043, 20.8870),
    "Dhaka": (90.4125, 23.8103),
    "Tawang": (91.8662, 27.5861),
    "Aksai Chin": (79.0000, 35.0000),
}


def make_manifest() -> dict:
    return {
        "dataset_id": "vIndian",
        "dataset_name": "古印度与印度史 vIndian",
        "schema_family": "v03-compatible-world-history",
        "created_by": "scripts/bootstrap_vindian_dataset.py",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "year_min": -3300,
        "year_max": 1990,
        "year_zero_policy": "no_year_zero",
        "space_scope": "Historical South Asia through 1947; Republic of India focus after 1947 with directly related partition/border events.",
        "files": DATASET_FILES,
        "template_files": TEMPLATE_FILES,
        "field_notes": {
            "macro_period": "Large chronological period, not China-specific.",
            "dynasty_name": "Dynasty, ruling house, civilization, colonial phase, or republic/administrative phase label.",
            "modern_admin_units_raw": "Modern country and first-level administrative approximation; not a claim of exact historical borders.",
            "ruler_temple_name": "East Asian style field; leave empty unless a culture has an equivalent formal name.",
            "v02_*": "Retained only for v03 compatibility; empty for non-v02 datasets.",
            "mythological_timeline": "Separate playable layer for epic, Puranic, dynastic-origin, and regional royal-chronicle traditions. These rows must not generate historical polity yearly rows.",
        },
    }


def write_templates() -> None:
    for key, filename in TEMPLATE_FILES.items():
        write_csv(TEMPLATE_DIR / filename, HEADER_BY_KEY[key], [])

    (TEMPLATE_DIR / "dataset_manifest_template.json").write_text(
        json.dumps(make_manifest(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (TEMPLATE_DIR / "README.md").write_text(
        """# v03-compatible world history templates

These templates preserve the v03 CSV column order while making the field
semantics reusable for India, Egypt, Babylon, Europe, and later datasets.

Rules:

- Keep UTF-8 with BOM for CSV files, comma delimiters, and `|` for multi-value fields.
- BCE years are negative integers and year 0 is forbidden.
- `modern_admin_units_raw` is a modern geographic approximation, not a historical boundary claim.
- East Asian ruler-name columns may stay empty when they do not apply.
- Uncertain chronologies, legendary king lists, and territorial disputes must be recorded in the issues table.
- Epic, Puranic, dynastic-origin, and other mythic traditions belong in `mythological_timeline_template.csv`, not in historical polity yearly rows.
- Dataset-specific file names are declared in `dataset_manifest_*.json`; validators compare each dataset file to these templates.
""",
        encoding="utf-8",
    )


class Builder:
    def __init__(self) -> None:
        self.polities: list[dict[str, str]] = []
        self.rulers: list[dict[str, str]] = []
        self.capitals: list[dict[str, str]] = []
        self.events: list[dict[str, str]] = []
        self.anecdotes: list[dict[str, str]] = []
        self.myths: list[dict[str, str]] = []
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
        self._myth_seq = 1
        self._strategic_seq = 1
        self._issue_seq = 1

    def next_polity_id(self) -> str:
        value = f"polity_ind_{self._polity_seq:04d}"
        self._polity_seq += 1
        return value

    def add_polity(
        self,
        key: str,
        name: str,
        macro: str,
        dynasty: str,
        ptype: str,
        start: int,
        end: int,
        *,
        aliases: str = "",
        display: str = "",
        disambiguation: str = "",
        date_precision: str = "year",
        geography: str = "",
        modern_admin: str = "",
        capital: str = "",
        family: str = "",
        group: str = "",
        founder: str = "",
        last_ruler: str = "",
        successor: str = "",
        source_ids: list[str] | None = None,
        source_raw: str = "",
        confidence: int = 75,
        note: str = "",
        review_status: str = "verified",
        risk_flags: str = "",
    ) -> str:
        source_ids = source_ids or ["source_ind_0001", "source_ind_0009"]
        pid = self.next_polity_id()
        row = {
            "polity_id": pid,
            "macro_period": macro,
            "dynasty_name": dynasty,
            "polity_name": name,
            "polity_aliases": aliases,
            "polity_display_name": display or name,
            "polity_name_disambiguation": disambiguation,
            "polity_name_review_status": review_status,
            "polity_name_risk_flags": risk_flags,
            "polity_type": ptype,
            "polity_start_year": str(start),
            "polity_start_label": year_label(start),
            "polity_end_year": str(end),
            "polity_end_label": year_label(end),
            "polity_date_raw": f"{year_label(start)}-{year_label(end)}",
            "polity_date_precision": date_precision,
            "historical_geography_raw": geography,
            "modern_admin_units_raw": modern_admin,
            "capital_historical": capital,
            "capital_modern": capital,
            "ruling_family_or_clan": family,
            "ethnicity_or_group": group,
            "founder": founder,
            "last_ruler": last_ruler,
            "destroyed_by_or_successor": successor,
            "polity_source_titles": source_titles(source_ids),
            "polity_source_urls": source_urls(source_ids),
            "polity_source_raw": source_raw,
            "confidence_score": str(confidence),
            "confidence_note": note,
            "calendar_system_note": "BCE years are negative; no year 0. Dates before early historic inscriptions are approximate.",
            "v02_row_count": "",
            "v02_actual_min_year": "",
            "v02_actual_max_year": "",
            "v02_actual_years": "",
            "merged_from_v02_contexts": "",
        }
        self.polities.append(row)
        self.polity_key_to_id[key] = pid
        self.polity_names.add(name.lower())
        return pid

    def add_ruler(
        self,
        polity_key: str,
        name: str,
        title: str,
        start: int,
        end: int,
        *,
        personal: str = "",
        source_ids: list[str] | None = None,
        section: str = "",
        confidence: int = 75,
        note: str = "",
    ) -> str:
        pid = self.polity_key_to_id[polity_key]
        polity_name = next(row["polity_name"] for row in self.polities if row["polity_id"] == pid)
        rid = f"ruler_ind_{self._ruler_seq:05d}"
        self._ruler_seq += 1
        source_ids = source_ids or ["source_ind_0009"]
        self.rulers.append(
            {
                "ruler_id": rid,
                "polity_id": pid,
                "polity_name": polity_name,
                "ruler_name": name,
                "ruler_title": title,
                "ruler_temple_name": "",
                "ruler_posthumous_name": "",
                "ruler_personal_name": personal,
                "ruler_reign_start_year": str(start),
                "ruler_reign_start_label": year_label(start),
                "ruler_reign_end_year": str(end),
                "ruler_reign_end_label": year_label(end),
                "ruler_reign_raw": f"{year_label(start)}-{year_label(end)}",
                "ruler_reign_precision": "year",
                "era_names": "",
                "ruler_source_title": source_titles(source_ids),
                "ruler_source_url": source_urls(source_ids),
                "ruler_source_section": section,
                "ruler_confidence_score": str(confidence),
                "ruler_confidence_note": note,
                "merged_from_v02_rows": "",
            }
        )
        return rid

    def add_event(
        self,
        year: int,
        title: str,
        description: str,
        significance: str,
        *,
        event_type: str,
        polity_keys: list[str] | None = None,
        people: str = "",
        location: str = "",
        source_ids: list[str] | None = None,
        date_precision: str = "year",
        item_kind: str = "core_event",
        coverage_role: str = "exact_year_event",
        importance: int = 2,
        priority: int = 100,
        confidence: int = 80,
        note: str = "",
    ) -> str:
        eid = f"event_ind_{self._event_seq:04d}"
        self._event_seq += 1
        source_ids = source_ids or ["source_ind_0009"]
        pids = "|".join(self.polity_key_to_id[key] for key in polity_keys or [] if key in self.polity_key_to_id)
        lon, lat = COORDS.get(location, ("", ""))
        self.events.append(
            {
                "event_id": eid,
                "year": str(year),
                "sort_order": str(self._event_seq),
                "date_label": year_label(year),
                "date_precision": date_precision,
                "coverage_role": coverage_role,
                "coverage_start_year": str(year),
                "coverage_end_year": str(year),
                "coverage_group_id": "",
                "item_kind": item_kind,
                "event_type": event_type,
                "title": title,
                "description": description,
                "significance": significance,
                "primary_education_stage": "高中",
                "education_stage_tags": "世界史|南亚史",
                "curriculum_basis": "world_history_dataset_vIndian",
                "importance_level": str(importance),
                "display_priority": str(priority),
                "related_polity_ids": pids,
                "related_people": people,
                "location_name": location,
                "longitude": str(lon),
                "latitude": str(lat),
                "location_historical_name": location,
                "location_modern_name": location,
                "location_modern_admin_id": "",
                "location_precision": "city" if location and lon else "",
                "location_confidence_score": "80" if location and lon else "",
                "location_source_titles": source_titles(["source_ind_0001", "source_ind_0022"]) if location and lon else "",
                "location_source_urls": source_urls(["source_ind_0001", "source_ind_0022"]) if location and lon else "",
                "location_note": "Coordinates are city/site approximations for map placement." if location and lon else "",
                "source_titles": source_titles(source_ids),
                "source_urls": source_urls(source_ids),
                "source_type": "synthesized_secondary",
                "confidence_score": str(confidence),
                "confidence_note": note,
                "fact_review_status": "verified" if confidence >= 75 else "candidate",
                "review_note": "",
            }
        )
        return eid

    def add_capital(self, polity_key: str, capital: str, start: int, end: int, source_ids: list[str], confidence: int = 76) -> None:
        if capital not in COORDS or polity_key not in self.polity_key_to_id:
            return
        lon, lat = COORDS[capital]
        pid = self.polity_key_to_id[polity_key]
        self.capitals.append(
            {
                "capital_event_id": f"capital_ind_{self._capital_seq:04d}",
                "polity_id": pid,
                "capital_name_historical": capital,
                "capital_name_modern": capital,
                "valid_from_year": str(start),
                "valid_to_year": str(end),
                "longitude": str(lon),
                "latitude": str(lat),
                "is_primary": "true",
                "event_type": "initial_capital",
                "location_precision": "city",
                "source_titles": source_titles(source_ids),
                "source_urls": source_urls(source_ids),
                "source_raw": "Capital field normalized from vIndian polity source row.",
                "confidence_score": str(confidence),
                "confidence_note": "City-level approximation for historical capital marker.",
            }
        )
        self._capital_seq += 1

    def add_myth(
        self,
        tradition_name: str,
        tradition_type: str,
        mythic_cycle: str,
        title: str,
        *,
        year: int,
        coverage_start: int,
        coverage_end: int,
        historicity_status: str,
        summary: str,
        cultural_significance: str,
        historical_boundary_note: str,
        source_ids: list[str],
        variant_title: str = "",
        relative_sequence: str = "",
        traditional_year: str = "",
        date_precision: str = "approx",
        calendar_note: str = "",
        geographic_scope: str = "",
        location: str = "",
        location_precision: str = "city",
        polity_keys: list[str] | None = None,
        people_or_deities: str = "",
        related_texts: str = "",
        source_type: str = "synthesized_secondary",
        confidence: int = 70,
        note: str = "",
        review_status: str = "verified",
        review_note: str = "",
    ) -> str:
        mid = f"myth_ind_{self._myth_seq:04d}"
        self._myth_seq += 1
        lon, lat = COORDS.get(location, ("", ""))
        related_polities = "|".join(
            self.polity_key_to_id[key] for key in polity_keys or [] if key in self.polity_key_to_id
        )
        self.myths.append(
            {
                "myth_id": mid,
                "tradition_name": tradition_name,
                "tradition_type": tradition_type,
                "mythic_cycle": mythic_cycle,
                "title": title,
                "variant_title": variant_title,
                "relative_sequence": relative_sequence or str(self._myth_seq),
                "traditional_year": traditional_year,
                "year": str(year),
                "year_label": year_label(year),
                "date_precision": date_precision,
                "coverage_start_year": str(coverage_start),
                "coverage_end_year": str(coverage_end),
                "calendar_note": calendar_note,
                "geographic_scope": geographic_scope,
                "location_name": location,
                "longitude": str(lon),
                "latitude": str(lat),
                "location_precision": location_precision if location else "",
                "related_historical_polity_ids": related_polities,
                "related_people_or_deities": people_or_deities,
                "related_texts": related_texts,
                "summary": summary,
                "cultural_significance": cultural_significance,
                "historicity_status": historicity_status,
                "historical_boundary_note": historical_boundary_note,
                "source_titles": source_titles(source_ids),
                "source_urls": source_urls(source_ids),
                "source_type": source_type,
                "confidence_score": str(confidence),
                "confidence_note": note,
                "review_status": review_status,
                "review_note": review_note,
            }
        )
        return mid

    def add_issue(self, issue_type: str, entity_type: str, field: str, selected: str, alternatives: str, note: str, source_ids: list[str], polity_key: str = "") -> None:
        pid = self.polity_key_to_id.get(polity_key, "")
        pname = next((row["polity_name"] for row in self.polities if row["polity_id"] == pid), "")
        self.issues.append(
            {
                "issue_id": f"issue_ind_{self._issue_seq:04d}",
                "issue_type": issue_type,
                "entity_type": entity_type,
                "polity_id": pid,
                "polity_name": pname,
                "field_name": field,
                "selected_value": selected,
                "alternative_values": alternatives,
                "source_titles": source_titles(source_ids),
                "source_urls": source_urls(source_ids),
                "note": note,
                "action_in_v03": "Preserve selected working value and expose uncertainty in confidence_note/review_note.",
            }
        )
        self._issue_seq += 1


def add_core_polities(builder: Builder) -> None:
    p = builder.add_polity
    common = ["source_ind_0001", "source_ind_0004", "source_ind_0009"]
    p("early_harappan", "早期哈拉帕文化", "史前与原史时期", "印度河文明", "archaeological_culture", -3300, -2600, aliases="Early Harappan", date_precision="approx", geography="Indus and Ghaggar-Hakra related urbanizing zones", modern_admin="Pakistan Sindh/Punjab|India Haryana/Rajasthan/Gujarat", capital="", source_ids=["source_ind_0001", "source_ind_0004", "source_ind_0030"], confidence=70, note="Archaeological culture layer, not a centralized polity.")
    p("mature_harappan", "成熟哈拉帕/印度河文明", "史前与原史时期", "印度河文明", "civilization_complex", -2600, -1900, aliases="Mature Harappan|Indus civilization", date_precision="approx", geography="Indus basin and western India urban network", modern_admin="Pakistan Sindh/Punjab/Balochistan|India Gujarat/Rajasthan/Haryana", capital="", source_ids=["source_ind_0001", "source_ind_0004", "source_ind_0007", "source_ind_0030"], confidence=78, note="Urban civilization complex; political unity is not assumed.")
    p("late_harappan", "晚期哈拉帕文化", "史前与原史时期", "印度河文明", "archaeological_culture", -1900, -1300, aliases="Late Harappan", date_precision="approx", geography="Post-urban regional cultures across northwestern South Asia", modern_admin="Pakistan|Northwestern India", source_ids=["source_ind_0001", "source_ind_0004", "source_ind_0030"], confidence=68, note="Represents cultural transition after mature urban phase.")
    p("vedic_horizon", "吠陀文化圈", "吠陀与列国时期", "吠陀时期", "cultural_horizon", -1500, -600, aliases="Vedic period", date_precision="approx", geography="Punjab, Ganga-Yamuna doab and northern India in expanding phases", modern_admin="India Punjab/Haryana/Uttar Pradesh|Pakistan Punjab", source_ids=["source_ind_0001", "source_ind_0004", "source_ind_0031"], confidence=62, note="Cultural horizon; not represented as a single state.")

    mahajanapadas = [
        ("anga", "鸯伽", "Anga", -600, -530, "Bihar/Jharkhand/West Bengal borderlands", "IN-BR|IN-JH|IN-WB", "Champa"),
        ("assaka", "阿湿波/阿萨卡", "Assaka|Asmaka", -600, -300, "Godavari valley", "IN-MH|IN-TG", "Potana"),
        ("avanti", "阿槃提", "Avanti", -600, -400, "Malwa and Narmada region", "IN-MP", "Ujjain"),
        ("chedi", "支提", "Chedi", -600, -300, "Bundelkhand region", "IN-MP|IN-UP", ""),
        ("gandhara", "犍陀罗", "Gandhara", -600, -300, "Peshawar and Taxila region", "PK-KP|PK-PB|AFG", "Taxila"),
        ("kamboja", "剑浮沙", "Kamboja", -600, -300, "Northwestern frontier", "AFG|PAK", ""),
        ("kashi", "迦尸", "Kashi", -600, -490, "Varanasi region", "IN-UP", "Varanasi"),
        ("kosala", "拘萨罗", "Kosala", -600, -460, "Awadh and eastern Uttar Pradesh", "IN-UP", "Ayodhya"),
        ("kuru", "俱卢", "Kuru", -600, -300, "Delhi-Haryana-western Uttar Pradesh", "IN-DL|IN-HR|IN-UP", "Indraprastha"),
        ("magadha_mahajanapada", "摩揭陀列国", "Magadha", -600, -345, "South Bihar", "IN-BR", "Rajgir"),
        ("malla", "末罗", "Malla", -600, -300, "Eastern Uttar Pradesh and Bihar", "IN-UP|IN-BR", "Kushinagar"),
        ("matsya", "摩蹉", "Matsya", -600, -300, "Jaipur-Alwar region", "IN-RJ", "Viratanagara"),
        ("panchala", "般阇罗", "Panchala", -600, -300, "Ganga-Yamuna doab", "IN-UP", ""),
        ("surasena", "苏罗娑那", "Surasena", -600, -300, "Mathura region", "IN-UP", "Mathura"),
        ("vajji", "跋耆联盟", "Vajji|Vrijji|Licchavi confederacy", -600, -468, "North Bihar republican confederacy", "IN-BR", "Vaishali"),
        ("vatsa", "婆蹉", "Vatsa", -600, -300, "Kaushambi/Allahabad region", "IN-UP", "Kaushambi"),
    ]
    for key, name, aliases, start, end, geo, admin, capital in mahajanapadas:
        p(key, name, "吠陀与列国时期", "十六大国", "mahajanapada", start, end, aliases=aliases, date_precision="approx", geography=geo, modern_admin=admin, capital=capital, source_ids=["source_ind_0001", "source_ind_0004", "source_ind_0032"], confidence=66, note="Mahajanapada dates are conventional approximations.")

    core = [
        ("haryanka", "诃黎王朝/哈里扬卡", "Haryanka dynasty", "摩揭陀王国", "dynastic_kingdom", -544, -413, "South Bihar Magadha core", "IN-BR", "Rajgir", "Haryanka", "Bimbisara", "Nagadasaka", "Shishunaga", ["source_ind_0004", "source_ind_0032"], 70),
        ("shishunaga", "希舒那伽王朝", "Shishunaga dynasty", "摩揭陀王国", "dynastic_kingdom", -413, -345, "Magadha and northern India", "IN-BR|IN-UP", "Pataliputra", "Shishunaga", "Shishunaga", "Mahanandin", "Nanda dynasty", ["source_ind_0004", "source_ind_0032"], 70),
        ("nanda", "难陀王朝", "Nanda dynasty", "摩揭陀王国", "dynastic_kingdom", -345, -321, "Magadha-centered north Indian empire", "IN-BR|IN-UP|IN-MP", "Pataliputra", "Nanda", "Mahapadma Nanda", "Dhana Nanda", "Mauryan Empire", ["source_ind_0004", "source_ind_0032"], 73),
        ("maurya", "孔雀帝国", "Mauryan Empire", "孔雀王朝", "imperial_state", -321, -185, "Most of the subcontinent except far south at maximum extent", "India|Pakistan|Bangladesh|Afghanistan parts|Nepal parts", "Pataliputra", "Maurya", "Chandragupta Maurya", "Brihadratha", "Shunga dynasty", ["source_ind_0001", "source_ind_0004", "source_ind_0010", "source_ind_0033"], 82),
        ("shunga", "巽伽王朝", "Shunga dynasty", "后孔雀时期", "dynastic_kingdom", -185, -73, "Middle Ganga basin and central India", "IN-BR|IN-UP|IN-MP", "Pataliputra", "Shunga", "Pushyamitra Shunga", "Devabhuti", "Kanva dynasty", common, 68),
        ("kanva", "甘婆王朝", "Kanva dynasty", "后孔雀时期", "dynastic_kingdom", -73, -28, "Magadha and middle Ganga basin", "IN-BR|IN-UP", "Pataliputra", "Kanva", "Vasudeva Kanva", "Susharman", "Satavahana and regional powers", common, 64),
        ("satavahana", "百乘王朝", "Satavahana dynasty", "后孔雀与早期古典时期", "dynastic_kingdom", -100, 220, "Deccan plateau and Andhra region", "IN-MH|IN-TG|IN-AP|IN-MP", "Pratishthana", "Satavahana", "Simuka", "", "Western Kshatrapas and regional dynasties", ["source_ind_0001", "source_ind_0004", "source_ind_0055"], 72),
        ("indo_greek", "印度-希腊王国", "Indo-Greek Kingdom", "后孔雀与早期古典时期", "regional_kingdom", -180, 10, "Northwestern South Asia and Bactrian frontier", "PK|AFG|IN-PB", "Taxila", "Yavana/Greek houses", "Demetrius I", "Strato II", "Indo-Scythian powers", ["source_ind_0001", "source_ind_0009"], 65),
        ("indo_scythian", "印度-塞种政权", "Indo-Scythians|Saka", "后孔雀与早期古典时期", "regional_kingdom", -100, 395, "Northwestern and western India", "PK|IN-GJ|IN-MP", "", "Saka", "", "", "Western Kshatrapas/Kushan/Gupta", ["source_ind_0001", "source_ind_0009"], 62),
        ("indo_parthian", "印度-帕提亚王国", "Indo-Parthian Kingdom", "后孔雀与早期古典时期", "regional_kingdom", 19, 226, "Gandhara and northwest", "PK|AFG", "Taxila", "Gondopharid", "Gondophares", "", "Kushan and Sasanian-related powers", ["source_ind_0001", "source_ind_0009"], 62),
        ("kushan", "贵霜帝国", "Kushan Empire", "早期古典时期", "imperial_state", 30, 375, "Bactria, Gandhara, Punjab and north India at maximum extent", "AFG|PK|IN-UP|IN-BR", "Peshawar", "Kushan/Yuezhi", "Kujula Kadphises", "", "Kidarites/Gupta/regional powers", ["source_ind_0001", "source_ind_0034"], 74),
        ("western_kshatrapas", "西部总督/西刹陀罗波", "Western Kshatrapas", "早期古典时期", "regional_kingdom", 35, 405, "Western India and Malwa", "IN-GJ|IN-MP|IN-MH", "Ujjain", "Saka Kshatrapa", "", "Rudrasimha III", "Gupta expansion", ["source_ind_0001", "source_ind_0009"], 68),
        ("gupta", "笈多帝国", "Gupta Empire", "古典时期", "imperial_state", 320, 550, "North and central India", "IN-UP|IN-BR|IN-MP|IN-WB|IN-GJ", "Pataliputra", "Gupta", "Chandragupta I", "", "post-Gupta regional powers", ["source_ind_0001", "source_ind_0004", "source_ind_0011"], 82),
        ("vakataka", "伐迦陀迦王朝", "Vakataka dynasty", "古典时期", "regional_kingdom", 250, 500, "Deccan and central India", "IN-MH|IN-MP|IN-TG", "", "Vakataka", "Vindhyashakti", "", "Chalukya and regional powers", common, 67),
        ("vardhana", "戒日王朝/伐弹那", "Vardhana dynasty", "后笈多时期", "regional_empire", 606, 647, "Upper Ganga and north India", "IN-HR|IN-UP|IN-BR", "Kannauj", "Pushyabhuti/Vardhana", "Harsha", "Harsha", "regional kingdoms", ["source_ind_0001", "source_ind_0004", "source_ind_0009"], 72),
        ("pallava", "帕拉瓦王朝", "Pallava dynasty", "南印度古典时期", "regional_kingdom", 275, 897, "Northern Tamil region and Andhra coast", "IN-TN|IN-AP", "Kanchipuram", "Pallava", "", "Aparajita", "Chola expansion", ["source_ind_0001", "source_ind_0009"], 69),
        ("badami_chalukya", "遮娄其王朝（巴达米）", "Chalukyas of Badami", "南印度古典时期", "regional_kingdom", 543, 753, "Deccan plateau", "IN-KA|IN-MH|IN-TG", "Badami", "Chalukya", "Pulakeshin I", "Kirtivarman II", "Rashtrakuta", ["source_ind_0001", "source_ind_0009"], 70),
        ("eastern_chalukya", "东遮娄其王朝", "Eastern Chalukyas", "南印度古典时期", "regional_kingdom", 624, 1189, "Vengi/Andhra region", "IN-AP", "Vengi", "Chalukya", "Kubja Vishnuvardhana", "", "Chola and Kakatiya powers", ["source_ind_0001", "source_ind_0009"], 66),
        ("rashtrakuta", "罗湿陀罗拘陀王朝", "Rashtrakuta dynasty", "早期中世纪三强", "imperial_state", 753, 982, "Deccan and parts of north/south India", "IN-KA|IN-MH|IN-MP|IN-GJ", "Manyakheta", "Rashtrakuta", "Dantidurga", "Indra IV", "Western Chalukyas", ["source_ind_0001", "source_ind_0009"], 72),
        ("pala", "波罗王朝", "Pala Empire", "早期中世纪三强", "imperial_state", 750, 1161, "Bengal and Bihar", "IN-WB|IN-BR|BD", "", "Pala", "Gopala", "", "Sena dynasty", ["source_ind_0001", "source_ind_0009"], 72),
        ("gurjara_pratihara", "瞿折罗-普腊蒂哈腊王朝", "Gurjara-Pratihara dynasty", "早期中世纪三强", "imperial_state", 730, 1036, "Rajasthan, Gujarat and north India", "IN-RJ|IN-GJ|IN-UP|IN-MP", "Kannauj", "Pratihara", "Nagabhata I", "", "Rajput and regional powers", ["source_ind_0001", "source_ind_0009"], 70),
        ("sena", "犀那王朝", "Sena dynasty", "早期中世纪", "regional_kingdom", 1070, 1230, "Bengal", "IN-WB|BD", "Nabadwip", "Sena", "Hemanta Sena", "", "Delhi/Bengal Sultanate", ["source_ind_0001", "source_ind_0009"], 66),
        ("chola_imperial", "朱罗帝国", "Imperial Chola", "南印度中世纪", "imperial_state", 850, 1279, "Tamil region, Sri Lanka influence and maritime Southeast Asian connections", "IN-TN|LK", "Thanjavur", "Chola", "Vijayalaya", "Rajendra III", "Pandya and regional powers", ["source_ind_0001", "source_ind_0035"], 78),
        ("hoysala", "曷萨拉王朝", "Hoysala Empire", "南印度中世纪", "regional_kingdom", 1026, 1343, "Karnataka and southern Deccan", "IN-KA", "Dorasamudra", "Hoysala", "", "", "Vijayanagara", ["source_ind_0001", "source_ind_0009"], 68),
        ("kakatiya", "卡卡提亚王朝", "Kakatiya dynasty", "南印度中世纪", "regional_kingdom", 1083, 1323, "Telangana and Andhra region", "IN-TG|IN-AP", "Warangal", "Kakatiya", "", "Prataparudra", "Delhi Sultanate", ["source_ind_0001", "source_ind_0009"], 68),
        ("yadava_devagiri", "提婆耆厘 यादव/雅达瓦王朝", "Seuna/Yadava of Devagiri", "南印度中世纪", "regional_kingdom", 1187, 1317, "Northern Deccan", "IN-MH", "Devagiri", "Seuna/Yadava", "", "", "Delhi Sultanate", ["source_ind_0001", "source_ind_0009"], 66),
        ("delhi_sultanate", "德里苏丹国", "Delhi Sultanate", "德里苏丹国时期", "sultanate", 1206, 1526, "North India with varying subcontinental influence", "IN-DL|IN-UP|IN-HR|IN-BR|IN-MP|IN-RJ|IN-PB", "Delhi", "Mamluk|Khalji|Tughlaq|Sayyid|Lodi", "Qutb ud-Din Aibak", "Ibrahim Lodi", "Mughal Empire", ["source_ind_0001", "source_ind_0005", "source_ind_0012"], 82),
        ("vijayanagara", "毗奢耶那伽罗帝国", "Vijayanagara Empire", "南印度中世纪", "imperial_state", 1336, 1646, "Southern India and Deccan", "IN-KA|IN-AP|IN-TN|IN-TG", "Hampi", "Sangama|Saluva|Tuluva|Aravidu", "Harihara I", "Sriranga III", "Deccan successor states", ["source_ind_0001", "source_ind_0025", "source_ind_0036"], 80),
        ("bahmani", "巴赫曼尼苏丹国", "Bahmani Sultanate", "德干苏丹国时期", "sultanate", 1347, 1527, "Deccan plateau", "IN-KA|IN-MH|IN-TG", "Gulbarga", "Bahmani", "Ala-ud-Din Bahman Shah", "Kalimullah", "Deccan Sultanates", ["source_ind_0001", "source_ind_0005", "source_ind_0009"], 72),
        ("bengal_sultanate", "孟加拉苏丹国", "Bengal Sultanate", "区域苏丹国时期", "sultanate", 1352, 1576, "Bengal delta and eastern India", "BD|IN-WB", "Pandua", "Ilyas Shahi and others", "Shamsuddin Ilyas Shah", "", "Mughal Bengal", ["source_ind_0001", "source_ind_0005"], 70),
        ("gujarat_sultanate", "古吉拉特苏丹国", "Gujarat Sultanate", "区域苏丹国时期", "sultanate", 1407, 1573, "Gujarat", "IN-GJ", "Ahmedabad", "Muzaffarid", "Zafar Khan Muzaffar", "", "Mughal Empire", ["source_ind_0001", "source_ind_0005"], 70),
        ("malwa_sultanate", "摩腊婆苏丹国", "Malwa Sultanate", "区域苏丹国时期", "sultanate", 1392, 1562, "Malwa plateau", "IN-MP", "Mandu", "Ghurid/Khalji of Malwa", "", "", "Mughal Empire", ["source_ind_0001", "source_ind_0005"], 66),
        ("jaunpur_sultanate", "章普尔苏丹国", "Jaunpur Sultanate", "区域苏丹国时期", "sultanate", 1394, 1479, "Eastern Ganga plain", "IN-UP", "Jaunpur", "Sharqi", "Malik Sarwar", "", "Lodi/Delhi", ["source_ind_0001", "source_ind_0005"], 66),
        ("ahmadnagar_sultanate", "艾哈迈德讷格尔苏丹国", "Ahmadnagar Sultanate", "德干苏丹国时期", "sultanate", 1490, 1636, "Western Deccan", "IN-MH", "Ahmadnagar", "Nizam Shahi", "Malik Ahmad Nizam Shah I", "", "Mughal Empire", ["source_ind_0001", "source_ind_0005"], 68),
        ("bijapur_sultanate", "比贾布尔苏丹国", "Bijapur Sultanate", "德干苏丹国时期", "sultanate", 1490, 1686, "Western Deccan", "IN-KA|IN-MH", "Bijapur", "Adil Shahi", "Yusuf Adil Shah", "Sikandar Adil Shah", "Mughal Empire", ["source_ind_0001", "source_ind_0005"], 68),
        ("golconda_sultanate", "戈尔康达苏丹国", "Golconda Sultanate", "德干苏丹国时期", "sultanate", 1518, 1687, "Telangana and Andhra", "IN-TG|IN-AP", "Golconda", "Qutb Shahi", "Quli Qutb Mulk", "Abul Hasan Qutb Shah", "Mughal Empire", ["source_ind_0001", "source_ind_0005"], 68),
        ("mughal", "莫卧儿帝国", "Mughal Empire", "莫卧儿时期", "imperial_state", 1526, 1857, "Northern India and much of the subcontinent at maximum extent", "India|Pakistan|Bangladesh|Afghanistan parts", "Agra", "Timurid/Mughal", "Babur", "Bahadur Shah II", "British Crown rule", ["source_ind_0001", "source_ind_0005", "source_ind_0013"], 84),
        ("sur", "苏尔帝国", "Sur Empire", "莫卧儿间断期", "imperial_state", 1540, 1556, "North India", "IN-UP|IN-BR|IN-DL|PK-PB", "Delhi", "Sur", "Sher Shah Suri", "Adil Shah Suri", "Mughal restoration", ["source_ind_0001", "source_ind_0005"], 74),
        ("maratha", "马拉塔联盟/帝国", "Maratha Empire/Confederacy", "早期近代印度", "confederacy", 1674, 1818, "Western and central India with wider subcontinental influence", "IN-MH|IN-MP|IN-GJ|IN-KA|IN-TN|IN-UP", "Pune", "Bhonsle|Peshwa and allied houses", "Shivaji", "Peshwa Baji Rao II", "British East India Company", ["source_ind_0001", "source_ind_0037"], 80),
        ("sikh_empire", "锡克帝国", "Sikh Empire", "早期近代印度", "regional_empire", 1799, 1849, "Punjab and northwestern frontier", "IN-PB|PK-PB|PK-KP|Jammu and Kashmir", "Lahore", "Sukerchakia", "Ranjit Singh", "Duleep Singh", "British East India Company", ["source_ind_0001", "source_ind_0038"], 78),
        ("mysore_kingdom", "迈索尔王国", "Kingdom of Mysore", "早期近代印度", "regional_kingdom", 1399, 1947, "Southern Karnataka and adjoining regions", "IN-KA", "Mysore", "Wodeyar|Hyder Ali-Tipu interlude", "Yaduraya", "Jayachamaraja Wadiyar", "Dominion of India", ["source_ind_0001", "source_ind_0047", "source_ind_0015"], 76),
        ("east_india_company", "英国东印度公司在印度的统治层", "East India Company rule in India", "殖民时期", "colonial_company_rule", 1757, 1858, "Company-controlled territories and presidencies", "India|Pakistan|Bangladesh|Myanmar parts", "Kolkata", "British East India Company", "", "", "British Crown rule", ["source_ind_0001", "source_ind_0046"], 80),
        ("british_raj", "英属印度", "British Raj", "殖民时期", "colonial_crown_rule", 1858, 1947, "British India provinces and paramountcy over princely states", "India|Pakistan|Bangladesh|Myanmar before 1937", "Kolkata", "British Crown", "Queen Victoria", "George VI", "Dominion of India and Dominion of Pakistan", ["source_ind_0001", "source_ind_0014", "source_ind_0018"], 84),
        ("portuguese_india", "葡属印度", "Portuguese India", "殖民时期", "colonial_enclave", 1510, 1961, "Goa, Daman, Diu and related enclaves", "IN-GA|IN-DD|IN-DN", "Goa", "Portuguese Crown/Estado da India", "", "", "Republic of India", ["source_ind_0001", "source_ind_0044"], 78),
        ("french_india", "法属印度", "French India", "殖民时期", "colonial_enclave", 1674, 1954, "Pondicherry and scattered French settlements", "IN-PY|IN-WB|IN-AP|IN-KL", "Puducherry", "French Crown/Republic", "", "", "Republic of India", ["source_ind_0001", "source_ind_0009"], 74),
        ("jammu_kashmir_princely", "查谟和克什米尔土邦", "Jammu and Kashmir princely state", "殖民时期", "princely_state", 1846, 1947, "Western Himalaya princely state", "India/Pakistan/China disputed Himalayan region", "Srinagar", "Dogra", "Gulab Singh", "Hari Singh", "accession dispute and first Indo-Pakistani war", ["source_ind_0045", "source_ind_0018", "source_ind_0015"], 76),
        ("sikkim_kingdom", "锡金王国/保护国", "Kingdom of Sikkim", "喜马拉雅边疆", "himalayan_kingdom", 1642, 1975, "Eastern Himalaya", "IN-SK", "Gangtok", "Namgyal", "Phuntsog Namgyal", "Palden Thondup Namgyal", "Republic of India", ["source_ind_0043", "source_ind_0048"], 74),
        ("dominion_india", "印度自治领", "Dominion of India", "独立与共和国时期", "dominion_state", 1947, 1950, "Post-partition Dominion of India", "India", "New Delhi", "Indian Union", "Jawaharlal Nehru", "Jawaharlal Nehru", "Republic of India", ["source_ind_0018", "source_ind_0008"], 86),
        ("republic_india", "印度共和国", "Republic of India", "独立与共和国时期", "republic_state", 1950, 1990, "Republic of India; dataset stops in 1990", "India", "New Delhi", "Republic of India", "Rajendra Prasad", "", "dataset cutoff", ["source_ind_0019", "source_ind_0008"], 88),
        ("dominion_pakistan", "巴基斯坦自治领", "Dominion of Pakistan", "印巴分治相关", "dominion_state_context", 1947, 1956, "Post-partition Pakistan as directly related South Asian context", "Pakistan|Bangladesh before 1971", "Karachi", "Pakistan", "Muhammad Ali Jinnah", "", "Islamic Republic of Pakistan", ["source_ind_0018", "source_ind_0041"], 80),
        ("bangladesh", "孟加拉国", "Bangladesh", "1971年南亚危机相关", "republic_state_context", 1971, 1990, "Bangladesh as directly related to 1971 India-Pakistan war context", "Bangladesh", "Dhaka", "Bangladesh", "Sheikh Mujibur Rahman", "", "dataset cutoff", ["source_ind_0017", "source_ind_0042"], 82),
    ]
    for row in core:
        key, name, aliases, macro, ptype, start, end, geo, admin, capital, family, founder, last, successor, sources, confidence = row
        p(key, name, macro, aliases, ptype, start, end, aliases=aliases, geography=geo, modern_admin=admin, capital=capital, family=family, founder=founder, last_ruler=last, successor=successor, source_ids=sources, confidence=confidence)


def add_core_rulers(builder: Builder) -> None:
    r = builder.add_ruler
    r("haryanka", "Bimbisara", "King", -544, -492, source_ids=["source_ind_0004", "source_ind_0032"])
    r("haryanka", "Ajatashatru", "King", -492, -460, source_ids=["source_ind_0004", "source_ind_0032"])
    r("nanda", "Mahapadma Nanda", "King", -345, -329, source_ids=["source_ind_0004", "source_ind_0032"], confidence=68)
    r("nanda", "Dhana Nanda", "King", -329, -321, source_ids=["source_ind_0004", "source_ind_0032"], confidence=68)
    for name, start, end in [
        ("Chandragupta Maurya", -321, -297),
        ("Bindusara", -297, -273),
        ("Ashoka", -268, -232),
        ("Dasharatha Maurya", -232, -224),
        ("Samprati", -224, -215),
        ("Shalishuka", -215, -202),
        ("Devavarman", -202, -195),
        ("Shatadhanvan", -195, -187),
        ("Brihadratha Maurya", -187, -185),
    ]:
        r("maurya", name, "Emperor", start, end, source_ids=["source_ind_0010", "source_ind_0033"], confidence=78)
    for name, start, end in [("Pushyamitra Shunga", -185, -149), ("Agnimitra", -149, -141), ("Devabhuti", -83, -73)]:
        r("shunga", name, "King", start, end, source_ids=["source_ind_0004", "source_ind_0009"], confidence=66)
    for name, start, end in [("Simuka", -230, -207), ("Satakarni I", -180, -170), ("Gautamiputra Satakarni", 86, 110), ("Vasisthiputra Pulumavi", 110, 138), ("Yajna Sri Satakarni", 170, 199)]:
        r("satavahana", name, "King", start, end, source_ids=["source_ind_0001", "source_ind_0009"], confidence=65)
    for name, start, end in [("Kujula Kadphises", 30, 80), ("Vima Kadphises", 95, 127), ("Kanishka I", 127, 150), ("Huvishka", 150, 190), ("Vasudeva I", 190, 230)]:
        r("kushan", name, "Emperor", start, end, source_ids=["source_ind_0034"], confidence=70)
    for name, start, end in [("Chandragupta I", 320, 335), ("Samudragupta", 335, 375), ("Chandragupta II", 375, 415), ("Kumaragupta I", 415, 455), ("Skandagupta", 455, 467)]:
        r("gupta", name, "Emperor", start, end, source_ids=["source_ind_0011"], confidence=78)
    r("vardhana", "Harsha", "King", 606, 647, source_ids=["source_ind_0004", "source_ind_0009"], confidence=74)
    for name, start, end in [("Pulakeshin II", 610, 642), ("Dantidurga", 735, 756), ("Dhruva Dharavarsha", 780, 793), ("Amoghavarsha I", 814, 878), ("Gopala", 750, 770), ("Dharmapala", 770, 810), ("Devapala", 810, 850), ("Nagabhata I", 730, 760), ("Mihira Bhoja", 836, 885)]:
        key = "badami_chalukya" if name == "Pulakeshin II" else "rashtrakuta" if name in {"Dantidurga", "Dhruva Dharavarsha", "Amoghavarsha I"} else "pala" if name in {"Gopala", "Dharmapala", "Devapala"} else "gurjara_pratihara"
        r(key, name, "King", start, end, source_ids=["source_ind_0001", "source_ind_0009"], confidence=68)
    for name, start, end in [("Vijayalaya Chola", 850, 871), ("Rajaraja I", 985, 1014), ("Rajendra I", 1014, 1044), ("Kulottunga I", 1070, 1122), ("Rajendra III", 1246, 1279)]:
        r("chola_imperial", name, "King", start, end, source_ids=["source_ind_0035"], confidence=74)
    for name, start, end in [("Qutb ud-Din Aibak", 1206, 1210), ("Iltutmish", 1211, 1236), ("Razia", 1236, 1240), ("Balban", 1266, 1287), ("Alauddin Khalji", 1296, 1316), ("Muhammad bin Tughlaq", 1325, 1351), ("Firuz Shah Tughlaq", 1351, 1388), ("Bahlul Lodi", 1451, 1489), ("Sikandar Lodi", 1489, 1517), ("Ibrahim Lodi", 1517, 1526)]:
        r("delhi_sultanate", name, "Sultan", start, end, source_ids=["source_ind_0012", "source_ind_0005"], confidence=78)
    for name, start, end in [("Harihara I", 1336, 1356), ("Bukka I", 1356, 1377), ("Deva Raya II", 1422, 1446), ("Krishnadevaraya", 1509, 1529), ("Sriranga III", 1642, 1646)]:
        r("vijayanagara", name, "King", start, end, source_ids=["source_ind_0025", "source_ind_0036"], confidence=76)
    for name, start, end in [("Babur", 1526, 1530), ("Humayun", 1530, 1540), ("Akbar", 1556, 1605), ("Jahangir", 1605, 1627), ("Shah Jahan", 1628, 1658), ("Aurangzeb", 1658, 1707), ("Bahadur Shah I", 1707, 1712), ("Muhammad Shah", 1719, 1748), ("Shah Alam II", 1759, 1806), ("Bahadur Shah II", 1837, 1857)]:
        r("mughal", name, "Emperor", start, end, source_ids=["source_ind_0013", "source_ind_0005"], confidence=82)
    r("sur", "Sher Shah Suri", "Sultan", 1540, 1545, source_ids=["source_ind_0005"], confidence=76)
    for name, start, end in [("Shivaji", 1674, 1680), ("Sambhaji", 1681, 1689), ("Shahu I", 1708, 1749), ("Baji Rao I", 1720, 1740), ("Baji Rao II", 1796, 1818)]:
        r("maratha", name, "Chhatrapati/Peshwa", start, end, source_ids=["source_ind_0037"], confidence=74)
    r("sikh_empire", "Ranjit Singh", "Maharaja", 1799, 1839, source_ids=["source_ind_0038"], confidence=78)
    for name, start, end in [("Hyder Ali", 1761, 1782), ("Tipu Sultan", 1782, 1799), ("Krishnaraja Wadiyar III", 1799, 1868), ("Jayachamaraja Wadiyar", 1940, 1947)]:
        r("mysore_kingdom", name, "Ruler", start, end, source_ids=["source_ind_0047"], confidence=74)
    for name, start, end in [("Jawaharlal Nehru", 1947, 1964), ("Lal Bahadur Shastri", 1964, 1966), ("Indira Gandhi", 1966, 1977), ("Morarji Desai", 1977, 1979), ("Charan Singh", 1979, 1980), ("Indira Gandhi", 1980, 1984), ("Rajiv Gandhi", 1984, 1989), ("V. P. Singh", 1989, 1990), ("Chandra Shekhar", 1990, 1990)]:
        key = "dominion_india" if start < 1950 else "republic_india"
        r(key, name, "Prime Minister", start, end, source_ids=["source_ind_0008", "source_ind_0019"], confidence=82, note="Stored in ruler table as head of government for v03 compatibility.")


def import_rulers_org_states(builder: Builder, use_network: bool = True) -> None:
    if not use_network:
        return
    urls = ["https://www.rulers.org/indstat1.html", "https://www.rulers.org/indstat2.html"]
    for url in urls:
        try:
            raw = urllib.request.urlopen(url, timeout=25).read().decode("latin-1")
        except Exception as exc:
            print(f"warning: could not fetch {url}: {exc}")
            continue
        for h2, pre in re.findall(r"<H2>(.*?)</H2>.*?<PRE>(.*?)</PRE>", raw, re.S):
            title = strip_tags(h2).strip()
            canonical = re.sub(r"\s*\(.*?\)", "", title).strip()
            if not canonical or canonical.lower() in builder.polity_names:
                continue
            years = [int(y) for y in re.findall(r"(?<!\d)(1[0-9]{3}|[2-9][0-9]{2})(?!\d)", strip_tags(pre))]
            if not years:
                continue
            start = None
            for line in strip_tags(pre).splitlines():
                if "founded" in line or "recognized as a state" in line or "state is founded" in line:
                    start = year_from_text(line)
                    if start:
                        break
            if start is None:
                start = min(years)
            end = 1947 if "15 Aug 1947" in strip_tags(pre) else max(year for year in years if year <= 1949)
            if start > end or end < 1700:
                continue
            key = f"pstate_{canonical.lower().replace(' ', '_').replace('-', '_')}"
            pid = builder.add_polity(
                key,
                canonical,
                "英属印度土邦体系",
                "Princely state",
                "princely_state_under_paramountcy",
                start,
                end,
                aliases=title if title != canonical else "",
                date_precision="approx",
                geography="British Indian princely-state geography; exact agency/modern location requires gazetteer review.",
                modern_admin="Historical South Asia; modern country/ADM1 requires item-level review.",
                capital=canonical if canonical in COORDS else "",
                family="local ruling house",
                successor="Dominion of India/Pakistan or later administrative integration",
                source_ids=["source_ind_0020" if "indstat1" in url else "source_ind_0021", "source_ind_0002", "source_ind_0015"],
                source_raw=f"Imported from {url} section {title}",
                confidence=64,
                note="Princely-state chronology imported from Rulers.org as a structured index; important states need Gazetteer/official corroboration before high-confidence display.",
                review_status="candidate",
                risk_flags="needs_geography_review",
            )
            title_context = "Ruler"
            for raw_line in pre.splitlines():
                line = strip_tags(raw_line)
                if not line.strip():
                    continue
                if line.strip().startswith(("Rulers", "Rajas", "Maharajas", "Nawabs", "Ruler", "Raja", "Maharaja", "Nawab")):
                    title_context = clean_name(line).replace("Rulers", "Ruler")
                    continue
                if "regent" in line.lower() or "jointly with" in line.lower():
                    continue
                if " - " not in line:
                    continue
                parts = line.split(" - ", 1)
                start_year = year_from_text(parts[0])
                end_match = re.search(r"(?<!\d)(\d{3,4})(?!\d)", parts[1])
                end_year = int(end_match.group(1)) if end_match else None
                if start_year is None or end_year is None or start_year > end_year or end_year < start or start_year > end:
                    continue
                name = clean_name(parts[1][end_match.end():] if end_match else parts[1])
                if not name or len(name) < 3 or name.lower().startswith(("occupied", "state", "the ", "incorporated", "absorbed", "extinguished")):
                    continue
                rid = f"ruler_ind_{builder._ruler_seq:05d}"
                builder._ruler_seq += 1
                builder.rulers.append(
                    {
                        "ruler_id": rid,
                        "polity_id": pid,
                        "polity_name": canonical,
                        "ruler_name": name,
                        "ruler_title": title_context[:80],
                        "ruler_temple_name": "",
                        "ruler_posthumous_name": "",
                        "ruler_personal_name": "",
                        "ruler_reign_start_year": str(max(start_year, start)),
                        "ruler_reign_start_label": year_label(max(start_year, start)),
                        "ruler_reign_end_year": str(min(end_year, end)),
                        "ruler_reign_end_label": year_label(min(end_year, end)),
                        "ruler_reign_raw": line.strip(),
                        "ruler_reign_precision": "year",
                        "era_names": "",
                        "ruler_source_title": source_titles(["source_ind_0020" if "indstat1" in url else "source_ind_0021"]),
                        "ruler_source_url": source_urls(["source_ind_0020" if "indstat1" in url else "source_ind_0021"]),
                        "ruler_source_section": title,
                        "ruler_confidence_score": "62",
                        "ruler_confidence_note": "Parsed from Rulers.org; exact day/month and contested accessions are normalized to years.",
                        "merged_from_v02_rows": "",
                    }
                )


def apply_specific_princely_corrections(builder: Builder) -> None:
    corrections = {
        "pstate_haydarabad": ("Hyderabad", 1948, "Dominion of India after Operation Polo/Police Action", "Endpoint adjusted for the 1948 Hyderabad integration; Rulers.org spelling Haydarabad is preserved as source alias."),
        "pstate_junagadh": ("Junagadh", 1948, "Dominion of India after 1947 crisis and 1948 plebiscite", "Endpoint adjusted for the Junagadh accession crisis and 1948 plebiscite context."),
    }
    for key, (capital, end_year, successor, note) in corrections.items():
        pid = builder.polity_key_to_id.get(key)
        if not pid:
            continue
        row = next(item for item in builder.polities if item["polity_id"] == pid)
        row["capital_historical"] = capital
        row["capital_modern"] = capital
        row["polity_end_year"] = str(end_year)
        row["polity_end_label"] = year_label(end_year)
        row["polity_date_raw"] = f"{row['polity_start_label']}-{row['polity_end_label']}"
        row["destroyed_by_or_successor"] = successor
        row["confidence_note"] = f"{row['confidence_note']} {note}"

    release_note_corrections = {
        "Tripura": {
            "start": 1400,
            "source_ids": ["source_ind_0021", "source_ind_0053", "source_ind_0054"],
            "confidence_note": "System correction: pre-1400 Rajmala lunar-dynasty chronology is treated as legendary; historical polity playback begins around the early Manikya state formation.",
        },
        "Udaipur [in Rajasthan]": {
            "start": 728,
            "source_ids": ["source_ind_0021", "source_ind_0058", "source_ind_0059", "source_ind_0060"],
            "confidence_note": "System correction: 530 CE is retained as Guhila origin tradition only; Mewar/Udaipur polity playback begins with the Bappa Rawal/Chittor foundation horizon.",
        },
        "Chamba": {
            "start": 500,
            "source_ids": ["source_ind_0020", "source_ind_0056", "source_ind_0057"],
            "risk_flags": "approx_or_uncertain|needs_geography_review",
            "confidence_note": "System marker: circa 500 CE foundation is a local tradition involving legendary Maru and mythical Kalpagrama; retain as approximate with explicit uncertainty.",
        },
    }
    for polity_name, data in release_note_corrections.items():
        row = next((item for item in builder.polities if item["polity_name"] == polity_name), None)
        if not row:
            continue
        start = data["start"]
        row["polity_start_year"] = str(start)
        row["polity_start_label"] = year_label(start)
        row["polity_date_raw"] = f"{row['polity_start_label']}-{row['polity_end_label']}"
        row["polity_date_precision"] = "approx" if polity_name in {"Tripura", "Chamba"} else row["polity_date_precision"]
        row["polity_source_titles"] = source_titles(data["source_ids"])
        row["polity_source_urls"] = source_urls(data["source_ids"])
        row["confidence_note"] = f"{row['confidence_note']} {data['confidence_note']}".strip()
        if data.get("risk_flags"):
            row["polity_name_risk_flags"] = data["risk_flags"]


def add_events_capitals_and_context(builder: Builder) -> None:
    e = builder.add_event
    e(-7000, "梅赫尔格尔早期农业遗址进入南亚史背景", "俾路支地区的梅赫尔格尔常被用作南亚新石器和早期农业社会的重要背景点。", "为印度河文明之前的长期社会复杂化提供背景。", event_type="archaeological_context", location="Mehrgarh", source_ids=["source_ind_0001", "source_ind_0022"], date_precision="approx", importance=3, confidence=70)
    e(-2600, "成熟哈拉帕城市化阶段形成", "印度河文明进入成熟城市化阶段，哈拉帕、摩亨佐-达罗、朵拉维拉等城市网络扩展。", "这是南亚最早的大规模城市文明层。", event_type="urbanization", polity_keys=["mature_harappan"], location="Harappa", source_ids=["source_ind_0004", "source_ind_0030"], date_precision="approx", importance=1, confidence=78)
    e(-1900, "印度河城市体系衰退与区域化", "成熟哈拉帕城市网络逐步衰退，晚期哈拉帕区域文化延续。", "该转型影响了随后西北和北印度历史文化格局。", event_type="civilization_transition", polity_keys=["late_harappan"], location="Mohenjo-daro", source_ids=["source_ind_0004", "source_ind_0030"], date_precision="approx", importance=1, confidence=74)
    e(-600, "十六大国时代", "恒河流域和北印度进入列国竞争、城市化和新宗教运动活跃的时代。", "为佛教、耆那教、摩揭陀崛起和后来的帝国政治奠定背景。", event_type="period_context", polity_keys=["magadha_mahajanapada", "vajji", "kosala", "avanti"], location="Rajgir", source_ids=["source_ind_0004"], date_precision="approx", importance=1, confidence=72)
    e(-326, "亚历山大远征至印度西北", "亚历山大军队进入印度西北并与波罗斯作战，随后撤退。", "希腊化世界与西北南亚政治互动增强，但其控制范围和持续影响须谨慎表达。", event_type="invasion", polity_keys=["gandhara"], location="Taxila", source_ids=["source_ind_0001", "source_ind_0009"], importance=2, confidence=75)
    e(-321, "旃陀罗笈多建立孔雀帝国", "旃陀罗笈多推翻难陀政权，建立以华氏城为中心的孔雀帝国。", "南亚首次出现可明确追踪的大型帝国政治结构之一。", event_type="polity_start", polity_keys=["maurya"], people="Chandragupta Maurya|Chanakya", location="Pataliputra", source_ids=["source_ind_0010"], importance=1, confidence=82)
    e(-261, "阿育王征服羯陵伽", "阿育王征服羯陵伽后，在铭文传统中强调悔悟和法的治理。", "该事件是孔雀帝国政治、宗教和铭文传播的关键节点。", event_type="war", polity_keys=["maurya"], people="Ashoka", source_ids=["source_ind_0033", "source_ind_0004"], importance=1, confidence=80)
    e(78, "传统萨迦纪元起点", "78年常被作为萨迦纪元起点；其政治归属和精确解释在学术上有不同看法。", "体现印度古代纪年体系与王朝政治的复杂关系。", event_type="calendar", polity_keys=["western_kshatrapas", "kushan"], source_ids=["source_ind_0001"], importance=3, confidence=62)
    e(320, "笈多纪元与笈多帝国兴起", "笈多王朝在4世纪建立北印度强权。", "笈多时期常被视为古典印度政治与文化的重要阶段。", event_type="polity_start", polity_keys=["gupta"], location="Pataliputra", source_ids=["source_ind_0011"], importance=1, confidence=82)
    e(606, "戒日王即位", "戒日王统合北印度部分区域，以曲女城为政治中心。", "后笈多北印度政治再整合的重要代表。", event_type="succession", polity_keys=["vardhana"], people="Harsha", location="Kannauj", source_ids=["source_ind_0004", "source_ind_0009"], importance=2, confidence=74)
    e(712, "阿拉伯势力进入信德", "穆罕默德·本·卡西姆征服信德，开启伊斯兰政权在南亚西北的早期存在。", "这是中世纪南亚宗教与政治互动的重要节点。", event_type="conquest", source_ids=["source_ind_0001", "source_ind_0005"], importance=2, confidence=72)
    e(850, "朱罗王朝复兴", "朱罗在泰米尔地区复兴，后来发展出强大的南印度和海上影响力。", "南印度政治与印度洋贸易史的关键起点。", event_type="polity_start", polity_keys=["chola_imperial"], location="Thanjavur", source_ids=["source_ind_0035"], importance=2, confidence=76)
    e(1001, "伽色尼马哈茂德进攻印度西北", "伽色尼马哈茂德多次进攻印度西北和北印度。", "反映中亚、阿富汗与北印度政治军事联系。", event_type="invasion", polity_keys=["gandhara"], source_ids=["source_ind_0001", "source_ind_0005"], importance=2, confidence=70)
    e(1025, "索姆纳特遭伽色尼进攻", "索姆纳特神庙遭伽色尼马哈茂德进攻，事件在后世记忆中被高度政治化。", "需要区分中世纪事件、后世叙事和现代政治记忆。", event_type="raid", location="Goa", source_ids=["source_ind_0005"], importance=3, confidence=60, note="Location intentionally not linked to Somnath coordinates pending a dedicated gazetteer row.")
    e(1192, "第二次塔莱因战役", "古尔势力击败乔汉王朝，为德里苏丹国兴起铺路。", "北印度政治格局转折点。", event_type="battle", polity_keys=["delhi_sultanate"], location="Tarain", source_ids=["source_ind_0012", "source_ind_0005"], importance=1, confidence=78)
    e(1206, "德里苏丹国建立", "库特布丁·艾伊拜克在德里建立苏丹政权。", "开启北印度持续数百年的苏丹国政治阶段。", event_type="polity_start", polity_keys=["delhi_sultanate"], location="Delhi", source_ids=["source_ind_0012"], importance=1, confidence=82)
    e(1336, "毗奢耶那伽罗建立", "南印度出现以通加巴德拉河流域为核心的毗奢耶那伽罗帝国。", "成为中世纪南印度最重要的帝国之一。", event_type="polity_start", polity_keys=["vijayanagara"], location="Hampi", source_ids=["source_ind_0025", "source_ind_0036"], importance=1, confidence=80)
    e(1347, "巴赫曼尼苏丹国建立", "德干地区形成巴赫曼尼苏丹国，与毗奢耶那伽罗长期互动和对抗。", "塑造德干政治格局。", event_type="polity_start", polity_keys=["bahmani"], location="Gulbarga", source_ids=["source_ind_0005"], importance=2, confidence=74)
    e(1498, "达伽马抵达卡利卡特", "葡萄牙航海者达伽马抵达印度西海岸。", "印度洋贸易和欧洲殖民势力进入南亚的重要节点。", event_type="maritime_contact", source_ids=["source_ind_0009", "source_ind_0044"], importance=1, confidence=82)
    e(1510, "葡萄牙占领果阿", "葡萄牙在印度西海岸取得果阿，形成长期殖民据点。", "南亚欧洲殖民飞地的关键开端。", event_type="occupation", polity_keys=["portuguese_india"], location="Goa", source_ids=["source_ind_0044"], importance=1, confidence=80)
    e(1526, "第一次帕尼帕特战役", "巴布尔击败洛迪王朝，莫卧儿帝国建立。", "北印度从德里苏丹国转入莫卧儿政治秩序。", event_type="battle", polity_keys=["mughal", "delhi_sultanate"], people="Babur|Ibrahim Lodi", location="Panipat", source_ids=["source_ind_0013"], importance=1, confidence=84)
    e(1556, "第二次帕尼帕特战役", "阿克巴政权在北印度巩固莫卧儿复兴。", "莫卧儿帝国进入长期扩张与整合阶段。", event_type="battle", polity_keys=["mughal"], people="Akbar", location="Panipat", source_ids=["source_ind_0013"], importance=2, confidence=80)
    e(1565, "塔利科塔战役", "德干苏丹国联盟击败毗奢耶那伽罗主力。", "南印度帝国重心和德干政治格局发生重大变化。", event_type="battle", polity_keys=["vijayanagara", "bahmani"], source_ids=["source_ind_0025", "source_ind_0036"], importance=1, confidence=80)
    e(1600, "英国东印度公司获特许", "英国东印度公司成立并逐步进入南亚贸易和政治竞争。", "后来公司统治的制度起点。", event_type="colonial_company", polity_keys=["east_india_company"], source_ids=["source_ind_0046"], importance=2, confidence=82)
    e(1674, "湿婆吉加冕", "湿婆吉在西印度建立马拉塔政治权威。", "马拉塔力量崛起为莫卧儿后期和殖民前夜的重要变量。", event_type="polity_start", polity_keys=["maratha"], people="Shivaji", location="Pune", source_ids=["source_ind_0037"], importance=1, confidence=78)
    e(1707, "奥朗则布去世", "奥朗则布去世后，莫卧儿中央权威加速松动。", "区域强权和殖民公司扩张空间扩大。", event_type="succession", polity_keys=["mughal", "maratha"], people="Aurangzeb", source_ids=["source_ind_0013"], importance=1, confidence=82)
    e(1757, "普拉西战役", "英国东印度公司在孟加拉击败纳瓦布势力。", "公司由贸易势力转向领土政治权力的关键节点。", event_type="battle", polity_keys=["east_india_company"], location="Plassey", source_ids=["source_ind_0046"], importance=1, confidence=84)
    e(1764, "布克萨尔战役", "公司击败孟加拉、奥德和莫卧儿皇帝联军。", "公司获得孟加拉财政与行政权的前奏。", event_type="battle", polity_keys=["east_india_company", "mughal"], location="Buxar", source_ids=["source_ind_0046"], importance=1, confidence=82)
    e(1799, "第四次迈索尔战争结束", "提普苏丹在斯里兰伽帕特纳战死，迈索尔威胁被英国削弱。", "南印度殖民扩张的重要转折。", event_type="war", polity_keys=["mysore_kingdom", "east_india_company"], people="Tipu Sultan", location="Srirangapatna", source_ids=["source_ind_0047"], importance=2, confidence=78)
    e(1818, "第三次英马战争后马拉塔联盟瓦解", "英国东印度公司击败马拉塔主要力量。", "公司成为印度次大陆最强政治权力。", event_type="war", polity_keys=["maratha", "east_india_company"], source_ids=["source_ind_0037", "source_ind_0046"], importance=1, confidence=80)
    e(1857, "1857年印度起义", "北印度和中印度爆发针对公司统治的大规模起义。", "直接促成1858年英国王冠接管印度。", event_type="rebellion", polity_keys=["east_india_company", "mughal", "british_raj"], location="Meerut", source_ids=["source_ind_0039"], importance=1, confidence=84)
    e(1858, "英属印度王冠统治开始", "英国政府取代东印度公司直接统治英属印度。", "殖民治理结构发生根本变化。", event_type="colonial_transfer", polity_keys=["british_raj", "east_india_company"], source_ids=["source_ind_0014"], importance=1, confidence=84)
    e(1885, "印度国民大会成立", "印度国民大会在殖民政治中形成组织化民族运动平台。", "现代印度民族运动的重要组织起点。", event_type="political_organization", polity_keys=["british_raj"], source_ids=["source_ind_0040"], importance=1, confidence=82)
    e(1905, "孟加拉分割", "英国殖民政府分割孟加拉，引发大规模政治反应。", "推动民族主义、抵制运动和政治组织变化。", event_type="administrative_partition", polity_keys=["british_raj"], source_ids=["source_ind_0006"], importance=2, confidence=78)
    e(1911, "英属印度首都宣布迁往德里", "英王乔治五世在德里宣布将首都从加尔各答迁往德里。", "殖民政治空间重心改变。", event_type="capital_relocation", polity_keys=["british_raj"], location="Delhi", source_ids=["source_ind_0014"], importance=2, confidence=80)
    e(1919, "贾利安瓦拉巴格惨案", "阿姆利则发生殖民军队开枪事件。", "成为印度民族运动记忆中的重大转折。", event_type="massacre", polity_keys=["british_raj"], location="Amritsar", source_ids=["source_ind_0006"], importance=1, confidence=80)
    e(1930, "丹迪盐行军", "甘地领导盐行军挑战殖民盐税。", "非暴力不合作运动的标志性事件。", event_type="civil_disobedience", polity_keys=["british_raj"], people="Mahatma Gandhi", location="Dandi", source_ids=["source_ind_0006"], importance=1, confidence=82)
    e(1947, "印巴分治与两个自治领成立", "英国印度被分割为印度自治领和巴基斯坦自治领，伴随大规模迁徙和暴力。", "现代南亚国家体系和边界争议的核心节点。", event_type="partition", polity_keys=["dominion_india", "dominion_pakistan", "british_raj"], source_ids=["source_ind_0018", "source_ind_0041"], importance=1, confidence=88)
    e(1947, "查谟和克什米尔加入印度与第一次印巴战争", "克什米尔归属引发军事冲突和长期争议。", "必须区分法理文件、实际控制线和各方主张。", event_type="disputed_accession_war", polity_keys=["dominion_india", "dominion_pakistan"], location="Srinagar", source_ids=["source_ind_0045", "source_ind_0018"], importance=1, confidence=76)
    e(1948, "朱纳格特问题与并入印度", "朱纳格特在分治后出现归属危机，随后由印度接管并举行公投。", "该案例显示土邦整合不能简单等同于1947年8月自动完成。", event_type="princely_state_integration", polity_keys=["pstate_junagadh", "dominion_india"], location="Junagadh", source_ids=["source_ind_0015", "source_ind_0041"], importance=2, confidence=72)
    e(1948, "海得拉巴并入印度", "海得拉巴在1948年经印度军事/政治行动并入印度联邦。", "海得拉巴是独立后土邦整合和中央权力建构的重要案例。", event_type="princely_state_integration", polity_keys=["pstate_haydarabad", "dominion_india"], location="Hyderabad", source_ids=["source_ind_0015", "source_ind_0041"], importance=1, confidence=72)
    e(1950, "印度共和国成立", "印度宪法生效，印度自治领转为共和国。", "现代印度国家制度的起点。", event_type="republic", polity_keys=["republic_india"], location="New Delhi", source_ids=["source_ind_0019"], importance=1, confidence=90)
    e(1956, "印度邦重组", "《邦重组法》按语言和行政原则重划印度内部邦界。", "共和国疆域内部行政结构的重要转折。", event_type="territorial_reorganization", polity_keys=["republic_india"], source_ids=["source_ind_0016"], importance=1, confidence=88)
    e(1961, "印度接管果阿、达曼和第乌", "印度军事行动结束葡萄牙在果阿等地的殖民统治。", "后殖民领土整合的重要事件。", event_type="retrocession_integration", polity_keys=["republic_india", "portuguese_india"], location="Goa", source_ids=["source_ind_0044"], importance=1, confidence=82)
    e(1962, "中印边境战争", "印度与中国在喜马拉雅边境发生战争。", "阿克赛钦和NEFA/阿鲁纳恰尔相关实际控制与主张需区分。", event_type="border_war", polity_keys=["republic_india"], location="Tawang", source_ids=["source_ind_0009"], importance=1, confidence=76)
    e(1965, "第二次印巴战争", "印度和巴基斯坦围绕克什米尔等问题爆发战争。", "延续分治后的边界与安全格局。", event_type="war", polity_keys=["republic_india"], source_ids=["source_ind_0009"], importance=2, confidence=76)
    e(1971, "第三次印巴战争与孟加拉国独立", "印度介入东巴基斯坦危机，战争后孟加拉国独立。", "重塑南亚国家格局。", event_type="war_and_state_formation", polity_keys=["republic_india", "bangladesh"], location="Dhaka", source_ids=["source_ind_0017", "source_ind_0042"], importance=1, confidence=86)
    e(1975, "锡金成为印度邦", "锡金经政治与法律程序成为印度的一个邦。", "喜马拉雅边疆整合的重要节点。", event_type="territorial_integration", polity_keys=["republic_india"], source_ids=["source_ind_0043", "source_ind_0048"], importance=1, confidence=84)
    e(1975, "印度紧急状态开始", "印度进入1975-1977年紧急状态时期。", "共和国政治制度和公民权利史的重大节点。", event_type="constitutional_crisis", polity_keys=["republic_india"], people="Indira Gandhi", source_ids=["source_ind_0008", "source_ind_0019"], importance=1, confidence=78)
    e(1984, "蓝星行动与英迪拉·甘地遇刺", "旁遮普危机升级，蓝星行动后英迪拉·甘地遇刺。", "影响印度联邦政治、宗教社群关系和安全治理。", event_type="political_crisis", polity_keys=["republic_india"], people="Indira Gandhi", location="Amritsar", source_ids=["source_ind_0009"], importance=2, confidence=74)
    e(1990, "vIndian首批数据截止年", "本数据包按计划在1990年截止，后续年份不在本批展开。", "提供明确的年度边界，避免把1990年后的事实混入本批数据。", event_type="dataset_boundary", polity_keys=["republic_india"], source_ids=["source_ind_0019"], importance=4, confidence=90)

    for row in list(builder.polities):
        key = next((k for k, pid in builder.polity_key_to_id.items() if pid == row["polity_id"]), "")
        if not key:
            continue
        start = int(row["polity_start_year"])
        end = int(row["polity_end_year"])
        priority = 850 if row["polity_type"] == "princely_state_under_paramountcy" else 500
        importance = 4 if row["polity_type"] == "princely_state_under_paramountcy" else 3
        event_source_ids = (
            ["source_ind_0020", "source_ind_0021", "source_ind_0002", "source_ind_0015"]
            if row["polity_type"] == "princely_state_under_paramountcy"
            else ["source_ind_0001", "source_ind_0009"]
        )
        builder.add_event(
            start,
            f"{row['polity_display_name']}形成或建立",
            f"{row['polity_display_name']}在vIndian政权表中的起始年为{row['polity_start_label']}。",
            "由政权标准表自动派生的建立/形成事件，用于年度浏览与检索。",
            event_type="polity_start",
            polity_keys=[key],
            source_ids=event_source_ids,
            date_precision=row["polity_date_precision"],
            item_kind="representative_event",
            importance=importance,
            priority=priority,
            confidence=int(row["confidence_score"]),
            note=row["confidence_note"],
        )
        if end != 1990 and row["destroyed_by_or_successor"] != "dataset cutoff":
            builder.add_event(
                end,
                f"{row['polity_display_name']}结束或转型",
                f"{row['polity_display_name']}在vIndian政权表中的结束年为{row['polity_end_label']}；后继/结局：{row['destroyed_by_or_successor']}。",
                "由政权标准表自动派生的结束/转型事件，用于年度浏览与检索。",
                event_type="polity_end",
                polity_keys=[key],
                source_ids=event_source_ids,
                date_precision=row["polity_date_precision"],
                item_kind="representative_event",
                importance=importance,
                priority=priority + 1,
                confidence=int(row["confidence_score"]),
                note=row["confidence_note"],
            )

    for row in builder.polities:
        key = next((k for k, pid in builder.polity_key_to_id.items() if pid == row["polity_id"]), "")
        if key and row["capital_historical"]:
            builder.add_capital(key, row["capital_historical"], int(row["polity_start_year"]), int(row["polity_end_year"]), ["source_ind_0001", "source_ind_0002"])

    for pid_key in ["maurya", "gupta", "delhi_sultanate", "mughal", "british_raj", "republic_india"]:
        if pid_key in builder.polity_key_to_id:
            row = next(item for item in builder.polities if item["polity_id"] == builder.polity_key_to_id[pid_key])
            builder.territories.append(
                {
                    "polity_id": row["polity_id"],
                    "polity_name": row["polity_name"],
                    "admin_ids": row["modern_admin_units_raw"],
                    "valid_from_year": row["polity_start_year"],
                    "valid_to_year": row["polity_end_year"],
                    "match_source": "manual_modern_region_approximation",
                    "confidence_score": row["confidence_score"],
                    "note": "Textual modern-region approximation only; no South Asia historical boundary GeoJSON in this phase.",
                    "source_titles": row["polity_source_titles"],
                    "source_raw": row["polity_source_raw"],
                }
            )


def add_anecdotes_strategic_issues(builder: Builder) -> None:
    def anecdote(key: str, year: int, title: str, phrase: str, story: str, source_id: str, location: str = "", polity_key: str = "") -> None:
        lon, lat = COORDS.get(location, ("", ""))
        builder.anecdotes.append(
            {
                "anecdote_id": f"anecdote_ind_{builder._anecdote_seq:04d}",
                "dynasty_name": key,
                "macro_period": "印度史典故与历史记忆",
                "year": str(year),
                "sort_order": str(builder._anecdote_seq),
                "date_label": year_label(year),
                "date_precision": "approx",
                "coverage_start_year": str(year),
                "coverage_end_year": str(year),
                "anecdote_type": "historical_memory",
                "title": title,
                "phrase": phrase,
                "short_description": story[:80],
                "story_text": story,
                "source_title": SOURCE_BY_ID[source_id].title,
                "source_section": "",
                "source_url": SOURCE_BY_ID[source_id].url,
                "source_type": SOURCE_BY_ID[source_id].source_type,
                "source_note": "Anecdote/context row; not used as sole chronology source.",
                "related_polity_ids": builder.polity_key_to_id.get(polity_key, ""),
                "related_people": "",
                "location_historical_name": location,
                "location_modern_name": location,
                "longitude": str(lon),
                "latitude": str(lat),
                "location_precision": "city" if lon else "",
                "primary_education_stage": "高中",
                "education_stage_tags": "世界史|南亚史",
                "display_priority": str(200 + builder._anecdote_seq),
                "review_status": "candidate",
                "review_note": "Use as historical memory/context; avoid treating literary tradition as exact chronology.",
            }
        )
        builder._anecdote_seq += 1

    anecdote("佛教史", -528, "菩提伽耶成道传统", "菩提树下成道", "佛陀在菩提伽耶成道的传统叙事对南亚宗教地理具有核心意义。", "source_ind_0029", "Bodh Gaya")
    anecdote("孔雀王朝", -261, "阿育王与羯陵伽后的悔悟", "羯陵伽之后", "阿育王铭文传统中以羯陵伽战争后的道德转向说明王权与法的关系。", "source_ind_0033", "", "maurya")
    anecdote("古典印度", 400, "那烂陀学术传统", "那烂陀", "那烂陀成为佛教和跨区域学术交流的重要象征。", "source_ind_0023", "Nalanda")
    anecdote("莫卧儿", 1571, "法泰赫普尔西克里", "胜利之城", "阿克巴建设法泰赫普尔西克里，体现莫卧儿宫廷政治与宗教讨论空间。", "source_ind_0026", "Fatehpur Sikri", "mughal")
    anecdote("民族运动", 1930, "一把盐的政治", "盐行军", "甘地以盐税为切入点，将日常生活与反殖民政治动员连接起来。", "source_ind_0006", "Dandi", "british_raj")

    strategic_items = [
        ("Mehrgarh", "archaeological_site", "early_agriculture", -7000, -2600, "南亚早期农业和定居社会的重要遗址。"),
        ("Harappa", "archaeological_site", "urban_site", -3300, -1300, "印度河文明核心城市遗址之一。"),
        ("Mohenjo-daro", "archaeological_site", "urban_site", -2600, -1900, "成熟哈拉帕城市遗址，常用于展示印度河城市化。"),
        ("Dholavira", "archaeological_site", "urban_site", -3000, -1500, "古吉拉特哈拉帕城市遗址，UNESCO世界遗产。"),
        ("Taxila", "transport_hub", "city", -600, 500, "西北通道、犍陀罗和跨区域交流要地。"),
        ("Rajgir", "fortress_city", "city", -600, -400, "早期摩揭陀政治中心。"),
        ("Pataliputra", "fortress_city", "capital", -400, 600, "摩揭陀、孔雀和笈多政治核心城市。"),
        ("Vaishali", "fortress_city", "republic", -600, -300, "跋耆/离车联盟重要中心。"),
        ("Bodh Gaya", "cultural_allusion", "religious_site", -528, 1990, "佛教圣地和历史记忆核心地点。"),
        ("Sarnath", "cultural_allusion", "religious_site", -528, 1990, "初转法轮传统相关地点。"),
        ("Ujjain", "transport_hub", "city", -600, 1200, "摩腊婆、贸易和天文文化传统中心。"),
        ("Mathura", "transport_hub", "city", -600, 1200, "北印度宗教、交通和政治节点。"),
        ("Kannauj", "fortress_city", "capital", 600, 1200, "后笈多和早期中世纪北印度争夺焦点。"),
        ("Nalanda", "cultural_allusion", "monastery", 400, 1200, "佛教大学和跨区域学术网络象征。"),
        ("Kanchipuram", "fortress_city", "capital", 300, 900, "帕拉瓦和南印度宗教文化中心。"),
        ("Badami", "fortress_city", "capital", 543, 753, "巴达米遮娄其山地都城。"),
        ("Manyakheta", "fortress_city", "capital", 753, 982, "罗湿陀罗拘陀政治中心。"),
        ("Thanjavur", "fortress_city", "capital", 850, 1279, "朱罗王朝核心都城和寺庙城市。"),
        ("Delhi", "fortress_city", "capital", 1206, 1990, "德里苏丹国、莫卧儿后期、英属印度和共和国首都节点。"),
        ("Hampi", "fortress_city", "capital", 1336, 1565, "毗奢耶那伽罗帝国核心遗址。"),
        ("Gulbarga", "fortress_city", "capital", 1347, 1425, "巴赫曼尼早期都城。"),
        ("Bidar", "fortress_city", "capital", 1425, 1527, "巴赫曼尼后期都城。"),
        ("Bijapur", "fortress_city", "capital", 1490, 1686, "德干苏丹国重要都城。"),
        ("Golconda", "fortress_city", "capital", 1518, 1687, "钻石贸易和德干政治中心。"),
        ("Agra", "fortress_city", "capital", 1526, 1707, "莫卧儿核心都城之一。"),
        ("Fatehpur Sikri", "fortress_city", "capital", 1571, 1585, "阿克巴时期规划都城。"),
        ("Pune", "transport_hub", "capital", 1674, 1818, "马拉塔政治中心。"),
        ("Lahore", "fortress_city", "capital", 1799, 1849, "锡克帝国都城和旁遮普重镇。"),
        ("Panipat", "battlefield", "battle", 1526, 1761, "三次帕尼帕特战役改变北印度政治格局。"),
        ("Tarain", "battlefield", "battle", 1191, 1192, "古尔-乔汉战争转折地。"),
        ("Chittorgarh", "fortress_city", "fort", 700, 1568, "拉其普特城防和政治记忆重镇。"),
        ("Haldighati", "battlefield", "battle", 1576, 1576, "莫卧儿与梅瓦尔冲突记忆地点。"),
        ("Plassey", "battlefield", "battle", 1757, 1757, "公司统治转折战场。"),
        ("Buxar", "battlefield", "battle", 1764, 1764, "公司财政权扩张前奏战场。"),
        ("Srirangapatna", "fortress_city", "capital", 1761, 1799, "迈索尔战争关键要塞。"),
        ("Kolkata", "maritime_port", "capital", 1690, 1911, "公司和英属印度早期首都港市。"),
        ("Goa", "maritime_port", "colonial_port", 1510, 1961, "葡属印度核心港口和殖民飞地。"),
        ("Puducherry", "maritime_port", "colonial_port", 1674, 1954, "法属印度核心据点。"),
        ("New Delhi", "fortress_city", "capital", 1911, 1990, "殖民后期和共和国首都。"),
        ("Amritsar", "cultural_allusion", "city", 1800, 1984, "锡克宗教中心及近现代政治事件地点。"),
        ("Meerut", "fortress_city", "military_station", 1857, 1857, "1857年起义重要爆发地。"),
        ("Dandi", "cultural_allusion", "national_movement", 1930, 1930, "盐行军终点。"),
        ("Srinagar", "frontier_gate", "frontier_city", 1947, 1990, "克什米尔争议和喜马拉雅边疆核心城市。"),
        ("Tawang", "frontier_gate", "frontier", 1962, 1962, "NEFA/阿鲁纳恰尔边境战争关键方向。"),
        ("Aksai Chin", "frontier_gate", "disputed_region", 1950, 1990, "中印边界争议中的高原区域，坐标为区域近似。"),
        ("Dhaka", "fortress_city", "capital", 1971, 1990, "1971年战争和孟加拉国独立核心城市。"),
    ]
    for name, category, icon, start, end, summary in strategic_items:
        lon, lat = COORDS[name]
        builder.strategic.append(
            {
                "location_id": f"strategic_ind_{builder._strategic_seq:04d}",
                "name": name,
                "aliases": "",
                "category": category if category in {"battlefield", "frontier_gate", "fortress_city", "transport_hub", "maritime_port", "cultural_allusion"} else "cultural_allusion",
                "icon_key": icon,
                "importance_level": "2",
                "display_priority": str(100 + builder._strategic_seq),
                "start_year": str(start),
                "end_year": str(end),
                "active_years_raw": f"{year_label(start)}-{year_label(end)}",
                "related_event_ids": "",
                "related_anecdote_ids": "",
                "related_polity_ids": "",
                "related_people": "",
                "historical_name": name,
                "modern_name": name,
                "modern_admin_units_raw": "South Asia modern location; see source and coordinate note.",
                "longitude": str(lon),
                "latitude": str(lat),
                "location_precision": "region" if name == "Aksai Chin" else "city",
                "location_confidence_score": "78" if name == "Aksai Chin" else "85",
                "strategic_summary": summary,
                "historical_significance": summary,
                "source_titles": source_titles(["source_ind_0001", "source_ind_0022"]),
                "source_urls": source_urls(["source_ind_0001", "source_ind_0022"]),
                "source_type": "historical_atlas|official_archaeology_or_heritage",
                "confidence_note": "Coordinate is for map placement; site-level precision varies by location.",
                "review_status": "verified" if name != "Aksai Chin" else "candidate",
                "review_note": "",
            }
        )
        builder._strategic_seq += 1

    builder.add_issue("chronology_uncertainty", "polity", "polity_start_year", "-3300", "regional chronologies vary", "Harappan phase boundaries are archaeological conventions and should not be read as exact political dates.", ["source_ind_0004", "source_ind_0030"], "early_harappan")
    builder.add_issue("legendary_tradition", "event", "year", "not used as polity chronology", "epic/Puranic king lists", "Epic and Puranic traditions belong in the mythological timeline layer, not as exact yearly polity rows without corroboration.", ["source_ind_0004", "source_ind_0051", "source_ind_0052"])
    builder.add_issue("territorial_dispute", "polity", "modern_admin_units_raw", "Jammu and Kashmir context", "India/Pakistan/China claims and actual control differ", "Kashmir-related entries must distinguish accession documents, claims, and actual control.", ["source_ind_0045", "source_ind_0018"], "republic_india")
    builder.add_issue("territorial_dispute", "event", "location", "Aksai Chin region approximate", "multiple claim/control formulations", "Aksai Chin is included only as disputed frontier context; no exact boundary polygon is asserted.", ["source_ind_0045"], "republic_india")
    builder.add_issue("integration_dispute", "polity", "polity_end_year", "1961", "Portuguese sovereignty claim continued briefly in diplomatic terms", "Portuguese India rows use Indian military/political control endpoint for data playback.", ["source_ind_0044"], "portuguese_india")
    builder.add_issue("integration_dispute", "polity", "polity_end_year", "1954", "de facto/de jure transfer dates differ", "French India endpoint uses de facto transfer; de jure treaty chronology should be expanded later.", ["source_ind_0001"], "french_india")
    builder.add_issue("territorial_integration", "event", "year", "1975", "protectorate and monarchy steps precede statehood", "Sikkim integration should be split into protectorate, referendum, amendment, and statehood in a later detailed pass.", ["source_ind_0043", "source_ind_0048"], "republic_india")
    builder.add_issue("princely_state_integration", "polity", "polity_end_year", "1948", "1947 accession crisis versus 1948 plebiscite/administrative consolidation", "Junagadh is singled out because its post-partition accession path differs from a simple 15 August 1947 endpoint.", ["source_ind_0015", "source_ind_0041"], "pstate_junagadh")
    builder.add_issue("princely_state_integration", "polity", "polity_end_year", "1948", "1947 independence claim versus 1948 Police Action/Operation Polo", "Hyderabad is singled out because its integration into India occurred after armed intervention in 1948.", ["source_ind_0015", "source_ind_0041"], "pstate_haydarabad")


def add_mythological_timeline(builder: Builder) -> None:
    m = builder.add_myth
    m(
        "吠陀神话与赞歌传统",
        "ritual_text_context",
        "Vedic hymnic tradition",
        "梨俱吠陀诸神与祭祀赞歌的文化层",
        year=-1500,
        coverage_start=-1500,
        coverage_end=-1000,
        historicity_status="textual_cultural_horizon",
        summary="保存早期吠陀社会的祭祀观念与神话叙事；可作为文化时间线背景播放，不等同于单一政权或可逐年定位事件。",
        cultural_significance="为理解后续印度宗教、王权礼仪和史诗传统提供前史背景。",
        historical_boundary_note="不得把吠陀神话人物或赞歌情节写入确定历史政权年表；仅作为文化和文本传统层展示。",
        source_ids=["source_ind_0004", "source_ind_0031"],
        relative_sequence="01",
        date_precision="literary_layer_range",
        calendar_note="BCE negative years mark textual-cultural horizon not event occurrence.",
        geographic_scope="Northwestern South Asia and early Indo-Gangetic transition",
        people_or_deities="Indra|Agni|Soma|Varuna",
        related_texts="Rigveda",
        source_type="education_source|encyclopedia",
        confidence=72,
        note="年代为学术通行的文本层近似范围；不代表每个叙事的发生年代。",
    )
    m(
        "罗摩衍那史诗传统",
        "epic",
        "Ramayana cycle",
        "罗摩衍那叙事循环",
        year=-300,
        coverage_start=-300,
        coverage_end=200,
        historicity_status="epic_tradition",
        summary="以阿逾陀王子罗摩、悉多和兰卡战争为核心的史诗传统；可在神话时间线中播放为文学和宗教文化事件。",
        cultural_significance="深刻影响印度与东南亚文学、节庆、王权伦理和视觉艺术。",
        historical_boundary_note="不把罗摩、十车王或兰卡战争作为已证实的逐年政治事件；若关联拘萨罗，仅表示史诗地理和文化记忆。",
        source_ids=["source_ind_0052"],
        relative_sequence="02",
        traditional_year="traditional Treta Yuga",
        date_precision="literary_layer_range",
        calendar_note="Timeline year marks approximate literary formation horizon.",
        geographic_scope="North India and wider South Asian cultural sphere",
        location="Ayodhya",
        polity_keys=["kosala"],
        people_or_deities="Rama|Sita|Lakshmana|Hanuman|Ravana",
        related_texts="Valmiki Ramayana",
        source_type="encyclopedia",
        confidence=76,
        note="Britannica 将其列为史诗并说明成书不早于约前300年；地理点为阿逾陀城市级定位。",
    )
    m(
        "太阳王朝谱系传统",
        "puranic_genealogy",
        "Ramayana and Puranic royal genealogies",
        "拘萨罗与太阳王朝谱系",
        year=-600,
        coverage_start=-700,
        coverage_end=-300,
        historicity_status="puranic_chronology",
        summary="史诗和往世书传统把拘萨罗王统追溯到太阳王朝；这是一种王权合法性叙事，而非可直接逐年验证的君主表。",
        cultural_significance="说明史诗谱系如何影响古代和中世纪王朝的祖源叙述。",
        historical_boundary_note="拘萨罗史实行仅保留十六大国时期的可核验政治框架；太阳王朝长谱系不得直接生成年表行。",
        source_ids=["source_ind_0052"],
        relative_sequence="03",
        traditional_year="mythic royal genealogy",
        date_precision="mythic_relative",
        geographic_scope="Kosala and Ayodhya region",
        location="Ayodhya",
        polity_keys=["kosala"],
        people_or_deities="Rama|Ikshvaku|Solar dynasty",
        related_texts="Ramayana|Puranas",
        source_type="encyclopedia",
        confidence=68,
        note="源文本与历史地理有关联，但谱系长度和纪年属于传统叙事。",
    )
    m(
        "摩诃婆罗多史诗传统",
        "epic",
        "Mahabharata cycle",
        "俱卢之战与般度族叙事",
        year=-400,
        coverage_start=-400,
        coverage_end=400,
        historicity_status="epic_tradition",
        summary="以俱卢族内战为核心的史诗传统；其战争年代和历史发生性存在争论，但文本本身是研究早期印度宗教和社会观念的重要资料。",
        cultural_significance="影响印度伦理、政治思想、神学、戏剧和民间叙事。",
        historical_boundary_note="不得将俱卢之战作为已证实的具体年份战争写入历史事件表；可与俱卢、般阇罗作文化地理关联。",
        source_ids=["source_ind_0051", "source_ind_0004"],
        relative_sequence="04",
        traditional_year="traditional Kurukshetra war",
        date_precision="literary_layer_range",
        calendar_note="Timeline year marks approximate epic formation horizon.",
        geographic_scope="Kuru-Panchala and North India",
        location="Kurukshetra",
        polity_keys=["kuru", "panchala"],
        people_or_deities="Krishna|Arjuna|Yudhishthira|Duryodhana|Bhishma",
        related_texts="Mahabharata",
        source_type="encyclopedia|education_source",
        confidence=74,
        note="Britannica 明确战争年代和发生性有争论；年份只用于播放排序。",
    )
    m(
        "薄伽梵歌传统",
        "epic",
        "Mahabharata cycle",
        "薄伽梵歌作为摩诃婆罗多神学层",
        year=-200,
        coverage_start=-200,
        coverage_end=200,
        historicity_status="textual_cultural_horizon",
        summary="《薄伽梵歌》作为史诗中的神学与伦理对话，可作为宗教思想时间线节点展示。",
        cultural_significance="它是后世印度宗教哲学、奉爱传统和政治伦理解读的重要文本。",
        historical_boundary_note="作为文本和思想史节点保存，不作为战场对话的可核验逐年史实。",
        source_ids=["source_ind_0051"],
        relative_sequence="05",
        traditional_year="within Mahabharata narrative",
        date_precision="literary_layer_range",
        geographic_scope="Kurukshetra region",
        location="Kurukshetra",
        polity_keys=["kuru", "panchala"],
        people_or_deities="Krishna|Arjuna",
        related_texts="Bhagavad Gita|Mahabharata",
        source_type="encyclopedia",
        confidence=70,
        note="时间为文本层近似值；地理点跟随史诗设定而非考古确证。",
    )
    m(
        "往世书王统传统",
        "puranic_genealogy",
        "Epic-Puranic royal genealogies",
        "月亮王朝与太阳王朝长谱系",
        year=-1000,
        coverage_start=-1500,
        coverage_end=500,
        historicity_status="puranic_chronology",
        summary="往世书和史诗把许多王朝祖先纳入太阳、月亮等长谱系；这些谱系可用于文化记忆研究，但不能直接当作历史君主年表。",
        cultural_significance="解释南亚多个王族为何借用神话祖源来塑造合法性。",
        historical_boundary_note="凡缺少铭文、钱币或同时代文本支撑的长谱系，只进入神话时间线或争议表，不进入 polity yearly。",
        source_ids=["source_ind_0051", "source_ind_0052"],
        relative_sequence="06",
        traditional_year="mythic dynastic ages",
        date_precision="mythic_relative",
        calendar_note="Relative placement only; no exact historical year.",
        geographic_scope="North India and pan-Indic royal memory",
        people_or_deities="Lunar dynasty|Solar dynasty|Yayati|Puru|Bharata",
        related_texts="Puranas|Mahabharata|Ramayana",
        source_type="encyclopedia",
        confidence=66,
        note="该行概括史诗-往世书谱系传统；需要后续专题研究细分各谱系。",
    )
    m(
        "特里普拉 Rajmala 王统传统",
        "regional_royal_chronicle",
        "Rajmala Tripura kings",
        "《Rajmala》早期特里普拉王表",
        year=100,
        coverage_start=100,
        coverage_end=1399,
        historicity_status="legendary_dynastic_origin",
        summary="《Rajmala》保存特里普拉王族记忆，但其早期王表含大量传说成分；Banglapedia 明确前135位君主缺乏考古或历史来源。",
        cultural_significance="可展示地方王权如何通过古老谱系叙述自身起源。",
        historical_boundary_note="特里普拉 polity 起年采用约1400；公元100年前后传统王表只保存在神话层，不生成史实年度控制区。",
        source_ids=["source_ind_0053", "source_ind_0054"],
        relative_sequence="07",
        traditional_year="traditional 5000 year dynasty",
        date_precision="traditional_chronology",
        calendar_note="Traditional date preserved only as rejected historical chronology.",
        geographic_scope="Tripura and adjoining Bengal hill-plain zone",
        location="Agartala",
        polity_keys=["pstate_tripura"],
        people_or_deities="Durjoy|Ratna Manikya|Manikya kings",
        related_texts="Rajmala",
        source_type="encyclopedia",
        confidence=82,
        note="依据 Banglapedia 对 Rajmala 早期王表缺证的说明；坐标为阿加尔塔拉城市级定位。",
    )
    m(
        "特里普拉 Rajmala 编纂传统",
        "regional_royal_chronicle",
        "Rajmala Tripura kings",
        "1431年《Rajmala》宫廷编纂",
        year=1431,
        coverage_start=1431,
        coverage_end=1431,
        historicity_status="mixed_history_memory",
        summary="《Rajmala》在法王摩尼基亚一世时期由宫廷人员整理和翻译，成为特里普拉王朝叙事的重要文本。",
        cultural_significance="该节点说明传说资料形成书面王朝记忆的时间。",
        historical_boundary_note="编纂事实可作文本史节点；书中远古王表仍需与史实年表分离。",
        source_ids=["source_ind_0053"],
        relative_sequence="08",
        traditional_year="1431 CE",
        date_precision="year",
        calendar_note="Historical compilation year; contents include legendary material.",
        geographic_scope="Tripura court tradition",
        location="Agartala",
        polity_keys=["pstate_tripura"],
        people_or_deities="Dharma Manikya I|Dhurlabhendra Chantai",
        related_texts="Rajmala",
        source_type="encyclopedia",
        confidence=84,
        note="编纂年份来源较明确；文本内容的远古纪年仍分级处理。",
    )
    m(
        "梅瓦尔 Guhila 祖源传统",
        "dynastic_origin_legend",
        "Guhila and Bappa Rawal traditions",
        "530年前后 Guhila 祖源与早期梅瓦尔传说",
        year=530,
        coverage_start=530,
        coverage_end=727,
        historicity_status="legendary_dynastic_origin",
        summary="梅瓦尔早期祖源传统将王族追溯到更早的 Guhila 祖先；但作为政治实体起点需要和后来的 Bappa Rawal/Chittor 传统区分。",
        cultural_significance="反映拉杰普特王族通过祖源和圣地叙事塑造合法性的方式。",
        historical_boundary_note="Udaipur/Mewar polity 起年保留728；530作为祖源传说层，不用于生成史实政权年度行。",
        source_ids=["source_ind_0058", "source_ind_0059"],
        relative_sequence="09",
        traditional_year="530 CE",
        date_precision="traditional_chronology",
        calendar_note="Traditional origin date not used as kingdom start.",
        geographic_scope="Mewar and Chittor region",
        location="Chittorgarh",
        polity_keys=["pstate_udaipur_[in_rajasthan]"],
        people_or_deities="Guhila|Guhadatta|Bappa Rawal",
        related_texts="Guhila inscriptions|Ekalinga Mahatmya|bardic chronicles",
        source_type="encyclopedia",
        confidence=70,
        note="728与734等年份存在来源差异；530应维持传说层而非确定起点。",
    )
    m(
        "梅瓦尔 Bappa Rawal 叙事传统",
        "dynastic_origin_legend",
        "Guhila and Bappa Rawal traditions",
        "Bappa Rawal 与 Chittor 建国记忆",
        year=728,
        coverage_start=728,
        coverage_end=734,
        historicity_status="mixed_history_memory",
        summary="后世传统把 Bappa Rawal 视为梅瓦尔重要奠基者，并叙述其取得 Chittor 的故事；其中神迹、师承和族源部分应与政治史实分开。",
        cultural_significance="保留梅瓦尔政治记忆和地方身份形成的关键叙事。",
        historical_boundary_note="可作为梅瓦尔起点的近似说明，但其中宗教神迹和 bardic 细节不得转写为史实事件。",
        source_ids=["source_ind_0060", "source_ind_0059", "source_ind_0058"],
        relative_sequence="10",
        traditional_year="728 or 734 CE",
        date_precision="approx",
        calendar_note="Competing traditional dates preserved as labels.",
        geographic_scope="Mewar and Chittor region",
        location="Chittorgarh",
        polity_keys=["pstate_udaipur_[in_rajasthan]"],
        people_or_deities="Bappa Rawal|Kalabhoja|Harit Rashi",
        related_texts="Ekalinga Mahatmya|regional chronicles",
        source_type="encyclopedia",
        confidence=72,
        note="Treccani 给出734；现有数据采用728并需保留约略和争议说明。",
    )
    m(
        "占婆 Chamba 建国传说",
        "dynastic_origin_legend",
        "Chamba origin tradition",
        "Maru 从神话地 Kalpagrama 迁出并建 Brahampura",
        year=500,
        coverage_start=500,
        coverage_end=550,
        historicity_status="legendary_dynastic_origin",
        summary="占婆官方地方史称约500年有传奇英雄 Maru 从神话地 Kalpagrama 迁出并建立 Brahampura；这支持保留早期传统，但必须标注不确定。",
        cultural_significance="解释 Chamba 为何可保留约500年的地方王统记忆，同时不把传说细节硬写成确证史实。",
        historical_boundary_note="Chamba polity 可暂用500并标 approx_or_uncertain；Maru 和 Kalpagrama 细节进入神话层。",
        source_ids=["source_ind_0056", "source_ind_0057"],
        relative_sequence="11",
        traditional_year="circa 500 CE",
        date_precision="approx",
        calendar_note="Approximate traditional foundation horizon.",
        geographic_scope="Chamba and Bharmour region",
        location="Bharmour",
        polity_keys=["pstate_chamba"],
        people_or_deities="Maru|Sahilla Varman",
        related_texts="Chamba district tradition",
        source_type="official_history|encyclopedia",
        confidence=86,
        note="官方页面明确使用 legendary hero 和 mythical place；故此行高可信地标注其传说属性。",
    )
    m(
        "百乘王朝往世书长年代",
        "puranic_genealogy",
        "Satavahana Puranic chronology",
        "前3世纪百乘王朝起源传统",
        year=-230,
        coverage_start=-230,
        coverage_end=-101,
        historicity_status="puranic_chronology",
        summary="部分依据往世书的解释把百乘王朝上溯至前3世纪；Britannica 指出更稳妥的百乘势力兴起可放在前1世纪晚期。",
        cultural_significance="保留被剔除的传统年代，便于解释为什么史实表采用前100而不是前230。",
        historical_boundary_note="polity_ind_0027 使用前100至220；前230只作为往世书长年代候选，不进入年度政权表。",
        source_ids=["source_ind_0055", "source_ind_0004"],
        relative_sequence="12",
        traditional_year="3rd century BCE tradition",
        date_precision="traditional_chronology",
        calendar_note="Rejected for polity start; preserved as source tradition.",
        geographic_scope="Deccan and Andhra tradition",
        location="Pratishthana",
        polity_keys=["satavahana"],
        people_or_deities="Simuka|Andhra jati",
        related_texts="Puranas",
        source_type="encyclopedia|education_source",
        confidence=84,
        note="该修正直接对应 release_notes_vIndian.md 的百乘王朝条目。",
    )


def write_dataset(builder: Builder) -> None:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    (DATASET_DIR / "dataset_manifest_vIndian.json").write_text(
        json.dumps(make_manifest(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (DATASET_DIR / "README.md").write_text(
        """# 古印度与印度史 vIndian

This directory is a v03-compatible source dataset for Indian and South Asian
history through 1990.

Current scope:

- Historical South Asia before 1947.
- Republic of India focus after 1947, with Pakistan/Bangladesh context only
  where directly tied to partition, war, or territorial integration.
- BCE years are negative integers and year 0 is omitted.
- Modern geography fields are approximations for indexing, not historical
  boundary claims.
- Princely-state rows imported from Rulers.org are candidate rows and should
  be upgraded with Imperial Gazetteer or official corroboration before being
  used for high-confidence map display.
- Epic, Puranic, dynastic-origin, and regional royal-chronicle traditions are
  stored separately in `mythological_timeline_vIndian.csv`. They may be played
  as a cultural timeline, but they must not generate historical polity yearly
  rows or actual-control map claims.

Regenerate yearly rows:

```bash
python3 scripts/generate_world_history_yearly.py --dataset vIndian
python3 scripts/validate_world_history_dataset.py --dataset vIndian
```
""",
        encoding="utf-8",
    )
    write_csv(DATASET_DIR / DATASET_FILES["polities_master"], MASTER_FIELDS, builder.polities)
    write_csv(DATASET_DIR / DATASET_FILES["rulers_master"], RULERS_MASTER_FIELDS, builder.rulers)
    write_csv(DATASET_DIR / DATASET_FILES["polities_yearly"], YEARLY_FIELDS, [])
    write_csv(DATASET_DIR / DATASET_FILES["capital_events"], CAPITAL_FIELDS, builder.capitals)
    write_csv(DATASET_DIR / DATASET_FILES["historical_events"], EVENT_FIELDS, sorted(builder.events, key=lambda row: (int(row["year"]), int(row["sort_order"]))))
    write_csv(DATASET_DIR / DATASET_FILES["historical_anecdotes"], ANECDOTE_FIELDS, builder.anecdotes)
    write_csv(DATASET_DIR / DATASET_FILES["mythological_timeline"], MYTH_FIELDS, builder.myths)
    write_csv(DATASET_DIR / DATASET_FILES["strategic_locations"], STRATEGIC_FIELDS, builder.strategic)
    write_csv(DATASET_DIR / DATASET_FILES["territory_overrides"], TERRITORY_FIELDS, builder.territories)
    write_csv(DATASET_DIR / DATASET_FILES["issues"], ISSUE_FIELDS, builder.issues)
    write_csv(DATASET_DIR / DATASET_FILES["sources"], SOURCE_FIELDS, [source.__dict__ | {"source_type": source.source_type, "credibility_tier": source.tier, "covers_fields": source.fields, "source_title": source.title, "source_url": source.url} for source in SOURCE_REFS])
    write_csv(DATASET_DIR / DATASET_FILES["validation_report"], VALIDATION_FIELDS, [])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-network", action="store_true", help="Skip Rulers.org import and build only embedded core data.")
    args = parser.parse_args()

    write_templates()
    builder = Builder()
    add_core_polities(builder)
    add_core_rulers(builder)
    import_rulers_org_states(builder, use_network=not args.no_network)
    apply_specific_princely_corrections(builder)
    add_events_capitals_and_context(builder)
    add_anecdotes_strategic_issues(builder)
    add_mythological_timeline(builder)
    write_dataset(builder)
    print(
        "Wrote vIndian seed dataset: "
        f"{len(builder.polities)} polities, {len(builder.rulers)} rulers, "
        f"{len(builder.events)} events, {len(builder.capitals)} capitals, "
        f"{len(builder.myths)} myth timeline rows, "
        f"{len(builder.strategic)} strategic locations."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
