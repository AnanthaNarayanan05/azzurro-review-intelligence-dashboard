import { apiFetch } from "@/services/api-client";
import type { AnalysisRunResult, AnalysisScope, AnalysisStatus, DataResponse } from "@/types/api";

export async function getAnalysisStatus(): Promise<AnalysisStatus> {
  return (await apiFetch<DataResponse<AnalysisStatus>>("/api/analysis/status", { cache: "no-store" })).data;
}

export async function runAnalysis(scope: AnalysisScope): Promise<AnalysisRunResult> {
  return (
    await apiFetch<DataResponse<AnalysisRunResult>>("/api/analysis/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope }),
    })
  ).data;
}
