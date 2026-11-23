import { describe, expect, it } from "vitest";

import {
  DEFAULT_FILTERS,
  dateRangeProblem,
  filtersToApiQuery,
  filtersToParams,
  hasActiveFilters,
  parseFilters,
  toQueryString,
} from "@/lib/filters";
import { parseReviewQuery, ratingRangeProblem } from "@/lib/reviews-query";

describe("global filters in the URL", () => {
  it("defaults to all properties, no dates and genuine data only", () => {
    expect(parseFilters(new URLSearchParams(""))).toEqual(DEFAULT_FILTERS);
    expect(hasActiveFilters(DEFAULT_FILTERS)).toBe(false);
  });

  it("round-trips through the URL", () => {
    const filters = { propertyIds: [3, 1], dateFrom: "2026-01-01", dateTo: "2026-02-01", dataScope: "all" as const };
    const params = filtersToParams(filters);
    expect(params.toString()).toBe("properties=3%2C1&from=2026-01-01&to=2026-02-01&scope=all");
    expect(parseFilters(params)).toEqual({ ...filters, propertyIds: [1, 3] });
  });

  it("omits defaults so clean URLs stay clean, and keeps unrelated parameters", () => {
    const params = filtersToParams(DEFAULT_FILTERS, new URLSearchParams("q=wifi&scope=all&from=2026-01-01"));
    expect(params.toString()).toBe("q=wifi");
  });

  it("ignores malformed values instead of failing", () => {
    const parsed = parseFilters(
      new URLSearchParams("properties=1,abc,-2,1.5,1&from=yesterday&to=2026-13&scope=everything"),
    );
    expect(parsed).toEqual({ propertyIds: [1], dateFrom: "", dateTo: "", dataScope: "genuine" });
  });

  it("uses the API's own parameter names and always sends the data scope", () => {
    expect(filtersToApiQuery(DEFAULT_FILTERS)).toEqual({ data_scope: "genuine" });
    expect(
      filtersToApiQuery({ propertyIds: [2, 4], dateFrom: "2026-01-01", dateTo: "", dataScope: "synthetic" }),
    ).toEqual({ data_scope: "synthetic", property_ids: "2,4", date_from: "2026-01-01" });
  });

  it("flags a start date after the end date", () => {
    expect(dateRangeProblem({ ...DEFAULT_FILTERS, dateFrom: "2026-03-01", dateTo: "2026-02-01" })).toMatch(/after/);
    expect(dateRangeProblem({ ...DEFAULT_FILTERS, dateFrom: "2026-01-01", dateTo: "2026-02-01" })).toBeNull();
  });

  it("builds query strings without empty values", () => {
    expect(toQueryString({ a: "1", b: "", c: undefined, d: 0 })).toBe("?a=1&d=0");
    expect(toQueryString({})).toBe("");
  });
});

describe("review explorer parameters", () => {
  it("reads valid values and falls back for invalid ones", () => {
    const good = parseReviewQuery(
      new URLSearchParams("q=wifi&sentiment=negative&rating_min=5&rating_max=9&aspect=cleanliness&aspect_sentiment=negative&sort=oldest&page=3"),
    );
    expect(good).toMatchObject({
      q: "wifi",
      sentiment: "negative",
      ratingMin: "5",
      ratingMax: "9",
      aspect: "cleanliness",
      aspectSentiment: "negative",
      sort: "oldest",
      page: 3,
    });
    const bad = parseReviewQuery(new URLSearchParams("sentiment=angry&rating_min=99&sort=random&page=-4&aspect_sentiment=negative"));
    expect(bad).toMatchObject({ sentiment: "", ratingMin: "", sort: "newest", page: 1, aspectSentiment: "" });
  });

  it("flags an inverted rating range", () => {
    expect(ratingRangeProblem(parseReviewQuery(new URLSearchParams("rating_min=8&rating_max=3")))).toMatch(/higher/);
    expect(ratingRangeProblem(parseReviewQuery(new URLSearchParams("rating_min=3&rating_max=8")))).toBeNull();
  });
});
