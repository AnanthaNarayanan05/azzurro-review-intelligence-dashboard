"use client";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useHealth } from "@/hooks/use-health";
import { useHydrated } from "@/hooks/use-hydrated";
import { cn } from "@/lib/utils";

type Tone = "checking" | "ok" | "warning" | "error";

const dotClass: Record<Tone, string> = {
  checking: "bg-muted-foreground/50 animate-pulse",
  ok: "bg-emerald-500",
  warning: "bg-amber-500",
  error: "bg-red-500",
};

/** Compact header indicator of backend and database connectivity. */
export function ApiStatus() {
  const { data, error, isPending } = useHealth();
  const hydrated = useHydrated();

  let tone: Tone;
  let label: string;
  let detail: string;

  if (!hydrated || isPending) {
    tone = "checking";
    label = "Checking service";
    detail = "Contacting the analytics API…";
  } else if (error) {
    tone = "error";
    label = "Service unreachable";
    detail = error.message;
  } else if (data?.database !== "ok") {
    tone = "warning";
    label = "Database unavailable";
    detail = "The API is running but cannot reach its database.";
  } else {
    tone = "ok";
    label = "Service connected";
    detail = `API v${data.version} · ${data.database_backend} database`;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          role="status"
          aria-live="polite"
          tabIndex={0}
          className="flex items-center gap-2 rounded-full border bg-card px-3 py-1 text-xs font-medium text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className={cn("size-2 rounded-full", dotClass[tone])} aria-hidden />
          <span className="sr-only sm:not-sr-only">{label}</span>
        </div>
      </TooltipTrigger>
      <TooltipContent>{detail}</TooltipContent>
    </Tooltip>
  );
}
