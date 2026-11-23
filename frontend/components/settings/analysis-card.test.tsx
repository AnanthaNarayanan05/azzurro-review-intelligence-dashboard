import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { AnalysisCard } from "@/components/settings/analysis-card";
import { jsonResponse, mockFetch, renderWithProviders } from "@/test/utils";
import type { AnalysisStatus } from "@/types/api";

const status: AnalysisStatus = {
  engine: "vader-3.3.2",
  lexicon_version: "1.0.0",
  total_reviews: 20,
  analysed: 16,
  no_text: 2,
  non_english: 1,
  pending: 1,
  latest_run: null,
  notes: ["Sentiment uses VADER, an English-only lexicon method."],
};

describe("AnalysisCard", () => {
  it("shows the counts, the method and the honesty notes", async () => {
    mockFetch(jsonResponse({ data: status }));
    renderWithProviders(<AnalysisCard />);
    expect(await screen.findByText("No analysis has run yet.", { exact: false })).toBeInTheDocument();
    expect(screen.getByText(/vader-3.3.2/)).toBeInTheDocument();
    expect(screen.getByText("Sentiment uses VADER, an English-only lexicon method.")).toBeInTheDocument();
    expect(screen.getByText("16")).toBeInTheDocument();
  });

  it("disables the waiting-reviews button when nothing is waiting", async () => {
    mockFetch(jsonResponse({ data: { ...status, pending: 0, analysed: 17 } }));
    renderWithProviders(<AnalysisCard />);
    expect(await screen.findByRole("button", { name: /Analyse waiting reviews \(0\)/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Re-analyse all reviews" })).toBeEnabled();
  });

  it("runs the analysis with the chosen scope and refreshes the status", async () => {
    const fetchMock = mockFetch(
      jsonResponse({ data: status }),
      jsonResponse({ data: { run: null, processed: 20, analysed: 17, no_text: 2, non_english: 1, aspect_mentions: 9 } }),
      jsonResponse({ data: { ...status, pending: 0, analysed: 17 } }),
    );
    renderWithProviders(<AnalysisCard />);
    await userEvent.click(await screen.findByRole("button", { name: "Re-analyse all reviews" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    const [url, init] = fetchMock.mock.calls[1];
    expect(String(url)).toContain("/api/analysis/run");
    expect(JSON.parse(init.body as string)).toEqual({ scope: "all" });
  });

  it("shows an error with a retry when the status cannot be loaded", async () => {
    mockFetch(jsonResponse({ error: { code: "X", message: "Service is down", details: null } }, 500));
    renderWithProviders(<AnalysisCard />);
    expect(await screen.findByText("Service is down")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });
});
