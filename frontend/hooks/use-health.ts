"use client";

import { useQuery } from "@tanstack/react-query";

import { getHealth } from "@/services/system";

export const healthQueryKey = ["system", "health"] as const;

/** Backend health, re-checked every 30 seconds so the status indicator recovers on its own. */
export function useHealth() {
  return useQuery({
    queryKey: healthQueryKey,
    queryFn: getHealth,
    refetchInterval: 30_000,
  });
}
