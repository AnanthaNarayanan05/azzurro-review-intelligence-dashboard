"use client";

import { useMutation } from "@tanstack/react-query";
import { FileSpreadsheet, Loader2, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";

import { ErrorState } from "@/components/states/error-state";
import { uploadForPreview } from "@/services/imports";
import type { ImportPreview } from "@/types/api";

const ACCEPTED = [".csv", ".xlsx"];
/** Matches the backend default (MAX_UPLOAD_MB). The server is the real authority. */
const SOFT_LIMIT_MB = 20;

export function UploadStep({ onPreview }: { onPreview: (preview: ImportPreview) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [clientError, setClientError] = useState<string | null>(null);

  const mutation = useMutation({ mutationFn: uploadForPreview, onSuccess: onPreview });

  function handleFile(file: File | undefined) {
    setClientError(null);
    if (!file) return;
    const lower = file.name.toLowerCase();
    if (!ACCEPTED.some((ext) => lower.endsWith(ext))) {
      setClientError("Only .csv and .xlsx files can be imported.");
      return;
    }
    if (file.size > SOFT_LIMIT_MB * 1024 * 1024) {
      setClientError(`This file is larger than ${SOFT_LIMIT_MB} MB. Split it into smaller files.`);
      return;
    }
    mutation.mutate(file);
  }

  const error = clientError ?? (mutation.isError ? mutation.error.message : null);

  return (
    <div className="space-y-4">
      <label
        htmlFor="import-file"
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          handleFile(event.dataTransfer.files[0]);
        }}
        className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-10 text-center transition-colors focus-within:ring-2 focus-within:ring-ring ${
          dragging ? "border-primary bg-primary/5" : "border-border hover:bg-muted/50"
        }`}
      >
        {mutation.isPending ? (
          <>
            <Loader2 className="size-8 animate-spin text-primary" aria-hidden />
            <span className="font-medium">Reading and checking the file…</span>
          </>
        ) : (
          <>
            <UploadCloud className="size-8 text-primary" aria-hidden />
            <span className="font-medium">Choose a file or drop it here</span>
            <span className="text-sm text-muted-foreground">
              CSV or Excel (.xlsx), up to {SOFT_LIMIT_MB} MB. Nothing is imported until you confirm.
            </span>
          </>
        )}
        <input
          ref={inputRef}
          id="import-file"
          type="file"
          accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          className="sr-only"
          disabled={mutation.isPending}
          onChange={(event) => {
            handleFile(event.target.files?.[0]);
            event.target.value = ""; // allow choosing the same file again after an error
          }}
        />
      </label>

      {error && <ErrorState title="This file can't be used" message={error} />}

      <div className="flex gap-3 rounded-md bg-muted/50 p-4 text-sm text-muted-foreground">
        <FileSpreadsheet className="mt-0.5 size-4 shrink-0" aria-hidden />
        <p>
          Use a review export you are allowed to use. This tool does not collect reviews from Booking.com
          automatically. Files are checked, previewed and mapped first, and the uploaded copy is deleted once the
          import finishes.
        </p>
      </div>
    </div>
  );
}
