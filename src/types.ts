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
  admin_boundary_source: string;
  admin_boundary_source_release: string;
  admin_boundary_license: string;
  admin_boundary_attribution: string;
  admin_boundary_feature_count: number;
  admin_boundary_crs: string;
  territory_geometry_quality: {
    min_coordinate_count: number;
    max_coordinate_count: number;
    formal_rect_fixture: boolean;
  };
  max_concurrent_polities: number;
  max_concurrent_polity_years: number[];
  max_concurrent_territory_coverage: number;
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
  source_text: string;
  geometry_source?: string;
  geometry_source_license?: string;
  geometry_source_attribution?: string;
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
  macro_period: string;
  dynasty_name: string;
  polity_type: string;
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
  capital_event_id?: string;
  start_year?: number | null;
  end_year?: number | null;
  longitude?: number;
  latitude?: number;
}

export interface AliasIndex {
  entries: SearchEntry[];
}

export interface TerritoryFeatureProperties extends TerritoryInfo {
  polity_id: string;
  polity_name: string;
  macro_period: string;
  dynasty_name: string;
  polity_type: string;
  color?: string;
  selected?: boolean;
}

export interface AppState {
  schema_version: "1.2.0";
  data_version: "v03";
  updated_at: string;
  timeline: {
    current_year: number;
    is_playing: boolean;
    playback_speed: number;
  };
  map_view: {
    center: [number, number];
    zoom: number;
    bearing: number;
    pitch: number;
  };
  selection: {
    selected_polity_id: string | null;
    selected_capital_event_id: string | null;
  };
  layers: {
    territories: boolean;
    territory_labels: boolean;
    modern_admin_reference: boolean;
    capitals: boolean;
    capital_migration_paths: boolean;
  };
  filters: {
    territory_status: "all" | "has_territory" | "missing";
    min_confidence_score: number;
    show_disputed: boolean;
  };
}
