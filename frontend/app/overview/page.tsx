import type { Metadata } from "next";
import { LayoutDashboard } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/states/empty-state";
import { SystemStatusCard } from "@/components/system/system-status-card";

export const metadata: Metadata = { title: "Overview" };

export default function OverviewPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Overview"
        description="Portfolio-level guest satisfaction across all properties."
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <EmptyState
            icon={LayoutDashboard}
            title="Executive overview not built yet"
            description={
              <>
                KPIs, sentiment, trends and aspect analysis will appear here once review import
                (roadmap phase 3) and the analytics engine (phase 4) are in place. No figures are
                shown until they can be calculated from imported reviews.
              </>
            }
          />
        </div>
        <SystemStatusCard />
      </div>
    </div>
  );
}
