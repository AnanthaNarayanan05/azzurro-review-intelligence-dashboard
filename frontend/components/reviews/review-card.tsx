import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatDate, formatRating } from "@/lib/format";
import type { ReviewItem, SentimentLabel } from "@/types/analytics";

export const SENTIMENT_TEXT: Record<SentimentLabel, string> = {
  positive: "Positive",
  neutral: "Neutral",
  negative: "Negative",
};

const STATUS_TEXT: Record<string, string> = {
  no_text: "No text to analyse",
  non_english: "Not in English: not analysed",
};

/** Colour never carries the meaning alone: every label is also written out. */
export function SentimentDot({ label }: { label: SentimentLabel }) {
  const color =
    label === "positive" ? "var(--viz-positive)" : label === "negative" ? "var(--viz-negative)" : "var(--viz-neutral)";
  return <span className="inline-block size-2.5 shrink-0 rounded-full" style={{ backgroundColor: color }} aria-hidden />;
}

export function ReviewCard({ review, onOpen }: { review: ReviewItem; onOpen: (id: number) => void }) {
  const hasStructured = review.positive_text || review.negative_text;
  return (
    <Card size="sm">
      <CardContent className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
          <span className="font-medium">{review.property_name}</span>
          <span className="text-muted-foreground">{formatDate(review.review_date)}</span>
          <span className="tabular-nums">Rating {formatRating(review.rating)}</span>
          {review.sentiment && (
            <span className="inline-flex items-center gap-1.5">
              <SentimentDot label={review.sentiment.label} />
              {SENTIMENT_TEXT[review.sentiment.label as SentimentLabel]} text
            </span>
          )}
          {review.is_synthetic && <Badge variant="outline">Synthetic demo</Badge>}
          {review.analysis_status && STATUS_TEXT[review.analysis_status] && (
            <Badge variant="secondary">{STATUS_TEXT[review.analysis_status]}</Badge>
          )}
          {review.analysis_status === null && <Badge variant="secondary">Waiting for analysis</Badge>}
        </div>
        {review.title && <p className="text-sm font-medium">{review.title}</p>}
        {review.positive_text && (
          <p className="text-sm">
            <span className="font-medium">Liked: </span>
            {review.positive_text}
          </p>
        )}
        {review.negative_text && (
          <p className="text-sm">
            <span className="font-medium">Disliked: </span>
            {review.negative_text}
          </p>
        )}
        {!hasStructured && review.body_text && <p className="text-sm">{review.body_text}</p>}
        {review.aspects.length > 0 && (
          <ul className="flex flex-wrap gap-2" aria-label="Aspects mentioned">
            {review.aspects.map((aspect) => (
              <li
                key={aspect.aspect}
                className="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs"
              >
                <SentimentDot label={aspect.label} />
                {aspect.display_name}: {aspect.label}
              </li>
            ))}
          </ul>
        )}
        <div>
          <Button variant="outline" size="sm" onClick={() => onOpen(review.id)}>
            Why this analysis?
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
