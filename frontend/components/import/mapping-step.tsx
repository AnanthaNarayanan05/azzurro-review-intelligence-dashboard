"use client";

import { useQuery } from "@tanstack/react-query";
import { Info } from "lucide-react";

import { ErrorState } from "@/components/states/error-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useHydrated } from "@/hooks/use-hydrated";
import { mappingProblems, NONE } from "@/lib/import-wizard";
import { listImportFields } from "@/services/imports";
import type { ImportPreview } from "@/types/api";

interface MappingStepProps {
  preview: ImportPreview;
  mapping: Record<string, string>;
  onMappingChange: (field: string, column: string | null) => void;
  onSheetChange: (sheet: string) => void;
  sheetLoading: boolean;
  sheetError: string | null;
  onBack: () => void;
  onNext: () => void;
}

const REQUIRED_LABEL = { always: "Required", one_of: "Rating or text required", no: "Optional" } as const;

export function MappingStep(props: MappingStepProps) {
  const { preview, mapping, onMappingChange, onSheetChange, sheetLoading, sheetError, onBack, onNext } = props;
  const hydrated = useHydrated();
  const fields = useQuery({ queryKey: ["imports", "fields"], queryFn: listImportFields, staleTime: Infinity });
  const problems = mappingProblems(mapping);
  const sampleColumns = preview.columns.slice(0, 8);

  return (
    <div className="space-y-6">
      <div className="space-y-1 text-sm text-muted-foreground">
        <p>
          <span className="font-medium text-foreground">{preview.filename}</span> · {preview.total_rows.toLocaleString()}{" "}
          rows · {preview.columns.length} columns
          {preview.delimiter && ` · delimiter "${preview.delimiter === "\t" ? "tab" : preview.delimiter}"`}
          {preview.encoding && ` · ${preview.encoding}`}
        </p>
        <p>Match each field to the column in your file. We suggested the matches below; check them.</p>
      </div>

      {preview.already_imported_as !== null && (
        <Alert>
          <Info aria-hidden />
          <AlertTitle>This exact file was imported before</AlertTitle>
          <AlertDescription>
            Import #{preview.already_imported_as} used an identical file. Importing it again will not create
            duplicates: repeated reviews are skipped and reported.
          </AlertDescription>
        </Alert>
      )}

      {preview.sheets.length > 1 && (
        <div className="max-w-xs space-y-2">
          <Label htmlFor="sheet-select">Worksheet</Label>
          <Select value={preview.sheet ?? undefined} onValueChange={onSheetChange} disabled={sheetLoading}>
            <SelectTrigger id="sheet-select" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {preview.sheets.map((sheet) => (
                <SelectItem key={sheet} value={sheet}>
                  {sheet}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {sheetError && <p className="text-sm text-destructive">{sheetError}</p>}
        </div>
      )}

      {fields.isError ? (
        <ErrorState title="Could not load the field list" message={fields.error.message} onRetry={() => fields.refetch()} />
      ) : !hydrated || fields.isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <div className="grid gap-x-6 gap-y-4 md:grid-cols-2" role="group" aria-label="Column mapping">
          {fields.data.map((field) => (
            <div key={field.key} className="space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <Label htmlFor={`map-${field.key}`}>{field.label}</Label>
                <Badge variant={field.required === "no" ? "outline" : "secondary"}>
                  {REQUIRED_LABEL[field.required]}
                </Badge>
              </div>
              <Select
                value={mapping[field.key] ?? NONE}
                onValueChange={(value) => onMappingChange(field.key, value === NONE ? null : value)}
              >
                <SelectTrigger id={`map-${field.key}`} className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NONE}>Not in this file</SelectItem>
                  {preview.columns.map((column) => (
                    <SelectItem key={column} value={column}>
                      {column}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">{field.description}</p>
            </div>
          ))}
        </div>
      )}

      <div className="space-y-2">
        <h3 className="text-sm font-medium">First rows of your file</h3>
        <div className="overflow-x-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                {sampleColumns.map((column) => (
                  <TableHead key={column}>{column}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {preview.sample_rows.slice(0, 5).map((row, index) => (
                <TableRow key={index}>
                  {sampleColumns.map((column) => (
                    <TableCell key={column} className="max-w-64 truncate">
                      {row[column]}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        {preview.columns.length > sampleColumns.length && (
          <p className="text-xs text-muted-foreground">
            Showing the first {sampleColumns.length} of {preview.columns.length} columns.
          </p>
        )}
      </div>

      {problems.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-sm text-destructive" role="alert">
          {problems.map((problem) => (
            <li key={problem}>{problem}</li>
          ))}
        </ul>
      )}

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack}>
          Choose a different file
        </Button>
        <Button onClick={onNext} disabled={problems.length > 0 || sheetLoading}>
          Continue
        </Button>
      </div>
    </div>
  );
}
