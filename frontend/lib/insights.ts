import { toQueryString } from "@/lib/filters";
import type { EvidenceStrength, Insight, InsightType } from "@/types/analytics";

export const INSIGHT_PAGE_SIZE = 20;

export const TYPE_LABELS: Record<InsightType, string> = {
  emerging_negative_trend: "Emerging negative trend",
  cross_property_issue: "Cross-property issue",
  property_issue: "Property-specific issue",
  recurring_complaint: "Recurring complaint",
  opportunity: "Opportunity",
  strength: "Strength to preserve",
};

export const STRENGTH_LABELS: Record<EvidenceStrength, string> = {
  strong: "Strong evidence",
  moderate: "Moderate evidence",
  limited: "Limited evidence",
};

const TYPES = Object.keys(TYPE_LABELS) as InsightType[];
const STRENGTHS = Object.keys(STRENGTH_LABELS) as EvidenceStrength[];

export interface InsightQuery {
  type: InsightType | "";
  strength: EvidenceStrength | "";
  page: number;
  pageSize: number;
}

/** Reads the Insights page's own URL parameters; the global filters are read separately. */
export function parseInsightQuery(params: URLSearchParams): InsightQuery {
  const type = params.get("type") as InsightType | null;
  const strength = params.get("strength") as EvidenceStrength | null;
  const page = Number(params.get("page") ?? "1");
  return {
    type: type && TYPES.includes(type) ? type : "",
    strength: strength && STRENGTHS.includes(strength) ? strength : "",
    page: Number.isInteger(page) && page >= 1 ? page : 1,
    pageSize: INSIGHT_PAGE_SIZE,
  };
}

export function hasInsightFilters(query: InsightQuery): boolean {
  return query.type !== "" || query.strength !== "";
}

/**
 * The Reviews explorer filtered to exactly the reviews an insight is based on. The explorer's total
 * equals the insight's `supporting_review_count`, so the claim can be checked in one click.
 */
export function supportingReviewsHref(insight: Insight): string {
  const f = insight.metrics.filters;
  return `/reviews${toQueryString({
    properties: f.property_ids.join(","),
    from: f.date_from,
    to: f.date_to,
    scope: f.data_scope === "genuine" ? "" : f.data_scope,
    aspect: f.aspect,
    aspect_sentiment: f.aspect_sentiment ?? "",
  })}`;
}

/** Opens one example review in the explorer's drawer. */
export function exampleReviewHref(insight: Insight, reviewId: number): string {
  return `/reviews${toQueryString({
    scope: insight.data_scope === "genuine" ? "" : insight.data_scope,
    review: reviewId,
  })}`;
}
