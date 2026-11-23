import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ReportView } from "@/components/import/report-view";
import { renderWithProviders } from "@/test/utils";
import type { ImportReport } from "@/types/api";

vi.mock("@/components/import/issues-table", () => ({ IssuesTable: () => <div>issues table</div> }));

const report: ImportReport = {
  id: 4,
  filename: "export.csv",
  source_type: "csv",
  source_name: "booking.com",
  status: "completed",
  is_synthetic: false,
  rating_scale_max: 10,
  total_rows: 100,
  imported_rows: 80,
  updated_rows: 5,
  duplicate_rows: 10,
  rejected_rows: 5,
  warning_count: 3,
  created_at: "2026-11-01T10:00:00",
  completed_at: "2026-11-01T10:00:05",
  error_message: null,
  column_mapping: {},
  issue_summary: [{ outcome: "rejected", code: "INVALID_DATE", count: 5 }],
};

describe("ReportView", () => {
  it("shows counts that add up to the file's row total", () => {
    renderWithProviders(<ReportView report={report} />);
    expect(screen.getByTestId("reconciliation")).toHaveTextContent(
      "100 rows in the file = 80 imported + 5 updated + 10 duplicates + 5 rejected",
    );
    expect(screen.getByText(/Unreadable date/)).toBeInTheDocument();
  });

  it("labels synthetic imports and failed imports", () => {
    renderWithProviders(
      <ReportView report={{ ...report, is_synthetic: true, status: "failed", error_message: "Disk is full" }} />,
    );
    expect(screen.getByText("Synthetic demo data")).toBeInTheDocument();
    expect(screen.getByText(/nothing saved/i)).toBeInTheDocument();
    expect(screen.getByText("Disk is full")).toBeInTheDocument();
  });
});
