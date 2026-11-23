import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";

import { TooltipProvider } from "@/components/ui/tooltip";

/** Render with the same providers as the app, using a fresh, non-retrying query client. */
export function renderWithProviders(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <TooltipProvider>{ui}</TooltipProvider>
    </QueryClientProvider>,
  );
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Replace global fetch with a mock that returns the given responses (or throws) in order. */
export function mockFetch(...results: Array<Response | Error>) {
  const fn = vi.fn();
  for (const result of results) {
    if (result instanceof Error) fn.mockRejectedValueOnce(result);
    else fn.mockResolvedValueOnce(result);
  }
  vi.stubGlobal("fetch", fn);
  return fn;
}

export const healthyStatus = {
  status: "ok",
  version: "0.1.0",
  environment: "test",
  database: "ok",
  database_backend: "sqlite",
  sentiment_engine: "vader",
  llm_enabled: false,
} as const;
