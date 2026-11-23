"use client";

import { useState } from "react";
import { Scale } from "lucide-react";

import { IntervalChart } from "@/components/charts/interval-chart";
import { NoData } from "@/components/dashboard/no-data";
import { DatasetBanner } from "@/components/filters/dataset-banner";
import { FilterBar } from "@/components/filters/filter-bar";
import { QueryView } from "@/components/states/query-view";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useComparison } from "@/hooks/use-analytics";
import { useFilters } from "@/hooks/use-filters";
import { formatCount, formatPercent, formatRating } from "@/lib/format";
import type { Comparison } from "@/types/analytics";

function RankingNotice({ data }: { data: Comparison }) {
  const { rating_ranking: ranking } = data;
  const name = (id: number | null) => data.properties.find((p) => p.property_id === id)?.name ?? "";
  if (ranking.status === "ranked") {
    return (
      <Alert>
        <Scale aria-hidden />
        <AlertTitle>
          Highest rated: {name(ranking.best)}. Lowest rated: {name(ranking.worst)}.
        </AlertTitle>
        <AlertDescription>
          Their 95% intervals do not overlap, so the gap is unlikely to be chance. Other properties
          in between are not ranked against each other.
        </AlertDescription>
      </Alert>
    );
  }
  return (
    <Alert>
      <Scale aria-hidden />
      <AlertTitle>
        {ranking.status === "difference_not_significant"
          ? "No clear best or worst property"
          : "Not enough data to rank the properties"}
      </AlertTitle>
      <AlertDescription>
        {ranking.reason} {data.note}
      </AlertDescription>
    </Alert>
  );
}

function AspectMatrix({ data }: { data: Comparison }) {
  const [measure, setMeasure] = useState<"negative_share" | "positive_share">("negative_share");
  const aspectKeys = new Map<string, string>();
  for (const row of data.properties) for (const a of row.aspects) aspectKeys.set(a.aspect, a.display_name);
  const keys = [...aspectKeys.entries()].sort((a, b) => a[1].localeCompare(b[1]));

  if (keys.length === 0) {
    return <p className="text-sm text-muted-foreground">No aspect mentions in this selection.</p>;
  }
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="aspect-measure" className="text-xs text-muted-foreground">
          Show
        </Label>
        <Select value={measure} onValueChange={(v) => setMeasure(v as typeof measure)}>
          <SelectTrigger id="aspect-measure" className="w-64">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="negative_share">Negative share of mentions</SelectItem>
            <SelectItem value="positive_share">Positive share of mentions</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Aspect</TableHead>
              {data.properties.map((p) => (
                <TableHead key={p.property_id} className="text-right">
                  {p.name}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {keys.map(([key, label]) => (
              <TableRow key={key}>
                <TableCell className="font-medium">{label}</TableCell>
                {data.properties.map((p) => {
                  const cell = p.aspects.find((a) => a.aspect === key);
                  return (
                    <TableCell
                      key={p.property_id}
                      className={cell?.low_sample ? "text-right tabular-nums text-muted-foreground" : "text-right tabular-nums"}
                    >
                      {cell ? (
                        <>
                          {formatPercent(cell[measure])}
                          <span className="ml-1 text-xs text-muted-foreground">
                            (n={formatCount(cell.mentions)}
                            {cell.low_sample ? ", low sample" : ""})
                          </span>
                        </>
                      ) : (
                        <span className="text-xs text-muted-foreground">not mentioned</span>
                      )}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <p className="text-xs text-muted-foreground">
        n is the number of reviews that mention the aspect. With fewer than {data.min_aspect_mentions} the
        percentage is shown greyed out and should not be used to compare properties.
      </p>
    </div>
  );
}

export function ComparisonView() {
  const { filters, problem } = useFilters();
  const comparison = useComparison(filters, !problem);

  return (
    <div className="flex flex-col gap-6">
      <FilterBar />
      {problem ? null : (
        <QueryView
          query={comparison}
          skeleton={<Skeleton className="h-96 w-full" />}
          errorTitle="Could not load the comparison"
        >
          {(data) =>
            data.properties.length === 0 || data.properties.every((p) => p.reviews === 0) ? (
              <>
                <DatasetBanner dataset={data.dataset} />
                <NoData />
              </>
            ) : (
              <>
                <DatasetBanner dataset={data.dataset} />
                <RankingNotice data={data} />
                <Card>
                  <CardHeader>
                    <CardTitle>Average rating</CardTitle>
                    <CardDescription>
                      A property is only ranked above another when the intervals are clearly apart (at
                      least {data.min_sample} rated reviews each).
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <IntervalChart
                      rows={data.properties.map((p) => ({
                        id: p.property_id,
                        name: p.name,
                        value: p.rating.value,
                        low: p.rating.ci_low ?? null,
                        high: p.rating.ci_high ?? null,
                        n: p.rating.n,
                        lowSample: p.rating.low_sample,
                      }))}
                    />
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle>Side by side</CardTitle>
                  </CardHeader>
                  <CardContent className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Property</TableHead>
                          <TableHead className="text-right">Reviews</TableHead>
                          <TableHead className="text-right">Avg rating</TableHead>
                          <TableHead className="text-right">Positive</TableHead>
                          <TableHead className="text-right">Negative</TableHead>
                          <TableHead className="text-right">Text analysed</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.properties.map((p) => (
                          <TableRow key={p.property_id}>
                            <TableCell className="font-medium">
                              {p.name}
                              {p.rating.low_sample && (
                                <Badge variant="outline" className="ml-2">
                                  Low sample
                                </Badge>
                              )}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">{formatCount(p.reviews)}</TableCell>
                            <TableCell className="text-right tabular-nums">{formatRating(p.rating.value)}</TableCell>
                            <TableCell className="text-right tabular-nums">
                              {formatPercent(p.sentiment.positive_share)}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {formatPercent(p.sentiment.negative_share)}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {formatCount(p.sentiment.analysed_n)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle>Aspects by property</CardTitle>
                    <CardDescription>Where each property is strong or weak, with the sample behind it.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <AspectMatrix data={data} />
                  </CardContent>
                </Card>
              </>
            )
          }
        </QueryView>
      )}
    </div>
  );
}
