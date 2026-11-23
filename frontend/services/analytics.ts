import { filtersToApiQuery, toQueryString, type FilterState } from "@/lib/filters";
import { apiFetch } from "@/services/api-client";
import type {
  AspectExample,
  AspectSummary,
  Comparison,
  Granularity,
  Overview,
  PropertyDetail,
  ReviewDetail,
  ReviewItem,
  ReviewSort,
  SentimentLabel,
  TrendMetric,
  Trends,
} from "@/types/analytics";
import type { DataResponse, ListResponse } from "@/types/api";

const noStore = { cache: "no-store" } as const;

function get<T>(path: string, query: Record<string, string | number | undefined>) {
  return apiFetch<DataResponse<T>>(`${path}${toQueryString(query)}`, noStore).then((r) => r.data);
}

export function getOverview(filters: FilterState): Promise<Overview> {
  return get("/api/analytics/overview", filtersToApiQuery(filters));
}

export function getComparison(filters: FilterState): Promise<Comparison> {
  return get("/api/analytics/comparison", filtersToApiQuery(filters));
}

export function getPropertyDetail(id: number, filters: FilterState): Promise<PropertyDetail> {
  // The property is chosen by the URL path, so a property filter is ignored here.
  return get(
    `/api/analytics/properties/${id}`,
    filtersToApiQuery({ ...filters, propertyIds: [] }),
  );
}

export function getAspects(filters: FilterState): Promise<AspectSummary> {
  return get("/api/analytics/aspects", filtersToApiQuery(filters));
}

export function getAspectExamples(
  aspect: string,
  sentiment: SentimentLabel,
  filters: FilterState,
  limit = 5,
): Promise<AspectExample[]> {
  return get(`/api/analytics/aspects/${encodeURIComponent(aspect)}/examples`, {
    ...filtersToApiQuery(filters),
    sentiment,
    limit,
  });
}

export interface TrendParams {
  metric: TrendMetric;
  granularity: Granularity;
  aspect?: string;
}

export function getTrends(filters: FilterState, params: TrendParams): Promise<Trends> {
  return get("/api/analytics/trends", {
    ...filtersToApiQuery(filters),
    metric: params.metric,
    granularity: params.granularity,
    aspect: params.aspect,
  });
}

export interface ReviewQuery {
  q: string;
  ratingMin: string;
  ratingMax: string;
  sentiment: SentimentLabel | "";
  aspect: string;
  aspectSentiment: SentimentLabel | "";
  sort: ReviewSort;
  page: number;
  pageSize: number;
}

export function listReviews(
  filters: FilterState,
  query: ReviewQuery,
): Promise<ListResponse<ReviewItem>> {
  const params = {
    ...filtersToApiQuery(filters),
    q: query.q.trim(),
    rating_min: query.ratingMin,
    rating_max: query.ratingMax,
    sentiment: query.sentiment,
    aspect: query.aspect,
    aspect_sentiment: query.aspect ? query.aspectSentiment : "",
    sort: query.sort,
    page: query.page,
    page_size: query.pageSize,
  };
  return apiFetch<ListResponse<ReviewItem>>(`/api/reviews${toQueryString(params)}`, noStore);
}

export function getReview(id: number): Promise<ReviewDetail> {
  return apiFetch<DataResponse<ReviewDetail>>(`/api/reviews/${id}`, noStore).then((r) => r.data);
}
