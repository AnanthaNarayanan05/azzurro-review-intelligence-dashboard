import type { ReactNode } from "react";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface ChartTableProps {
  caption: string;
  columns: string[];
  rows: ReactNode[][];
}

/** Every chart has its numbers available as a table: for screen readers, keyboards and checking. */
export function ChartTable({ caption, columns, rows }: ChartTableProps) {
  return (
    <details className="group mt-3 text-sm">
      <summary className="w-fit cursor-pointer text-muted-foreground underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50">
        View as table
      </summary>
      <div className="mt-2 overflow-x-auto">
        <Table>
          <caption className="sr-only">{caption}</caption>
          <TableHeader>
            <TableRow>
              {columns.map((column, i) => (
                <TableHead key={column} className={i === 0 ? undefined : "text-right"}>
                  {column}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row, r) => (
              <TableRow key={r}>
                {row.map((cell, c) => (
                  <TableCell key={c} className={c === 0 ? undefined : "text-right tabular-nums"}>
                    {cell}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </details>
  );
}
