import { describe, expect, it } from "vitest";

import { buildCommitRequest, effectiveChoice, mappingProblems, propertyProblems, SKIP } from "@/lib/import-wizard";
import type { PropertyValue } from "@/types/api";

const value = (raw: string, suggested: number | null = null, count = 1): PropertyValue => ({
  value: raw,
  count,
  suggested_property_id: suggested,
  match_type: suggested === null ? null : "name",
});

describe("mappingProblems", () => {
  it("requires a date and either a rating or some review text", () => {
    expect(mappingProblems({})).toHaveLength(2);
    expect(mappingProblems({ review_date: "Date" })).toHaveLength(1);
    expect(mappingProblems({ review_date: "Date", rating: "Score" })).toEqual([]);
    expect(mappingProblems({ review_date: "Date", body_text: "Review" })).toEqual([]);
  });
});

describe("effectiveChoice", () => {
  it("prefers the user's choice over the automatic suggestion", () => {
    expect(effectiveChoice(value("A", 1), { A: 2 })).toBe(2);
    expect(effectiveChoice(value("A", 1), {})).toBe(1);
    expect(effectiveChoice(value("A"), {})).toBeUndefined();
    expect(effectiveChoice(value("A", 1), { A: SKIP })).toBe(SKIP);
  });
});

describe("propertyProblems", () => {
  const base = { fixedPropertyId: null, mapping: { property: "Hotel" }, choices: {} };

  it("asks for a property in fixed mode", () => {
    expect(propertyProblems({ ...base, mode: "fixed", values: [] })).toHaveLength(1);
    expect(propertyProblems({ ...base, mode: "fixed", fixedPropertyId: 3, values: [] })).toEqual([]);
  });

  it("blocks column mode while a value has no property and no decision", () => {
    const problems = propertyProblems({ ...base, mode: "column", values: [value("A", 1), value("B")] });
    expect(problems).toEqual(["Choose a property (or skip) for 1 unmatched value."]);
  });

  it("accepts skipping a value as a decision", () => {
    expect(propertyProblems({ ...base, mode: "column", values: [value("B")], choices: { B: SKIP } })).toEqual([]);
  });

  it("needs a mapped column in column mode", () => {
    expect(propertyProblems({ ...base, mapping: {}, mode: "column", values: [] })).toHaveLength(1);
  });
});

describe("buildCommitRequest", () => {
  const common = {
    ratingScaleMax: 10,
    dateFormat: "auto" as const,
    sourceName: "  ",
    isSynthetic: false,
    sheet: null,
  };

  it("maps each distinct value, leaving skipped values out", () => {
    const request = buildCommitRequest({
      ...common,
      mapping: { review_date: "Date", property: "Hotel" },
      mode: "column",
      fixedPropertyId: null,
      values: [value("A", 1), value("B"), value("C", 3)],
      choices: { B: 2, C: SKIP },
    });
    expect(request.property_mapping).toEqual({ A: 1, B: 2 });
    expect(request.fixed_property_id).toBeNull();
    expect(request.column_mapping).toEqual({ review_date: "Date", property: "Hotel" });
    expect(request.source_name).toBe("booking.com");
  });

  it("drops the property column and sends the fixed property in fixed mode", () => {
    const request = buildCommitRequest({
      ...common,
      mapping: { review_date: "Date", property: "Hotel" },
      mode: "fixed",
      fixedPropertyId: 7,
      values: [value("A", 1)],
      choices: {},
    });
    expect(request.column_mapping).toEqual({ review_date: "Date" });
    expect(request.property_mapping).toEqual({});
    expect(request.fixed_property_id).toBe(7);
  });
});
