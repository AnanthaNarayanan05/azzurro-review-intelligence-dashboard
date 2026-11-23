"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { toast } from "sonner";

import { ErrorState } from "@/components/states/error-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useHydrated } from "@/hooks/use-hydrated";
import { getAnalysisStatus, runAnalysis } from "@/services/analysis";
import type { AnalysisScope } from "@/types/api";

export const analysisQueryKey = ["analysis", "status"] as const;

/** The API sends UTC timestamps without a zone suffix; without one the browser would read them as local time. */
function asUtc(timestamp: string): Date {
  return new Date(/(Z|[+-]\d\d:?\d\d)$/.test(timestamp) ? timestamp : `${timestamp}Z`);
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border p-3">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-lg font-semibold tabular-nums">{value.toLocaleString()}</dd>
    </div>
  );
}

export function AnalysisCard() {
  const hydrated = useHydrated();
  const queryClient = useQueryClient();
  const status = useQuery({ queryKey: analysisQueryKey, queryFn: getAnalysisStatus });

  const run = useMutation({
    mutationFn: (scope: AnalysisScope) => runAnalysis(scope),
    onSuccess: (result) => {
      toast.success(`Analysed ${result.processed.toLocaleString()} reviews.`);
      void queryClient.invalidateQueries({ queryKey: ["analysis"] });
      void queryClient.invalidateQueries({ queryKey: ["analytics"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="size-4" aria-hidden /> Text analysis
        </CardTitle>
        <CardDescription>
          Sentiment and aspect mentions are worked out from review text when you import. Re-run it here if an analysis
          failed, or to re-score everything after a method change.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!hydrated || status.isPending ? (
          <Skeleton className="h-24 w-full" />
        ) : status.isError ? (
          <ErrorState title="Could not load analysis status" message={status.error.message} onRetry={() => status.refetch()} />
        ) : (
          <>
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              <Stat label="Reviews" value={status.data.total_reviews} />
              <Stat label="Analysed" value={status.data.analysed} />
              <Stat label="Waiting" value={status.data.pending} />
              <Stat label="No text" value={status.data.no_text} />
              <Stat label="Not English" value={status.data.non_english} />
            </dl>
            <p className="text-sm text-muted-foreground">
              Method: {status.data.engine}, aspect lexicon {status.data.lexicon_version}.{" "}
              {status.data.latest_run
                ? `Last run: ${asUtc(status.data.latest_run.started_at).toLocaleString()} (${status.data.latest_run.triggered_by}).`
                : "No analysis has run yet."}
            </p>
            <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {status.data.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() => run.mutate("pending")}
                disabled={run.isPending || status.data.pending === 0}
                title={status.data.pending === 0 ? "No reviews are waiting" : undefined}
              >
                {run.isPending && run.variables === "pending" ? "Analysing…" : `Analyse waiting reviews (${status.data.pending})`}
              </Button>
              <Button variant="outline" onClick={() => run.mutate("all")} disabled={run.isPending || status.data.total_reviews === 0}>
                {run.isPending && run.variables === "all" ? "Re-analysing…" : "Re-analyse all reviews"}
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
