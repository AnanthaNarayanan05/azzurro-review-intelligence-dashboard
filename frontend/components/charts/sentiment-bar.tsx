import { formatCount, formatPercent } from "@/lib/format";
import type { SentimentBlock } from "@/types/analytics";

const SEGMENTS = [
  { key: "positive", label: "Positive", color: "var(--viz-positive)" },
  { key: "neutral", label: "Neutral", color: "var(--viz-neutral)" },
  { key: "negative", label: "Negative", color: "var(--viz-negative)" },
] as const;

/**
 * Positive / neutral / negative split of the reviews that have analysable text.
 * Reviews that could not be analysed are listed beside it, never folded into the shares.
 */
export function SentimentBar({ sentiment, showNotes = true }: { sentiment: SentimentBlock; showNotes?: boolean }) {
  const { analysed_n: total, not_analysed: skipped } = sentiment;
  const skippedTotal = skipped.no_text + skipped.non_english + skipped.pending;

  return (
    <div>
      {total === 0 ? (
        <p className="text-sm text-muted-foreground">No analysed review text in this selection.</p>
      ) : (
        <>
          <div
            className="flex h-4 gap-0.5 overflow-hidden rounded-full"
            role="img"
            aria-label={SEGMENTS.map(
              (s) => `${s.label} ${formatPercent(sentiment[`${s.key}_share`])}`,
            ).join(", ")}
          >
            {SEGMENTS.map((s) =>
              sentiment[s.key] > 0 ? (
                <div
                  key={s.key}
                  title={`${s.label}: ${formatCount(sentiment[s.key])} reviews`}
                  style={{ flexGrow: sentiment[s.key], backgroundColor: s.color }}
                />
              ) : null,
            )}
          </div>
          <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm">
            {SEGMENTS.map((s) => (
              <li key={s.key} className="flex items-center gap-2">
                <span className="size-2.5 rounded-sm" style={{ backgroundColor: s.color }} aria-hidden />
                <span>{s.label}</span>
                <span className="tabular-nums text-muted-foreground">
                  {formatPercent(sentiment[`${s.key}_share`])} ({formatCount(sentiment[s.key])})
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
      {showNotes && (
        <p className="mt-2 text-xs text-muted-foreground">
          Shares are of {formatCount(total)} reviews with {sentiment.share_denominator.replace("reviews with ", "")}.
          {skippedTotal > 0 && (
            <>
              {" "}
              Not analysed: {formatCount(skipped.no_text)} without text, {formatCount(skipped.non_english)} not
              in English, {formatCount(skipped.pending)} waiting.
            </>
          )}
        </p>
      )}
    </div>
  );
}
