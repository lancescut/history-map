export interface Metadata {
  data_version: string;
  generated_at: string;
  year_min: number;
  year_max: number;
  year_count: number;
  has_year_zero: boolean;
  polity_count: number;
  ruler_count: number;
  yearly_row_count: number;
  capital_event_count: number;
  capital_polity_count: number;
  capital_migration_count: number;
  capital_migration_years: number[];
  territory_polity_count: number;
  territory_missing_count: number;
  territory_low_confidence_count: number;
  territory_coverage_ratio: number;
  territory_label: string;
  territory_boundary_level: string;
  admin_boundary_source: string;
  admin_boundary_source_release: string;
  admin_boundary_license: string;
  admin_boundary_attribution: string;
  admin_boundary_feature_count: number;
  admin_boundary_level: string;
  county_unit_count: number;
  county_units_path: string;
  county_index_path: string;
  summary_admin_boundary_feature_count: number;
  summary_admin_boundary_path: string;
  modern_admin_reference_feature_count: number;
  modern_admin_reference_path: string;
  admin_boundary_crs: string;
  territory_geometry_quality: {
    min_coordinate_count: number;
    max_coordinate_count: number;
    formal_rect_fixture: boolean;
  };
  max_concurrent_polities: number;
  max_concurrent_polity_years: number[];
  max_concurrent_territory_coverage: number;
  historical_event_count?: number;
  historical_event_years?: number[];
  historical_event_covered_year_count?: number;
  historical_event_full_year_coverage?: boolean;
  historical_event_marker_count?: number;
  historical_event_marker_years?: number[];
  historical_anecdote_count?: number;
  historical_anecdote_years?: number[];
  historical_anecdote_marker_count?: number;
  historical_context_count?: number;
  historical_context_years?: number[];
  historical_context_covered_year_count?: number;
  historical_context_full_year_coverage?: boolean;
}

export type CapitalEventType =
  | "initial_capital"
  | "relocation"
  | "co_capital"
  | "temporary_capital"
  | "disputed";

export interface CapitalEvent {
  capital_event_id: string;
  polity_id: string;
  polity_name: string;
  polity_display_name?: string;
  capital_name_historical: string;
  capital_name_modern: string;
  valid_from_year: number;
  valid_from_label: string;
  valid_to_year: number;
  valid_to_label: string;
  longitude: number;
  latitude: number;
  is_primary: boolean;
  event_type: CapitalEventType;
  location_precision: "exact" | "city" | "region" | "approximate" | "unknown";
  source_titles: string;
  source_urls: string;
  source_raw: string;
  confidence_score: number;
  confidence_note: string;
  is_disputed: boolean;
}

export interface CapitalMigration {
  migration_id: string;
  polity_id: string;
  polity_name: string;
  polity_display_name?: string;
  year: number;
  year_label: string;
  from_capital_event_id: string;
  to_capital_event_id: string;
  from_capital_name: string;
  to_capital_name: string;
  from_coordinates: [number, number];
  to_coordinates: [number, number];
  is_disputed: boolean;
  confidence_score: number;
  label: string;
}

export interface CapitalQuality {
  status: "missing" | "out_of_range" | "present" | "disputed";
  label: string;
  has_dispute: boolean;
  lowest_confidence_score: number | null;
  location_precision: string;
  source_status: string;
}

export interface TerritoryInfo {
  geometry_ref: string | null;
  territory_status: "matched" | "matched_low_confidence" | "missing";
  territory_method: "modern_admin_approximation";
  approx_area_km2: number | null;
  match_confidence: number;
  matched_admin_ids: string[];
  matched_admin_units: string[];
  matched_county_count: number;
  county_index_ref: string | null;
  boundary_level: "county" | "province" | "country" | "missing";
  match_resolution: string;
  coarse_fallback_reason: string;
  source_text: string;
  cross_border_iso_codes?: string[];
  cross_border_country_names?: string[];
  geometry_source?: string;
  geometry_source_license?: string;
  geometry_source_attribution?: string;
  county_geometry_source?: string;
  match_source?: string;
  confidence_note?: string;
  geometry_coordinate_count?: number;
  generated_at?: string;
  label: string;
  centroid?: [number, number];
}

export interface RulerSummary {
  ruler_id: string;
  ruler_name: string;
  ruler_title: string;
  ruler_temple_name: string;
  ruler_posthumous_name: string;
  ruler_personal_name: string;
  era_names: string;
  ruler_reign_start_year: number | null;
  ruler_reign_end_year: number | null;
  ruler_source_title: string;
  ruler_source_url: string;
  ruler_confidence_score: number | null;
}

export interface YearPolity {
  polity_id: string;
  polity_name: string;
  polity_aliases: string;
  polity_display_name?: string;
  polity_name_disambiguation?: string;
  polity_name_review_status?: "verified" | "needs_review" | string;
  polity_name_risk_flags?: string;
  macro_period: string;
  dynasty_name: string;
  polity_type: string;
  is_nomadic?: boolean;
  is_steppe_origin?: boolean;
  polity_start_year: number | null;
  polity_end_year: number | null;
  capital_modern_raw: string;
  modern_admin_units_raw: string;
  ruling_family_or_clan: string;
  ethnicity_or_group: string;
  founder: string;
  last_ruler: string;
  destroyed_by_or_successor: string;
  polity_source_titles: string;
  polity_source_urls: string;
  polity_source_raw: string;
  confidence_score: number | null;
  rulers: RulerSummary[];
  capitals: CapitalEvent[];
  active_capital_event_ids: string[];
  has_capital_migration_in_year: boolean;
  capital_quality: CapitalQuality;
  territory: TerritoryInfo;
  quality: {
    confidence_score: number | null;
    has_dispute: boolean;
    has_unmatched_ruler: boolean;
  };
}

export interface YearData {
  year: number;
  year_label: string;
  polity_count: number;
  polities: YearPolity[];
  capital_migrations: CapitalMigration[];
  has_capital_migration_in_year: boolean;
  historical_events: HistoricalEvent[];
  historical_anecdotes?: HistoricalAnecdote[];
  historical_contexts?: HistoricalContext[];
}

export interface CapitalsData {
  data_version: string;
  generated_at: string;
  capital_events: CapitalEvent[];
  capital_migrations: CapitalMigration[];
  by_polity: Record<string, CapitalEvent[]>;
  migrations_by_year: Record<string, CapitalMigration[]>;
}

export interface SearchEntry {
  alias: string;
  normalized: string;
  entity_type: "polity" | "ruler" | "capital";
  entity_id: string;
  label: string;
  polity_id?: string;
  polity_display_name?: string;
  capital_event_id?: string;
  start_year?: number | null;
  end_year?: number | null;
  longitude?: number;
  latitude?: number;
}

export interface AliasIndex {
  entries: SearchEntry[];
}

export type IssueType =
  | "merged_v02_contexts"
  | "partial_boundary"
  | "chronology_variant"
  | string;

export interface PolityIssue {
  issue_id: string;
  issue_type: IssueType;
  entity_type: "polity" | "ruler" | string;
  polity_id: string;
  polity_name: string;
  polity_display_name?: string;
  field_name: string;
  selected_value: string;
  alternative_values: string;
  source_titles: string;
  source_urls: string;
  note: string;
  action_in_v03: string;
}

export interface IssuesData {
  data_version: string;
  issues: PolityIssue[];
}

export interface ValidationCheck {
  check_name: string;
  status: "PASS" | "WARN" | "FAIL" | string;
  checked_count: string;
  issue_count: string;
  details: string;
}

export interface ValidationData {
  data_version: string;
  checks: ValidationCheck[];
}

export type HistoricalEventType =
  | "unification"
  | "war"
  | "dynasty_start"
  | "dynasty_end"
  | "event"
  | "polity_start"
  | "polity_end"
  | "allusion"
  | string;

export type HistoricalEventItemKind =
  | "core_event"
  | "representative_event"
  | "annual_fact"
  | "context"
  | "annual_chronicle"
  | "range_anchor"
  | "anecdote";

export type HistoricalEventCoverageRole =
  | "exact_year_event"
  | "annual_chronicle"
  | "range_anchor"
  | "nearby_enrichment"
  | "anecdote"
  | string;

export type EducationStage = "小学" | "初中" | "高中" | "大学" | string;

export interface HistoricalEventLocation {
  historical_name: string;
  modern_name: string;
  modern_admin_id: string;
  precision: "exact" | "city" | "region" | "approximate" | string;
  confidence_score: number | null;
  source_titles: string;
  source_urls: string[];
  note: string;
  longitude: number | null;
  latitude: number | null;
}

export interface HistoricalContext {
  context_id: string;
  year: number;
  year_label: string;
  current_year: number;
  title: string;
  description: string;
  start_year: number;
  end_year: number;
  start_label: string;
  end_label: string;
  progress_ratio: number;
  sort_order: number;
  display_priority: number;
  longitude: number | null;
  latitude: number | null;
  location_name: string;
  location_historical_name?: string;
  location_modern_name?: string;
  location_precision?: string;
  location?: HistoricalEventLocation | null;
  source_titles: string;
  source_urls: string[];
  source_type: string;
  confidence_score: number | null;
  confidence_note: string;
}

export interface HistoricalEvent {
  event_id: string;
  year: number;
  year_label: string;
  sort_order: number;
  date_label: string;
  date_precision: "year" | "approx" | "range" | string;
  coverage_role: HistoricalEventCoverageRole;
  coverage_start_year: number;
  coverage_end_year: number;
  coverage_group_id: string;
  item_kind: HistoricalEventItemKind;
  event_type: HistoricalEventType;
  title: string;
  description: string;
  significance: string;
  primary_education_stage: EducationStage;
  education_stage_tags: string[];
  curriculum_basis: string;
  importance_level: number;
  display_priority: number;
  longitude: number | null;
  latitude: number | null;
  related_polity_ids: string[];
  related_people: string[];
  location_name: string;
  location_historical_name?: string;
  location_modern_name?: string;
  location_modern_admin_id?: string;
  location_precision?: string;
  location_confidence_score?: number | null;
  location_source_titles?: string;
  location_source_urls?: string[];
  location_note?: string;
  location?: HistoricalEventLocation | null;
  source_titles: string;
  source_urls: string[];
  source_type: string;
  confidence_score: number | null;
  confidence_note: string;
  fact_review_status?: "verified" | "candidate" | "needs_review" | "rejected" | string;
  review_note?: string;
  anecdote_id?: string;
  anecdote_type?: "chengyu" | "historical_story" | "literary_allusion" | "folk_tale" | string;
  dynasty_name?: string;
  macro_period?: string;
  phrase?: string;
  story_text?: string;
  source_title?: string;
  source_section?: string;
  source_url?: string;
  source_note?: string;
  is_anecdote?: boolean;
}

export interface HistoricalAnecdote extends HistoricalEvent {
  anecdote_id: string;
  anecdote_type: "chengyu" | "historical_story" | "literary_allusion" | "folk_tale" | string;
  item_kind: "anecdote";
  event_type: "allusion";
  coverage_role: "anecdote";
  dynasty_name: string;
  macro_period: string;
  phrase: string;
  story_text: string;
  source_title: string;
  source_section: string;
  source_url: string;
  source_note: string;
  is_anecdote: true;
}

export interface HistoricalEventsData {
  data_version: string;
  generated_at: string;
  event_count: number;
  covered_year_count?: number;
  full_year_coverage?: boolean;
  marker_count?: number;
  events: HistoricalEvent[];
}

export interface HistoricalAnecdotesData {
  data_version: string;
  generated_at: string;
  anecdote_count: number;
  marker_count?: number;
  covered_year_count?: number;
  by_dynasty: Record<string, number>;
  anecdotes: HistoricalAnecdote[];
}

export interface HistoricalContextsData {
  data_version: string;
  generated_at: string;
  context_count: number;
  covered_year_count: number;
  full_year_coverage: boolean;
  context_years: number[];
  contexts: HistoricalContext[];
}

export interface StoryPresetStep {
  year: number;
  narration: string;
  polity_id?: string;
}

export interface StoryPreset {
  preset_id: string;
  title: string;
  subtitle: string;
  default_dwell_ms: number;
  steps: StoryPresetStep[];
}

export interface StoryPresetsData {
  data_version: string;
  generated_at: string;
  preset_count: number;
  presets: StoryPreset[];
}

export interface TerritoryFeatureProperties extends TerritoryInfo {
  polity_id: string;
  polity_name: string;
  polity_display_name?: string;
  polity_name_disambiguation?: string;
  polity_name_review_status?: string;
  polity_name_risk_flags?: string;
  macro_period: string;
  dynasty_name: string;
  polity_type: string;
  is_nomadic?: boolean;
  is_steppe_origin?: boolean;
  color?: string;
  selected?: boolean;
}

export interface CountyUnitProperties {
  admin_id: string;
  name: string;
  aliases: string;
  admin_level: "county";
  source_shape_id: string;
  parent_admin_ids: string[];
  parent_admin_names: string[];
  license: string;
  coordinate_count: number;
  bbox: [number, number, number, number];
  centroid: [number, number];
}

export interface PolityCountyIndexEntry {
  polity_id: string;
  polity_name: string;
  polity_display_name?: string;
  county_ids: string[];
  county_count: number;
  summary_admin_ids: string[];
  summary_admin_units: string[];
  matched_resolution: string;
  match_source: string;
  source_text: string;
}

export interface PolityCountyIndex {
  data_version: string;
  generated_at: string;
  source: string;
  polities: Record<string, PolityCountyIndexEntry>;
}

export interface AppState {
  schema_version: string;
  data_version: string;
  updated_at: string;
  timeline: {
    current_year: number;
    is_playing: boolean;
    playback_speed: number;
    timeline_mode: "current_year";
  };
  map_view: {
    center: [number, number];
    zoom: number;
    bearing: number;
    pitch: number;
  };
  selection: {
    selected_polity_id: string | null;
  };
  layers: {
    territories: boolean;
    territory_labels: boolean;
    modern_admin_reference: boolean;
    capitals: boolean;
    capital_migration_paths: boolean;
    physical_rivers: boolean;
    physical_lakes: boolean;
    physical_glaciers: boolean;
    geographic_lines: boolean;
    modern_country_boundaries: boolean;
    cn_border_overlay: boolean;
  };
  filters: {
    polity_types: string[];
    territory_status: "all" | "has_territory" | "missing";
    min_confidence_score: number;
    show_disputed: boolean;
    show_unmatched_ruler: boolean;
    search_keyword: string;
  };
  ui: {
    side_panel_open: boolean;
    auto_follow_main_polity: boolean;
    show_historical_anecdotes: boolean;
    panel_collapsed: {
      layers_polity: boolean;
      layers_physical: boolean;
      layers_demo: boolean;
      legend: boolean;
    };
  };
}
