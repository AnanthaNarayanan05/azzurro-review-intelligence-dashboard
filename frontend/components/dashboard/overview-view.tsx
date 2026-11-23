"use client";

import { AspectsSection } from "@/components/dashboard/aspects-section";
import { KpiTile } from "@/components/dashboard/kpi-tile";
import { NoData } from "@/components/dashboard/no-data";
import { PropertyTable } from "@/components/dashboard/property-table";
import { TrendsPanel } from "@/components/dashboard/trends-panel";
import { RatingDistribution } from "@/components/charts/rating-distribution";
import { SentimentBar } from "@/components/charts/sentiment-bar";
import { DatasetBanner, DatasetPeriod } from "@/components/filters/dataset-banner";
import { FilterBar } from "@/components/filters/filter-bar";
import { QueryView } from "@/components/states/query-view";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useOverview } from "@/hooks/use-analytics";
import { useFilters } from "@/hooks/use-filters";
import { formatCount, formatPercent, formatRating } from "@/lib/format";

function OverviewSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {[0, 1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-28" />
      ))}
    </div>
  );
}

export function OverviewView() {
  const { filters, problem } = useFilters();
  const overview = useOverview(filters, !problem);

  return (
    <div className="flex flex-col gap-6">
      <FilterBar />
      {problem ? null : (
        <QueryView query={overview} skeleton={<OverviewSkeleton />} errorTitle="Could not load the overview">
          {(data) => (
            <>
              <DatasetBanner dataset={data.dataset} />
              {data.reviews.n === 0 ? (
                <NoData />
              ) : (
                <>
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
                        <CardDescription>How guests scored their stay.</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <RatingDistribution bins={data.rating.distribution} />
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader>
                        <CardTitle>What guests wrote</CardTitle>
                        <CardDescription>
                          Sentiment of the review text (VADER), not the star rating.
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <SentimentBar sentiment={data.sentiment} />
                      </CardContent>
                    </Card>
                  </div>

                  <Card>
                    <CardHeader>
                      <CardTitle>Properties</CardTitle>
                      <CardDescription>
                        Open a property for its strengths, complaints and evidence.
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <PropertyTable rows={data.properties} filters={filters} />
                    </CardContent>
                  </Card>

                  <AspectsSection filters={filters} top={data.aspects} />
                  <TrendsPanel filters={filters} />
                </>
              )}
            </>
          )}
        </QueryView>
      )}
    </div>
  );
}
