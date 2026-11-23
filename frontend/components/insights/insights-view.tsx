"use client";

import { ChevronLeft, ChevronRight, Lightbulb, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { NoData } from "@/components/dashboard/no-data";
import { DatasetBanner } from "@/components/filters/dataset-banner";
import { FilterBar } from "@/components/filters/filter-bar";
import { InsightCard } from "@/components/insights/insight-card";
import { EmptyState } from "@/components/states/empty-state";
import { QueryView } from "@/components/states/query-view";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useFilters, useUrlParams } from "@/hooks/use-filters";
import { useGenerateInsights, useInsights } from "@/hooks/use-insights";
import { formatCount, formatDateTime } from "@/lib/format";
import {
  STRENGTH_LABELS,
  TYPE_LABELS,
  hasInsightFilters,
  parseInsightQuery,
} from "@/lib/insights";
import type { DataScope, EvidenceStrength, InsightList, InsightType } from "@/types/analytics";

const ANY = "any";

function reviewsInScope(dataset: InsightList["meta"]["dataset"], scope: DataScope): number {
  if (scope === "genuine") return dataset.genuine_reviews;
  if (scope === "synthetic") return dataset.synthetic_reviews;
  return dataset.genuine_reviews + dataset.synthetic_reviews;
}

export function InsightsView() {
  const { filters } = useFilters();
  const { params, setParams } = useUrlParams();
  const query = parseInsightQuery(params);
  const insights = useInsights(filters, query);
  const generate = useGenerateInsights();
  const filtered = hasInsightFilters(query);

  function run() {
    generate.mutate(filters.dataScope, {
      onSuccess: (result) => {
        const note =
          result.rejected_by_validator > 0
            ? ` ${result.rejected_by_validator} draft(s) were rejected because they were not fully backed by the data.`
            : "";
        toast.success(
          result.created === 0
            ? "No insight met the evidence rules for this data."
            : `Generated ${formatCount(result.created)} insights.${note}`,
        );
      },
      onError: (error: Error) => toast.error(error.message),
    });
  }

  const generateButton = (label: string) => (
    <Button type="button" onClick={run} disabled={generate.isPending}>
      <RefreshCw className={generate.isPending ? "animate-spin" : undefined} aria-hidden />
      {generate.isPending ? "Generating…" : label}
    </Button>
  );

  return (
    <div className="flex flex-col gap-6">
      <FilterBar showDates={false} />

      <QueryView query={insights} skeleton={<Skeleton className="h-96 w-full" />} errorTitle="Could not load insights">
        {(data) => {
          const pages = Math.max(1, Math.ceil(data.meta.total / data.meta.page_size));
          const inScope = reviewsInScope(data.meta.dataset, data.meta.data_scope);
          return (
            <>
              <DatasetBanner dataset={data.meta.dataset} />

              <section aria-label="Insight controls" className="flex flex-col gap-4 rounded-lg border bg-card p-4">
                <div className="flex flex-wrap items-end gap-3">
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor="insight-type" className="text-xs text-muted-foreground">
                      Type
                    </Label>
                    <Select
                      value={query.type || ANY}
                      onValueChange={(v) => setParams({ type: v === ANY ? null : v })}
                    >
                      <SelectTrigger id="insight-type" className="w-56">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={ANY}>All types</SelectItem>
                        {(Object.keys(TYPE_LABELS) as InsightType[]).map((type) => (
                          <SelectItem key={type} value={type}>
                            {TYPE_LABELS[type]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor="insight-strength" className="text-xs text-muted-foreground">
                      Evidence
                    </Label>
                    <Select
                      value={query.strength || ANY}
                      onValueChange={(v) => setParams({ strength: v === ANY ? null : v })}
                    >
                      <SelectTrigger id="insight-strength" className="w-48">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={ANY}>Any strength</SelectItem>
                        {(Object.keys(STRENGTH_LABELS) as EvidenceStrength[]).map((s) => (
                          <SelectItem key={s} value={s}>
                            {STRENGTH_LABELS[s]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  {filtered && (
                    <Button type="button" variant="outline" onClick={() => setParams({ type: null, strength: null })}>
                      Clear
                    </Button>
                  )}
                  <div className="ml-auto flex items-center gap-3">
                    {data.meta.generated_at && (
                      <span className="text-xs text-muted-foreground">
                        Generated {formatDateTime(data.meta.generated_at)}
                      </span>
                    )}
                    {inScope > 0 && generateButton(data.meta.generated_at ? "Regenerate insights" : "Generate insights")}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Insights are written from fixed templates and rules, never free-text AI. Each cites real review
                  sentences, and “See all reviews” opens exactly the reviews it counted. They show patterns in what
                  guests wrote, not proof of cause.
                </p>
              </section>

              {data.meta.stale && data.meta.total > 0 && (
                <Alert>
                  <RefreshCw aria-hidden />
                  <AlertTitle>These insights are out of date</AlertTitle>
                  <AlertDescription>
                    Reviews or their analysis changed after these were generated. Regenerate to refresh them.
                  </AlertDescription>
                </Alert>
              )}

              {data.meta.total === 0 ? (
                inScope === 0 ? (
                  <NoData what="insights" />
                ) : filtered ? (
                  <EmptyState
                    icon={Lightbulb}
                    title="No insights match"
                    description="Try a different type or evidence strength."
                    action={
                      <Button variant="outline" onClick={() => setParams({ type: null, strength: null })}>
                        Clear filters
                      </Button>
                    }
                  />
                ) : (
                  <EmptyState
                    icon={Lightbulb}
                    title={data.meta.generated_at ? "No insights for this selection" : "No insights generated yet"}
                    description={
                      data.meta.generated_at
                        ? "Nothing met the evidence rules (enough mentions, a clear difference or trend) for these properties. Regenerate after new reviews arrive."
                        : "Insights are created on request from the analysed reviews, using fixed rules and minimum evidence. Generate them for the selected data."
                    }
                    action={generateButton("Generate insights")}
                  />
                )
              ) : (
                <>
                  <p className="text-sm text-muted-foreground" aria-live="polite">
                    {formatCount(data.meta.total)} {data.meta.total === 1 ? "insight" : "insights"}
                    {insights.isFetching && " · updating…"}. Page {query.page} of {formatCount(pages)}.
                  </p>
                  <ul className="flex flex-col gap-4">
                    {data.data.map((insight) => (
                      <li key={insight.id}>
                        <InsightCard insight={insight} />
                      </li>
                    ))}
                  </ul>
                  {pages > 1 && (
                    <nav aria-label="Pagination" className="flex items-center justify-between">
                      <Button
                        variant="outline"
                        disabled={query.page <= 1}
                        onClick={() => setParams({ page: query.page - 1 <= 1 ? null : String(query.page - 1) })}
                      >
                        <ChevronLeft aria-hidden /> Previous
                      </Button>
                      <span className="text-sm text-muted-foreground">
                        Page {query.page} of {formatCount(pages)}
                      </span>
                      <Button
                        variant="outline"
                        disabled={query.page >= pages}
                        onClick={() => setParams({ page: String(query.page + 1) })}
                      >
                        Next <ChevronRight aria-hidden />
                      </Button>
                    </nav>
                  )}
                </>
              )}
            </>
          );
        }}
      </QueryView>
    </div>
  );
}
