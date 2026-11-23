"use client";

import { useRef, useState } from "react";

import { ChartTable } from "@/components/charts/chart-table";
import { formatMonth, formatShortDate } from "@/lib/format";
import type { Granularity, TrendPoint } from "@/types/analytics";

const W = 640;
const H = 240;
const M = { left: 48, right: 14, top: 14, bottom: 30 };

interface LineChartProps {
  series: TrendPoint[];
  granularity: Granularity;
  /** Formats a value for the axis and tooltip. */
  formatValue: (value: number) => string;
  valueLabel: string;
  /** Observations a period needs before its point counts as reliable. */
  minSample: number;
  /** Start the axis at zero (counts and shares) or zoom to the data (ratings). */
  zeroBased: boolean;
  /** Fixed ceiling, for example 1 for shares or 10 for ratings. */
  ceiling?: number;
}

function periodLabel(point: TrendPoint, granularity: Granularity): string {
  return granularity === "month" ? formatMonth(point.period_start) : formatShortDate(point.period_start);
}

/** Hand-drawn SVG line chart: gaps for empty periods, hollow points where the data is thin. */
export function LineChart({
  series,
  granularity,
  formatValue,
  valueLabel,
  minSample,
  zeroBased,
  ceiling,
}: LineChartProps) {
  const box = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<number | null>(null);

  const values = series.map((p) => p.value).filter((v): v is number => v !== null);
  if (values.length === 0) {
    return <p className="text-sm text-muted-foreground">No data points in this selection.</p>;
  }

  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const cap = ceiling ?? Number.POSITIVE_INFINITY;
  const lo = zeroBased ? 0 : Math.max(0, Math.floor(rawMin - 0.5));
  let hi = zeroBased ? Math.min(cap, rawMax * 1.15) : Math.min(cap, Math.ceil(rawMax + 0.5));
  if (hi - lo < 1e-9) hi = lo + 1;

  const innerW = W - M.left - M.right;
  const innerH = H - M.top - M.bottom;
  const x = (i: number) => M.left + (series.length === 1 ? innerW / 2 : (i * innerW) / (series.length - 1));
  const y = (v: number) => M.top + innerH - ((v - lo) / (hi - lo)) * innerH;
  const ticks = [0, 1, 2, 3, 4].map((t) => lo + ((hi - lo) * t) / 4);

  // Break the line where a period has no value, so a gap is not drawn as a trend.
  const segments: string[] = [];
  let current: string[] = [];
  series.forEach((p, i) => {
    if (p.value === null) {
      if (current.length) segments.push(current.join(" "));
      current = [];
    } else {
      current.push(`${current.length ? "L" : "M"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`);
    }
  });
  if (current.length) segments.push(current.join(" "));

  const labelEvery = Math.max(1, Math.ceil(series.length / 7));

  function onMove(event: React.PointerEvent<SVGRectElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = (event.clientX - rect.left) / rect.width;
    const index = Math.round(ratio * (series.length - 1));
    setHover(Math.min(series.length - 1, Math.max(0, series.length === 1 ? 0 : index)));
  }

  const hovered = hover === null ? null : series[hover];

  return (
    <div>
      <div ref={box} className="relative">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-auto w-full"
          role="img"
          aria-label={`${valueLabel} by ${granularity}, ${series.length} periods`}
        >
          {ticks.map((tick) => (
            <g key={tick}>
              <line x1={M.left} x2={W - M.right} y1={y(tick)} y2={y(tick)} className="stroke-[var(--viz-grid)]" />
              <text x={M.left - 8} y={y(tick) + 4} textAnchor="end" className="fill-muted-foreground text-[11px]">
                {formatValue(tick)}
              </text>
            </g>
          ))}
          {segments.map((d) => (
            <path key={d} d={d} fill="none" strokeWidth={2} strokeLinejoin="round" className="stroke-[var(--viz-bar)]" />
          ))}
          {series.map((p, i) =>
            p.value === null ? null : (
              <circle
                key={p.period_start}
                cx={x(i)}
                cy={y(p.value)}
                r={hover === i ? 5.5 : 4}
                strokeWidth={2}
                className={
                  p.complete && !p.low_sample
                    ? "fill-[var(--viz-bar)] stroke-card"
                    : "fill-card stroke-[var(--viz-bar)]"
                }
              />
            ),
          )}
          {series.map((p, i) =>
            i % labelEvery === 0 ? (
              <text key={p.period_start} x={x(i)} y={H - 8} textAnchor="middle" className="fill-muted-foreground text-[11px]">
                {periodLabel(p, granularity)}
              </text>
            ) : null,
          )}
          {hover !== null && (
            <line x1={x(hover)} x2={x(hover)} y1={M.top} y2={M.top + innerH} className="stroke-muted-foreground" strokeDasharray="3 3" />
          )}
          <rect
            x={M.left}
            y={M.top}
            width={innerW}
            height={innerH}
            fill="transparent"
            onPointerMove={onMove}
            onPointerLeave={() => setHover(null)}
          />
        </svg>
        {hovered && hover !== null && (
          <div
            className="pointer-events-none absolute z-10 w-52 -translate-x-1/2 rounded-md border bg-popover p-2 text-xs shadow-md"
            style={{
              left: `${Math.min(88, Math.max(12, (x(hover) / W) * 100))}%`,
              top: 0,
            }}
          >
            <p className="font-medium">
              {periodLabel(hovered, granularity)}
              {granularity === "week" ? " (week)" : ""}
            </p>
            <p>
              {valueLabel}: {hovered.value === null ? "no reviews" : formatValue(hovered.value)}
            </p>
            <p className="text-muted-foreground">
              {hovered.n} {hovered.n === 1 ? "observation" : "observations"}
              {!hovered.complete && " · period not finished"}
              {hovered.low_sample && ` · fewer than ${minSample}`}
            </p>
          </div>
        )}
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        Hollow points: the period is not finished, or has fewer than {minSample} observations, so it is a
        weak signal.
      </p>
      <ChartTable
        caption={`${valueLabel} per ${granularity}`}
        columns={["Period starting", valueLabel, "Observations", "Note"]}
        rows={series.map((p) => [
          p.period_start,
          p.value === null ? "–" : formatValue(p.value),
          p.n,
          [!p.complete ? "not finished" : "", p.low_sample ? "low sample" : ""]
            .filter(Boolean)
            .join(", ") || "–",
        ])}
      />
    </div>
  );
}
