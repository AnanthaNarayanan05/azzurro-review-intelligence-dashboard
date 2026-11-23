/**
 * Types mirroring the backend API contract (backend/app/schemas).
 * Keep in sync with docs/API_SPECIFICATION.md.
 */

export interface DataResponse<T> {
  data: T;
}

export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface ListResponse<T> {
  data: T[];
  meta: PageMeta;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details: unknown[];
}

export interface HealthStatus {
  status: "ok" | "degraded";
  version: string;
  environment: string;
  database: "ok" | "unavailable";
  database_backend: string;
  sentiment_engine: string;
  llm_enabled: boolean;
}
