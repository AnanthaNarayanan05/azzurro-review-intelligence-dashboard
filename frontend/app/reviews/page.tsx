import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { ReviewsView } from "@/components/reviews/reviews-view";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Reviews" };

export default function ReviewsPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Reviews"
        description="Search and filter individual reviews, and see exactly how each was analysed."
      />
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <ReviewsView />
      </Suspense>
    </div>
  );
}
