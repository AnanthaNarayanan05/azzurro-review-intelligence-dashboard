import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { NavLinks } from "@/components/layout/nav-links";
import { NAV_SECTIONS } from "@/lib/navigation";
import { renderWithProviders } from "@/test/utils";

vi.mock("next/navigation", () => ({ usePathname: () => "/overview" }));

describe("NavLinks", () => {
  it("renders available pages as links and marks the current page", () => {
    renderWithProviders(<NavLinks />);

    const overview = screen.getByRole("link", { name: "Overview" });
    expect(overview).toHaveAttribute("href", "/overview");
    expect(overview).toHaveAttribute("aria-current", "page");
  });

  it("renders pages that are not built yet as disabled, never as working links", () => {
    renderWithProviders(<NavLinks />);

    const unavailable = NAV_SECTIONS.flatMap((s) => s.items).filter((item) => !item.available);
    expect(unavailable.length).toBeGreaterThan(0);
    for (const item of unavailable) {
      expect(screen.queryByRole("link", { name: new RegExp(item.label) })).toBeNull();
      const element = screen.getByTestId(`nav-disabled-${item.href}`);
      expect(element).toHaveAttribute("aria-disabled", "true");
      expect(element).toHaveTextContent(`planned for phase ${item.phase}`);
    }
  });
});
