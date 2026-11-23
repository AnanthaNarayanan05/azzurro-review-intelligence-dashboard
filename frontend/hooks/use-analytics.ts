"use client";

import { useQuery } from "@tanstack/react-query";

import type { FilterState } from "@/lib/filters";
import {
  getAspectExamples,
  getAspects,
  getComparison,
  getOverview,
  getPropertyDetail,
  getReview,
  getTrends,
  listReviews,
  type ReviewQuery,
  type TrendParams,
} from "@/services/analytics";
import type { SentimentLabel } from "@/types/analytics";

// Every analytics query key starts with "analytics" so a re-analysis or import can refresh them all.

export function useOverview(filters: FilterState, enabled = true) {
  return useQuery({
    queryKey: ["analytics", "overview", filters],
    queryFn: () => getOverview(filters),
    enabled,
  });
}

export function useComparison(filters: FilterState, enabled = true) {
  return useQuery({
    queryKey: ["analytics", "comparison", filters],
    queryFn: () => getComparison(filters),
    enabled,
  });
}

export function usePropertyDetail(id: number, filters: FilterState, enabled = true) {
  return useQuery({
    queryKey: ["analytics", "property", id, { ...filters, propertyIds: [] }],
    queryFn: () => getPropertyDetail(id, filters),
    enabled,
  });
}

export function useAspects(filters: FilterState, enabled = true) {
  return useQuery({
    queryKey: ["analytics", "aspects", filters],
    queryFn: () => getAspects(filters),
    enabled,
  });
}

export function useAspectExamples(
  aspect: string | null,
  sentiment: SentimentLabel,
  filters: FilterState,
) {
  return useQuery({
    queryKey: ["analytics", "examples", aspect, sentiment, filters],
    queryFn: () => getAspectExamples(aspect as string, sentiment, filters),
    enabled: aspect !== null,
  });
}

export function useTrends(filters: FilterState, params: TrendParams, enabled = true) {
  return useQuery({
    queryKey: ["analytics", "trends", filters, params],
    queryFn: () => getTrends(filters, params),
    enabled,
  });
}

export function useReviews(filters: FilterState, query: ReviewQuery, enabled = true) {
  return useQuery({
    queryKey: ["analytics", "reviews", filters, query],
    queryFn: () => listReviews(filters, query),
    enabled,
    placeholderData: (previous) => previous,
  });
}

export function useReview(id: number | null) {
  return useQuery({
    queryKey: ["analytics", "review", id],
    queryFn: () => getReview(id as number),
    enabled: id !== null,
  });
}
