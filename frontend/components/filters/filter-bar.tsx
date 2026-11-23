"use client";

import { RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useFilters } from "@/hooks/use-filters";
import { useHydrated } from "@/hooks/use-hydrated";
import { useProperties } from "@/hooks/use-properties";
import { hasActiveFilters } from "@/lib/filters";
import { cn } from "@/lib/utils";
import type { DataScope } from "@/types/analytics";

const SCOPE_LABELS: Record<DataScope, string> = {
  genuine: "Genuine reviews only",
  synthetic: "Synthetic demo data only",
  all: "Genuine and synthetic (mixed)",
};

interface FilterBarProps {
  /** Hide the property chips on pages that are already about one property. */
  showProperties?: boolean;
}

/** The global filters. State lives in the URL, so every view can be bookmarked and shared. */
export function FilterBar({ showProperties = true }: FilterBarProps) {
  const hydrated = useHydrated();
  const { filters, problem, update, reset } = useFilters();
  const properties = useProperties();
  const active = (properties.data ?? []).filter((p) => p.is_active);

  function toggle(id: number) {
    const next = filters.propertyIds.includes(id)
      ? filters.propertyIds.filter((x) => x !== id)
      : [...filters.propertyIds, id];
    update({ propertyIds: next.sort((a, b) => a - b) });
  }

  return (
    <section aria-label="Filters" className="rounded-lg border bg-card p-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:flex-wrap lg:items-end">
        {showProperties && (
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            <span id="filter-properties" className="text-xs font-medium text-muted-foreground">
              Properties {filters.propertyIds.length === 0 && "(all)"}
            </span>
            <div role="group" aria-labelledby="filter-properties" className="flex flex-wrap gap-2">
              {!hydrated || properties.isPending ? (
                <span className="text-sm text-muted-foreground">Loading properties…</span>
              ) : properties.isError ? (
                <span className="text-sm text-destructive">Could not load properties.</span>
              ) : active.length === 0 ? (
                <span className="text-sm text-muted-foreground">
                  No properties yet. Add them in Settings.
                </span>
              ) : (
                active.map((property) => {
                  const selected = filters.propertyIds.includes(property.id);
                  return (
                    <button
                      key={property.id}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => toggle(property.id)}
                      className={cn(
                        "rounded-full border px-3 py-1 text-sm transition-colors focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
                        selected
                          ? "border-primary bg-primary text-primary-foreground"
                          : "bg-background hover:bg-muted",
                      )}
                    >
                      {property.name}
                    </button>
                  );
                })
              )}
            </div>
          </div>
        )}

        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="filter-from" className="text-xs text-muted-foreground">
              From
            </Label>
            <Input
              id="filter-from"
              type="date"
              value={filters.dateFrom}
              max={filters.dateTo || undefined}
              aria-invalid={problem ? true : undefined}
              onChange={(e) => update({ dateFrom: e.target.value })}
              className="w-40"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="filter-to" className="text-xs text-muted-foreground">
              To
            </Label>
            <Input
              id="filter-to"
              type="date"
              value={filters.dateTo}
              min={filters.dateFrom || undefined}
              aria-invalid={problem ? true : undefined}
              onChange={(e) => update({ dateTo: e.target.value })}
              className="w-40"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="filter-scope" className="text-xs text-muted-foreground">
              Data
            </Label>
            <Select
              value={filters.dataScope}
              onValueChange={(value) => update({ dataScope: value as DataScope })}
            >
              <SelectTrigger id="filter-scope" className="w-60">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(SCOPE_LABELS) as DataScope[]).map((scope) => (
                  <SelectItem key={scope} value={scope}>
                    {SCOPE_LABELS[scope]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            type="button"
            variant="outline"
            onClick={reset}
            disabled={!hasActiveFilters(filters)}
          >
            <RotateCcw aria-hidden /> Reset
          </Button>
        </div>
      </div>
      {problem && (
        <p role="alert" className="mt-3 text-sm text-destructive">
          {problem} Nothing is loaded until the range is fixed.
        </p>
      )}
    </section>
  );
}
