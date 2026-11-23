import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { NavLinks } from "@/components/layout/nav-links";
import { NAV_SECTIONS } from "@/lib/navigation";
import { renderWithProviders } from "@/test/utils";

vi.mock("next/navigation", () => ({ usePathname: () => "/overview" }));

// Every real page is built now, so a not-yet-built entry is added to prove the disabled rendering
// still works for any page that is listed before it exists.
vi.mock("@/lib/navigation", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/navigation")>();
  const planned = { href: "/planned", label: "Planned page", icon: actual.NAV_SECTIONS[0].items[0].icon, phase: 9, available: false };
  return {
    ...actual,
    NAV_SECTIONS: [{ ...actual.NAV_SECTIONS[0], items: [...actual.NAV_SECTIONS[0].items, planned] }, ...actual.NAV_SECTIONS.slice(1)],
  };
});

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
