import type { ApiErrorBody } from "@/types/api";

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

/** A failed API call, normalised from the backend's error envelope or from a network failure. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown[];
  /** Body returned with the error status, when the backend sent a non-error envelope (e.g. 503 health). */
  readonly body: unknown;

  constructor(status: number, code: string, message: string, details: unknown[] = [], body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.body = body;
  }
}

function isErrorEnvelope(value: unknown): value is { error: ApiErrorBody } {
  if (typeof value !== "object" || value === null || !("error" in value)) return false;
  const error = (value as { error: unknown }).error;
  return typeof error === "object" && error !== null && "code" in error && "message" in error;
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return undefined;
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

/** Fetch a backend endpoint and return its parsed JSON body, throwing `ApiError` on any failure. */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { Accept: "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "The analytics service could not be reached.");
  }

  const body = await readJson(response);

  if (!response.ok) {
    if (isErrorEnvelope(body)) {
      const { code, message, details } = body.error;
      throw new ApiError(response.status, code, message, details ?? [], body);
    }
    throw new ApiError(
      response.status,
      "HTTP_ERROR",
      `The analytics service responded with status ${response.status}.`,
      [],
      body,
    );
  }

  if (body === undefined) {
    throw new ApiError(response.status, "INVALID_RESPONSE", "The analytics service returned an unreadable response.");
  }
  return body as T;
}
