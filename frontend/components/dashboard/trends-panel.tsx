"use client";

import { useState } from "react";

import { LineChart } from "@/components/charts/line-chart";
import { QueryView } from "@/components/states/query-view";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useAspects, useTrends } from "@/hooks/use-analytics";
import type { FilterState } from "@/lib/filters";
import { formatCount, formatDate, formatPercent, formatSigned } from "@/lib/format";
import type { Granularity, TrendChange, TrendMetric, Trends } from "@/types/analytics";

const METRICS: { value: TrendMetric; label: string }[] = [
  { value: "avg_rating", label: "Average rating" },
  { value: "volume", label: "Number of reviews" },
  { value: "sentiment_positive_share", label: "Positive share" },
  { value: "sentiment_negative_share", label: "Negative share" },
  { value: "aspect_negative_share", label: "Negative share for one aspect" },
];

function isShare(metric: TrendMetric): boolean {
  return metric !== "avg_rating" && metric !== "volume";
}

function valueFormatter(metric: TrendMetric): (v: number) => string {
  if (metric === "volume") return (v) => formatCount(Math.round(v));
  if (metric === "avg_rating") return (v) => v.toFixed(1);
  return (v) => formatPercent(v);
}

function ChangeSummary({ trends, label }: { trends: Trends; label: string }) {
  const change: TrendChange = trends.change;
  const share = isShare(trends.metric);
  const fmt = valueFormatter(trends.metric);
  const windows = `${formatDate(change.previous_window.from)} to ${formatDate(change.previous_window.to)} (${formatCount(change.previous_window.n)}) against ${formatDate(change.recent_window.from)} to ${formatDate(change.recent_window.to)} (${formatCount(change.recent_window.n)})`;

  if (change.status === "insufficient_data") {
    return (
      <p className="text-sm">
        <span className="font-medium">Not enough data to call a change.</span>{" "}
        {change.reason} Compared: {windows}.
      </p>
    );
  }
  if (change.status === "descriptive") {
    return (
      <p className="text-sm">
        {formatCount(change.recent_value ?? 0)} reviews in the latest {trends.window_periods}{" "}
        complete {trends.granularity}s against {formatCount(change.previous_value ?? 0)} in the {trends.window_periods}{" "}
        before. Counts are described, not tested for significance.
      </p>
    );
  }
  const diff = change.difference ?? 0;
  const diffText = share
    ? `${formatSigned(diff * 100, 1)} percentage points`
    : `${formatSigned(diff, 2)} rating points`;
  const interval =
    change.ci_low !== null && change.ci_low !== undefined && change.ci_high !== null && change.ci_high !== undefined
      ? share
        ? `${formatSigned(change.ci_low * 100, 1)} to ${formatSigned(change.ci_high * 100, 1)} points`
        : `${formatSigned(change.ci_low, 2)} to ${formatSigned(change.ci_high, 2)}`
      : null;
  const headline =
    change.status === "no_significant_change"
      ? `No meaningful change in ${label.toLowerCase()}.`
      : `${label} ${change.status === "increase" ? "rose" : "fell"}.`;
  return (
    <p className="text-sm">
      <span className="font-medium">{headline}</span> {fmt(change.previous_value ?? 0)} →{" "}
      {fmt(change.recent_value ?? 0)} ({diffText}
      {interval && `; 95% interval ${interval}`}). Compared: {windows}. A change is reported only if it is
      statistically clear and at least {share ? `${(change.practical_threshold ?? 0) * 100} percentage points` : `${change.practical_threshold} rating points`}.
    </p>
  );
}

interface TrendsPanelProps {
  filters: FilterState;
  title?: string;
}

export function TrendsPanel({ filters, title = "Trends over time" }: TrendsPanelProps) {
  const [metric, setMetric] = useState<TrendMetric>("avg_rating");
  const [granularity, setGranularity] = useState<Granularity>("month");
  const [aspect, setAspect] = useState<string>("");
  const aspects = useAspects(filters);
  const aspectOptions = aspects.data?.items ?? [];
  const needsAspect = metric === "aspect_negative_share";
  const effectiveAspect = needsAspect ? aspect || aspectOptions[0]?.aspect || "" : "";
  const waitingForAspect = needsAspect && !effectiveAspect;

  const trends = useTrends(
    filters,
    { metric, granularity, aspect: effectiveAspect || undefined },
    !waitingForAspect,
  );
  const metricLabel =
    metric === "aspect_negative_share"
      ? `Negative share: ${aspectOptions.find((a) => a.aspect === effectiveAspect)?.display_name ?? "aspect"}`
      : (METRICS.find((m) => m.value === metric)?.label ?? metric);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>
          Weeks run Monday to Sunday. Changes are judged only on complete periods, so a half-finished week never
          looks like a drop.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="trend-metric" className="text-xs text-muted-foreground">
              Measure
            </Label>
            <Select value={metric} onValueChange={(v) => setMetric(v as TrendMetric)}>
              <SelectTrigger id="trend-metric" className="w-64">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {METRICS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {needsAspect && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="trend-aspect" className="text-xs text-muted-foreground">
                Aspect
              </Label>
              <Select value={effectiveAspect} onValueChange={setAspect}>
                <SelectTrigger id="trend-aspect" className="w-48">
                  <SelectValue placeholder="Choose an aspect" />
                </SelectTrigger>
                <SelectContent>
                  {aspectOptions.map((a) => (
                    <SelectItem key={a.aspect} value={a.aspect}>
                      {a.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="trend-granularity" className="text-xs text-muted-foreground">
              Group by
            </Label>
            <Select value={granularity} onValueChange={(v) => setGranularity(v as Granularity)}>
              <SelectTrigger id="trend-granularity" className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="week">Week</SelectItem>
                <SelectItem value="month">Month</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {waitingForAspect ? (
          <p className="text-sm text-muted-foreground">
            No aspect has been mentioned in this selection, so there is nothing to trend.
          </p>
        ) : (
          <QueryView query={trends} skeleton={<Skeleton className="h-64 w-full" />}>
            {(data) =>
              data.series.length === 0 ? (
                <p className="text-sm text-muted-foreground">No reviews in this selection.</p>
              ) : (
                <>
                  <LineChart
                    series={data.series}
                    granularity={data.granularity}
                    formatValue={valueFormatter(data.metric)}
                    valueLabel={metricLabel}
                    minSample={data.min_sample}
                    zeroBased={data.metric !== "avg_rating"}
                    ceiling={data.metric === "avg_rating" ? 10 : isShare(data.metric) ? 1 : undefined}
                  />
                  <div className="rounded-md bg-muted/50 p-3">
                    <ChangeSummary trends={data} label={metricLabel} />
                  </div>
                </>
              )
            }
          </QueryView>
        )}
      </CardContent>
    </Card>
  );
}
