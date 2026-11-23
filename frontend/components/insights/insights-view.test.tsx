import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { InsightsView } from "@/components/insights/insights-view";
import { dataset, propertyList } from "@/test/fixtures";
import { evidence, insight } from "@/test/insight-fixtures";
import { jsonResponse, renderWithProviders } from "@/test/utils";
import type { Dataset, Insight } from "@/types/analytics";

const nav = vi.hoisted(() => ({ search: "", replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/insights",
  useRouter: () => ({ replace: nav.replace }),
  useSearchParams: () => new URLSearchParams(nav.search),
}));

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const result = {
  data_scope: "genuine",
  as_of: "2026-03-30",
  created: 2,
  replaced: 0,
  rejected_by_validator: 0,
  by_type: {},
  checked_property_aspects: 8,
  below_mention_floor: 3,
  comparisons_skipped_too_few: 0,
  notes: [],
};

interface Meta {
  stale: boolean;
  generated_at: string | null;
}

function api(items: Insight[], meta: Partial<Meta> = {}, ds: Dataset = dataset()) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input));
    if (url.pathname === "/api/properties") return jsonResponse({ data: propertyList });
    if (url.pathname === "/api/insights/generate" && init?.method === "POST") {
      return jsonResponse({ data: result });
    }
    if (url.pathname === "/api/insights") {
      return jsonResponse({
        data: items,
        meta: {
          page: 1,
          page_size: 20,
          total: items.length,
          data_scope: "genuine",
          generated_at: meta.generated_at === undefined ? "2026-03-31T09:00:00" : meta.generated_at,
          stale: meta.stale ?? false,
          analysis_run_id: 1,
          dataset: ds,
        },
      });
    }
    return jsonResponse({ error: { code: "NOT_FOUND", message: url.pathname, details: null } }, 404);
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
  Element.prototype.hasPointerCapture = vi.fn(() => false);
  Element.prototype.releasePointerCapture = vi.fn();
});

beforeEach(() => {
  nav.search = "";
  nav.replace.mockReset();
});

describe("InsightsView", () => {
  it("shows what was found, the action, and a link to exactly the supporting reviews", async () => {
    api([insight()]);
    renderWithProviders(<InsightsView />);
    expect(await screen.findByText(/Cleanliness is a recurring complaint/)).toBeInTheDocument();
    expect(screen.getByText("Moderate evidence")).toBeInTheDocument();
    expect(screen.getByText(/Review housekeeping standards/)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /See all 10 reviews/ });
    expect(link.getAttribute("href")).toContain("/reviews?");
    expect(link.getAttribute("href")).toContain("aspect=cleanliness");
  });

  it("reveals the verbatim example sentences, each linking to the full review", async () => {
    api([insight()]);
    renderWithProviders(<InsightsView />);
    const toggle = await screen.findByRole("button", { name: /Show 2 example sentences/ });
    expect(screen.queryByText(/The room was dirty/)).not.toBeInTheDocument();
    fireEvent.click(toggle);
    expect(screen.getByText(/The room was dirty/)).toBeInTheDocument();
    expect(screen.getByText(/Dust everywhere/)).toBeInTheDocument();
    const open = screen.getAllByRole("link", { name: "Open full review" });
    expect(open[0].getAttribute("href")).toContain("review=11");
    fireEvent.click(screen.getByRole("button", { name: /Hide 2 example sentences/ }));
    expect(screen.queryByText(/Dust everywhere/)).not.toBeInTheDocument();
  });

  it("labels insights built from synthetic data", async () => {
    api(
      [insight({ data_scope: "synthetic", evidence: [evidence({ is_synthetic: true })] })],
      {},
      dataset({ scope: "synthetic" }),
    );
    renderWithProviders(<InsightsView />);
    const labels = await screen.findAllByText("Synthetic demo data");
    // The page banner and the badge on the insight card.
    expect(labels.length).toBeGreaterThanOrEqual(2);
  });

  it("warns when insights are out of date and regenerates on request", async () => {
    const fn = api([insight()], { stale: true });
    renderWithProviders(<InsightsView />);
    expect(await screen.findByText("These insights are out of date")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Regenerate insights" }));
    await waitFor(() => {
      const post = fn.mock.calls.find(
        ([u, i]) => String(u).endsWith("/api/insights/generate") && i?.method === "POST",
      );
      expect(post).toBeTruthy();
      expect(JSON.parse(String(post?.[1]?.body))).toEqual({ data_scope: "genuine" });
    });
  });

  it("does not claim staleness when current", async () => {
    api([insight()]);
    renderWithProviders(<InsightsView />);
    await screen.findByText(/Cleanliness is a recurring complaint/);
    expect(screen.queryByText("These insights are out of date")).not.toBeInTheDocument();
  });

  it("offers to generate when none exist yet", async () => {
    api([], { generated_at: null });
    renderWithProviders(<InsightsView />);
    expect(await screen.findByText("No insights generated yet")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Generate insights" }).length).toBeGreaterThan(0);
  });

  it("explains an empty result after generation instead of inventing insights", async () => {
    api([]);
    renderWithProviders(<InsightsView />);
    expect(await screen.findByText("No insights for this selection")).toBeInTheDocument();
    expect(screen.getByText(/Nothing met the evidence rules/)).toBeInTheDocument();
  });

  it("points to import when there are no reviews at all", async () => {
    api([], { generated_at: null }, dataset({ genuine_reviews: 0, synthetic_reviews: 0 }));
    renderWithProviders(<InsightsView />);
    expect(await screen.findByText("No insights to show")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Generate insights" })).not.toBeInTheDocument();
  });

  it("sends the chosen filters to the API and clears them through the URL", async () => {
    nav.search = "type=strength&strength=strong";
    const fn = api([insight({ insight_type: "strength" })]);
    renderWithProviders(<InsightsView />);
    await screen.findByText(/Cleanliness is a recurring complaint/);
    const call = fn.mock.calls
      .map(([u]) => new URL(String(u)))
      .find((u) => u.pathname === "/api/insights");
    expect(call?.searchParams.get("insight_type")).toBe("strength");
    expect(call?.searchParams.get("evidence_strength")).toBe("strong");
    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(nav.replace).toHaveBeenCalledWith("/insights", { scroll: false });
  });

  it("shows an error with retry when the API fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) =>
        new URL(String(input)).pathname === "/api/properties"
          ? jsonResponse({ data: propertyList })
          : jsonResponse({ error: { code: "INTERNAL", message: "boom", details: null } }, 500),
      ),
    );
    renderWithProviders(<InsightsView />);
    expect(await screen.findByText("Could not load insights")).toBeInTheDocument();
  });
});
