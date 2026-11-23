import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ApiStatus } from "@/components/system/api-status";
import { SystemStatusCard } from "@/components/system/system-status-card";
import { healthyStatus, jsonResponse, mockFetch, renderWithProviders } from "@/test/utils";

describe("ApiStatus", () => {
  it("shows a checking state, then connected when the API is healthy", async () => {
    mockFetch(jsonResponse({ data: healthyStatus }));
    renderWithProviders(<ApiStatus />);

    expect(screen.getByRole("status")).toHaveTextContent("Checking service");
    expect(await screen.findByText("Service connected")).toBeInTheDocument();
  });

  it("warns when the API is up but the database is not", async () => {
    mockFetch(jsonResponse({ data: { ...healthyStatus, status: "degraded", database: "unavailable" } }, 503));
    renderWithProviders(<ApiStatus />);

    expect(await screen.findByText("Database unavailable")).toBeInTheDocument();
  });

  it("reports the API as unreachable on network failure", async () => {
    mockFetch(new TypeError("Failed to fetch"));
    renderWithProviders(<ApiStatus />);

    expect(await screen.findByText("Service unreachable")).toBeInTheDocument();
  });
});

describe("SystemStatusCard", () => {
  it("lists live health details", async () => {
    mockFetch(jsonResponse({ data: healthyStatus }));
    renderWithProviders(<SystemStatusCard />);

    expect(await screen.findByText("Connected (sqlite)")).toBeInTheDocument();
    expect(screen.getByText("VADER")).toBeInTheDocument();
    expect(screen.getByText("Disabled (template insights)")).toBeInTheDocument();
  });

  it("offers a working retry after a failure", async () => {
    const fetchMock = mockFetch(new TypeError("Failed to fetch"), jsonResponse({ data: healthyStatus }));
    renderWithProviders(<SystemStatusCard />);

    const retry = await screen.findByRole("button", { name: /try again/i });
    retry.click();

    expect(await screen.findByText("Connected (sqlite)")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
