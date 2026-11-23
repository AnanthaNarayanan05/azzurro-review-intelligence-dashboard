import type { Insight, InsightEvidence } from "@/types/analytics";

export const evidence = (over: Partial<InsightEvidence> = {}): InsightEvidence => ({
  review_id: 11,
  excerpt: "The room was dirty and the bathroom smelled.",
  rank: 1,
  property_id: 1,
  property_name: "Alpha Hotel",
  review_date: "2026-02-10",
  rating: 4,
  is_synthetic: false,
  ...over,
});

export const insight = (over: Partial<Insight> = {}): Insight => ({
  id: 1,
  insight_type: "recurring_complaint",
  scope: "property",
  data_scope: "genuine",
  aspect: { key: "cleanliness", display_name: "Cleanliness" },
  title: "Cleanliness is a recurring complaint at Alpha Hotel",
  explanation: "Of 14 reviews that mention cleanliness, 10 (71%) were negative.",
  recommended_action: "Review housekeeping standards and room inspection checks.",
  supporting_review_count: 10,
  period_start: "2026-01-01",
  period_end: "2026-03-30",
  evidence_strength: "moderate",
  generation_method: "template",
  generated_at: "2026-03-31T09:00:00",
  properties: [{ id: 1, name: "Alpha Hotel" }],
  evidence: [evidence(), evidence({ review_id: 12, excerpt: "Dust everywhere.", rank: 2, rating: null })],
  metrics: {
    rule: "recurring_complaint",
    filters: {
      property_ids: [1],
      aspect: "cleanliness",
      aspect_sentiment: "negative",
      date_from: "2026-01-01",
      date_to: "2026-03-30",
      data_scope: "genuine",
    },
    thresholds: {},
    evidence: { supporting_reviews: 10, months_spanned: 3, strength_rule: "" },
    generation: {
      as_of: "2026-03-30",
      analysis_run_id: 1,
      reviews_in_scope: 100,
      sentiment_engine: "vader",
      lexicon_version: "1.0.0",
    },
  },
  ...over,
});
