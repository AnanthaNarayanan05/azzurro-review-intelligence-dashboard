"use client";

import Link from "next/link";
import { Building2, MapPin } from "lucide-react";

import { EmptyState } from "@/components/states/empty-state";
import { DatasetBanner } from "@/components/filters/dataset-banner";
import { FilterBar } from "@/components/filters/filter-bar";
import { QueryView } from "@/components/states/query-view";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useOverview } from "@/hooks/use-analytics";
import { filtersHref, useFilters } from "@/hooks/use-filters";
import { useProperties } from "@/hooks/use-properties";
import { formatCount, formatRating } from "@/lib/format";

export function PropertiesView() {
  const { filters, problem } = useFilters();
  // Properties are the page's subject, so the property filter is not applied here.
  const scoped = { ...filters, propertyIds: [] };
  const properties = useProperties();
  const overview = useOverview(scoped, !problem);

  return (
    <div className="flex flex-col gap-6">
      <FilterBar showProperties={false} />
      {problem ? null : (
        <QueryView query={properties} skeleton={<Skeleton className="h-48 w-full" />} errorTitle="Could not load properties">
          {(list) => {
            const active = list.filter((p) => p.is_active);
            if (active.length === 0) {
              return (
                <EmptyState
                  icon={Building2}
                  title="No properties yet"
                  description="Add the properties you want to analyse in Settings, then import their reviews."
                  action={
                    <Button asChild>
                      <Link href="/settings">Open Settings</Link>
                    </Button>
                  }
                />
              );
            }
            return (
              <QueryView query={overview} skeleton={<Skeleton className="h-48 w-full" />} errorTitle="Could not load ratings">
                {(data) => (
                  <>
                    <DatasetBanner dataset={data.dataset} />
                    <div className="grid gap-4 sm:grid-cols-2">
                      {active.map((property) => {
                        const stats = data.properties.find((p) => p.property_id === property.id);
                        return (
                          <Card key={property.id}>
                            <CardHeader>
                              <CardTitle>
                                <Link
                                  href={filtersHref(`/properties/${property.id}`, scoped)}
                                  className="underline-offset-4 hover:underline"
                                >
                                  {property.name}
                                </Link>
                              </CardTitle>
                              {property.location && (
                                <p className="flex items-center gap-1 text-sm text-muted-foreground">
                                  <MapPin className="size-3.5" aria-hidden /> {property.location}
                                </p>
                              )}
                            </CardHeader>
                            <CardContent>
                              {stats ? (
                                <dl className="grid grid-cols-2 gap-3">
                                  <div>
                                    <dt className="text-xs text-muted-foreground">Average rating (0–10)</dt>
                                    <dd className="text-2xl font-semibold tabular-nums">
                                      {formatRating(stats.rating.value)}
                                    </dd>
                                    {stats.rating.low_sample && (
                                      <Badge variant="outline" className="mt-1">
                                        Low sample
                                      </Badge>
                                    )}
                                  </div>
                                  <div>
                                    <dt className="text-xs text-muted-foreground">Reviews in selection</dt>
                                    <dd className="text-2xl font-semibold tabular-nums">
                                      {formatCount(stats.reviews)}
                                    </dd>
                                    <p className="text-xs text-muted-foreground">
                                      {formatCount(stats.rating.n)} with a rating
                                    </p>
                                  </div>
                                </dl>
                              ) : (
                                <p className="text-sm text-muted-foreground">
                                  No reviews in the current selection.
                                </p>
                              )}
                            </CardContent>
                          </Card>
                        );
                      })}
                    </div>
                  </>
                )}
              </QueryView>
            );
          }}
        </QueryView>
      )}
    </div>
  );
}
