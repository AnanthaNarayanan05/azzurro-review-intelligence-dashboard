import { ChartTable } from "@/components/charts/chart-table";
import { formatCount, formatRating } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface IntervalRow {
  id: number;
  name: string;
  value: number | null;
  low: number | null;
  high: number | null;
  n: number;
  lowSample: boolean;
}

/**
 * Average rating per property with its 95% interval. Overlapping intervals mean the difference may be
 * chance, which is why the chart shows them instead of just ranking the dots.
 */
export function IntervalChart({ rows }: { rows: IntervalRow[] }) {
  const drawable = rows.filter((r) => r.value !== null && r.low !== null && r.high !== null);
  if (drawable.length === 0) {
    return <p className="text-sm text-muted-foreground">No rated reviews to compare.</p>;
  }
  const min = Math.min(...drawable.map((r) => r.low as number));
  const max = Math.max(...drawable.map((r) => r.high as number));
  const d0 = Math.max(0, Math.floor(min - 0.5));
  const d1 = Math.min(10, Math.ceil(max + 0.5));
  const pct = (v: number) => `${(((v - d0) / (d1 - d0)) * 100).toFixed(2)}%`;
  const ticks = Array.from({ length: d1 - d0 + 1 }, (_, i) => d0 + i);

  return (
    <div>
      <ul className="space-y-3">
        {rows.map((row) => {
          const ok = row.value !== null && row.low !== null && row.high !== null;
          return (
            <li
              key={row.id}
              className="grid grid-cols-[minmax(7rem,11rem)_1fr] items-center gap-x-3 gap-y-0.5 sm:grid-cols-[minmax(7rem,11rem)_1fr_11rem]"
            >
              <span className="text-sm font-medium">{row.name}</span>
              <div className="relative h-6" role="img" aria-label={ok ? `${row.name}: ${formatRating(row.value)}, 95% interval ${formatRating(row.low)} to ${formatRating(row.high)}, ${row.n} rated reviews` : `${row.name}: not enough data`}>
                <div className="absolute inset-x-0 top-1/2 h-px bg-[var(--viz-grid)]" />
                {ok && (
                  <>
                    <div
                      className="absolute top-1/2 h-0.5 -translate-y-1/2 bg-[var(--viz-bar)]"
                      style={{ left: pct(row.low as number), width: `calc(${pct(row.high as number)} - ${pct(row.low as number)})` }}
                    />
                    {[row.low as number, row.high as number].map((end) => (
                      <div
                        key={end}
                        className="absolute top-1/2 h-3 w-0.5 -translate-x-1/2 -translate-y-1/2 bg-[var(--viz-bar)]"
                        style={{ left: pct(end) }}
                      />
                    ))}
                    <div
                      className={cn(
                        "absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--viz-bar)]",
                        row.lowSample ? "bg-card" : "bg-[var(--viz-bar)] ring-2 ring-card",
                      )}
                      style={{ left: pct(row.value as number) }}
                    />
                  </>
                )}
              </div>
              <span className="col-start-2 text-xs tabular-nums text-muted-foreground sm:col-start-3">
                {ok
                  ? `${formatRating(row.value)} (${formatRating(row.low)}–${formatRating(row.high)}), n=${formatCount(row.n)}`
                  : `n=${formatCount(row.n)}, too few to estimate`}
                {row.lowSample && ok && " · low sample"}
              </span>
            </li>
          );
        })}
      </ul>
      <div className="mt-2 grid grid-cols-[minmax(7rem,11rem)_1fr] gap-x-3 sm:grid-cols-[minmax(7rem,11rem)_1fr_11rem]">
        <span />
        <div className="relative h-4 text-xs text-muted-foreground" aria-hidden>
          {ticks.map((t) => (
            <span key={t} className="absolute -translate-x-1/2 tabular-nums" style={{ left: pct(t) }}>
              {t}
            </span>
          ))}
        </div>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        Dot: average rating. Line: 95% interval. Hollow dot: low sample. The axis is zoomed to {d0}–{d1} so
        differences are visible; the scale is 0–10.
      </p>
      <ChartTable
        caption="Average rating per property with 95% interval"
        columns={["Property", "Average rating", "Interval low", "Interval high", "Rated reviews"]}
        rows={rows.map((r) => [r.name, formatRating(r.value), formatRating(r.low), formatRating(r.high), formatCount(r.n)])}
      />
    </div>
  );
}
