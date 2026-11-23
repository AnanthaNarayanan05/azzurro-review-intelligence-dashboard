import { filtersToApiQuery, toQueryString, type FilterState } from "@/lib/filters";
import type { InsightQuery } from "@/lib/insights";
import { apiFetch } from "@/services/api-client";
import type { GenerationResult, InsightList } from "@/types/analytics";
import type { DataResponse } from "@/types/api";

/** Insights are not date-filtered (each has its own period), so only property and data scope apply. */
export function listInsights(filters: FilterState, query: InsightQuery): Promise<InsightList> {
  const { data_scope, property_ids } = filtersToApiQuery(filters);
  return apiFetch<InsightList>(
    `/api/insights${toQueryString({
      data_scope,
      property_ids,
      insight_type: query.type,
      evidence_strength: query.strength,
      page: query.page,
      page_size: query.pageSize,
    })}`,
    { cache: "no-store" },
  );
}

export async function generateInsights(dataScope: FilterState["dataScope"]): Promise<GenerationResult> {
  return (
    await apiFetch<DataResponse<GenerationResult>>("/api/insights/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data_scope: dataScope }),
    })
  ).data;
}
