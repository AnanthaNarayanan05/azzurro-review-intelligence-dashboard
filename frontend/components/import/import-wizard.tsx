"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2 } from "lucide-react";
import { useState } from "react";

import { MappingStep } from "@/components/import/mapping-step";
import { DEFAULT_OPTIONS, OptionsStep, ratingScaleOf, type OptionsState } from "@/components/import/options-step";
import { ReportView } from "@/components/import/report-view";
import { UndoImportButton } from "@/components/import/undo-import-dialog";
import { UploadStep } from "@/components/import/upload-step";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { propertiesQueryKey } from "@/hooks/use-properties";
import { buildCommitRequest } from "@/lib/import-wizard";
import { commitImport, getPropertyValues, rereadPreview } from "@/services/imports";
import type { ImportPreview, ImportReport } from "@/types/api";

type Step = "upload" | "mapping" | "options" | "result";

const STEPS: { key: Step; label: string }[] = [
  { key: "upload", label: "Upload" },
  { key: "mapping", label: "Match columns" },
  { key: "options", label: "Properties and formats" },
  { key: "result", label: "Report" },
];

function mappingFromPreview(preview: ImportPreview): Record<string, string> {
  const mapping: Record<string, string> = {};
  for (const [field, column] of Object.entries(preview.suggested_mapping)) {
    if (column) mapping[field] = column;
  }
  return mapping;
}

function freshOptions(preview: ImportPreview): OptionsState {
  return { ...DEFAULT_OPTIONS, mode: preview.suggested_mapping.property ? "column" : "fixed" };
}

function Stepper({ current }: { current: Step }) {
  const currentIndex = STEPS.findIndex((step) => step.key === current);
  return (
    <ol className="flex flex-wrap gap-x-6 gap-y-2" aria-label="Import progress">
      {STEPS.map((step, index) => {
        const state = index < currentIndex ? "done" : index === currentIndex ? "current" : "todo";
        return (
          <li
            key={step.key}
            aria-current={state === "current" ? "step" : undefined}
            className={`flex items-center gap-2 text-sm ${state === "todo" ? "text-muted-foreground" : "font-medium"}`}
          >
            <span
              className={`flex size-6 items-center justify-center rounded-full border text-xs ${
                state === "current"
                  ? "border-primary bg-primary text-primary-foreground"
                  : state === "done"
                    ? "border-primary text-primary"
                    : ""
              }`}
            >
              {state === "done" ? <CheckCircle2 className="size-4" aria-hidden /> : index + 1}
            </span>
            {step.label}
          </li>
        );
      })}
    </ol>
  );
}

export function ImportWizard() {
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>("upload");
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [options, setOptions] = useState<OptionsState>(DEFAULT_OPTIONS);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [sheetError, setSheetError] = useState<string | null>(null);

  const propertyColumn = mapping.property;
  const valuesQuery = useQuery({
    queryKey: ["imports", preview?.import_id, "property-values", propertyColumn, preview?.sheet],
    queryFn: () => getPropertyValues(preview!.import_id, propertyColumn, preview!.sheet),
    enabled: step === "options" && options.mode === "column" && Boolean(preview && propertyColumn),
  });

  const sheetMutation = useMutation({
    mutationFn: (sheet: string) => rereadPreview(preview!.import_id, sheet),
    onSuccess: (next) => {
      setSheetError(null);
      setPreview(next);
      setMapping(mappingFromPreview(next));
      setOptions(freshOptions(next));
    },
    onError: (error: Error) => setSheetError(error.message),
  });

  const commitMutation = useMutation({
    mutationFn: () =>
      commitImport(
        preview!.import_id,
        buildCommitRequest({
          mapping,
          mode: options.mode,
          fixedPropertyId: options.fixedPropertyId,
          values: valuesQuery.data?.values ?? [],
          choices: options.choices,
          ratingScaleMax: ratingScaleOf(options),
          dateFormat: options.dateFormat,
          sourceName: options.isSynthetic ? "synthetic-demo" : options.sourceName,
          isSynthetic: options.isSynthetic,
          sheet: preview!.sheet,
        }),
      ),
    onSuccess: (result) => {
      setConfirmOpen(false);
      setReport(result);
      setStep("result");
      void queryClient.invalidateQueries({ queryKey: ["imports"] });
      void queryClient.invalidateQueries({ queryKey: propertiesQueryKey });
      void queryClient.invalidateQueries({ queryKey: ["demo"] });
      void queryClient.invalidateQueries({ queryKey: ["analysis"] });
      void queryClient.invalidateQueries({ queryKey: ["analytics"] });
    },
    onError: () => setConfirmOpen(false), // the message is shown in the form
  });

  function reset() {
    setStep("upload");
    setPreview(null);
    setMapping({});
    setOptions(DEFAULT_OPTIONS);
    setReport(null);
    setSheetError(null);
    commitMutation.reset();
  }

  function handlePreview(next: ImportPreview) {
    setPreview(next);
    setMapping(mappingFromPreview(next));
    setOptions(freshOptions(next));
    setStep("mapping");
  }

  return (
    <Card>
      <CardHeader className="gap-4">
        <CardTitle className="sr-only">Import reviews</CardTitle>
        <Stepper current={step} />
      </CardHeader>
      <CardContent>
        {step === "upload" && <UploadStep onPreview={handlePreview} />}

        {step === "mapping" && preview && (
          <MappingStep
            preview={preview}
            mapping={mapping}
            onMappingChange={(field, column) =>
              setMapping((current) => {
                const next = { ...current };
                if (column) next[field] = column;
                else delete next[field];
                return next;
              })
            }
            onSheetChange={(sheet) => sheetMutation.mutate(sheet)}
            sheetLoading={sheetMutation.isPending}
            sheetError={sheetError}
            onBack={reset}
            onNext={() => setStep("options")}
          />
        )}

        {step === "options" && preview && (
          <>
            <OptionsStep
              preview={preview}
              mapping={mapping}
              options={options}
              onChange={(patch) => setOptions((current) => ({ ...current, ...patch }))}
              valuesQuery={valuesQuery}
              onBack={() => setStep("mapping")}
              onSubmit={() => setConfirmOpen(true)}
              submitting={commitMutation.isPending}
              submitError={commitMutation.isError ? commitMutation.error.message : null}
            />
            <AlertDialog open={confirmOpen} onOpenChange={(open) => !commitMutation.isPending && setConfirmOpen(open)}>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Import {preview.total_rows.toLocaleString()} rows?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Valid reviews from <strong>{preview.filename}</strong> will be added
                    {options.isSynthetic ? " and marked as synthetic demo data" : ""}. Duplicates are skipped and
                    problem rows are reported, never silently dropped. You can undo the whole import afterwards.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel disabled={commitMutation.isPending}>Cancel</AlertDialogCancel>
                  <Button onClick={() => commitMutation.mutate()} disabled={commitMutation.isPending}>
                    {commitMutation.isPending ? "Importing, please wait…" : "Import reviews"}
                  </Button>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </>
        )}

        {step === "result" && report && (
          <div className="space-y-6">
            <ReportView report={report} />
            <div className="flex flex-wrap gap-3">
              <Button onClick={reset}>Import another file</Button>
              {report.status === "completed" && <UndoImportButton report={report} onUndone={reset} />}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
