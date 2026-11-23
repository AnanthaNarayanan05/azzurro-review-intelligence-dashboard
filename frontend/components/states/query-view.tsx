"use client";

import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { ErrorState } from "@/components/states/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useHydrated } from "@/hooks/use-hydrated";

interface QueryViewProps<T> {
  query: UseQueryResult<T>;
  /** Shown while loading; defaults to a generic block. */
  skeleton?: ReactNode;
  errorTitle?: string;
  children: (data: T) => ReactNode;
}

/** One place for the three states every data view needs: loading, error (with retry) and data. */
export function QueryView<T>({ query, skeleton, errorTitle, children }: QueryViewProps<T>) {
  const hydrated = useHydrated();

  if (!hydrated || query.isPending) {
    // A disabled query (for example an invalid date range) is also "pending"; the page explains why.
    return <>{skeleton ?? <Skeleton className="h-40 w-full" />}</>;
  }
  if (query.isError) {
    return (
      <ErrorState
        title={errorTitle ?? "Could not load this data"}
        message={query.error.message}
        onRetry={() => void query.refetch()}
        retrying={query.isFetching}
      />
    );
  }
  return <>{children(query.data)}</>;
}
