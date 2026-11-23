"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/states/error-state";
import { useHealth } from "@/hooks/use-health";
import { useHydrated } from "@/hooks/use-hydrated";
import { API_BASE_URL } from "@/services/api-client";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}

/** Live backend status: proves the frontend ↔ API ↔ database path works end to end. */
export function SystemStatusCard() {
  const { data, error, isPending, refetch, isFetching } = useHealth();
  const hydrated = useHydrated();

  return (
    <Card>
      <CardHeader>
        <CardTitle>System status</CardTitle>
        <CardDescription>Live response from the analytics API health check.</CardDescription>
      </CardHeader>
      <CardContent>
        {!hydrated || isPending ? (
          <div className="space-y-3" aria-label="Loading system status">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-4/6" />
          </div>
        ) : error ? (
          <ErrorState
            title="Analytics API unreachable"
            message={`${error.message} Expected at ${API_BASE_URL}. Check that the backend is running.`}
            onRetry={() => refetch()}
            retrying={isFetching}
          />
        ) : (
          <dl className="divide-y">
            <Row label="API" value={data.status === "ok" ? "Operational" : "Degraded"} />
            <Row label="Database" value={data.database === "ok" ? `Connected (${data.database_backend})` : "Unavailable"} />
            <Row label="Sentiment engine" value={data.sentiment_engine.toUpperCase()} />
            <Row label="LLM narrative layer" value={data.llm_enabled ? "Enabled" : "Disabled (template insights)"} />
            <Row label="Environment" value={data.environment} />
            <Row label="API version" value={data.version} />
          </dl>
        )}
      </CardContent>
    </Card>
  );
}
