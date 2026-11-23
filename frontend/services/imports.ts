import { apiFetch } from "@/services/api-client";
import type {
  CommitRequest,
  DataResponse,
  DemoStatus,
  ImportFieldSpec,
  ImportIssue,
  ImportPreview,
  ImportReport,
  IssueOutcome,
  ListResponse,
  PropertyValues,
  RemovedResult,
} from "@/types/api";

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export async function uploadForPreview(file: File): Promise<ImportPreview> {
  const form = new FormData(); // the browser sets the multipart boundary itself
  form.append("file", file);
  return (await apiFetch<DataResponse<ImportPreview>>("/api/imports/preview", { method: "POST", body: form })).data;
}

export async function rereadPreview(importId: number, sheet: string): Promise<ImportPreview> {
  const query = new URLSearchParams({ sheet });
  return (await apiFetch<DataResponse<ImportPreview>>(`/api/imports/${importId}/preview?${query}`)).data;
}

export async function getPropertyValues(
  importId: number,
  column: string,
  sheet: string | null,
): Promise<PropertyValues> {
  const query = new URLSearchParams({ column });
  if (sheet) query.set("sheet", sheet);
  return (await apiFetch<DataResponse<PropertyValues>>(`/api/imports/${importId}/property-values?${query}`)).data;
}

export async function commitImport(importId: number, request: CommitRequest): Promise<ImportReport> {
  return (await apiFetch<DataResponse<ImportReport>>(`/api/imports/${importId}/commit`, json("POST", request))).data;
}

export async function listImportFields(): Promise<ImportFieldSpec[]> {
  return (await apiFetch<DataResponse<ImportFieldSpec[]>>("/api/imports/fields")).data;
}

export async function listImports(page: number, pageSize = 10): Promise<ListResponse<ImportReport>> {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return apiFetch<ListResponse<ImportReport>>(`/api/imports?${query}`, { cache: "no-store" });
}

export async function listIssues(
  importId: number,
  params: { outcome?: IssueOutcome; page: number; pageSize?: number },
): Promise<ListResponse<ImportIssue>> {
  const query = new URLSearchParams({ page: String(params.page), page_size: String(params.pageSize ?? 15) });
  if (params.outcome) query.set("outcome", params.outcome);
  return apiFetch<ListResponse<ImportIssue>>(`/api/imports/${importId}/issues?${query}`, { cache: "no-store" });
}

export async function deleteImport(importId: number): Promise<RemovedResult> {
  return (await apiFetch<DataResponse<RemovedResult>>(`/api/imports/${importId}`, { method: "DELETE" })).data;
}

export async function getDemoStatus(): Promise<DemoStatus> {
  return (await apiFetch<DataResponse<DemoStatus>>("/api/demo", { cache: "no-store" })).data;
}

export async function loadDemoData(): Promise<ImportReport> {
  return (await apiFetch<DataResponse<ImportReport>>("/api/demo/load", { method: "POST" })).data;
}

export async function removeDemoData(): Promise<RemovedResult> {
  return (await apiFetch<DataResponse<RemovedResult>>("/api/demo", { method: "DELETE" })).data;
}
