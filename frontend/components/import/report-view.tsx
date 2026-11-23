import { IssuesTable } from "@/components/import/issues-table";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { formatDateTime, issueCodeLabel } from "@/lib/import-labels";
import type { ImportReport } from "@/types/api";

function Stat({ label, value, hint }: { label: string; value: number; hint: string }) {
  return (
    <Card size="sm">
      <CardContent>
        <div className="text-2xl font-semibold tabular-nums">{value.toLocaleString()}</div>
        <div className="text-sm font-medium">{label}</div>
        <div className="text-xs text-muted-foreground">{hint}</div>
      </CardContent>
    </Card>
  );
}

/** The outcome of one import: reconciled counts, why rows were not imported, and every row issue. */
export function ReportView({ report }: { report: ImportReport }) {
  const { imported_rows, updated_rows, duplicate_rows, rejected_rows, total_rows } = report;

  return (
    <div className="space-y-5" data-testid="import-report">
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <span className="font-medium text-foreground">{report.filename}</span>
        <span>· {report.source_type.toUpperCase()}</span>
        <span>· source: {report.source_name}</span>
        <span>· {formatDateTime(report.completed_at ?? report.created_at)}</span>
        {report.is_synthetic && <Badge variant="outline">Synthetic demo data</Badge>}
        {report.status === "failed" && <Badge variant="destructive">Failed, nothing saved</Badge>}
      </div>

      {report.error_message && <p className="text-sm text-destructive">{report.error_message}</p>}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Imported" value={imported_rows} hint="New reviews added" />
        <Stat label="Updated" value={updated_rows} hint="Existing reviews changed" />
        <Stat label="Duplicates" value={duplicate_rows} hint="Skipped, already stored" />
        <Stat label="Rejected" value={rejected_rows} hint="Could not be imported" />
      </div>

      <p className="text-sm text-muted-foreground" data-testid="reconciliation">
        {total_rows.toLocaleString()} rows in the file = {imported_rows.toLocaleString()} imported +{" "}
        {updated_rows.toLocaleString()} updated + {duplicate_rows.toLocaleString()} duplicates +{" "}
        {rejected_rows.toLocaleString()} rejected
        {report.warning_count > 0 && ` (${report.warning_count.toLocaleString()} imported rows carry a warning)`}.
      </p>

      {report.issue_summary.length > 0 && (
        <ul className="flex flex-wrap gap-2" aria-label="Summary of issues">
          {report.issue_summary.map((item) => (
            <li key={`${item.outcome}-${item.code}`}>
              <Badge variant={item.outcome === "rejected" ? "destructive" : "secondary"}>
                {issueCodeLabel(item.code)} · {item.count.toLocaleString()}
              </Badge>
            </li>
          ))}
        </ul>
      )}

      <IssuesTable importId={report.id} />
    </div>
  );
}
