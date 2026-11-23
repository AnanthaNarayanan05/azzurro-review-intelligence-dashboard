import { fireEvent, screen } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { ReviewsView } from "@/components/reviews/reviews-view";
import { dataset, overview, propertyList } from "@/test/fixtures";
import { jsonResponse, renderWithProviders } from "@/test/utils";
import type { ReviewItem } from "@/types/analytics";

const nav = vi.hoisted(() => ({ search: "", replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/reviews",
  useRouter: () => ({ replace: nav.replace }),
  useSearchParams: () => new URLSearchParams(nav.search),
}));

const review = (id: number, over: Partial<ReviewItem> = {}): ReviewItem => ({
  id,
  property_id: 1,
  property_name: "Alpha Hotel",
  review_date: "2026-03-02",
  rating: 8.5,
  title: null,
  positive_text: "Great breakfast.",
  negative_text: "Noisy corridor.",
  body_text: null,
  language: "en",
  source: "import",
  is_synthetic: false,
  analysis_status: "analysed",
  sentiment: { label: "positive", score: 0.4 },
  aspects: [{ aspect: "food", display_name: "Food & breakfast", label: "positive" }],
  ...over,
});

function api(reviews: ReviewItem[], total = reviews.length) {
  const fn = vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input));
    if (url.pathname === "/api/properties") return jsonResponse({ data: propertyList });
    if (url.pathname === "/api/analytics/aspects")
      return jsonResponse({ data: { items: [{ aspect: "food", display_name: "Food & breakfast", mentions: 5, positive: 3, neutral: 1, negative: 1, positive_share: 0.6, negative_share: 0.2, mention_rate: 0.1, low_sample: true }], analysed_reviews: 50, min_mentions: 10, definition: "" } });
    if (url.pathname === "/api/analytics/overview") return jsonResponse({ data: overview({ dataset: dataset() }) });
    if (url.pathname === "/api/reviews") return jsonResponse({ data: reviews, meta: { page: 1, page_size: 20, total } });
    return jsonResponse({ error: { code: "NOT_FOUND", message: url.pathname, details: null } }, 404);
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

const reviewCalls = (fn: ReturnType<typeof api>) =>
  fn.mock.calls.map(([u]) => new URL(String(u))).filter((u) => u.pathname === "/api/reviews");

beforeAll(() => {
  // jsdom lacks these browser features, which Radix's Select needs when it opens.
  Element.prototype.scrollIntoView = vi.fn();
  Element.prototype.hasPointerCapture = vi.fn(() => false);
  Element.prototype.releasePointerCapture = vi.fn();
});

beforeEach(() => {
  nav.search = "";
  nav.replace.mockReset();
});

describe("ReviewsView", () => {
  it("lists reviews with their sentiment and aspect labels written out", async () => {
    api([review(1)]);
    renderWithProviders(<ReviewsView />);
    expect(await screen.findByText("Liked:")).toBeInTheDocument();
    expect(screen.getByText(/Noisy corridor/)).toBeInTheDocument();
    expect(screen.getByText(/Positive text/)).toBeInTheDocument();
    expect(screen.getByText("Food & breakfast: positive")).toBeInTheDocument();
    expect(screen.getByText(/1 review\b/)).toBeInTheDocument();
  });

  it("labels synthetic and unanalysed reviews", async () => {
    api([review(1, { is_synthetic: true }), review(2, { analysis_status: "non_english", sentiment: null, aspects: [] })]);
    renderWithProviders(<ReviewsView />);
    expect(await screen.findByText("Synthetic demo")).toBeInTheDocument();
    expect(screen.getByText("Not in English: not analysed")).toBeInTheDocument();
  });

  it("sends the URL's filters, search and sort to the API", async () => {
    nav.search = "scope=all&q=wifi&sentiment=negative&rating_min=3&aspect=food&aspect_sentiment=negative&sort=rating_asc&page=2";
    const fn = api([review(1)], 45);
    renderWithProviders(<ReviewsView />);
    await screen.findByText("Liked:");
    const call = reviewCalls(fn)[0];
    expect(Object.fromEntries(call.searchParams)).toMatchObject({
      data_scope: "all",
      q: "wifi",
      sentiment: "negative",
      rating_min: "3",
      aspect: "food",
      aspect_sentiment: "negative",
      sort: "rating_asc",
      page: "2",
      page_size: "20",
    });
  });

  it("changes the sentiment filter through the URL and returns to page 1", async () => {
    nav.search = "page=3";
    api([review(1)], 100);
    renderWithProviders(<ReviewsView />);
    await screen.findByText("Liked:");
    fireEvent.pointerDown(screen.getByRole("combobox", { name: /Overall sentiment/ }), { button: 0, ctrlKey: false, pointerType: "mouse" });
    fireEvent.click(await screen.findByRole("option", { name: "Negative" }));
    expect(nav.replace).toHaveBeenCalledWith("/reviews?sentiment=negative", { scroll: false });
  });

  it("pages forward and back", async () => {
    nav.search = "page=2";
    api([review(1)], 45);
    renderWithProviders(<ReviewsView />);
    await screen.findByText("Liked:");
    expect(screen.getAllByText(/Page 2 of 3/).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: /Next/ }));
    expect(nav.replace).toHaveBeenLastCalledWith("/reviews?page=3", { scroll: false });
    fireEvent.click(screen.getByRole("button", { name: /Previous/ }));
    expect(nav.replace).toHaveBeenLastCalledWith("/reviews", { scroll: false });
  });

  it("offers to clear the search when nothing matches", async () => {
    nav.search = "q=zzz";
    api([], 0);
    renderWithProviders(<ReviewsView />);
    expect(await screen.findByText("No reviews match")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: /Clear search and filters/ })[0]);
    expect(nav.replace).toHaveBeenCalled();
  });

  it("does not ask the API when the rating range is inverted", async () => {
    nav.search = "rating_min=9&rating_max=2";
    const fn = api([review(1)]);
    renderWithProviders(<ReviewsView />);
    expect(await screen.findByText(/lowest rating is higher/)).toBeInTheDocument();
    expect(reviewCalls(fn)).toHaveLength(0);
  });
});
