import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ComparisonView } from "@/components/dashboard/comparison-view";
import { OverviewView } from "@/components/dashboard/overview-view";
import { FilterBar } from "@/components/filters/filter-bar";
import { comparison, dataset, mockApi, overview, propertyList } from "@/test/fixtures";
import { jsonResponse, renderWithProviders } from "@/test/utils";

const nav = vi.hoisted(() => ({ search: "", replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/overview",
  useRouter: () => ({ replace: nav.replace }),
  useSearchParams: () => new URLSearchParams(nav.search),
}));

beforeEach(() => {
  nav.search = "";
  nav.replace.mockReset();
});

describe("FilterBar", () => {
  it("writes the chosen property to the URL, and only active properties are offered", async () => {
    mockApi({ "/api/properties": propertyList });
    renderWithProviders(<FilterBar />);

    const alpha = await screen.findByRole("button", { name: "Alpha Hotel" });
    expect(screen.queryByRole("button", { name: "Gamma Closed" })).toBeNull();
    fireEvent.click(alpha);
    expect(nav.replace).toHaveBeenCalledWith("/overview?properties=1", { scroll: false });
  });

  it("shows selected properties as pressed and can deselect them", async () => {
    nav.search = "properties=1,2&scope=all";
    mockApi({ "/api/properties": propertyList });
    renderWithProviders(<FilterBar />);

    const beta = await screen.findByRole("button", { name: "Beta Hotel" });
    expect(beta).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(beta);
    expect(nav.replace).toHaveBeenCalledWith("/overview?properties=1&scope=all", { scroll: false });
  });

  it("resets every filter to its default", async () => {
    nav.search = "properties=2&from=2026-01-01&scope=synthetic&q=keepme";
    mockApi({ "/api/properties": propertyList });
    renderWithProviders(<FilterBar />);

    fireEvent.click(await screen.findByRole("button", { name: /Reset/ }));
    expect(nav.replace).toHaveBeenCalledWith("/overview?q=keepme", { scroll: false });
  });

  it("disables Reset when nothing is filtered", async () => {
    mockApi({ "/api/properties": propertyList });
    renderWithProviders(<FilterBar />);
    expect(await screen.findByRole("button", { name: /Reset/ })).toBeDisabled();
  });

  it("changes the date range in the URL and rejects an inverted range", async () => {
    mockApi({ "/api/properties": propertyList });
    renderWithProviders(<FilterBar />);
    fireEvent.change(await screen.findByLabelText("From"), { target: { value: "2026-02-01" } });
    expect(nav.replace).toHaveBeenCalledWith("/overview?from=2026-02-01", { scroll: false });
  });

  it("explains an inverted date range", async () => {
    nav.search = "from=2026-03-01&to=2026-02-01";
    mockApi({ "/api/properties": propertyList });
    renderWithProviders(<FilterBar />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/start date is after the end date/);
  });
});

describe("OverviewView", () => {
  it("shows live numbers with their sample sizes and sends the filters to the API", async () => {
    nav.search = "properties=1&from=2026-01-01&scope=all";
    const fetchMock = mockApi({
      "/api/properties": propertyList,
      "/api/analytics/overview": overview({ dataset: dataset({ scope: "all", mixed: true, synthetic_reviews: 10 }) }),
      "/api/analytics/aspects": { items: [], analysed_reviews: 90, min_mentions: 10, definition: "" },
      "/api/analytics/trends": () => jsonResponse({ data: null }, 500),
    });
    renderWithProviders(<OverviewView />);

    expect(await screen.findByText("8.4")).toBeInTheDocument();
    expect(screen.getByText(/Based on 96 reviews; 4 without a value/)).toBeInTheDocument();
    expect(screen.getByText("70%")).toBeInTheDocument();
    expect(screen.getByText("Genuine and synthetic reviews are mixed")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Alpha Hotel" })).toHaveAttribute(
      "href",
      "/properties/1?from=2026-01-01&scope=all",
    );

    const overviewCall = fetchMock.mock.calls
      .map(([url]) => new URL(String(url)))
      .find((url) => url.pathname === "/api/analytics/overview");
    expect(overviewCall?.searchParams.get("property_ids")).toBe("1");
    expect(overviewCall?.searchParams.get("date_from")).toBe("2026-01-01");
    expect(overviewCall?.searchParams.get("data_scope")).toBe("all");
  });

  it("shows an empty state, not zeros, when nothing matches", async () => {
    mockApi({
      "/api/properties": propertyList,
      "/api/analytics/overview": overview({ reviews: { n: 0, with_text_analysis: 0 } }),
    });
    renderWithProviders(<OverviewView />);
    expect(await screen.findByText("No reviews to show")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Import reviews" })).toBeInTheDocument();
  });

  it("shows an error with a working retry", async () => {
    let calls = 0;
    mockApi({
      "/api/properties": propertyList,
      "/api/analytics/overview": () =>
        ++calls === 1
          ? jsonResponse({ error: { code: "INTERNAL", message: "boom", details: null } }, 500)
          : jsonResponse({ data: overview({ reviews: { n: 0, with_text_analysis: 0 } }) }),
    });
    renderWithProviders(<OverviewView />);

    expect(await screen.findByText("Could not load the overview")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Try again/ }));
    expect(await screen.findByText("No reviews to show")).toBeInTheDocument();
  });

  it("does not call the API while the date range is invalid", async () => {
    nav.search = "from=2026-03-01&to=2026-02-01";
    const fetchMock = mockApi({ "/api/properties": propertyList, "/api/analytics/overview": overview() });
    renderWithProviders(<OverviewView />);
    await screen.findByRole("alert");
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const paths = fetchMock.mock.calls.map(([url]) => new URL(String(url)).pathname);
    expect(paths).not.toContain("/api/analytics/overview");
  });
});

describe("ComparisonView", () => {
  it("names a best and worst property only when the API says they are ranked", async () => {
    mockApi({ "/api/properties": propertyList, "/api/analytics/comparison": comparison() });
    renderWithProviders(<ComparisonView />);
    expect(await screen.findByText(/Highest rated: Alpha Hotel\. Lowest rated: Beta Hotel\./)).toBeInTheDocument();
  });

  it("refuses to name a winner when the difference is not significant", async () => {
    mockApi({
      "/api/properties": propertyList,
      "/api/analytics/comparison": comparison({
        rating_ranking: {
          status: "difference_not_significant",
          reason: "The intervals of the highest and lowest property overlap.",
          best: null,
          worst: null,
          ordered: [1, 2],
        },
      }),
    });
    renderWithProviders(<ComparisonView />);
    expect(await screen.findByText("No clear best or worst property")).toBeInTheDocument();
    expect(screen.queryByText(/Highest rated/)).toBeNull();
  });

  it("explains insufficient data instead of ranking", async () => {
    mockApi({
      "/api/properties": propertyList,
      "/api/analytics/comparison": comparison({
        rating_ranking: { status: "insufficient_data", reason: "Fewer than two properties have 30 or more rated reviews.", best: null, worst: null, ordered: [] },
      }),
    });
    renderWithProviders(<ComparisonView />);
    expect(await screen.findByText("Not enough data to rank the properties")).toBeInTheDocument();
  });

  it("greys out aspect percentages that rest on too few mentions", async () => {
    mockApi({ "/api/properties": propertyList, "/api/analytics/comparison": comparison() });
    renderWithProviders(<ComparisonView />);
    expect(await screen.findByText(/n=4, low sample/)).toBeInTheDocument();
  });
});
