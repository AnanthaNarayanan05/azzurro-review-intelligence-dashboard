import type { Metadata } from "next";
import { Suspense } from "react";

import { ComparisonView } from "@/components/dashboard/comparison-view";
import { PageHeader } from "@/components/layout/page-header";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Comparison" };

export default function ComparisonPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Comparison"
        description="Properties side by side. A winner is only named when the difference is unlikely to be chance."
      />
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <ComparisonView />
      </Suspense>
    </div>
  );
}
