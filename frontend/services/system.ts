import { ApiError, apiFetch } from "@/services/api-client";
import type { DataResponse, HealthStatus } from "@/types/api";

/**
 * GET /api/health. A 503 still carries a health body (database unavailable), which is
 * returned as a "degraded" status rather than thrown, so the UI can explain what is wrong.
 */
export async function getHealth(): Promise<HealthStatus> {
  try {
    const response = await apiFetch<DataResponse<HealthStatus>>("/api/health", { cache: "no-store" });
    return response.data;
  } catch (error) {
    if (error instanceof ApiError && error.status === 503 && isHealthBody(error.body)) {
      return error.body.data;
    }
    throw error;
  }
}

function isHealthBody(value: unknown): value is DataResponse<HealthStatus> {
  return (
    typeof value === "object" &&
    value !== null &&
    "data" in value &&
    typeof (value as DataResponse<unknown>).data === "object" &&
    (value as DataResponse<HealthStatus>).data !== null &&
    "status" in (value as DataResponse<HealthStatus>).data
  );
}
