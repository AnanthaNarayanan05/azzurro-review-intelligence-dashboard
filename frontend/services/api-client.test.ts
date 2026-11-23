import { describe, expect, it } from "vitest";

import { ApiError, API_BASE_URL, apiFetch } from "@/services/api-client";
import { getHealth } from "@/services/system";
import { healthyStatus, jsonResponse, mockFetch } from "@/test/utils";

describe("apiFetch", () => {
  it("returns the parsed body and calls the configured base URL", async () => {
    const fetchMock = mockFetch(jsonResponse({ data: { ok: true } }));

    await expect(apiFetch("/api/thing")).resolves.toEqual({ data: { ok: true } });
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/api/thing`, expect.any(Object));
  });

  it("maps the backend error envelope to ApiError", async () => {
    mockFetch(jsonResponse({ error: { code: "NOT_FOUND", message: "Review not found", details: [] } }, 404));

    const error = await apiFetch("/api/reviews/9").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 404, code: "NOT_FOUND", message: "Review not found" });
  });

  it("reports network failures without leaking browser internals", async () => {
    mockFetch(new TypeError("Failed to fetch"));

    const error = await apiFetch("/api/health").catch((e: unknown) => e);
    expect(error).toMatchObject({ status: 0, code: "NETWORK_ERROR" });
  });

  it("handles non-JSON error responses such as proxy errors", async () => {
    mockFetch(new Response("<html>Bad gateway</html>", { status: 502 }));

    const error = await apiFetch("/api/health").catch((e: unknown) => e);
    expect(error).toMatchObject({ status: 502, code: "HTTP_ERROR" });
  });

  it("rejects successful responses with an unreadable body", async () => {
    mockFetch(new Response("not json", { status: 200 }));

    const error = await apiFetch("/api/health").catch((e: unknown) => e);
    expect(error).toMatchObject({ code: "INVALID_RESPONSE" });
  });
});

describe("getHealth", () => {
  it("returns the health payload", async () => {
    mockFetch(jsonResponse({ data: healthyStatus }));
    await expect(getHealth()).resolves.toEqual(healthyStatus);
  });

  it("returns the degraded payload carried by a 503 instead of throwing", async () => {
    const degraded = { ...healthyStatus, status: "degraded", database: "unavailable" };
    mockFetch(jsonResponse({ data: degraded }, 503));

    await expect(getHealth()).resolves.toEqual(degraded);
  });

  it("still throws for 503 responses without a health body", async () => {
    mockFetch(jsonResponse({ error: { code: "SERVICE_UNAVAILABLE", message: "Down", details: [] } }, 503));
    await expect(getHealth()).rejects.toBeInstanceOf(ApiError);
  });
});
