import type { IssueOutcome } from "@/types/api";

/** Plain-language names for the backend's issue codes. Unknown codes fall back to the raw code. */
const CODE_LABELS: Record<string, string> = {
  MISSING_DATE: "Missing date",
  INVALID_DATE: "Unreadable date",
  AMBIGUOUS_DATE: "Ambiguous date (day/month order unclear)",
  FUTURE_DATE: "Date in the future",
  INVALID_RATING: "Rating is not a number",
  RATING_OUT_OF_RANGE: "Rating outside the chosen scale",
  EMPTY_REVIEW: "No rating and no text",
  TEXT_TOO_LONG: "Text too long",
  MISSING_PROPERTY: "Property value missing",
  UNKNOWN_PROPERTY: "Property not mapped",
  DUPLICATE_EXTERNAL_ID: "Already imported (same review ID)",
  DUPLICATE_CONTENT: "Already imported (same content)",
  DUPLICATE_IN_FILE: "Repeated within this file",
  REVIEW_UPDATED: "Existing review updated",
  MISSING_RATING: "Imported without a rating",
  INVALID_LANGUAGE: "Language code ignored",
  INVALID_STAY_NIGHTS: "Nights value ignored",
  INVALID_URL: "Link ignored",
};

export function issueCodeLabel(code: string): string {
  return CODE_LABELS[code] ?? code;
}

export const OUTCOME_LABELS: Record<IssueOutcome, string> = {
  rejected: "Rejected",
  duplicate: "Duplicate",
  warning: "Warning",
};

/** The API sends UTC timestamps without a zone suffix; treat them as UTC. */
export function formatDateTime(value: string | null): string {
  if (!value) return "—";
  const iso = /[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`;
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
