"use client";

import { useState } from "react";

import { ChartTable } from "@/components/charts/chart-table";
import { formatCount, formatPercent } from "@/lib/format";
import type { DistributionBin } from "@/types/analytics";

/** How many reviews fall in each rating band (0 to 10). Single colour: the axis already says which band. */
export function RatingDistribution({ bins }: { bins: DistributionBin[] }) {
  const [active, setActive] = useState<number | null>(null);
  const max = Math.max(1, ...bins.map((b) => b.n));
  const shown = active === null ? null : bins[active];
  const total = bins.reduce((sum, b) => sum + b.n, 0);

  if (total === 0) {
    return <p className="text-sm text-muted-foreground">No rated reviews in this selection.</p>;
  }

  return (
    <div>
      <p className="mb-2 h-5 text-sm" aria-live="polite">
        {shown ? (
          <>
            <span className="font-medium">Rating {shown.label}:</span> {formatCount(shown.n)} reviews (
            {formatPercent(shown.share)})
          </>
        ) : (
          <span className="text-muted-foreground">Hover or focus a bar for the exact count.</span>
        )}
      </p>
      <div className="flex h-40 items-end gap-0.5 border-b" role="group" aria-label="Rating distribution">
        {bins.map((bin, i) => (
          <button
            key={bin.label}
            type="button"
            aria-label={`Rating ${bin.label}: ${bin.n} reviews`}
            onMouseEnter={() => setActive(i)}
            onMouseLeave={() => setActive(null)}
            onFocus={() => setActive(i)}
            onBlur={() => setActive(null)}
            className="flex h-full flex-1 items-end justify-center rounded-t-sm focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
          >
            <span
              className="w-full rounded-t-[4px] bg-[var(--viz-bar)] transition-opacity"
              style={{
                height: `${(bin.n / max) * 100}%`,
                minHeight: bin.n > 0 ? 2 : 0,
                opacity: active === null || active === i ? 1 : 0.55,
              }}
            />
          </button>
        ))}
      </div>
      <div className="mt-1 flex gap-0.5 text-xs text-muted-foreground" aria-hidden>
        {bins.map((bin) => (
          <span key={bin.label} className="flex-1 text-center tabular-nums">
            {bin.from}
          </span>
        ))}
      </div>
      <p className="mt-1 text-center text-xs text-muted-foreground">
        Rating band (each bar covers one point, 0 to 10)
      </p>
      <ChartTable
        caption="Number of reviews per rating band"
        columns={["Rating band", "Reviews", "Share"]}
        rows={bins.map((b) => [b.label, formatCount(b.n), formatPercent(b.share, 1)])}
      />
    </div>
  );
}
