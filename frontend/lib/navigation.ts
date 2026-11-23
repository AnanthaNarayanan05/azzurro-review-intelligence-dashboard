import {
  BarChart3,
  Building2,
  GitCompareArrows,
  LayoutDashboard,
  Lightbulb,
  MessageSquareText,
  Settings,
  Upload,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Roadmap phase that delivers the page. Pages that are not built yet are shown disabled. */
  phase: number;
  available: boolean;
}

export interface NavSection {
  title: string;
  items: NavItem[];
}

/** Single source of truth for navigation. Flip `available` when a page is actually implemented. */
export const NAV_SECTIONS: NavSection[] = [
  {
    title: "Analytics",
    items: [
      { href: "/overview", label: "Overview", icon: LayoutDashboard, phase: 5, available: true },
      { href: "/properties", label: "Properties", icon: Building2, phase: 5, available: true },
      { href: "/comparison", label: "Comparison", icon: GitCompareArrows, phase: 5, available: true },
      { href: "/reviews", label: "Reviews", icon: MessageSquareText, phase: 5, available: true },
      { href: "/insights", label: "Insights", icon: Lightbulb, phase: 6, available: false },
    ],
  },
  {
    title: "Data",
    items: [
      { href: "/import", label: "Data Import", icon: Upload, phase: 3, available: true },
      { href: "/settings", label: "Settings", icon: Settings, phase: 3, available: true },
    ],
  },
];

export const APP_NAME = "Azzurro Hotels";
export const APP_SUBTITLE = "Review Intelligence";
export const APP_ICON = BarChart3;

export function isActivePath(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
