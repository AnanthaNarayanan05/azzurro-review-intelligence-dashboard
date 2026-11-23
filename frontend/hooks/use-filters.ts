"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

import {
  DEFAULT_FILTERS,
  dateRangeProblem,
  filtersToParams,
  parseFilters,
  type FilterState,
} from "@/lib/filters";

/** Read and change URL query parameters without losing the ones you did not touch. */
export function useUrlParams() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const key = searchParams.toString();

  const params = useMemo(() => new URLSearchParams(key), [key]);

  const setParams = useCallback(
    (patch: Record<string, string | null | undefined>, options: { keepPage?: boolean } = {}) => {
      const next = new URLSearchParams(key);
      for (const [name, value] of Object.entries(patch)) {
        if (value === null || value === undefined || value === "") next.delete(name);
        else next.set(name, value);
      }
      // Any change to what is being listed starts again from page 1.
      if (!options.keepPage && !("page" in patch)) next.delete("page");
      const text = next.toString();
      router.replace(text ? `${pathname}?${text}` : pathname, { scroll: false });
    },
    [key, pathname, router],
  );

  return { params, setParams };
}

/** The global filters, held in the URL (`?properties=1,2&from=…&to=…&scope=…`). */
export function useFilters() {
  const { params, setParams } = useUrlParams();
  const filters = useMemo(() => parseFilters(params), [params]);
  const problem = dateRangeProblem(filters);

  const update = useCallback(
    (patch: Partial<FilterState>) => {
      const merged = filtersToParams({ ...filters, ...patch });
      setParams({
        properties: merged.get("properties"),
        from: merged.get("from"),
        to: merged.get("to"),
        scope: merged.get("scope"),
      });
    },
    [filters, setParams],
  );

  const reset = useCallback(() => update(DEFAULT_FILTERS), [update]);

  return { filters, problem, update, reset };
}

/** Link target that keeps the current filters when moving between pages. */
export function filtersHref(path: string, filters: FilterState): string {
  const text = filtersToParams(filters).toString();
  return text ? `${path}?${text}` : path;
}
