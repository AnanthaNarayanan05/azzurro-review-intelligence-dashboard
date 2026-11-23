"use client";

import { useQuery } from "@tanstack/react-query";
import { History } from "lucide-react";
import { useState } from "react";

import { ReportView } from "@/components/import/report-view";
import { UndoImportButton } from "@/components/import/undo-import-dialog";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useHydrated } from "@/hooks/use-hydrated";
import { formatDateTime } from "@/lib/import-labels";
import { listImports } from "@/services/imports";
import type { ImportReport } from "@/types/api";

const PAGE_SIZE = 10;

export function ImportHistory() {
  const hydrated = useHydrated();
  const [page, setPage] = useState(1);
  const [openId, setOpenId] = useState<number | null>(null);
  const query = useQuery({ queryKey: ["imports", "history", page], queryFn: () => listImports(page, PAGE_SIZE) });

  if (!hydrated || query.isPending) return <Skeleton className="h-48 w-full" />;
  if (query.isError) {
    return <ErrorState title="Could not load import history" message={query.error.message} onRetry={() => query.refetch()} />;
  }

  const { data: items, meta } = query.data;
  if (items.length === 0 && page === 1) {
    return (
      <EmptyState
        icon={History}
        title="No imports yet"
        description="Imported files and their reports will be listed here."
      />
    );
  }

  const opened: ImportReport | undefined = items.find((item) => item.id === openId);
  const pages = Math.max(1, Math.ceil(meta.total / PAGE_SIZE));

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>File</TableHead>
              <TableHead>When</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Imported</TableHead>
              <TableHead className="text-right">Duplicates</TableHead>
              <TableHead className="text-right">Rejected</TableHead>
              <TableHead className="w-24" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="max-w-64 truncate font-medium">
                  {item.filename}
                  {item.is_synthetic && (
                    <Badge variant="outline" className="ml-2">
                      Synthetic
                    </Badge>
                  )}
                </TableCell>
                <TableCell className="whitespace-nowrap">{formatDateTime(item.completed_at ?? item.created_at)}</TableCell>
                <TableCell>
                  <Badge variant={item.status === "failed" ? "destructive" : "secondary"}>{item.status}</Badge>
                </TableCell>
                <TableCell className="text-right tabular-nums">{item.imported_rows.toLocaleString()}</TableCell>
                <TableCell className="text-right tabular-nums">{item.duplicate_rows.toLocaleString()}</TableCell>
                <TableCell className="text-right tabular-nums">{item.rejected_rows.toLocaleString()}</TableCell>
                <TableCell>
                  <Button variant="outline" size="sm" onClick={() => setOpenId(item.id)}>
                    Details
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {pages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Page {page} of {pages}
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>
              Next
            </Button>
          </div>
        </div>
      )}

      <Sheet open={opened !== undefined} onOpenChange={(open) => !open && setOpenId(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-3xl">
          <SheetHeader>
            <SheetTitle>Import report</SheetTitle>
            <SheetDescription>Every row of this import is accounted for below.</SheetDescription>
          </SheetHeader>
          {opened && (
            <div className="space-y-4 px-4 pb-6">
              <ReportView report={opened} />
              {opened.status === "completed" && (
                <UndoImportButton report={opened} onUndone={() => setOpenId(null)} />
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
