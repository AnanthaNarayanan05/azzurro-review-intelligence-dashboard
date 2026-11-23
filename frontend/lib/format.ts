export function formatPercent(share: number | null | undefined, digits = 0): string {
  return share === null || share === undefined ? "–" : `${(share * 100).toFixed(digits)}%`;
}

export function formatRating(value: number | null | undefined): string {
  return value === null || value === undefined ? "–" : value.toFixed(1);
}

export function formatCount(n: number): string {
  return n.toLocaleString("en-GB");
}

function utcDate(iso: string): Date {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

/** `2026-03-02` -> `2 Mar 2026`. Calendar dates carry no time zone, so none is applied. */
export function formatDate(iso: string): string {
  return utcDate(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function formatShortDate(iso: string): string {
  return utcDate(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
}

export function formatMonth(iso: string): string {
  return utcDate(iso).toLocaleDateString("en-GB", {
    month: "short",
    year: "2-digit",
    timeZone: "UTC",
  });
}

export function formatSigned(value: number, digits = 1): string {
  const text = Math.abs(value).toFixed(digits);
  return value > 0 ? `+${text}` : value < 0 ? `−${text}` : text;
}

/** The API sends UTC timestamps without a zone suffix; without one the browser would read them as local time. */
export function formatDateTime(timestamp: string): string {
  const utc = /(Z|[+-]\d\d:?\d\d)$/.test(timestamp) ? timestamp : `${timestamp}Z`;
  return new Date(utc).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
}
