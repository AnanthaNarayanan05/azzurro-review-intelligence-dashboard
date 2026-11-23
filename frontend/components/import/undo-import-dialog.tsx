"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Undo2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { deleteImport } from "@/services/imports";
import type { ImportReport } from "@/types/api";

interface UndoImportButtonProps {
  report: ImportReport;
  onUndone?: () => void;
}

/** Removes an import and every review it created, after an explicit confirmation. */
export function UndoImportButton({ report, onUndone }: UndoImportButtonProps) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => deleteImport(report.id),
    onSuccess: (result) => {
      toast.success(`Import undone: ${result.removed_reviews.toLocaleString()} reviews removed.`);
      void queryClient.invalidateQueries({ queryKey: ["imports"] });
      void queryClient.invalidateQueries({ queryKey: ["properties"] });
      void queryClient.invalidateQueries({ queryKey: ["demo"] });
      setOpen(false);
      onUndone?.();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <Undo2 aria-hidden /> Undo import
      </Button>
      <AlertDialog open={open} onOpenChange={setOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Undo this import?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes {report.imported_rows.toLocaleString()} reviews added from{" "}
              <strong>{report.filename}</strong>, along with this import&apos;s report. Reviews that were only
              updated by this import keep their new content. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={mutation.isPending}>Keep import</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={mutation.isPending}
              onClick={(event) => {
                event.preventDefault(); // keep the dialog open until the request finishes
                mutation.mutate();
              }}
            >
              {mutation.isPending ? "Removing…" : "Remove reviews"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
