import type { Metadata } from "next";
import { Suspense } from "react";

import { PropertiesView } from "@/components/dashboard/properties-view";
import { PageHeader } from "@/components/layout/page-header";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Properties" };

export default function PropertiesPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Properties" description="Each property's rating and a way into its detail." />
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <PropertiesView />
      </Suspense>
    </div>
  );
}
