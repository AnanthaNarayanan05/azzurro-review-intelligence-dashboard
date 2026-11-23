"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";

import { ErrorState } from "@/components/states/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useHydrated } from "@/hooks/use-hydrated";
import { issueCodeLabel, OUTCOME_LABELS } from "@/lib/import-labels";
import { listIssues } from "@/services/imports";
import type { IssueOutcome } from "@/types/api";

const PAGE_SIZE = 15;
type Filter = IssueOutcome | "all";

const OUTCOME_STYLE: Record<IssueOutcome, "destructive" | "secondary" | "outline"> = {
  rejected: "destructive",
  duplicate: "secondary",
  warning: "outline",
};

/** Row-level results of one import. Every rejected, duplicate and warning row is listed here. */
export function IssuesTable({ importId, initialFilter = "all" }: { importId: number; initialFilter?: Filter }) {
  const [filter, setFilter] = useState<Filter>(initialFilter);
  const [page, setPage] = useState(1);
  const hydrated = useHydrated();

  const query = useQuery({
    queryKey: ["imports", importId, "issues", filter, page],
    queryFn: () => listIssues(importId, { outcome: filter === "all" ? undefined : filter, page, pageSize: PAGE_SIZE }),
  });

  const total = query.data?.meta.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-medium">Row details</h3>
        <Select
          value={filter}
          onValueChange={(value) => {
            setFilter(value as Filter);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-44" aria-label="Filter rows by outcome">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All issues</SelectItem>
            <SelectItem value="rejected">Rejected rows</SelectItem>
            <SelectItem value="duplicate">Duplicates</SelectItem>
            <SelectItem value="warning">Warnings and updates</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {query.isError ? (
        <ErrorState
          title="Could not load row details"
          message={query.error.message}
          onRetry={() => query.refetch()}
          retrying={query.isFetching}
        />
      ) : !hydrated || query.isPending ? (
        <Skeleton className="h-40 w-full" />
      ) : total === 0 ? (
        <p className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
          {filter === "all" ? "Every row imported cleanly. Nothing to report." : "No rows with this outcome."}
        </p>
      ) : (
        <>
          <div className="overflow-x-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-20">Row</TableHead>
                  <TableHead className="w-28">Outcome</TableHead>
                  <TableHead>What happened</TableHead>
                  <TableHead className="w-32">Field</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {query.data.data.map((issue) => (
                  <TableRow key={issue.id}>
                    <TableCell className="tabular-nums">{issue.row_number}</TableCell>
                    <TableCell>
                      <Badge variant={OUTCOME_STYLE[issue.outcome]}>{OUTCOME_LABELS[issue.outcome]}</Badge>
                    </TableCell>
                    <TableCell className="whitespace-normal">
                      <div className="font-medium">{issueCodeLabel(issue.code)}</div>
                      <div className="text-muted-foreground">{issue.message}</div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{issue.field ?? "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              {total.toLocaleString()} {total === 1 ? "row" : "rows"} · page {page} of {pageCount}
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                <ChevronLeft aria-hidden /> Previous
              </Button>
              <Button variant="outline" size="sm" disabled={page >= pageCount} onClick={() => setPage(page + 1)}>
                Next <ChevronRight aria-hidden />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
