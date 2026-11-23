"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { AspectsSection } from "@/components/dashboard/aspects-section";
import { KpiTile } from "@/components/dashboard/kpi-tile";
import { NoData } from "@/components/dashboard/no-data";
import { TrendsPanel } from "@/components/dashboard/trends-panel";
import { RatingDistribution } from "@/components/charts/rating-distribution";
import { SentimentBar } from "@/components/charts/sentiment-bar";
import { DatasetBanner, DatasetPeriod } from "@/components/filters/dataset-banner";
import { FilterBar } from "@/components/filters/filter-bar";
import { PageHeader } from "@/components/layout/page-header";
import { QueryView } from "@/components/states/query-view";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePropertyDetail } from "@/hooks/use-analytics";
import { filtersHref, useFilters } from "@/hooks/use-filters";
import { useProperties } from "@/hooks/use-properties";
import { formatCount, formatDate, formatPercent, formatRating } from "@/lib/format";
import type { TopAspect } from "@/types/analytics";

function EvidenceList({
  title,
  description,
  items,
  kind,
  emptyText,
}: {
  title: string;
  description: string;
  items: TopAspect[];
  kind: "positive" | "negative";
  emptyText: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">{emptyText}</p>
        ) : (
          <ul className="space-y-5">
            {items.map((item) => (
              <li key={item.aspect}>
                <p className="text-sm font-medium">
                  {item.display_name}{" "}
                  <span className="font-normal text-muted-foreground">
                    {formatCount(item[kind])} of {formatCount(item.mentions)} reviews that mention it (
                    {formatPercent(item[`${kind}_share`])})
                  </span>
                </p>
                <ul className="mt-2 space-y-2">
                  {(item.examples ?? []).map((example) => (
                    <li key={`${example.review_id}-${example.evidence_text}`} className="text-sm">
                      <blockquote className="border-l-2 pl-3">“{example.evidence_text}”</blockquote>
                      <p className="pl-3 text-xs text-muted-foreground">
                        {formatDate(example.review_date)}
                        {example.is_synthetic && (
                          <Badge variant="outline" className="ml-2">
                            Synthetic
                          </Badge>
                        )}
                      </p>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export function PropertyDetailView() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const valid = Number.isInteger(id) && id > 0;
  const { filters, problem } = useFilters();
  // The property comes from the URL path; the other filters still apply.
  const scoped = { ...filters, propertyIds: valid ? [id] : [] };
  const properties = useProperties();
  const detail = usePropertyDetail(id, filters, valid && !problem);
  const property = properties.data?.find((p) => p.id === id);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          href={filtersHref("/properties", { ...filters, propertyIds: [] })}
          className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" aria-hidden /> All properties
        </Link>
        <PageHeader
          title={property?.name ?? (valid ? `Property ${id}` : "Property")}
          description={property?.location ?? undefined}
        />
      </div>
      <FilterBar showProperties={false} />
      {!valid ? (
        <p className="text-sm text-destructive">“{params.id}” is not a valid property id.</p>
      ) : problem ? null : (
        <QueryView query={detail} skeleton={<Skeleton className="h-96 w-full" />} errorTitle="Could not load this property">
          {(data) =>
            data.reviews.n === 0 ? (
              <>
                <DatasetBanner dataset={data.dataset} />
                <NoData />
              </>
            ) : (
              <>
                <DatasetBanner dataset={data.dataset} />
                <DatasetPeriod dataset={data.dataset} />
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <KpiTile label="Reviews" value={formatCount(data.reviews.n)} n={data.reviews.n} />
                  <KpiTile
                    label="Average rating (0–10)"
                    value={formatRating(data.rating.value)}
                    n={data.rating.n}
                    missing={data.rating.missing}
                    lowSample={data.rating.low_sample}
                  />
                  <KpiTile
                    label="Positive reviews"
                    value={formatPercent(data.sentiment.positive_share)}
                    n={data.sentiment.analysed_n}
                    note="Of reviews with analysed text"
                    lowSample={data.sentiment.analysed_n < data.min_sample}
                  />
                  <KpiTile
                    label="Negative reviews"
                    value={formatPercent(data.sentiment.negative_share)}
                    n={data.sentiment.analysed_n}
                    note="Of reviews with analysed text"
                    lowSample={data.sentiment.analysed_n < data.min_sample}
                  />
                </div>
                <div className="grid gap-4 lg:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle>Rating distribution</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <RatingDistribution bins={data.rating.distribution} />
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardTitle>What guests wrote</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <SentimentBar sentiment={data.sentiment} />
                    </CardContent>
                  </Card>
                </div>
                <div className="grid gap-4 lg:grid-cols-2">
                  <EvidenceList
                    title="What guests praise"
                    description={`Strongest positive aspects (at least ${data.aspects.min_mentions} mentions), with sentences from real reviews.`}
                    items={data.top_praise}
                    kind="positive"
                    emptyText="No aspect has enough positive mentions to be named yet."
                  />
                  <EvidenceList
                    title="What guests complain about"
                    description={`Strongest negative aspects (at least ${data.aspects.min_mentions} mentions), with sentences from real reviews.`}
                    items={data.top_complaints}
                    kind="negative"
                    emptyText="No aspect has enough negative mentions to be named yet."
                  />
                </div>
                <AspectsSection filters={scoped} />
                <TrendsPanel filters={scoped} />
              </>
            )
          }
        </QueryView>
      )}
    </div>
  );
}
