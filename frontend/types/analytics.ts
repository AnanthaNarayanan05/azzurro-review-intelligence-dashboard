/** Shapes returned by `/api/analytics/*` and `/api/reviews`. See docs/API_SPECIFICATION.md. */

export type DataScope = "genuine" | "synthetic" | "all";
export type SentimentLabel = "positive" | "neutral" | "negative";

export interface Dataset {
  scope: DataScope;
  genuine_reviews: number;
  synthetic_reviews: number;
  mixed: boolean;
  first_review_date: string | null;
  last_review_date: string | null;
}

/** A number never travels without its sample size. */
export interface Measure {
  value: number | null;
  n: number;
  missing: number;
  low_sample: boolean;
}

export interface RatingMeasure extends Measure {
  ci_low?: number | null;
  ci_high?: number | null;
}

export interface DistributionBin {
  label: string;
  from: number;
  to: number;
  n: number;
  share: number | null;
}

export interface SentimentBlock {
  analysed_n: number;
  positive: number;
  neutral: number;
  negative: number;
  positive_share: number | null;
  neutral_share: number | null;
  negative_share: number | null;
  share_denominator: string;
  not_analysed: { no_text: number; non_english: number; pending: number };
}

export interface AspectRow {
  aspect: string;
  display_name: string;
  mentions: number;
  positive: number;
  neutral: number;
  negative: number;
  positive_share: number | null;
  negative_share: number | null;
  mention_rate: number | null;
  low_sample: boolean;
  property_id?: number;
}

export interface AspectExample {
  review_id: number;
  property_id: number;
  review_date: string;
  is_synthetic: boolean;
  sentiment: SentimentLabel;
  evidence_text: string;
  matched_term: string;
  source_field: string;
}

export interface TopAspect extends AspectRow {
  examples?: AspectExample[];
}

export interface PropertyRating {
  property_id: number;
  name: string;
  reviews: number;
  rating: Measure;
}

export interface Overview {
  dataset: Dataset;
  reviews: { n: number; with_text_analysis: number };
  min_sample: number;
  rating: Measure & { distribution: DistributionBin[]; scale: string };
  sentiment: SentimentBlock;
  properties: PropertyRating[];
  aspects: { most_praised: AspectRow[]; most_criticised: AspectRow[]; min_mentions: number };
}

export interface PropertyDetail extends Overview {
  top_praise: TopAspect[];
  top_complaints: TopAspect[];
}

export interface ComparisonRow {
  property_id: number;
  name: string;
  reviews: number;
  rating: RatingMeasure;
  sentiment: SentimentBlock;
  aspects: AspectRow[];
}

export type RankingStatus = "ranked" | "difference_not_significant" | "insufficient_data";

export interface Comparison {
  dataset: Dataset;
  properties: ComparisonRow[];
  rating_ranking: {
    status: RankingStatus;
    reason: string | null;
    best: number | null;
    worst: number | null;
    ordered: number[];
  };
  min_sample: number;
  min_aspect_mentions: number;
  note: string;
}

export interface AspectSummary {
  items: AspectRow[];
  analysed_reviews: number;
  min_mentions: number;
  definition: string;
}

export type TrendMetric =
  | "volume"
  | "avg_rating"
  | "sentiment_positive_share"
  | "sentiment_negative_share"
  | "aspect_negative_share";
export type Granularity = "week" | "month";

export interface TrendPoint {
  period_start: string;
  period_end: string;
  n: number;
  value: number | null;
  complete: boolean;
  low_sample: boolean;
}

export type ChangeStatus =
  | "increase"
  | "decrease"
  | "no_significant_change"
  | "insufficient_data"
  | "descriptive";

export interface TrendWindow {
  from: string;
  to: string;
  n: number;
}

export interface TrendChange {
  status: ChangeStatus;
  reason?: string;
  recent_window: TrendWindow;
  previous_window: TrendWindow;
  recent_value?: number | null;
  previous_value?: number | null;
  difference?: number | null;
  relative_change?: number | null;
  ci_low?: number | null;
  ci_high?: number | null;
  practical_threshold?: number;
}

export interface Trends {
  metric: TrendMetric;
  granularity: Granularity;
  aspect: string | null;
  as_of: string;
  window_periods: number;
  min_sample: number;
  week_definition: string;
  series: TrendPoint[];
  change: TrendChange;
  dataset: Dataset;
}

export interface ReviewAspectLabel {
  aspect: string;
  display_name: string;
  label: SentimentLabel;
}

export interface ReviewItem {
  id: number;
  property_id: number;
  property_name: string;
  review_date: string;
  rating: number | null;
  title: string | null;
  positive_text: string | null;
  negative_text: string | null;
  body_text: string | null;
  language: string | null;
  source: string;
  is_synthetic: boolean;
  analysis_status: "analysed" | "no_text" | "non_english" | null;
  sentiment: { label: SentimentLabel; score: number } | null;
  aspects: ReviewAspectLabel[];
}

export interface ReviewMention {
  aspect: string;
  display_name: string;
  label: SentimentLabel;
  score: number;
  source_field: string;
  matched_term: string;
  evidence_text: string;
}

export interface ReviewDetail extends ReviewItem {
  language_detected: boolean;
  traveller_type: string | null;
  reviewer_country: string | null;
  room_type: string | null;
  stay_nights: number | null;
  source_url: string | null;
  imported_at: string;
  segments: { segment: string; label: SentimentLabel; score: number; model_name: string }[];
  mentions: ReviewMention[];
}

export type ReviewSort = "newest" | "oldest" | "rating_desc" | "rating_asc";

// ---------------------------------------------------------------------------------------------
// Insights (Phase 6)
// ---------------------------------------------------------------------------------------------
export type InsightType =
  | "recurring_complaint"
  | "strength"
  | "emerging_negative_trend"
  | "property_issue"
  | "cross_property_issue"
  | "opportunity";

export type EvidenceStrength = "strong" | "moderate" | "limited";

/** The exact filter that reproduces an insight's supporting reviews. */
export interface InsightFilters {
  property_ids: number[];
  aspect: string;
  aspect_sentiment: SentimentLabel | null;
  date_from: string;
  date_to: string;
  data_scope: DataScope;
}

export interface InsightEvidence {
  review_id: number;
  excerpt: string;
  rank: number;
  property_id: number;
  property_name: string;
  review_date: string;
  rating: number | null;
  is_synthetic: boolean;
}

export interface InsightMetrics {
  rule: InsightType;
  filters: InsightFilters;
  thresholds: Record<string, number | string>;
  evidence: { supporting_reviews: number; months_spanned: number; strength_rule: string };
  generation: {
    as_of: string | null;
    analysis_run_id: number | null;
    reviews_in_scope: number;
    sentiment_engine: string | null;
    lexicon_version: string | null;
  };
  [key: string]: unknown;
}

export interface Insight {
  id: number;
  insight_type: InsightType;
  scope: "portfolio" | "property" | "multi_property";
  data_scope: DataScope;
  aspect: { key: string; display_name: string } | null;
  title: string;
  explanation: string;
  recommended_action: string;
  supporting_review_count: number;
  period_start: string;
  period_end: string;
  evidence_strength: EvidenceStrength;
  generation_method: "template" | "llm";
  generated_at: string;
  properties: { id: number; name: string }[];
  evidence: InsightEvidence[];
  metrics: InsightMetrics;
}

export interface InsightList {
  data: Insight[];
  meta: {
    page: number;
    page_size: number;
    total: number;
    data_scope: DataScope;
    generated_at: string | null;
    stale: boolean;
    analysis_run_id: number | null;
    dataset: Dataset;
  };
}

export interface GenerationResult {
  data_scope: DataScope;
  as_of: string | null;
  created: number;
  replaced: number;
  rejected_by_validator: number;
  by_type: Partial<Record<InsightType, number>>;
  checked_property_aspects: number;
  below_mention_floor: number;
  comparisons_skipped_too_few: number;
  notes: string[];
}
