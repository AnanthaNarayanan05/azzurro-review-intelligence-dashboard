"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { FilterState } from "@/lib/filters";
import type { InsightQuery } from "@/lib/insights";
import { generateInsights, listInsights } from "@/services/insights";

// Keys start with "analytics" so an import, demo load or re-analysis refreshes insights (and their
// "out of date" flag) together with every other figure.
export function useInsights(filters: FilterState, query: InsightQuery, enabled = true) {
  return useQuery({
    queryKey: ["analytics", "insights", filters.propertyIds, filters.dataScope, query],
    queryFn: () => listInsights(filters, query),
    enabled,
    placeholderData: (previous) => previous,
  });
}

export function useGenerateInsights() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dataScope: FilterState["dataScope"]) => generateInsights(dataScope),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["analytics", "insights"] }),
  });
}
