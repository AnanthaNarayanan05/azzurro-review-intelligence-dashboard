import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FilterBar } from "@/components/filters/filter-bar";
import { propertyList } from "@/test/fixtures";
import { jsonResponse, renderWithProviders } from "@/test/utils";

vi.mock("next/navigation", () => ({
  usePathname: () => "/x",
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(""),
}));

describe("FilterBar", () => {
  it("shows the date range by default and hides it when asked", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ data: propertyList })));
    const { unmount } = renderWithProviders(<FilterBar />);
    expect(await screen.findByLabelText("From")).toBeInTheDocument();
    expect(screen.getByLabelText("To")).toBeInTheDocument();
    unmount();
    renderWithProviders(<FilterBar showDates={false} />);
    expect(await screen.findByLabelText("Data")).toBeInTheDocument();
    expect(screen.queryByLabelText("From")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("To")).not.toBeInTheDocument();
  });
});
