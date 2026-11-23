import type { Metadata } from "next";
import { Suspense } from "react";

import { OverviewView } from "@/components/dashboard/overview-view";
import { PageHeader } from "@/components/layout/page-header";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Overview" };

export default function OverviewPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Overview"
        description="Guest satisfaction across the properties, calculated from imported reviews."
      />
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <OverviewView />
      </Suspense>
    </div>
  );
}
