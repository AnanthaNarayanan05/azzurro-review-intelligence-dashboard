"use client";

import Link from "next/link";
import { useState } from "react";
import { X } from "lucide-react";

import { SplitBar } from "@/components/charts/split-bar";
import { QueryView } from "@/components/states/query-view";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAspectExamples, useAspects } from "@/hooks/use-analytics";
import { filtersHref } from "@/hooks/use-filters";
import { useProperties } from "@/hooks/use-properties";
import type { FilterState } from "@/lib/filters";
import { formatCount, formatDate, formatPercent } from "@/lib/format";
import type { AspectRow, SentimentLabel } from "@/types/analytics";

interface Selection {
  aspect: string;
  displayName: string;
  sentiment: SentimentLabel;
}

function Examples({
  selection,
  filters,
  onClose,
}: {
  selection: Selection;
  filters: FilterState;
  onClose: () => void;
}) {
  const query = useAspectExamples(selection.aspect, selection.sentiment, filters);
  const properties = useProperties();
  const names = new Map((properties.data ?? []).map((p) => [p.id, p.name]));
  const reviewsLink = (extra: Record<string, string>) => {
    const base = filtersHref("/reviews", filters);
    const params = new URLSearchParams(base.split("?")[1] ?? "");
    for (const [k, v] of Object.entries(extra)) params.set(k, v);
    return `/reviews?${params.toString()}`;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {selection.displayName}: {selection.sentiment === "positive" ? "praise" : "complaints"}
        </CardTitle>
        <CardDescription>
          The sentences in real reviews that the numbers above are based on, strongest first.
        </CardDescription>
        <div className="col-start-2 row-span-2 row-start-1 self-start justify-self-end">
          <Button variant="ghost" size="icon-sm" onClick={onClose} aria-label="Close examples">
            <X aria-hidden />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <QueryView query={query} skeleton={<Skeleton className="h-24 w-full" />}>
          {(examples) =>
            examples.length === 0 ? (
              <p className="text-sm text-muted-foreground">No example sentences in this selection.</p>
            ) : (
              <>
                <ul className="space-y-3">
                  {examples.map((example) => (
                    <li key={`${example.review_id}-${example.matched_term}-${example.evidence_text}`}>
                      <blockquote className="border-l-2 pl-3 text-sm">“{example.evidence_text}”</blockquote>
                      <p className="mt-1 pl-3 text-xs text-muted-foreground">
                        {names.get(example.property_id) ?? `Property ${example.property_id}`} ·{" "}
                        {formatDate(example.review_date)} · matched “{example.matched_term}” ·{" "}
                        {example.is_synthetic && <Badge variant="outline">Synthetic</Badge>}{" "}
                        <Link
                          href={reviewsLink({ review: String(example.review_id) })}
                          className="underline underline-offset-4"
                        >
                          Open review
                        </Link>
                      </p>
                    </li>
                  ))}
                </ul>
                <Link
                  href={reviewsLink({ aspect: selection.aspect, aspect_sentiment: selection.sentiment })}
                  className="mt-4 inline-block text-sm underline underline-offset-4"
                >
                  See all {selection.sentiment} reviews about {selection.displayName.toLowerCase()}
                </Link>
              </>
            )
          }
        </QueryView>
      </CardContent>
    </Card>
  );
}

function TopList({
  title,
  description,
  items,
  sentiment,
  onSelect,
}: {
  title: string;
  description: string;
  items: AspectRow[];
  sentiment: SentimentLabel;
  onSelect: (row: AspectRow, sentiment: SentimentLabel) => void;
}) {
  const key = sentiment === "positive" ? "positive" : "negative";
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No aspect has enough mentions yet to be named here.
          </p>
        ) : (
          <ol className="space-y-2">
            {items.map((row) => (
              <li key={row.aspect} className="flex items-center justify-between gap-3 text-sm">
                <button
                  type="button"
                  className="text-left underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
                  onClick={() => onSelect(row, sentiment)}
                >
                  {row.display_name}
                </button>
                <span className="tabular-nums text-muted-foreground">
                  {formatCount(row[key])} of {formatCount(row.mentions)} mentions (
                  {formatPercent(row[`${key}_share`])})
                </span>
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}

interface AspectsSectionProps {
  filters: FilterState;
  top?: { most_praised: AspectRow[]; most_criticised: AspectRow[]; min_mentions: number };
}

/** Aspect breakdown with drill-down: every number can be traced to the sentences behind it. */
export function AspectsSection({ filters, top }: AspectsSectionProps) {
  const [selection, setSelection] = useState<Selection | null>(null);
  const aspects = useAspects(filters);

  const select = (row: AspectRow, sentiment: SentimentLabel) =>
    setSelection({ aspect: row.aspect, displayName: row.display_name, sentiment });

  return (
    <div className="flex flex-col gap-4">
      {top && (
        <div className="grid gap-4 md:grid-cols-2">
          <TopList
            title="Most praised"
            description={`Aspects with the most positive reviews (at least ${top.min_mentions} mentions).`}
            items={top.most_praised}
            sentiment="positive"
            onSelect={select}
          />
          <TopList
            title="Most criticised"
            description={`Aspects with the most negative reviews (at least ${top.min_mentions} mentions).`}
            items={top.most_criticised}
            sentiment="negative"
            onSelect={select}
          />
        </div>
      )}

      {selection && <Examples selection={selection} filters={filters} onClose={() => setSelection(null)} />}

      <Card>
        <CardHeader>
          <CardTitle>Aspects guests talk about</CardTitle>
          <CardDescription>
            Each review counts once per aspect. Its stance is positive, negative or neutral by comparing
            positive and negative sentences about it.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <QueryView query={aspects} skeleton={<Skeleton className="h-48 w-full" />}>
            {(data) =>
              data.items.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No aspect mentions in this selection yet.
                </p>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Aspect</TableHead>
                          <TableHead className="text-right">Reviews</TableHead>
                          <TableHead className="w-48">Positive / neutral / negative</TableHead>
                          <TableHead className="text-right">Negative</TableHead>
                          <TableHead className="text-right">Examples</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.items.map((row) => (
                          <TableRow key={row.aspect}>
                            <TableCell className="font-medium">
                              {row.display_name}
                              {row.low_sample && (
                                <Badge variant="outline" className="ml-2">
                                  Low sample
                                </Badge>
                              )}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {formatCount(row.mentions)}
                            </TableCell>
                            <TableCell>
                              <SplitBar
                                positive={row.positive}
                                neutral={row.neutral}
                                negative={row.negative}
                                label={row.display_name}
                              />
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {formatPercent(row.negative_share)}
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex justify-end gap-1">
                                <Button
                                  variant="outline"
                                  size="xs"
                                  disabled={row.positive === 0}
                                  onClick={() => select(row, "positive")}
                                  aria-label={`Praise: examples for ${row.display_name}`}
                                >
                                  Praise
                                </Button>
                                <Button
                                  variant="outline"
                                  size="xs"
                                  disabled={row.negative === 0}
                                  onClick={() => select(row, "negative")}
                                  aria-label={`Complaints: examples for ${row.display_name}`}
                                >
                                  Complaints
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                  <p className="mt-3 text-xs text-muted-foreground">
                    {formatCount(data.analysed_reviews)} reviews with analysed text. “Low sample” means fewer
                    than {data.min_mentions} reviews mention the aspect, so treat the split as a hint, not a
                    finding.
                  </p>
                </>
              )
            }
          </QueryView>
        </CardContent>
      </Card>
    </div>
  );
}
