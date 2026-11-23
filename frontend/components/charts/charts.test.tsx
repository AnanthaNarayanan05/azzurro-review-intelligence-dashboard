import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { IntervalChart } from "@/components/charts/interval-chart";
import { LineChart } from "@/components/charts/line-chart";
import { RatingDistribution } from "@/components/charts/rating-distribution";
import { SentimentBar } from "@/components/charts/sentiment-bar";
import { KpiTile } from "@/components/dashboard/kpi-tile";
import { DatasetBanner } from "@/components/filters/dataset-banner";
import { dataset, overview, sentiment } from "@/test/fixtures";
import type { TrendPoint } from "@/types/analytics";

describe("KpiTile", () => {
  it("always shows the sample size, the missing count and a low-sample flag", () => {
    render(<KpiTile label="Average rating" value="8.5" n={12} missing={3} lowSample />);
    expect(screen.getByText("8.5")).toBeInTheDocument();
    expect(screen.getByText(/Based on 12 reviews; 3 without a value/)).toBeInTheDocument();
    expect(screen.getByText("Low sample")).toBeInTheDocument();
  });

  it("does not flag a large sample", () => {
    render(<KpiTile label="Reviews" value="465" n={465} />);
    expect(screen.queryByText("Low sample")).toBeNull();
  });
});

describe("DatasetBanner", () => {
  it("says nothing for genuine data", () => {
    const { container } = render(<DatasetBanner dataset={dataset()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("labels synthetic data as not real", () => {
    render(<DatasetBanner dataset={dataset({ scope: "synthetic", genuine_reviews: 0, synthetic_reviews: 465 })} />);
    expect(screen.getByText("Synthetic demo data")).toBeInTheDocument();
    expect(screen.getByText(/not real guest feedback/)).toBeInTheDocument();
  });

  it("warns loudly when genuine and synthetic are mixed", () => {
    render(<DatasetBanner dataset={dataset({ scope: "all", mixed: true, synthetic_reviews: 20 })} />);
    expect(screen.getByText("Genuine and synthetic reviews are mixed")).toBeInTheDocument();
    expect(screen.getByText(/100 genuine and 20 synthetic/)).toBeInTheDocument();
  });

  it("explains an empty genuine view when only demo data exists", () => {
    render(<DatasetBanner dataset={dataset({ genuine_reviews: 0, synthetic_reviews: 465 })} />);
    expect(screen.getByText("No genuine reviews imported yet")).toBeInTheDocument();
  });
});

describe("SentimentBar", () => {
  it("shows shares with counts and lists reviews that were not analysed separately", () => {
    render(<SentimentBar sentiment={sentiment()} />);
    expect(screen.getByText(/70% \(63\)/)).toBeInTheDocument();
    expect(screen.getByText(/20% \(18\)/)).toBeInTheDocument();
    expect(screen.getByText(/4 without text, 6 not in English, 0 waiting/)).toBeInTheDocument();
  });

  it("says so when there is no analysed text", () => {
    render(<SentimentBar sentiment={sentiment({ analysed_n: 0, positive: 0, neutral: 0, negative: 0, positive_share: null, neutral_share: null, negative_share: null })} />);
    expect(screen.getByText("No analysed review text in this selection.")).toBeInTheDocument();
  });
});

describe("RatingDistribution", () => {
  const bins = overview().rating.distribution;

  it("reveals exact counts on hover and offers a table", () => {
    render(<RatingDistribution bins={bins} />);
    fireEvent.mouseEnter(screen.getByRole("button", { name: "Rating 8-9: 50 reviews" }));
    expect(screen.getByText(/Rating 8-9:/)).toBeInTheDocument();
    expect(screen.getByText("View as table")).toBeInTheDocument();
  });

  it("does not draw an empty chart", () => {
    render(<RatingDistribution bins={bins.map((b) => ({ ...b, n: 0 }))} />);
    expect(screen.getByText("No rated reviews in this selection.")).toBeInTheDocument();
  });
});

describe("IntervalChart", () => {
  const rows = [
    { id: 1, name: "Alpha", value: 8.9, low: 8.7, high: 9.1, n: 58, lowSample: false },
    { id: 2, name: "Beta", value: 7.0, low: 5.0, high: 9.0, n: 6, lowSample: true },
    { id: 3, name: "Gamma", value: null, low: null, high: null, n: 2, lowSample: true },
  ];

  it("shows each interval with its sample size and marks thin data", () => {
    render(<IntervalChart rows={rows} />);
    expect(screen.getByLabelText(/Alpha: 8.9, 95% interval 8.7 to 9.1, 58 rated reviews/)).toBeInTheDocument();
    expect(screen.getByText(/7.0 \(5.0–9.0\), n=6 · low sample/)).toBeInTheDocument();
    expect(screen.getByText(/n=2, too few to estimate/)).toBeInTheDocument();
  });

  it("has a table with the same numbers", () => {
    render(<IntervalChart rows={rows} />);
    const table = screen.getByRole("table", { hidden: true });
    expect(within(table).getByText("Alpha")).toBeInTheDocument();
  });

  it("says so when nothing can be drawn", () => {
    render(<IntervalChart rows={[rows[2]]} />);
    expect(screen.getByText("No rated reviews to compare.")).toBeInTheDocument();
  });
});

describe("LineChart", () => {
  const point = (start: string, value: number | null, n: number, extra: Partial<TrendPoint> = {}): TrendPoint => ({
    period_start: start,
    period_end: start,
    n,
    value,
    complete: true,
    low_sample: false,
    ...extra,
  });
  const series = [
    point("2026-01-01", 8.2, 40),
    point("2026-02-01", null, 0),
    point("2026-03-01", 8.8, 35),
    point("2026-04-01", 7.9, 5, { complete: false, low_sample: true }),
  ];
  const props = { granularity: "month" as const, formatValue: (v: number) => v.toFixed(1), valueLabel: "Average rating", minSample: 30, zeroBased: false, ceiling: 10 };

  it("draws a point for periods with data, none for an empty period, and breaks the line there", () => {
    const { container } = render(<LineChart series={series} {...props} />);
    expect(container.querySelectorAll("circle")).toHaveLength(3);
    expect(container.querySelectorAll("path")).toHaveLength(2);
  });

  it("draws unfinished or thin periods as hollow points", () => {
    const { container } = render(<LineChart series={series} {...props} />);
    const circles = [...container.querySelectorAll("circle")];
    expect(circles[0].getAttribute("class")).toContain("fill-[var(--viz-bar)]");
    expect(circles[2].getAttribute("class")).toContain("fill-card");
    expect(screen.getByText(/Hollow points: the period is not finished, or has fewer than 30/)).toBeInTheDocument();
  });

  it("lists every period in the table with notes", () => {
    render(<LineChart series={series} {...props} />);
    const table = screen.getByRole("table", { hidden: true });
    expect(within(table).getByText("not finished, low sample")).toBeInTheDocument();
  });

  it("says so when there is nothing to plot", () => {
    render(<LineChart series={[point("2026-01-01", null, 0)]} {...props} />);
    expect(screen.getByText("No data points in this selection.")).toBeInTheDocument();
  });
});
