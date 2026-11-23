import { describe, expect, it } from "vitest";

import { exampleReviewHref, parseInsightQuery, supportingReviewsHref } from "@/lib/insights";
import { insight } from "@/test/insight-fixtures";

describe("parseInsightQuery", () => {
  it("defaults to no filters on page 1", () => {
    expect(parseInsightQuery(new URLSearchParams(""))).toEqual({
      type: "",
      strength: "",
      page: 1,
      pageSize: 20,
    });
  });

  it("reads valid values and drops unknown ones", () => {
    const q = parseInsightQuery(new URLSearchParams("type=strength&strength=strong&page=3"));
    expect(q).toMatchObject({ type: "strength", strength: "strong", page: 3 });
    const bad = parseInsightQuery(new URLSearchParams("type=bogus&strength=huge&page=-2"));
    expect(bad).toMatchObject({ type: "", strength: "", page: 1 });
    expect(parseInsightQuery(new URLSearchParams("page=abc")).page).toBe(1);
  });
});

describe("evidence links", () => {
  it("opens the reviews explorer with exactly the filters the insight counted", () => {
    const href = supportingReviewsHref(insight());
    const url = new URL(href, "http://x");
    expect(url.pathname).toBe("/reviews");
    expect(url.searchParams.get("properties")).toBe("1");
    expect(url.searchParams.get("aspect")).toBe("cleanliness");
    expect(url.searchParams.get("aspect_sentiment")).toBe("negative");
    expect(url.searchParams.get("from")).toBe("2026-01-01");
    expect(url.searchParams.get("to")).toBe("2026-03-30");
    expect(url.searchParams.has("scope")).toBe(false);
  });

  it("keeps a non-genuine data scope so the same reviews are counted", () => {
    const synthetic = insight({ data_scope: "synthetic" });
    synthetic.metrics.filters.data_scope = "synthetic";
    expect(new URL(supportingReviewsHref(synthetic), "http://x").searchParams.get("scope")).toBe("synthetic");
    expect(new URL(exampleReviewHref(synthetic, 7), "http://x").searchParams.get("review")).toBe("7");
  });
});
