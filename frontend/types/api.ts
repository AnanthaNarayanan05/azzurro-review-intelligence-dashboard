/**
 * Types mirroring the backend API contract (backend/app/schemas).
 * Keep in sync with docs/API_SPECIFICATION.md.
 */

export interface DataResponse<T> {
  data: T;
}

export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface ListResponse<T> {
  data: T[];
  meta: PageMeta;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details: unknown[];
}

export interface HealthStatus {
  status: "ok" | "degraded";
  version: string;
  environment: string;
  database: "ok" | "unavailable";
  database_backend: string;
  sentiment_engine: string;
  llm_enabled: boolean;
}

// ---------------------------------------------------------------------------------------------
// Properties
// ---------------------------------------------------------------------------------------------
export interface PropertyAlias {
  id: number;
  alias_normalised: string;
}

export interface Property {
  id: number;
  code: string;
  name: string;
  location: string | null;
  is_active: boolean;
  /** Genuine imported reviews. Synthetic demo reviews are counted separately. */
  review_count: number;
  synthetic_review_count: number;
  aliases: PropertyAlias[];
}

// ---------------------------------------------------------------------------------------------
// Imports
// ---------------------------------------------------------------------------------------------
export type IssueOutcome = "rejected" | "duplicate" | "warning";
export type ImportStatus = "previewed" | "processing" | "completed" | "failed";
export type DateFormat = "auto" | "iso" | "dmy" | "mdy";

export interface ImportFieldSpec {
  key: string;
  label: string;
  description: string;
  required: "always" | "one_of" | "no";
}

export interface PropertyValue {
  value: string;
  count: number;
  suggested_property_id: number | null;
  match_type: "alias" | "name" | "code" | "similar" | null;
}

export interface PropertyValues {
  values: PropertyValue[];
  truncated: boolean;
}

export interface ImportPreview {
  import_id: number;
  filename: string;
  source_type: "csv" | "xlsx";
  total_rows: number;
  columns: string[];
  sheets: string[];
  sheet: string | null;
  encoding: string | null;
  delimiter: string | null;
  sample_rows: Record<string, string>[];
  suggested_mapping: Record<string, string | null>;
  property_values: PropertyValues;
  already_imported_as: number | null;
}

export interface IssueSummaryItem {
  outcome: IssueOutcome;
  code: string;
  count: number;
}

export interface ImportReport {
  id: number;
  filename: string;
  source_type: string;
  source_name: string;
  status: ImportStatus;
  is_synthetic: boolean;
  rating_scale_max: number;
  total_rows: number;
  imported_rows: number;
  updated_rows: number;
  duplicate_rows: number;
  rejected_rows: number;
  warning_count: number;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  column_mapping: Record<string, string>;
  issue_summary: IssueSummaryItem[];
}

export interface ImportIssue {
  id: number;
  row_number: number;
  outcome: IssueOutcome;
  field: string | null;
  code: string;
  message: string;
  duplicate_of_review_id: number | null;
}

export interface CommitRequest {
  column_mapping: Record<string, string>;
  property_mapping: Record<string, number>;
  fixed_property_id: number | null;
  rating_scale_max: number;
  date_format: DateFormat;
  source_name: string;
  is_synthetic: boolean;
  sheet: string | null;
  remember_aliases: boolean;
}

export interface DemoStatus {
  loaded: boolean;
  synthetic_review_count: number;
  import_ids: number[];
  notice: string;
}

export interface RemovedResult {
  removed_reviews: number;
}

export type AnalysisScope = "pending" | "all";

export interface AnalysisRun {
  id: number;
  triggered_by: string;
  sentiment_engine: string;
  aspect_lexicon_version: string;
  status: string;
  reviews_processed: number;
  started_at: string;
  completed_at: string | null;
}

export interface AnalysisStatus {
  engine: string;
  lexicon_version: string;
  total_reviews: number;
  analysed: number;
  no_text: number;
  non_english: number;
  pending: number;
  latest_run: AnalysisRun | null;
  notes: string[];
}

export interface AnalysisRunResult {
  run: AnalysisRun | null;
  processed: number;
  analysed: number;
  no_text: number;
  non_english: number;
  aspect_mentions: number;
}
