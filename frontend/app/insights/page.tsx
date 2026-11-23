import type { Metadata } from "next";
import { Suspense } from "react";

import { InsightsView } from "@/components/insights/insights-view";
import { PageHeader } from "@/components/layout/page-header";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Insights" };

export default function InsightsPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Insights"
        description="Patterns in guest feedback, each backed by real review sentences you can open and check."
      />
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <InsightsView />
      </Suspense>
    </div>
  );
}
