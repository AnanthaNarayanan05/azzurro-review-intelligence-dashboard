import type { Metadata } from "next";

import { PageHeader } from "@/components/layout/page-header";
import { DemoDataCard } from "@/components/settings/demo-data-card";
import { PropertyManager } from "@/components/settings/property-manager";

export const metadata: Metadata = { title: "Settings" };

export default function SettingsPage() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader title="Settings" description="Manage properties and demo data." />
      <PropertyManager />
      <DemoDataCard />
    </div>
  );
}
