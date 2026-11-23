import { ApiError, API_BASE_URL, apiFetch } from "@/services/api-client";
import type { DataResponse, Property } from "@/types/api";

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export async function listProperties(): Promise<Property[]> {
  return (await apiFetch<DataResponse<Property[]>>("/api/properties", { cache: "no-store" })).data;
}

export async function createProperty(input: { name: string; location?: string | null }): Promise<Property> {
  return (await apiFetch<DataResponse<Property>>("/api/properties", json("POST", input))).data;
}

export async function updateProperty(id: number, input: { is_active?: boolean }): Promise<Property> {
  return (await apiFetch<DataResponse<Property>>(`/api/properties/${id}`, json("PATCH", input))).data;
}

export async function addAlias(id: number, alias: string): Promise<Property> {
  return (await apiFetch<DataResponse<Property>>(`/api/properties/${id}/aliases`, json("POST", { alias }))).data;
}

/** DELETE returns 204 with no body, so it cannot go through `apiFetch` (which expects JSON). */
export async function deleteAlias(propertyId: number, aliasId: number): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/properties/${propertyId}/aliases/${aliasId}`, { method: "DELETE" });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "The analytics service could not be reached.");
  }
  if (!response.ok) {
    throw new ApiError(response.status, "HTTP_ERROR", "The alias could not be removed.");
  }
}
