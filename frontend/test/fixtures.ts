import { vi } from "vitest";

import { jsonResponse } from "@/test/utils";
import type {
  AspectRow,
  Comparison,
  Dataset,
  Overview,
  SentimentBlock,
} from "@/types/analytics";

export const dataset = (over: Partial<Dataset> = {}): Dataset => ({
  scope: "genuine",
  genuine_reviews: 100,
  synthetic_reviews: 0,
  mixed: false,
  first_review_date: "2026-01-05",
  last_review_date: "2026-03-30",
  ...over,
});

export const sentiment = (over: Partial<SentimentBlock> = {}): SentimentBlock => ({
  analysed_n: 90,
  positive: 63,
  neutral: 9,
  negative: 18,
  positive_share: 0.7,
  neutral_share: 0.1,
  negative_share: 0.2,
  share_denominator: "reviews with analysed text",
  not_analysed: { no_text: 4, non_english: 6, pending: 0 },
  ...over,
});

export const aspect = (over: Partial<AspectRow> = {}): AspectRow => ({
  aspect: "cleanliness",
  display_name: "Cleanliness",
  mentions: 40,
  positive: 28,
  neutral: 4,
  negative: 8,
  positive_share: 0.7,
  negative_share: 0.2,
  mention_rate: 0.44,
  low_sample: false,
  ...over,
});

export const overview = (over: Partial<Overview> = {}): Overview => ({
  dataset: dataset(),
  reviews: { n: 100, with_text_analysis: 90 },
  min_sample: 30,
  rating: {
    value: 8.4,
    n: 96,
    missing: 4,
    low_sample: false,
    scale: "0-10",
    distribution: Array.from({ length: 10 }, (_, k) => ({
      label: `${k}-${k + 1}`,
      from: k,
      to: k + 1,
      n: k === 8 ? 50 : k === 9 ? 30 : 2,
      share: null,
    })),
  },
  sentiment: sentiment(),
  properties: [
    { property_id: 1, name: "Alpha Hotel", reviews: 60, rating: { value: 8.6, n: 58, missing: 2, low_sample: false } },
    { property_id: 2, name: "Beta Hotel", reviews: 40, rating: { value: 8.1, n: 38, missing: 2, low_sample: false } },
  ],
  aspects: {
    most_praised: [aspect()],
    most_criticised: [aspect({ aspect: "wifi", display_name: "Wi-Fi", negative: 12, negative_share: 0.5 })],
    min_mentions: 10,
  },
  ...over,
});

export const comparison = (over: Partial<Comparison> = {}): Comparison => ({
  dataset: dataset(),
  properties: [
    {
      property_id: 1,
      name: "Alpha Hotel",
      reviews: 60,
      rating: { value: 8.9, n: 58, missing: 2, low_sample: false, ci_low: 8.7, ci_high: 9.1 },
      sentiment: sentiment(),
      aspects: [aspect()],
    },
    {
      property_id: 2,
      name: "Beta Hotel",
      reviews: 40,
      rating: { value: 7.2, n: 38, missing: 2, low_sample: false, ci_low: 6.9, ci_high: 7.5 },
      sentiment: sentiment({ positive_share: 0.5, negative_share: 0.4 }),
      aspects: [aspect({ low_sample: true, mentions: 4 })],
    },
  ],
  rating_ranking: { status: "ranked", reason: null, best: 1, worst: 2, ordered: [1, 2] },
  min_sample: 30,
  min_aspect_mentions: 10,
  note: "Best and worst are named only when the intervals do not overlap.",
  ...over,
});

export const propertyList = [
  { id: 1, code: "alpha", name: "Alpha Hotel", location: null, is_active: true, review_count: 60, synthetic_review_count: 0, aliases: [] },
  { id: 2, code: "beta", name: "Beta Hotel", location: null, is_active: true, review_count: 40, synthetic_review_count: 0, aliases: [] },
  { id: 3, code: "gamma", name: "Gamma Closed", location: null, is_active: false, review_count: 5, synthetic_review_count: 0, aliases: [] },
];

/** Answer fetch calls by URL path, so a page that makes several requests gets the right body for each. */
export function mockApi(routes: Record<string, unknown | ((url: URL) => Response)>) {
  const fn = vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input));
    const key = Object.keys(routes).find((path) => url.pathname === path);
    if (!key) return jsonResponse({ error: { code: "NOT_FOUND", message: `no mock for ${url.pathname}`, details: null } }, 404);
    const value = routes[key];
    if (typeof value === "function") return (value as (u: URL) => Response)(url);
    return jsonResponse({ data: value });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}
