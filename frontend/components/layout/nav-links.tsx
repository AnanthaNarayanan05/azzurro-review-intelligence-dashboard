"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { NAV_SECTIONS, isActivePath, type NavItem } from "@/lib/navigation";
import { cn } from "@/lib/utils";

const itemBase =
  "flex h-9 items-center gap-3 rounded-md px-3 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-sidebar-ring";

function DisabledItem({ item }: { item: NavItem }) {
  const Icon = item.icon;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        {/* Not a link and not focusable: the visible badge and sr-only text explain the state. */}
        <div
          aria-disabled="true"
          data-testid={`nav-disabled-${item.href}`}
          className={cn(itemBase, "cursor-not-allowed text-muted-foreground/70")}
        >
          <Icon className="size-4 shrink-0" aria-hidden />
          <span className="flex-1">
            {item.label}
            <span className="sr-only"> (not available yet, planned for phase {item.phase})</span>
          </span>
          <Badge variant="outline" className="text-[10px] font-normal text-muted-foreground" aria-hidden>
            Phase {item.phase}
          </Badge>
        </div>
      </TooltipTrigger>
      <TooltipContent side="right">Not built yet. Planned for roadmap phase {item.phase}.</TooltipContent>
    </Tooltip>
  );
}

function NavLinkList({ activePath, onNavigate }: { activePath: string | null; onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="flex flex-col gap-6">
      {NAV_SECTIONS.map((section) => (
        <div key={section.title} className="flex flex-col gap-1">
          <p className="px-3 pb-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">
            {section.title}
          </p>
          {section.items.map((item) => {
            if (!item.available) return <DisabledItem key={item.href} item={item} />;
            const Icon = item.icon;
            const active = activePath !== null && isActivePath(activePath, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onNavigate}
                aria-current={active ? "page" : undefined}
                className={cn(
                  itemBase,
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-sidebar-foreground/80 hover:bg-muted hover:text-sidebar-foreground",
                )}
              >
                <Icon className="size-4 shrink-0" aria-hidden />
                {item.label}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}

/** Navigation with the current page highlighted. Reads the URL, so render it inside <Suspense>. */
export function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return <NavLinkList activePath={pathname} onNavigate={onNavigate} />;
}

/** URL-independent fallback used while the active route is resolved. */
export function NavLinksFallback() {
  return <NavLinkList activePath={null} />;
}
