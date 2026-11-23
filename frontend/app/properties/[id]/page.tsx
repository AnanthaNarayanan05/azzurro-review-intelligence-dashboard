import type { Metadata } from "next";
import { Suspense } from "react";

import { PropertyDetailView } from "@/components/dashboard/property-detail-view";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Property" };

export default function PropertyPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <PropertyDetailView />
    </Suspense>
  );
}
