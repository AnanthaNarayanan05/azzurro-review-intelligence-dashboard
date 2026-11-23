import type { DataScope } from "@/types/analytics";

/** The global filters. They live in the URL so a view can be bookmarked, shared and survives refresh. */
export interface FilterState {
  propertyIds: number[];
  dateFrom: string;
  dateTo: string;
  dataScope: DataScope;
}

export const DEFAULT_FILTERS: FilterState = {
  propertyIds: [],
  dateFrom: "",
  dateTo: "",
  dataScope: "genuine",
};

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const SCOPES: DataScope[] = ["genuine", "synthetic", "all"];

export function parseFilters(params: URLSearchParams): FilterState {
  const ids = (params.get("properties") ?? "")
    .split(",")
    .map((part) => Number(part))
    .filter((n) => Number.isInteger(n) && n > 0);
  const from = params.get("from") ?? "";
  const to = params.get("to") ?? "";
  const scope = params.get("scope") as DataScope | null;
  return {
    propertyIds: [...new Set(ids)].sort((a, b) => a - b),
    dateFrom: ISO_DATE.test(from) ? from : "",
    dateTo: ISO_DATE.test(to) ? to : "",
    dataScope: scope && SCOPES.includes(scope) ? scope : "genuine",
  };
}

/** URL parameters for the filters; defaults are omitted so clean URLs stay clean. */
export function filtersToParams(
  filters: FilterState,
  into = new URLSearchParams(),
): URLSearchParams {
  const set = (key: string, value: string, fallback = "") => {
    if (value && value !== fallback) into.set(key, value);
    else into.delete(key);
  };
  set("properties", filters.propertyIds.join(","));
  set("from", filters.dateFrom);
  set("to", filters.dateTo);
  set("scope", filters.dataScope, "genuine");
  return into;
}

/** Query parameters for the analytics API (its own parameter names). */
export function filtersToApiQuery(filters: FilterState): Record<string, string> {
  const query: Record<string, string> = { data_scope: filters.dataScope };
  if (filters.propertyIds.length) query.property_ids = filters.propertyIds.join(",");
  if (filters.dateFrom) query.date_from = filters.dateFrom;
  if (filters.dateTo) query.date_to = filters.dateTo;
  return query;
}

export function hasActiveFilters(filters: FilterState): boolean {
  return (
    filters.propertyIds.length > 0 ||
    !!filters.dateFrom ||
    !!filters.dateTo ||
    filters.dataScope !== "genuine"
  );
}

export function dateRangeProblem(filters: FilterState): string | null {
  if (filters.dateFrom && filters.dateTo && filters.dateFrom > filters.dateTo) {
    return "The start date is after the end date.";
  }
  return null;
}

export function toQueryString(
  params: Record<string, string | number | undefined | null>,
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}
