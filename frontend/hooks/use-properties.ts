"use client";

import { useQuery } from "@tanstack/react-query";

import { listProperties } from "@/services/properties";

export const propertiesQueryKey = ["properties"] as const;

export function useProperties() {
  return useQuery({ queryKey: propertiesQueryKey, queryFn: listProperties });
}
