"use client";

import Link from "next/link";
import { Inbox } from "lucide-react";

import { EmptyState } from "@/components/states/empty-state";
import { Button } from "@/components/ui/button";
import { useFilters } from "@/hooks/use-filters";
import { hasActiveFilters } from "@/lib/filters";

/** Shown when a selection has no reviews: says why, and what to do about it. */
export function NoData({ what = "reviews" }: { what?: string }) {
  const { filters, reset } = useFilters();
  const filtered = hasActiveFilters(filters);
  return (
    <EmptyState
      icon={Inbox}
      title={`No ${what} to show`}
      description={
        filtered
          ? "Nothing matches the current filters. Widen the dates, pick more properties, or check the Data setting."
          : "No reviews have been imported yet. Import a review file, or load the labelled demo data from Settings."
      }
      action={
        filtered ? (
          <Button variant="outline" onClick={reset}>
            Reset filters
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button asChild>
              <Link href="/import">Import reviews</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/settings">Open Settings</Link>
            </Button>
          </div>
        )
      }
    />
  );
}
