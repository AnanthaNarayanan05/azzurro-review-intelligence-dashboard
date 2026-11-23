"use client";

import { QueryView } from "@/components/states/query-view";
import { SENTIMENT_TEXT, SentimentDot } from "@/components/reviews/review-card";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useReview } from "@/hooks/use-analytics";
import { formatDate, formatRating } from "@/lib/format";
import type { SentimentLabel } from "@/types/analytics";

const SEGMENT_TEXT: Record<string, string> = {
  overall: "Whole review",
  positive: "“Liked” box",
  negative: "“Disliked” box",
  body: "Review text",
};

function Detail({ label, value }: { label: string; value: string | number | null }) {
  if (value === null || value === "") return null;
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm">{value}</dd>
    </div>
  );
}

/** Shows the full review and exactly which sentences produced each label, so no result is a black box. */
export function ReviewDrawer({ reviewId, onClose }: { reviewId: number | null; onClose: () => void }) {
  const query = useReview(reviewId);

  return (
    <Sheet open={reviewId !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
        <SheetHeader>
          <SheetTitle>Review {reviewId}</SheetTitle>
          <SheetDescription>The text, and how each label was worked out from it.</SheetDescription>
        </SheetHeader>
        <div className="px-4 pb-6">
          <QueryView query={query} skeleton={<Skeleton className="h-64 w-full" />} errorTitle="Could not load this review">
            {(review) => (
              <div className="flex flex-col gap-5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{review.property_name}</span>
                  <span className="text-sm text-muted-foreground">{formatDate(review.review_date)}</span>
                  {review.is_synthetic && <Badge variant="outline">Synthetic demo</Badge>}
                </div>
                <div className="space-y-2 text-sm">
                  {review.title && <p className="font-medium">{review.title}</p>}
                  {review.positive_text && (
                    <p>
                      <span className="font-medium">Liked: </span>
                      {review.positive_text}
                    </p>
                  )}
                  {review.negative_text && (
                    <p>
                      <span className="font-medium">Disliked: </span>
                      {review.negative_text}
                    </p>
                  )}
                  {review.body_text && <p>{review.body_text}</p>}
                  {!review.title && !review.positive_text && !review.negative_text && !review.body_text && (
                    <p className="text-muted-foreground">This review has a rating but no text.</p>
                  )}
                </div>
                <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <Detail label="Rating (0–10)" value={review.rating === null ? "none" : formatRating(review.rating)} />
                  <Detail label="Language" value={review.language ? `${review.language}${review.language_detected ? " (detected)" : ""}` : null} />
                  <Detail label="Source" value={review.source} />
                  <Detail label="Traveller type" value={review.traveller_type} />
                  <Detail label="Reviewer country" value={review.reviewer_country} />
                  <Detail label="Room" value={review.room_type} />
                  <Detail label="Nights" value={review.stay_nights} />
                </dl>

                <section aria-labelledby="seg-title">
                  <h3 id="seg-title" className="mb-2 text-sm font-semibold">
                    Sentiment by part of the review
                  </h3>
                  {review.segments.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Not analysed
                      {review.analysis_status === "non_english" && " (the review is not in English)"}
                      {review.analysis_status === "no_text" && " (the review has no text)"}.
                    </p>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Part</TableHead>
                          <TableHead>Label</TableHead>
                          <TableHead className="text-right">Score</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {review.segments.map((segment) => (
                          <TableRow key={segment.segment}>
                            <TableCell>{SEGMENT_TEXT[segment.segment] ?? segment.segment}</TableCell>
                            <TableCell>
                              <span className="inline-flex items-center gap-1.5">
                                <SentimentDot label={segment.label as SentimentLabel} />
                                {SENTIMENT_TEXT[segment.label as SentimentLabel]}
                              </span>
                            </TableCell>
                            <TableCell className="text-right tabular-nums">{segment.score.toFixed(2)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                  {review.segments[0] && (
                    <p className="mt-2 text-xs text-muted-foreground">
                      Method: {review.segments[0].model_name}. Scores run from −1 (most negative) to +1 (most
                      positive); between −0.05 and +0.05 counts as neutral.
                    </p>
                  )}
                </section>

                <section aria-labelledby="men-title">
                  <h3 id="men-title" className="mb-2 text-sm font-semibold">
                    Aspects found, with the sentence behind each
                  </h3>
                  {review.mentions.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No aspect keywords were found in this review.</p>
                  ) : (
                    <ul className="space-y-3">
                      {review.mentions.map((mention) => (
                        <li key={`${mention.aspect}-${mention.evidence_text}`} className="text-sm">
                          <p className="flex items-center gap-1.5 font-medium">
                            <SentimentDot label={mention.label as SentimentLabel} />
                            {mention.display_name}: {mention.label}
                          </p>
                          <blockquote className="mt-1 border-l-2 pl-3">“{mention.evidence_text}”</blockquote>
                          <p className="pl-3 text-xs text-muted-foreground">
                            Matched “{mention.matched_term}” in the {SEGMENT_TEXT[mention.source_field] ?? mention.source_field}.
                          </p>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              </div>
            )}
          </QueryView>
        </div>
      </SheetContent>
    </Sheet>
  );
}
