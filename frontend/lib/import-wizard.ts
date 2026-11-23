import type { CommitRequest, DateFormat, PropertyValue } from "@/types/api";

/** Select items cannot have an empty value, so "not mapped" uses a sentinel. */
export const NONE = "__none__";
export const SKIP = "skip";

export type PropertyMode = "column" | "fixed";
export type PropertyChoice = number | typeof SKIP;

const TEXT_FIELDS = ["positive_text", "negative_text", "body_text"] as const;

/** Problems that stop the user leaving the column-mapping step. Empty means the mapping is usable. */
export function mappingProblems(mapping: Record<string, string>): string[] {
  const problems: string[] = [];
  if (!mapping.review_date) problems.push("Choose the column that holds the review date.");
  if (!mapping.rating && !TEXT_FIELDS.some((field) => mapping[field])) {
    problems.push("Choose at least a rating column or a review text column.");
  }
  return problems;
}

/** The property a distinct file value will go to: the user's choice, else the automatic suggestion. */
export function effectiveChoice(
  value: PropertyValue,
  choices: Record<string, PropertyChoice>,
): PropertyChoice | undefined {
  return choices[value.value] ?? value.suggested_property_id ?? undefined;
}

/** Problems that stop the import from starting. Skipped property values are allowed (their rows are rejected and reported). */
export function propertyProblems(args: {
  mode: PropertyMode;
  fixedPropertyId: number | null;
  mapping: Record<string, string>;
  values: PropertyValue[];
  choices: Record<string, PropertyChoice>;
}): string[] {
  if (args.mode === "fixed") {
    return args.fixedPropertyId === null ? ["Choose the property these reviews belong to."] : [];
  }
  if (!args.mapping.property) return ["Choose the column that holds the property name."];
  const undecided = args.values.filter((value) => effectiveChoice(value, args.choices) === undefined);
  return undecided.length > 0
    ? [`Choose a property (or skip) for ${undecided.length} unmatched value${undecided.length === 1 ? "" : "s"}.`]
    : [];
}

export interface CommitInputs {
  mapping: Record<string, string>;
  mode: PropertyMode;
  fixedPropertyId: number | null;
  values: PropertyValue[];
  choices: Record<string, PropertyChoice>;
  ratingScaleMax: number;
  dateFormat: DateFormat;
  sourceName: string;
  isSynthetic: boolean;
  sheet: string | null;
}

export function buildCommitRequest(input: CommitInputs): CommitRequest {
  const columnMapping: Record<string, string> = {};
  for (const [field, column] of Object.entries(input.mapping)) {
    if (column && (field !== "property" || input.mode === "column")) columnMapping[field] = column;
  }

  const propertyMapping: Record<string, number> = {};
  if (input.mode === "column") {
    for (const value of input.values) {
      const choice = effectiveChoice(value, input.choices);
      if (typeof choice === "number") propertyMapping[value.value] = choice;
    }
  }

  return {
    column_mapping: columnMapping,
    property_mapping: propertyMapping,
    fixed_property_id: input.mode === "fixed" ? input.fixedPropertyId : null,
    rating_scale_max: input.ratingScaleMax,
    date_format: input.dateFormat,
    source_name: input.sourceName.trim() || "booking.com",
    is_synthetic: input.isSynthetic,
    sheet: input.sheet,
    remember_aliases: true,
  };
}

export const DATE_FORMAT_LABELS: Record<DateFormat, string> = {
  auto: "Detect automatically (ambiguous dates are rejected)",
  iso: "Year-month-day (2026-03-14)",
  dmy: "Day/month/year (14/03/2026)",
  mdy: "Month/day/year (03/14/2026)",
};
