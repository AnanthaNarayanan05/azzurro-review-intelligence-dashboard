import type { ReviewQuery } from "@/services/analytics";
import type { ReviewSort, SentimentLabel } from "@/types/analytics";

export const PAGE_SIZE = 20;

const SENTIMENTS: SentimentLabel[] = ["positive", "neutral", "negative"];
const SORTS: ReviewSort[] = ["newest", "oldest", "rating_desc", "rating_asc"];

function rating(value: string | null): string {
  if (value === null || value.trim() === "") return "";
  const n = Number(value);
  return Number.isFinite(n) && n >= 0 && n <= 10 ? String(n) : "";
}

/** Reads the explorer's own URL parameters (the global filters are read separately). */
export function parseReviewQuery(params: URLSearchParams): ReviewQuery {
  const sentiment = params.get("sentiment") as SentimentLabel | null;
  const aspectSentiment = params.get("aspect_sentiment") as SentimentLabel | null;
  const sort = params.get("sort") as ReviewSort | null;
  const page = Number(params.get("page") ?? "1");
  const aspect = params.get("aspect") ?? "";
  return {
    q: params.get("q") ?? "",
    ratingMin: rating(params.get("rating_min")),
    ratingMax: rating(params.get("rating_max")),
    sentiment: sentiment && SENTIMENTS.includes(sentiment) ? sentiment : "",
    aspect,
    aspectSentiment: aspect && aspectSentiment && SENTIMENTS.includes(aspectSentiment) ? aspectSentiment : "",
    sort: sort && SORTS.includes(sort) ? sort : "newest",
    page: Number.isInteger(page) && page >= 1 ? page : 1,
    pageSize: PAGE_SIZE,
  };
}

export function ratingRangeProblem(query: ReviewQuery): string | null {
  if (query.ratingMin !== "" && query.ratingMax !== "" && Number(query.ratingMin) > Number(query.ratingMax)) {
    return "The lowest rating is higher than the highest rating.";
  }
  return null;
}

export function hasReviewFilters(query: ReviewQuery): boolean {
  return (
    query.q.trim() !== "" ||
    query.ratingMin !== "" ||
    query.ratingMax !== "" ||
    query.sentiment !== "" ||
    query.aspect !== ""
  );
}
