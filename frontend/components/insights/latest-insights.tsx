"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { InsightCard } from "@/components/insights/insight-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useInsights } from "@/hooks/use-insights";
import { filtersHref } from "@/hooks/use-filters";
import { INSIGHT_PAGE_SIZE } from "@/lib/insights";
import type { FilterState } from "@/lib/filters";

const TEASER = 3;

/** Top insights on the Overview. Quietly renders nothing when there are none or they can't load. */
export function LatestInsights({ filters }: { filters: FilterState }) {
  const insights = useInsights(filters, { type: "", strength: "", page: 1, pageSize: INSIGHT_PAGE_SIZE });
  if (!insights.data || insights.data.data.length === 0) return null;
  const { data, meta } = insights.data;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Top insights</CardTitle>
        <CardDescription>
          The strongest findings first{meta.stale ? " (out of date: regenerate on the Insights page)" : ""}.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <ul className="flex flex-col gap-3">
          {data.slice(0, TEASER).map((insight) => (
            <li key={insight.id}>
              <InsightCard insight={insight} compact />
            </li>
          ))}
        </ul>
        <Button asChild variant="outline" className="self-start">
          <Link href={filtersHref("/insights", filters)}>
            All {meta.total} insights <ArrowRight aria-hidden />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
