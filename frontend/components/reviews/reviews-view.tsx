"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, RotateCcw, Search } from "lucide-react";

import { NoData } from "@/components/dashboard/no-data";
import { DatasetBanner } from "@/components/filters/dataset-banner";
import { FilterBar } from "@/components/filters/filter-bar";
import { ReviewCard } from "@/components/reviews/review-card";
import { ReviewDrawer } from "@/components/reviews/review-drawer";
import { EmptyState } from "@/components/states/empty-state";
import { QueryView } from "@/components/states/query-view";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useAspects, useOverview, useReviews } from "@/hooks/use-analytics";
import { useFilters, useUrlParams } from "@/hooks/use-filters";
import { formatCount } from "@/lib/format";
import { hasReviewFilters, parseReviewQuery, ratingRangeProblem } from "@/lib/reviews-query";
import type { ReviewSort, SentimentLabel } from "@/types/analytics";

const ANY = "any";

const SORT_LABELS: Record<ReviewSort, string> = {
  newest: "Newest first",
  oldest: "Oldest first",
  rating_desc: "Highest rating first",
  rating_asc: "Lowest rating first",
};

/** Typed into freely; written to the URL shortly after typing stops. */
function SearchBox({ value, onCommit }: { value: string; onCommit: (q: string) => void }) {
  const [text, setText] = useState(value);
  useEffect(() => {
    if (text.trim() === value) return;
    const timer = setTimeout(() => onCommit(text.trim()), 400);
    return () => clearTimeout(timer);
  }, [text, value, onCommit]);
  return (
    <div className="relative">
      <Search
        className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden
      />
      <Input
        id="review-search"
        type="search"
        value={text}
        maxLength={200}
        placeholder="for example: wifi, breakfast, noisy"
        onChange={(e) => setText(e.target.value)}
        className="pl-8"
      />
    </div>
  );
}

export function ReviewsView() {
  const { filters, problem } = useFilters();
  const { params, setParams } = useUrlParams();
  const query = parseReviewQuery(params);
  const ratingProblem = ratingRangeProblem(query);
  const reviewId = Number(params.get("review")) || null;

  // Bumped to empty the search box when the explorer is reset (the box keeps its own text while typing).
  const [searchKey, setSearchKey] = useState(0);

  const aspects = useAspects(filters, !problem);
  const reviews = useReviews(filters, query, !problem && !ratingProblem);
  // For the "no genuine reviews" banner; shares its cache with the Overview page.
  const dataset = useOverview(filters, !problem);

  const aspectOptions = aspects.data?.items ?? [];
  const aspectLabel = aspectOptions.find((a) => a.aspect === query.aspect)?.display_name ?? query.aspect;
  const total = reviews.data?.meta.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / query.pageSize));
  const filtered = hasReviewFilters(query);

  function resetExplorer() {
    setSearchKey((k) => k + 1);
    setParams({
      q: null,
      sentiment: null,
      rating_min: null,
      rating_max: null,
      aspect: null,
      aspect_sentiment: null,
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <FilterBar />
      {dataset.data && <DatasetBanner dataset={dataset.data.dataset} />}

      <section aria-label="Search and filter reviews" className="rounded-lg border bg-card p-4">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="flex flex-col gap-1.5 sm:col-span-2">
            <Label htmlFor="review-search" className="text-xs text-muted-foreground">
              Search review text
            </Label>
            <SearchBox key={searchKey} value={query.q} onCommit={(q) => setParams({ q: q || null })} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="review-sentiment" className="text-xs text-muted-foreground">
              Overall sentiment of the text
            </Label>
            <Select
              value={query.sentiment || ANY}
              onValueChange={(v) => setParams({ sentiment: v === ANY ? null : v })}
            >
              <SelectTrigger id="review-sentiment" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>Any</SelectItem>
                <SelectItem value="positive">Positive</SelectItem>
                <SelectItem value="neutral">Neutral</SelectItem>
                <SelectItem value="negative">Negative</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="review-sort" className="text-xs text-muted-foreground">
              Sort
            </Label>
            <Select value={query.sort} onValueChange={(v) => setParams({ sort: v === "newest" ? null : v })}>
              <SelectTrigger id="review-sort" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(SORT_LABELS) as ReviewSort[]).map((sort) => (
                  <SelectItem key={sort} value={sort}>
                    {SORT_LABELS[sort]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex gap-2">
            <div className="flex flex-1 flex-col gap-1.5">
              <Label htmlFor="rating-min" className="text-xs text-muted-foreground">
                Rating from
              </Label>
              <Input
                id="rating-min"
                type="number"
                min={0}
                max={10}
                step={0.5}
                value={query.ratingMin}
                aria-invalid={ratingProblem ? true : undefined}
                onChange={(e) => setParams({ rating_min: e.target.value || null })}
              />
            </div>
            <div className="flex flex-1 flex-col gap-1.5">
              <Label htmlFor="rating-max" className="text-xs text-muted-foreground">
                to
              </Label>
              <Input
                id="rating-max"
                type="number"
                min={0}
                max={10}
                step={0.5}
                value={query.ratingMax}
                aria-invalid={ratingProblem ? true : undefined}
                onChange={(e) => setParams({ rating_max: e.target.value || null })}
              />
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="review-aspect" className="text-xs text-muted-foreground">
              Mentions aspect
            </Label>
            <Select
              value={query.aspect || ANY}
              onValueChange={(v) => setParams({ aspect: v === ANY ? null : v, aspect_sentiment: null })}
            >
              <SelectTrigger id="review-aspect" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>Any</SelectItem>
                {query.aspect && !aspectOptions.some((a) => a.aspect === query.aspect) && (
                  <SelectItem value={query.aspect}>{aspectLabel}</SelectItem>
                )}
                {aspectOptions.map((a) => (
                  <SelectItem key={a.aspect} value={a.aspect}>
                    {a.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="review-aspect-sentiment" className="text-xs text-muted-foreground">
              Stance on that aspect
            </Label>
            <Select
              value={query.aspectSentiment || ANY}
              disabled={!query.aspect}
              onValueChange={(v) => setParams({ aspect_sentiment: v === ANY ? null : v })}
            >
              <SelectTrigger id="review-aspect-sentiment" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>Any</SelectItem>
                {(["positive", "neutral", "negative"] as SentimentLabel[]).map((s) => (
                  <SelectItem key={s} value={s}>
                    {s[0].toUpperCase() + s.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-end">
            <Button type="button" variant="outline" onClick={resetExplorer} disabled={!filtered}>
              <RotateCcw aria-hidden /> Clear search and filters
            </Button>
          </div>
        </div>
        {ratingProblem && (
          <p role="alert" className="mt-3 text-sm text-destructive">
            {ratingProblem}
          </p>
        )}
      </section>

      {problem || ratingProblem ? null : (
        <QueryView query={reviews} skeleton={<Skeleton className="h-96 w-full" />} errorTitle="Could not load reviews">
          {(data) =>
            data.meta.total === 0 ? (
              filtered ? (
                <EmptyState
                  icon={Search}
                  title="No reviews match"
                  description="Try a different search word, or clear the search and filters."
                  action={
                    <Button variant="outline" onClick={resetExplorer}>
                      Clear search and filters
                    </Button>
                  }
                />
              ) : (
                <NoData />
              )
            ) : (
              <>
                <p className="text-sm text-muted-foreground" aria-live="polite">
                  {formatCount(data.meta.total)} {data.meta.total === 1 ? "review" : "reviews"}
                  {reviews.isFetching && " · updating…"}. Page {query.page} of {formatCount(pages)}.
                </p>
                <ul className="flex flex-col gap-3">
                  {data.data.map((review) => (
                    <li key={review.id}>
                      <ReviewCard review={review} onOpen={(id) => setParams({ review: String(id) }, { keepPage: true })} />
                    </li>
                  ))}
                </ul>
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
              </>
            )
          }
        </QueryView>
      )}

      <ReviewDrawer reviewId={reviewId} onClose={() => setParams({ review: null }, { keepPage: true })} />
    </div>
  );
}
