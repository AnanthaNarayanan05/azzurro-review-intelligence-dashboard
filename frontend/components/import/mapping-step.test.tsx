import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MappingStep } from "@/components/import/mapping-step";
import { jsonResponse, mockFetch, renderWithProviders } from "@/test/utils";
import type { ImportPreview } from "@/types/api";

const preview: ImportPreview = {
  import_id: 1,
  filename: "export.csv",
  source_type: "csv",
  total_rows: 12,
  columns: ["Date", "Score", "Text"],
  sheets: [],
  sheet: null,
  encoding: "utf-8",
  delimiter: ",",
  sample_rows: [{ Date: "2026-01-02", Score: "9", Text: "Lovely stay" }],
  suggested_mapping: {},
  property_values: { values: [], truncated: false },
  already_imported_as: null,
};

const fields = [
  { key: "review_date", label: "Review date", description: "When the review was written", required: "always" },
  { key: "rating", label: "Rating", description: "Overall score", required: "one_of" },
];

function setup(mapping: Record<string, string>, over: Partial<ImportPreview> = {}) {
  mockFetch(jsonResponse({ data: fields }));
  const onNext = vi.fn();
  renderWithProviders(
    <MappingStep
      preview={{ ...preview, ...over }}
      mapping={mapping}
      onMappingChange={vi.fn()}
      onSheetChange={vi.fn()}
      sheetLoading={false}
      sheetError={null}
      onBack={vi.fn()}
      onNext={onNext}
    />,
  );
  return onNext;
}

describe("MappingStep", () => {
  it("blocks continuing until a date and a rating or text column are chosen", async () => {
    const onNext = setup({});
    expect(await screen.findByLabelText("Review date")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent("review date");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(onNext).not.toHaveBeenCalled();
  });

  it("lets the user continue once the mapping is valid", async () => {
    const onNext = setup({ review_date: "Date", rating: "Score" });
    await screen.findByLabelText("Review date");
    const button = screen.getByRole("button", { name: "Continue" });
    await waitFor(() => expect(button).toBeEnabled());
    await userEvent.click(button);
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it("warns when the same file was imported before", async () => {
    setup({ review_date: "Date", rating: "Score" }, { already_imported_as: 7 });
    expect(await screen.findByText("This exact file was imported before")).toBeInTheDocument();
  });
});
